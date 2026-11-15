"""Evidence-bound, local spherical DEM sampling and streamed coverage. No SPICE."""
from contextlib import contextmanager
from collections import OrderedDict
from dataclasses import dataclass
import math
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Geod
from rasterio.windows import Window, from_bounds

from app.data.dem_models import DemReference, DemSample, DiskCoverage
from app.data.coordinates import LunarGrid
from app.data.errors import DemError
from app.data.manifest import sha256_file
from app.data.raster import Limits, open_local, validate_window
from app.models.analysis import Coordinates


@dataclass(frozen=True)
class CoverageLimits:
    max_total_pixels: int = 30_000_000
    chunk_pixels: int = 131_072

    def __post_init__(self):
        if self.max_total_pixels <= 0 or self.chunk_pixels <= 0:
            raise ValueError("Coverage budgets must be positive")


@contextmanager
def open_dem(path, reference: DemReference, limits: Limits = Limits()):
    """Hash once per session. A caller-supplied declaration is not authentication."""
    if sha256_file(Path(path)) != reference.raster_sha256:
        raise DemError("SOURCE_HASH_MISMATCH", "DEM SHA-256 does not match its evidence record")
    with rasterio.Env(GDAL_CACHEMAX=16 * 1024 * 1024):
        try:
            dataset = open_local(path)
        except rasterio.errors.RasterioIOError as exc:
            raise DemError("INVALID_RASTER", str(exc)) from exc
        with dataset as ds:
            grid = LunarGrid(ds)
            if ds.count != 1 or ds.dtypes[0] not in ("float32", "float64"):
                raise DemError("UNSUPPORTED_HEIGHT_ENCODING", "This DEM adapter requires one floating-point height band")
            if ds.scales != (1.0,) or ds.offsets != (0.0,):
                raise DemError("UNSUPPORTED_HEIGHT_ENCODING", "Nonidentity height scale/offset is not implemented")
            if ds.units[0] and ds.units[0] not in ("m", "metre", "meter"):
                raise DemError("UNKNOWN_VERTICAL_UNIT", "Raster height unit conflicts with metre evidence")
            reader = DemReader(ds, reference, grid, limits)
            try:
                yield reader
            finally:
                for quality_ds in reader._quality_readers.values():
                    quality_ds.close()


class DemReader:
    def __init__(self, ds, reference, grid, limits):
        self.ds, self.reference, self.grid, self.limits = ds, reference, grid, limits
        self.crs = grid.crs
        self.forward, self.reverse = grid.forward, grid.reverse
        self.geod = Geod(a=reference.declared_lunar_radius_m, b=reference.declared_lunar_radius_m)
        self.auxiliary_file_hashes = {Path(p).name: sha256_file(Path(p)) for p in ds.files
                                     if Path(p).resolve() != Path(ds.name).resolve()}
        self._quality_readers = OrderedDict()  # at most eight open quality datasets
        self._quality_hashes = {}  # immutable originals; verify once per DEM session

    def _project(self, location: Coordinates, allow_unverified_registration: bool):
        # No undocumented frame offset is introduced. This assumption stays visible.
        if self.reference.frame_status == "INCOMPATIBLE":
            raise DemError("INCOMPATIBLE_FRAME", "An incompatible source cannot use the prototype registration assumption")
        if not self.reference.product_specific_frame_verified and not allow_unverified_registration:
            raise DemError("FRAME_NOT_PRODUCT_VERIFIED", "Unverified product registration requires explicit prototype opt-in")
        x, y = self.forward.transform(location.longitude_deg_east, location.latitude_deg)
        if not all(math.isfinite(v) for v in (x, y)):
            raise DemError("INVALID_COORDINATE", "Location is outside the supported projection")
        return x, y

    def _read(self, window):
        validate_window(self.ds, window, self.limits)
        a = self.ds.read(1, window=window, masked=True)
        invalid = np.ma.getmaskarray(a) | ~np.isfinite(a.data)
        for missing in self.reference.missing_constants:
            invalid |= a.data == np.asarray(missing, dtype=a.dtype)
        return np.ma.array(a.data, mask=invalid)

    def _limitations(self):
        result = list(self.reference.limitations)
        if not self.reference.product_specific_frame_verified:
            result.append("Source-grid mapping uses a prototype registration assumption; product-specific SPICE alignment is not verified.")
        return result

    def sample(self, location: Coordinates, *, allow_unverified_registration=False, quality_layers=None) -> DemSample:
        x, y = self._project(location, allow_unverified_registration)
        index = self.grid.xy_to_pixel(x, y)
        row, col, inside = index.row_zero_based, index.column_zero_based, index.inside_raster
        raw = height = None
        status = "OUTSIDE_RASTER"
        if inside:
            a = self._read(Window(col, row, 1, 1))
            raw = float(a.data[0, 0]) if math.isfinite(float(a.data[0, 0])) else None
            status = "NODATA" if a.mask[0, 0] else "VALID"
            if status == "VALID":
                height = raw
        reasons = [{"VALID": "VALID_ELEVATION", "NODATA": "INVALID_NODATA", "OUTSIDE_RASTER": "OUT_OF_RASTER_BOUNDS"}[status],
                   "QUALITY_NOT_ASSESSED"]
        if not self.reference.product_specific_frame_verified:
            reasons.append("FRAME_NOT_PRODUCT_VERIFIED")
        result = DemSample(location=location, product_id=self.reference.product_id,
                         raster_sha256=self.reference.raster_sha256, status=status,
                         x_m=x, y_m=y, row_zero_based=row, column_zero_based=col,
                         raw_value=raw, surface_elevation_m=height, reference=self.reference, frame_status=self.reference.frame_status,
                         resolution_m=self.ds.res, crs_wkt=self.crs.to_wkt(), reason_codes=reasons,
                         auxiliary_file_hashes=self.auxiliary_file_hashes,
                         limitations=self._limitations() + ["Containing-cell elevation only; no interpolation or accuracy gain."],
                         prototype_registration_assumption_used=not self.reference.product_specific_frame_verified)
        if quality_layers:
            from app.data.quality import sample_quality_layers
            result.quality = sample_quality_layers(self, result, quality_layers)
            result.reason_codes = [code for code in reasons if code != "QUALITY_NOT_ASSESSED"] + [result.quality.status]
        return result

    def read_elevation_window(self, window: Window):
        """Bounded masked source-grid samples and evidence; no frame promotion."""
        return self._read(window), {
            "window": list(window.flatten()), "reference": self.reference.model_dump(mode="json"),
            "resolution_m": list(self.ds.res), "crs_wkt": self.crs.to_wkt(),
            "auxiliary_file_hashes": self.auxiliary_file_hashes,
            "sampling_method": "SOURCE_GRID_NO_INTERPOLATION", "science_ready": False,
        }

    def coverage(self, location: Coordinates, radius_m: float, *,
                 allow_unverified_registration=False, budget: CoverageLimits = CoverageLimits()) -> DiskCoverage:
        x, y = self._project(location, allow_unverified_registration)
        if not math.isfinite(radius_m) or not 0 < radius_m <= 5000:
            raise ValueError("Coverage radius must be in (0, 5000] metres")
        theta_max = math.radians(90 + location.latitude_deg) + radius_m / self.reference.declared_lunar_radius_m
        if theta_max >= math.pi / 2:
            raise ValueError("Coverage disks must remain in the southern hemisphere")
        params = {p.name: p.value for p in self.crs.coordinate_operation.params}
        # Polar stereographic local scale <= k0 * sec(theta_max/2)^2 on this disk.
        # For variant B, k0 <= 1; variant A may specify a larger k0.
        k0 = max(1.0, params.get("Scale factor at natural origin", 1.0))
        bound = radius_m * k0 / math.cos(theta_max / 2) ** 2
        w = from_bounds(x-bound, y-bound, x+bound, y+bound, self.ds.transform)
        c0, r0 = math.floor(w.col_off)-1, math.floor(w.row_off)-1
        width = math.ceil(w.col_off+w.width)+1-c0
        height = math.ceil(w.row_off+w.height)+1-r0
        if width * height > budget.max_total_pixels:
            raise ValueError("Coverage exceeds total pixel budget")
        # Coordinates, distances, masks and projection arrays all contribute.
        chunk_pixels = min(budget.chunk_pixels, self.limits.max_pixels,
                           self.limits.max_working_bytes // 128)
        if width > chunk_pixels:
            raise ValueError("One coverage row exceeds working-memory/pixel budget")
        chunk_rows = max(1, chunk_pixels // width)
        disk_count = inside_count = valid_count = 0
        for start in range(r0, r0+height, chunk_rows):
            stop = min(start+chunk_rows, r0+height)
            rows, cols = np.meshgrid(np.arange(start, stop), np.arange(c0, c0+width), indexing="ij")
            xx = self.ds.transform.c + self.ds.transform.a * (cols+.5)
            yy = self.ds.transform.f + self.ds.transform.e * (rows+.5)
            lon, lat = self.reverse.transform(xx, yy)
            _, _, distance = self.geod.inv(np.full(lon.shape, location.longitude_deg_east),
                                          np.full(lat.shape, location.latitude_deg), lon, lat)
            disk = distance <= radius_m
            in_bounds = (rows >= 0) & (rows < self.ds.height) & (cols >= 0) & (cols < self.ds.width)
            disk_count += int(disk.sum())
            inside_count += int((disk & in_bounds).sum())
            left, right = max(c0, 0), min(c0+width, self.ds.width)
            top, bottom = max(start, 0), min(stop, self.ds.height)
            if left < right and top < bottom:
                a = self._read(Window(left, top, right-left, bottom-top))
                selection = disk[top-start:bottom-start, left-c0:right-c0]
                valid_count += int((selection & ~np.ma.getmaskarray(a)).sum())
        if disk_count == 0:
            raise ValueError("Disk has no pixel-centre samples; increase radius or use finer data")
        if valid_count == 0:
            status = "NO_VALID_HEIGHT_DATA"
        elif valid_count == disk_count:
            status = "COMPLETE_SAMPLED_DISK"
        elif inside_count == disk_count:
            status = "BOUNDS_COMPLETE_DATA_PARTIAL"
        elif radius_m == 5000:
            status = "COVERAGE_INSUFFICIENT_FOR_FULL_5KM"
        else:
            status = "PARTIAL_RASTER_COVERAGE"
        return DiskCoverage(location=location, product_id=self.reference.product_id, radius_m=radius_m,
                            disk_pixel_centres=disk_count, inside_raster=inside_count,
                            valid_height_pixels=valid_count, status=status, reference=self.reference, frame_status=self.reference.frame_status,
                            resolution_m=self.ds.res, crs_wkt=self.crs.to_wkt(),
                            auxiliary_file_hashes=self.auxiliary_file_hashes,
                            limitations=self._limitations() + ["Approximate unweighted pixel-centre area fractions; no quality-layer distribution assessed."],
                            prototype_registration_assumption_used=not self.reference.product_specific_frame_verified)
