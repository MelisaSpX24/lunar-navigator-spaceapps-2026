"""Narrow PDS3 adapter for the supplied CR1 float32 height product, not LOLA."""
from pathlib import Path
import re

from app.data.dem_models import DemReference
from app.data.errors import DemError
from app.data.manifest import sha256_file
from app.data.raster import open_local, validate_lunar_crs

LROC_STANDARD_SOURCE = "https://doi.org/10.3847/psj/ad54c6"
LROC_ARCHIVE_SOURCE = "https://lroc.im-ldi.com/data/"


def inspect_lroc_label(path, label_path) -> DemReference:
    """Reject unsupported/mismatched labels rather than guessing units or datum.

    This is intentionally NOT a general PDS parser. Hashes bind this declaration
    to supplied files; they do not authenticate a NASA download.
    """
    path, label_path = Path(path), Path(label_path)
    if label_path.stat().st_size > 128 * 1024:
        raise ValueError("PDS label exceeds bounded text size")
    text = label_path.read_text(encoding="ascii")

    def field(name):
        matches = re.findall(rf"^\s*{re.escape(name)}\s*=\s*([^\r\n]+)", text, re.MULTILINE)
        if len(matches) != 1:
            raise ValueError(f"Missing or ambiguous PDS field: {name}")
        return matches[0].strip().strip('"')

    expected = {"PDS_VERSION_ID": "PDS3", "PRODUCT_ID": "NAC_DTM_ESALL_CR1",
                "DATA_SET_ID": "LRO-L-LROC-5-RDR-V1.0", "TARGET_NAME": "MOON",
                "SAMPLE_TYPE": "PC_REAL", "SAMPLE_BITS": "32", "BANDS": "1",
                "MAP_PROJECTION_TYPE": "POLARSTEREOGRAPHIC",
                "PROJECTION_LATITUDE_TYPE": "PLANETOCENTRIC",
                "POSITIVE_LONGITUDE_DIRECTION": "EAST", "CENTER_LATITUDE": "-90"}
    for name, value in expected.items():
        if field(name) != value:
            raise ValueError(f"Unsupported LROC PDS {name}; expected {value}")
    for axis in ("A_AXIS_RADIUS", "B_AXIS_RADIUS", "C_AXIS_RADIUS"):
        if not re.fullmatch(r"1737\.4\s*<KM>", field(axis)):
            raise ValueError("LROC label reference sphere is not 1737400 metres")
    if not re.fullmatch(r"0(?:\.0)?\s*<DEG>", field("CENTER_LONGITUDE")):
        raise ValueError("Unsupported LROC central meridian")
    pointer = re.fullmatch(r'\("([^\"]+)",\s*(\d+)\s*<BYTES>\)', field("^IMAGE"))
    if not pointer or pointer[1] != path.name:
        raise ValueError("PDS IMAGE pointer does not identify the supplied raster")
    description = re.search(r'\bDESCRIPTION\s*=\s*"([^\"]*)"', text, re.DOTALL)
    description = " ".join(description[1].split()) if description else ""
    if "Height [m] equals DN." not in description:
        raise DemError("UNKNOWN_VERTICAL_UNIT", "Missing explicit LROC DN-to-metre height evidence")
    if "Vertical reference: Height above the sphere/ellipsoid (as defined by map axis)." not in description:
        raise DemError("UNKNOWN_VERTICAL_DATUM", "Missing explicit LROC vertical reference evidence")
    if "missing constant of -1e+32" not in description:
        raise ValueError("Unsupported or undocumented LROC missing constant")
    scale = re.fullmatch(r"([0-9.]+)\s*<METERS/PIXEL>", field("MAP_SCALE"))
    if not scale:
        raise ValueError("Missing explicit metre-per-pixel scale")
    with open_local(path) as ds:
        crs = validate_lunar_crs(ds.crs)
        params = {p.name: p.value for p in crs.coordinate_operation.params}
        origin = params.get("Latitude of standard parallel", params.get("Latitude of natural origin"))
        meridian = params.get("Longitude of origin", params.get("Longitude of natural origin"))
        if origin != -90 or meridian != 0 or any(params.get(k, 0) != 0 for k in ("False easting", "False northing")):
            raise ValueError("GeoTIFF projection conflicts with LROC label")
        if ds.count != 1 or ds.dtypes != ("float32",):
            raise ValueError("LROC label requires one float32 height band")
        if (ds.height, ds.width) != (int(field("LINES")), int(field("LINE_SAMPLES"))):
            raise ValueError("LROC label dimensions do not match raster")
        if any(abs(v-float(scale[1])) > 1e-9 for v in ds.res):
            raise ValueError("LROC label pixel scale does not match raster")
        if ds.scales != (1.0,) or ds.offsets != (0.0,):
            raise ValueError("LROC DN height requires identity scale/offset")
        if ds.nodata is None or abs(ds.nodata / -3.40282266e38 - 1) > 1e-7:
            raise ValueError("LROC NoData differs from supported label description")
    return DemReference(
        product_id=field("PRODUCT_ID"), product_version=field("PRODUCT_VERSION_ID"),
        family="LROC_STEREO_DTM", source_url=LROC_ARCHIVE_SOURCE,
        provider_organization=field("PRODUCER_INSTITUTE_NAME"), source_product_family="LRO-L-LROC-5-RDR-V1.0",
        declared_lunar_radius_m=1737400, vertical_unit="m", vertical_reference="HEIGHT_ABOVE_REFERENCE_SPHERE",
        raster_sha256=sha256_file(path), label_sha256=sha256_file(label_path),
        vertical_evidence="Supplied PDS3 IMAGE DESCRIPTION: Height [m] equals DN; height above map-axis sphere",
        source_frame_evidence="SUPPORTED_BY_LROC_STANDARD", frame_evidence_source=LROC_STANDARD_SOURCE,
        product_specific_frame_verified=False, missing_constants=[-1e32])
