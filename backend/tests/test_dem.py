"""Generated fixtures are TEST ONLY; genuine file integrations are opt-in below."""
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
import pytest
from pydantic import ValidationError
from pyproj import CRS, Transformer
import rasterio
from rasterio.transform import from_origin
from rasterio.windows import Window

from app.data.dem import CoverageLimits, open_dem
from app.data.dem_models import DemReference, RayCoverageEvidence
from app.data.manifest import sha256_file
from app.data.raster import Limits
from app.models.analysis import Coordinates

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from data_pipeline.lroc import inspect_lroc_label

LUNAR = "+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400 +units=m +no_defs"
MISSING = -1e32


def raster(path, data=None, **options):
    if data is None:
        data = np.full((10, 10), 12.5, dtype="float32")
    profile = dict(driver="GTiff", width=data.shape[1], height=data.shape[0], count=1,
                   dtype=data.dtype, crs=LUNAR, transform=from_origin(-50, 50, 10, 10), nodata=-9999)
    profile.update(options)
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data, 1)
    return path


def reference(path, **changes):
    values = dict(product_id="SYNTHETIC_ONLY", product_version="test-1", family="SYNTHETIC_TEST_FIXTURE",
                  source_url="synthetic:test", raster_sha256=sha256_file(path),
                  vertical_evidence="Synthetic metre fixture; not NASA data",
                  declared_lunar_radius_m=1737400, vertical_unit="m", vertical_reference="HEIGHT_ABOVE_REFERENCE_SPHERE",
                  source_frame_evidence="TEST_FIXTURE", frame_evidence_source="synthetic:test",
                  missing_constants=[MISSING])
    values.update(changes)
    return DemReference(**values)


def location(x=5, y=-5):
    crs = CRS.from_user_input(LUNAR)
    lon, lat = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True).transform(x, y)
    return Coordinates(latitude_deg=lat, longitude_deg_east=lon % 360)


def sample(dem, loc=None):
    return dem.sample(loc or location(), allow_unverified_registration=True)


def disk(dem, loc=None, radius=20, **kwargs):
    return dem.coverage(loc or location(), radius, allow_unverified_registration=True, **kwargs)


def test_containing_cell_coordinates_units_negative_height_and_opt_in(tmp_path):
    data = np.full((10, 10), 99, dtype="float32")
    data[5, 5] = -12.5
    path = raster(tmp_path/"test.tif", data)
    with open_dem(path, reference(path)) as dem:
        with pytest.raises(ValueError, match="opt-in"):
            dem.sample(location())
        with pytest.raises(ValueError, match="opt-in"):
            dem.coverage(location(), 20)
        result = sample(dem)
    assert result.row_zero_based == result.column_zero_based == 5
    # PROJ inverse/forward round trip within metres of the pole loses micrometres.
    assert result.x_m == pytest.approx(5, abs=1e-4) and result.y_m == pytest.approx(-5, abs=1e-4)
    assert result.surface_elevation_m == -12.5  # below reference sphere is valid
    assert result.reference.vertical_unit == "m"
    assert result.prototype_registration_assumption_used and not result.science_ready
    assert result.sampling_method == "CONTAINING_CELL_NO_INTERPOLATION"


@pytest.mark.parametrize("value", [-9999, np.nan, np.inf, -np.inf, MISSING])
def test_missing_never_becomes_zero_or_interpolated_height(tmp_path, value):
    data = np.ones((10, 10), dtype="float32")
    data[5, 5] = value
    path = raster(tmp_path/"test.tif", data)
    with open_dem(path, reference(path)) as dem:
        result = sample(dem)
    assert result.status == "NODATA" and result.surface_elevation_m is None
    json.dumps(result.model_dump(mode="json"), allow_nan=False)


def test_outside_zero_and_half_open_pixel_edges(tmp_path):
    path = raster(tmp_path/"test.tif", np.zeros((10, 10), dtype="float32"))
    with open_dem(path, reference(path)) as dem:
        assert sample(dem).surface_elevation_m == 0  # genuine zero is not missing
        assert sample(dem, location(100, 100)).status == "OUTSIDE_RASTER"
        # Test exact projected boundaries without round-trip rounding ambiguity.
        class Fixed:
            def __init__(self, xy): self.xy = xy
            def transform(self, *args): return self.xy
        for xy, expected in [((-50, 50), "VALID"), ((50, 0), "OUTSIDE_RASTER"),
                             ((0, -50), "OUTSIDE_RASTER")]:
            dem.forward = Fixed(xy)
            assert sample(dem).status == expected


def test_changed_file_cannot_reuse_evidence(tmp_path):
    path = raster(tmp_path/"test.tif")
    ref = reference(path)
    with path.open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="SHA-256"):
        with open_dem(path, ref): pass


def test_south_polar_projection_matches_analytic_spherical_metres(tmp_path):
    path = raster(tmp_path/"test.tif")
    point = Coordinates(latitude_deg=-89.468, longitude_deg_east=222.6)
    rho = 2 * 1737400 * math.tan(math.pi/4 + math.radians(point.latitude_deg)/2)
    expected_x = rho * math.sin(math.radians(point.longitude_deg_east))
    expected_y = rho * math.cos(math.radians(point.longitude_deg_east))
    with open_dem(path, reference(path)) as dem:
        result = sample(dem, point)
    assert result.x_m == pytest.approx(expected_x, abs=1e-7)
    assert result.y_m == pytest.approx(expected_y, abs=1e-7)
    assert result.status == "OUTSIDE_RASTER"


@pytest.mark.parametrize("kind", ["uint8", "scale", "unit", "rotation", "radius", "prime_meridian"])
def test_unsupported_height_representations_rejected(tmp_path, kind):
    dtype = "uint8" if kind == "uint8" else "float32"
    crs = LUNAR.replace("1737400", "1737400.5") if kind == "radius" else LUNAR
    if kind == "prime_meridian": crs += " +pm=10"
    path = raster(tmp_path/"test.tif", np.ones((10, 10), dtype=dtype),
                  nodata=0 if kind == "uint8" else -9999, crs=crs)
    with rasterio.open(path, "r+") as ds:
        if kind == "scale": ds.scales = (2,)
        if kind == "unit": ds.set_band_unit(1, "feet")
        if kind == "rotation": ds.transform = rasterio.Affine(10, 1, -50, 0, -10, 50)
    with pytest.raises(ValueError):
        with open_dem(path, reference(path)): pass


def test_disk_counts_distinguish_complete_bounds_from_missing_data(tmp_path):
    data = np.ones((10, 10), dtype="float32")
    data[5, 5] = -9999
    path = raster(tmp_path/"test.tif", data)
    with open_dem(path, reference(path)) as dem:
        result = disk(dem)
    assert result.status == "BOUNDS_COMPLETE_DATA_PARTIAL"
    assert result.disk_pixel_centres == result.inside_raster
    assert result.valid_height_pixels == result.inside_raster - 1
    assert result.fractions()["raster_bounds_fraction"] == 1
    assert result.fractions()["valid_height_fraction"] < 1
    assert result.fractions()["outside_raster_fraction"] == 0


def test_disk_dense_independent_geodesic_oracle_and_streaming(tmp_path, monkeypatch):
    data = np.arange(100, dtype="float32").reshape(10, 10)
    data[3, 3] = -9999
    data[5, 5] = MISSING
    path = raster(tmp_path/"test.tif", data)
    loc = location(35, -35)
    # Independent destination-point construction of each known cell centre.
    # Chosen 10 m grid and 25 m radius; enumerate more than the full disk.
    with open_dem(path, reference(path)) as dem:
        original = dem.ds
        reads = []
        class Tracked:
            def __getattr__(self, name): return getattr(original, name)
            def read(self, *a, **kw):
                w = kw["window"]
                assert w.width * w.height <= 24
                reads.append(w)
                return original.read(*a, **kw)
        dem.ds = Tracked()
        actual = disk(dem, loc, 25, budget=CoverageLimits(chunk_pixels=24))
        total = inside = valid = 0
        for row in range(-5, 15):
            for col in range(-5, 15):
                x, y = -50+(col+.5)*10, 50-(row+.5)*10
                lon, lat = dem.reverse.transform(x, y)
                distance = dem.geod.inv(loc.longitude_deg_east, loc.latitude_deg, lon, lat)[2]
                if distance <= 25:
                    total += 1
                    if 0 <= row < 10 and 0 <= col < 10:
                        inside += 1
                        valid += int(data[row, col] != -9999 and data[row, col] != np.float32(MISSING))
    assert reads and len(reads) > 1
    assert (actual.disk_pixel_centres, actual.inside_raster, actual.valid_height_pixels) == (total, inside, valid)
    assert actual.status == "PARTIAL_RASTER_COVERAGE"


def test_all_invalid_and_all_outside_are_not_success(tmp_path):
    path = raster(tmp_path/"test.tif", np.full((10, 10), -9999, dtype="float32"))
    with open_dem(path, reference(path)) as dem:
        missing = disk(dem)
        outside = disk(dem, location(500, 500))
    assert missing.status == outside.status == "NO_VALID_HEIGHT_DATA"
    assert missing.fractions()["valid_height_fraction"] == 0
    assert outside.inside_raster == 0
    assert outside.fractions()["valid_height_fraction_inside_raster"] is None
    for report in (missing, outside):
        f = report.fractions()
        assert f["valid_height_fraction"] + f["unknown_or_missing_fraction"] == pytest.approx(1)
        assert f["valid_height_fraction"] + f["internal_nodata_fraction"] + f["outside_raster_fraction"] == pytest.approx(1)
        assert f["raster_bounds_fraction"] + f["outside_raster_fraction"] == pytest.approx(1)


def test_complete_and_five_kilometre_statuses(tmp_path):
    path = raster(tmp_path/"test.tif")
    with open_dem(path, reference(path)) as dem:
        assert disk(dem).status == "COMPLETE_SAMPLED_DISK"
    # Coarser grid makes a 5 km partial disk cheap; no optimization is performed.
    path = raster(tmp_path/"coarse.tif", transform=from_origin(-500, 500, 100, 100))
    with open_dem(path, reference(path)) as dem:
        assert disk(dem, radius=5000).status == "COVERAGE_INSUFFICIENT_FOR_FULL_5KM"


@pytest.mark.parametrize("case", ["total", "memory", "decode", "radius", "zero", "north"])
def test_coverage_budgets_and_unsupported_domains_fail_before_large_reads(tmp_path, case):
    path = raster(tmp_path/"test.tif")
    limits = Limits(max_working_bytes=100 if case == "memory" else 64*1024*1024)
    with open_dem(path, reference(path), limits) as dem:
        with pytest.raises(ValueError):
            if case == "total": disk(dem, budget=CoverageLimits(max_total_pixels=1))
            if case == "memory": disk(dem)
            if case == "decode":
                dem.limits = Limits(max_working_bytes=1)
                sample(dem)
            if case == "radius": disk(dem, radius=5001)
            if case == "zero": disk(dem, radius=0)
            if case == "north": disk(dem, Coordinates(latitude_deg=1, longitude_deg_east=0))


def test_ray_evidence_preserves_partial_information_without_claiming_visibility():
    result = RayCoverageEvidence(azimuth_deg=90, requested_range_m=1000,
                                 coverage_status="INCOMPLETE", partial_max_obstruction_elevation_deg=2)
    assert result.partial_max_obstruction_elevation_deg == 2
    assert not result.unobstructed_visibility_confirmed
    with pytest.raises(ValidationError):
        RayCoverageEvidence(azimuth_deg=90, requested_range_m=1000, partial_max_obstruction_elevation_deg=2)
    with pytest.raises(ValidationError):
        RayCoverageEvidence(azimuth_deg=90, requested_range_m=1000, unobstructed_visibility_confirmed=True)


def test_evidence_cannot_promote_standard_to_product_verification_or_invent_error(tmp_path):
    path = raster(tmp_path/"test.tif")
    with pytest.raises(ValidationError): reference(path, product_specific_frame_verified=True)
    with pytest.raises(ValidationError): reference(path, absolute_vertical_error_m=2)
    with pytest.raises(ValidationError): reference(path, family="LROC_STEREO_DTM")


def labelled_fixture(tmp_path):
    path = raster(tmp_path/"NAC_DTM_ESALL_CR1.TIF", nodata=-3.40282266e38)
    label = tmp_path/"NAC_DTM_ESALL_CR1.LBL"
    label.write_text('''/* SYNTHETIC TEST LABEL; NOT NASA DATA */
PDS_VERSION_ID = PDS3
PRODUCT_ID = "NAC_DTM_ESALL_CR1"
PRODUCT_VERSION_ID = "synthetic-1"
PRODUCER_INSTITUTE_NAME = "SYNTHETIC TEST PRODUCER; NOT NASA"
DATA_SET_ID = "LRO-L-LROC-5-RDR-V1.0"
TARGET_NAME = "MOON"
SAMPLE_TYPE = PC_REAL
SAMPLE_BITS = 32
BANDS = 1
LINES = 10
LINE_SAMPLES = 10
MAP_PROJECTION_TYPE = "POLARSTEREOGRAPHIC"
PROJECTION_LATITUDE_TYPE = PLANETOCENTRIC
POSITIVE_LONGITUDE_DIRECTION = EAST
CENTER_LATITUDE = -90
CENTER_LONGITUDE = 0 <DEG>
A_AXIS_RADIUS = 1737.4 <KM>
B_AXIS_RADIUS = 1737.4 <KM>
C_AXIS_RADIUS = 1737.4 <KM>
MAP_SCALE = 10.0 <METERS/PIXEL>
^IMAGE = ("NAC_DTM_ESALL_CR1.TIF", 1000 <BYTES>)
DESCRIPTION = "Height [m] equals DN.
Vertical reference: Height above the sphere/ellipsoid (as defined by map axis).
The NoDATA value is -3.40282266e+038 with a missing constant of -1e+32."
END
''')
    return path, label


def test_label_evidence_and_null_accuracy(tmp_path):
    path, label = labelled_fixture(tmp_path)
    ref = inspect_lroc_label(path, label)
    assert ref.product_version == "synthetic-1"  # fixture, not genuine product validation
    assert ref.label_sha256 == sha256_file(label)
    assert ref.source_frame_evidence == "SUPPORTED_BY_LROC_STANDARD"
    assert not ref.product_specific_frame_verified
    assert ref.absolute_horizontal_error_m is ref.absolute_vertical_error_m is ref.relative_vertical_error_m is None


@pytest.mark.parametrize("old,new", [("Height [m] equals DN.", "DN display image"),
    ("Height above the sphere/ellipsoid", "Unknown datum"), ("1737.4 <KM>", "1738.0 <KM>"),
    ("SAMPLE_BITS = 32", "SAMPLE_BITS = 8"), ("LINES = 10", "LINES = 11"),
    ("MAP_SCALE = 10.0", "MAP_SCALE = 2.0"),
    ('^IMAGE = ("NAC_DTM_ESALL_CR1.TIF"', '^IMAGE = ("OTHER.TIF"')])
def test_bad_label_never_supplies_physical_height_evidence(tmp_path, old, new):
    path, label = labelled_fixture(tmp_path)
    label.write_text(label.read_text().replace(old, new))
    with pytest.raises(ValueError): inspect_lroc_label(path, label)


def test_cli_requires_registration_opt_in_and_never_overwrites(tmp_path, monkeypatch, capsys):
    from data_pipeline.dem_cli import main
    path, label = labelled_fixture(tmp_path)
    loc = location()
    argv = ["dem_cli", "sample", "--path", str(path), "--label", str(label),
            "--latitude", str(loc.latitude_deg), "--longitude", str(loc.longitude_deg_east)]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as error: main()
    assert error.value.code == 2
    capsys.readouterr()
    output = tmp_path/"result.json"
    monkeypatch.setattr(sys, "argv", argv+["--allow-unverified-registration", "--output", str(output)])
    main()
    result = json.loads(output.read_text())
    assert result["status"] == "VALID" and result["science_ready"] is False
    with pytest.raises(SystemExit): main()
    assert json.loads(output.read_text()) == result


def test_cli_coverage_serializes_missing_area_and_reference(tmp_path, monkeypatch, capsys):
    from data_pipeline.dem_cli import main
    path, label = labelled_fixture(tmp_path)
    loc = location()
    monkeypatch.setattr(sys, "argv", ["dem_cli", "coverage", "--path", str(path), "--label", str(label),
                                     "--latitude", str(loc.latitude_deg), "--longitude", str(loc.longitude_deg_east),
                                     "--radii-m", "20", "--allow-unverified-registration"])
    main()
    result = json.loads(capsys.readouterr().out)
    assert result["coverage"][0]["valid_height_fraction"] == 1
    assert result["coverage"][0]["reference"]["absolute_vertical_error_m"] is None
    assert result["coverage"][0]["prototype_registration_assumption_used"]
    assert not result["science_ready"]


def test_closure_record_keeps_prototype_gate_separate_from_science_readiness():
    record = json.loads((ROOT/"data_pipeline/evidence/command-03-5.json").read_text())
    assert record["gate_status"] == "PROTOTYPE_DATA_GATE_PASSED_WITH_LIMITATIONS"
    assert record["science_ready"] is False
    lroc = record["lroc"]
    assert lroc["source_frame_evidence"] == "SUPPORTED_BY_LROC_STANDARD"
    assert not lroc["product_specific_frame_verified"]
    assert lroc["absolute_horizontal_error_m"] is lroc["absolute_vertical_error_m"] is lroc["relative_vertical_error_m"] is None
    assert lroc["coverage"][0]["raster_bounds_fraction"] == 1
    assert lroc["coverage"][0]["valid_height_fraction"] < 1
    assert record["astronomy"]["horizons_comparison"] == "NOT_VERIFIED"


@pytest.fixture
def real_lroc():
    path, label = os.environ.get("NASA_LROC_CR1_DEM"), os.environ.get("NASA_LROC_CR1_LABEL")
    if not path or not label:
        pytest.skip("Genuine CR1 LROC DTM/LBL absent; real DEM validation NOT_RUN")
    assert sha256_file(Path(path)) == "fc57e2d4452bf2522ae7ed3a091e4f6dfc4eea6a989324edb06344689712a453"
    assert sha256_file(Path(label)) == "543f640b90e0b6613130fc2558c1858213e8d748524ffe4a656899750b594e7a"
    return path, inspect_lroc_label(path, label)


def test_real_lroc_cr1_height_and_reference(real_lroc):
    path, ref = real_lroc
    with open_dem(path, ref) as dem:
        result = sample(dem, Coordinates(latitude_deg=-89.468, longitude_deg_east=222.6))
        # Inverse mapping is a source-grid transform, not product frame proof.
        lat, lon = dem.grid.pixel_center_geographic(1167, 1230)
        centre = sample(dem, Coordinates(latitude_deg=lat, longitude_deg_east=lon))
        assert (centre.row_zero_based, centre.column_zero_based) == (1167, 1230)
        assert centre.surface_elevation_m == result.surface_elevation_m
        first_row = dem._read(Window(0, 0, dem.ds.width, 1))
        missing_column = int(np.flatnonzero(np.ma.getmaskarray(first_row)[0])[0])
        lat, lon = dem.grid.pixel_center_geographic(0, missing_column)
        missing = sample(dem, Coordinates(latitude_deg=lat, longitude_deg_east=lon))
        assert missing.status == "NODATA" and missing.surface_elevation_m is None
        lat, lon = dem.grid.xy_to_geographic(dem.ds.bounds.right+2, result.y_m)
        assert sample(dem, Coordinates(latitude_deg=lat, longitude_deg_east=lon)).status == "OUTSIDE_RASTER"
        from app.data.observer import prepare_observer
        prepared = prepare_observer(result, 1)
        assert prepared.frame_status == "SUPPORTED_BY_SOURCE_STANDARD"
        assert prepared.observer.device_height_m == 1 and not prepared.science_ready
    assert result.status == "VALID"
    assert (result.row_zero_based, result.column_zero_based) == (1167, 1230)
    assert result.surface_elevation_m == pytest.approx(1944.1400146484375, abs=1e-8)
    assert ref.vertical_reference == "HEIGHT_ABOVE_REFERENCE_SPHERE"
    assert ref.product_version == "v1.2" and ref.declared_lunar_radius_m == 1737400
    assert not ref.product_specific_frame_verified


def test_real_lroc_disk_coverage_matches_prior_streamed_validation(real_lroc):
    path, ref = real_lroc
    loc = Coordinates(latitude_deg=-89.468, longitude_deg_east=222.6)
    expected = [(1000, 1.0, .9871142617787182, "BOUNDS_COMPLETE_DATA_PARTIAL"),
                (3000, .8377058020678666, .8030026617897367, "PARTIAL_RASTER_COVERAGE"),
                (5000, .3182951682997161, .29848768544003823, "COVERAGE_INSUFFICIENT_FOR_FULL_5KM")]
    with open_dem(path, ref) as dem:
        for radius, bounds, valid, status in expected:
            report = disk(dem, loc, radius)
            assert report.status == status
            assert report.fractions()["raster_bounds_fraction"] == pytest.approx(bounds, abs=1e-8)
            assert report.fractions()["valid_height_fraction"] == pytest.approx(valid, abs=1e-8)
