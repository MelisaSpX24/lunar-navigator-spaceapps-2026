"""Bounded local GeoTIFF/COG windows. No implicit network or reprojection."""
from dataclasses import dataclass
import math
from pathlib import Path

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window, from_bounds, transform as window_transform

from app.data.manifest import Product, sha256_file


@dataclass(frozen=True)
class Limits:
    max_pixels: int = 1_000_000
    max_working_bytes: int = 64 * 1024 * 1024

    def __post_init__(self):
        if self.max_pixels <= 0 or self.max_working_bytes <= 0:
            raise ValueError("Resource budgets must be positive")


def validate_lunar_crs(crs) -> CRS:
    if crs is None:
        raise ValueError("CRS is missing; lunar projection cannot be inferred")
    parsed = CRS.from_user_input(crs)
    operation = parsed.coordinate_operation
    params = {p.name: p.value for p in operation.params} if operation else {}
    method = operation.method_name if operation else ""
    south_polar = ((method == "Polar Stereographic (variant A)" and params.get("Latitude of natural origin") == -90)
                   or (method == "Polar Stereographic (variant B)" and params.get("Latitude of standard parallel", 0) < 0))
    if not parsed.is_projected or not south_polar:
        raise ValueError("Only explicit south polar stereographic lunar CRS is supported")
    if abs(parsed.ellipsoid.semi_major_metre - 1737400) > 1 or abs(parsed.ellipsoid.semi_minor_metre - 1737400) > 1:
        raise ValueError("Expected spherical lunar reference radius 1737400 m; do not assume Earth EPSG")
    if any(abs(axis.unit_conversion_factor - 1) > 1e-9 for axis in parsed.axis_info):
        raise ValueError("Projected coordinates must be in metres")
    return parsed


def open_local(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    ds = rasterio.open(path)
    if ds.driver != "GTiff":
        ds.close()
        raise ValueError("Only GeoTIFF/COG is supported")
    return ds


def check_layer(ds, product: Product):
    validate_lunar_crs(ds.crs)
    if product.frame != "MOON_ME_DE421":
        raise ValueError("Explicit MOON_ME_DE421 provenance is required")
    expected = {"ELEVATION": "m", "SLOPE": "deg", "HEIGHT_ERROR": "m",
                "SLOPE_ERROR": "deg", "EFFECTIVE_RESOLUTION": "m", "COUNT": "count"}
    if expected.get(product.kind) != product.units:
        raise ValueError("Unknown or inconsistent layer units")
    if ds.count != 1 or np.dtype(ds.dtypes[0]).kind not in "fiu":
        raise ValueError("Expected one numeric raster band")
    if ds.scales != (1.0,) or ds.offsets != (0.0,):
        raise ValueError("Scaled/offset rasters need an explicitly implemented conversion")
    unit = ds.units[0]
    aliases = {"m": {"m", "metre", "meter"}, "deg": {"deg", "degree", "degrees"}, "count": {"count", "1"}}
    if unit and unit not in aliases[product.units]:
        raise ValueError("Raster unit conflicts with product declaration")


def metadata(path):
    with open_local(path) as ds:
        return {"width": ds.width, "height": ds.height, "resolution": list(ds.res),
                "transform": list(ds.transform)[:6], "bounds": list(ds.bounds),
                "crs_wkt": ds.crs.to_wkt() if ds.crs else None,
                "dtype": ds.dtypes[0], "units": ds.units[0],
                "nodata": float(ds.nodata) if ds.nodata is not None and math.isfinite(ds.nodata) else None,
                "nodata_nonfinite": ds.nodata is not None and not math.isfinite(ds.nodata),
                "block_shapes": [list(v) for v in ds.block_shapes], "driver": ds.driver}


def validate_window(ds, window: Window, limits: Limits):
    values = (window.col_off, window.row_off, window.width, window.height)
    if any(not math.isfinite(v) or v != int(v) for v in values):
        raise ValueError("Window must use finite integer pixel offsets and dimensions")
    if window.width <= 0 or window.height <= 0 or window.col_off < 0 or window.row_off < 0:
        raise ValueError("Window is empty or outside the raster")
    if window.col_off + window.width > ds.width or window.row_off + window.height > ds.height:
        raise ValueError("Window exceeds raster coverage; no silent clipping")
    pixels = int(window.width * window.height)
    estimate = pixels * 32  # conservative array/mask/statistics working estimate; GDAL cache is separate
    if pixels > limits.max_pixels or estimate > limits.max_working_bytes:
        raise ValueError("Window exceeds configured pixel/memory budget")
    # A small window in a huge strip can still decode a huge block.
    block_pixels = max(h * w for h, w in ds.block_shapes)
    if block_pixels * np.dtype(ds.dtypes[0]).itemsize > limits.max_working_bytes:
        raise ValueError("Raster block exceeds decode budget; use tiled COG or re-tile locally")


def read_window(path, product: Product, window: Window, limits: Limits = Limits()):
    with rasterio.Env(GDAL_CACHEMAX=16 * 1024 * 1024):
        with open_local(path) as ds:
            check_layer(ds, product)
            return read_dataset_window(ds, product, window, limits)


def read_dataset_window(ds, product, window, limits):
    """Bounded read of an already metadata-checked open immutable dataset."""
    validate_window(ds, window, limits)
    raw = ds.read(1, window=window, masked=True)
    invalid = np.ma.getmaskarray(raw) | ~np.isfinite(raw.data)
    if product.kind != "ELEVATION":
        invalid |= raw.data < 0
    if product.kind == "SLOPE":
        invalid |= raw.data > 90
    data = np.ma.array(raw.data, mask=invalid)
    valid = data.compressed()
    report = {"product_id": product.id, "product_version": product.version,
              "kind": product.kind, "units": product.units,
              "window": [window.col_off, window.row_off, window.width, window.height],
              "valid_pixels": int(valid.size), "invalid_fraction": float(invalid.mean()),
              "min": float(valid.min()) if valid.size else None,
              "max": float(valid.max()) if valid.size else None,
              "transform": list(window_transform(window, ds.transform))[:6],
              "unit_evidence": "RASTER_AND_MANIFEST" if ds.units[0] else "MANIFEST_ONLY",
              "science_ready": False}
    return data, report

def projected_window(path, x: float, y: float, radius_m: float) -> Window:
    if not all(math.isfinite(v) for v in (x, y, radius_m)) or radius_m <= 0:
        raise ValueError("Finite coordinates and positive radius required")
    with open_local(path) as ds:
        validate_lunar_crs(ds.crs)
        if ds.transform.b or ds.transform.d:
            raise ValueError("Rotated raster windows are not supported")
        w = from_bounds(x-radius_m, y-radius_m, x+radius_m, y+radius_m, ds.transform)
        left, top = math.floor(w.col_off), math.floor(w.row_off)
        return Window(left, top, math.ceil(w.col_off+w.width)-left, math.ceil(w.row_off+w.height)-top)


def coverage(path, product: Product, latitude: float, longitude: float, radii=(1000, 3000, 5000)):
    if not (-90 <= latitude <= 90 and 0 <= longitude < 360):
        raise ValueError("Invalid planetocentric latitude/east longitude")
    with open_local(path) as ds:
        check_layer(ds, product)
        crs = validate_lunar_crs(ds.crs)
        x, y = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True).transform(longitude, latitude)
        results = []
        for radius in radii:
            window = projected_window(path, x, y, radius)
            inside = (window.col_off >= 0 and window.row_off >= 0 and
                      window.col_off+window.width <= ds.width and window.row_off+window.height <= ds.height)
            results.append({"projected_radius_m": radius, "bounding_square_inside": inside,
                            "valid_data_coverage": "NOT_CHECKED", "window": list(window.flatten())})
        return {"x_m": x, "y_m": y, "frame_evidence": "MANIFEST_DECLARATION",
                "point_inside": bool(ds.bounds.left <= x < ds.bounds.right and ds.bounds.bottom < y <= ds.bounds.top),
                "areas": results, "science_ready": False,
                "limitation": "Projected square coverage only; not geodesic-circle coverage or valid-pixel proof."}


def aligned(paths):
    grids = []
    for path in paths:
        with open_local(path) as ds:
            validate_lunar_crs(ds.crs)
            grids.append((ds.crs, ds.transform, ds.width, ds.height))
    return bool(grids) and all(g == grids[0] for g in grids[1:])


def export_window(path, product, window, output, limits=Limits()):
    output = Path(output)
    sidecar = output.with_suffix(output.suffix + ".json")
    if output.exists() or sidecar.exists() or output.resolve() == Path(path).resolve():
        raise ValueError("Refusing to overwrite data or provenance")
    data, report = read_window(path, product, window, limits)
    with open_local(path) as ds:
        profile = {"driver": "GTiff", "height": int(window.height), "width": int(window.width),
                   "count": 1, "dtype": data.dtype, "crs": ds.crs,
                   "transform": window_transform(window, ds.transform)}
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(output, "w", **profile) as dest:
            dest.write(data.filled(0), 1)
            dest.write_mask((~np.ma.getmaskarray(data)).astype("uint8") * 255)
            dest.set_band_unit(1, product.units)
    import json
    report.update({"source": product.model_dump(), "source_file_sha256": sha256_file(Path(path)),
                   "derived_file_sha256": sha256_file(output), "data_origin": "DERIVED_LOCAL_RASTER"})
    sidecar.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report
