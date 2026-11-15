"""Analytic and numerical spherical checks; these fixtures are not NASA data."""
import math

import pytest

from app.data.coordinates import LunarGrid, surface_distance_m, validate_coordinates
from app.data.errors import DemError
from app.data.raster import open_local
from test_dem import raster

RADIUS_M = 1737400


@pytest.mark.parametrize("lat,lon", [(-90, 0), (90, 0), (91, 0), (0, -1), (0, 360), (float('nan'), 0), (0, float('inf'))])
def test_invalid_coordinate_codes(lat, lon):
    with pytest.raises(DemError) as exc: validate_coordinates(lat, lon)
    assert exc.value.code == "INVALID_COORDINATE"


@pytest.mark.parametrize("lat,lon", [(-89.468, 222.6), (-89.999, 359.9999), (-89, 0.0001), (-80, 0), (-60, 120)])
def test_projection_round_trip_and_east_longitude(tmp_path, lat, lon):
    with open_local(raster(tmp_path/"test.tif")) as ds:
        grid = LunarGrid(ds)
    point = validate_coordinates(lat, lon)
    xy = grid.geographic_to_xy(point)
    actual_lat, actual_lon = grid.xy_to_geographic(*xy)
    assert actual_lat == pytest.approx(lat, abs=1e-9)
    assert (actual_lon-lon+180) % 360 - 180 == pytest.approx(0, abs=1e-9)


def test_pixel_center_is_not_corner_and_inverse_index_is_zero_based(tmp_path):
    with open_local(raster(tmp_path/"test.tif")) as ds:
        grid = LunarGrid(ds)
    assert grid.pixel_center_xy(2, 3) == (-15, 25)
    assert (grid.transform.c+3*grid.transform.a, grid.transform.f+2*grid.transform.e) == (-20, 30)
    index = grid.xy_to_pixel(-15, 25)
    assert (index.row_zero_based, index.column_zero_based, index.inside_raster) == (2, 3, True)
    lat, lon = grid.pixel_center_geographic(2, 3)
    xy = grid.geographic_to_xy(validate_coordinates(lat, lon))
    assert xy == pytest.approx((-15, 25), abs=1e-4)
    assert not grid.xy_to_pixel(50, 0).inside_raster
    assert not grid.xy_to_pixel(0, -50).inside_raster
    with pytest.raises(DemError, match="OUT_OF_RASTER_BOUNDS"): grid.pixel_center_xy(-1, 0)
    with pytest.raises(DemError, match="INVALID_PIXEL_INDEX"): grid.pixel_center_xy(.5, 0)
    with pytest.raises(DemError, match="INVALID_COORDINATE"): grid.xy_to_geographic(0, 0)  # exact pole
    with pytest.raises(DemError, match="INVALID_COORDINATE"): grid.xy_to_pixel(float('inf'), 0)


def test_longitude_wrap_is_continuous_not_a_large_jump(tmp_path):
    with open_local(raster(tmp_path/"test.tif")) as ds: grid = LunarGrid(ds)
    first, second = validate_coordinates(-89.5, 359.9), validate_coordinates(-89.5, .1)
    a, b = grid.geographic_to_xy(first), grid.geographic_to_xy(second)
    assert a[0] < 0 < b[0]
    assert math.dist(a, b) < 100
    assert surface_distance_m(first, second, RADIUS_M) < 100


def test_distance_zero_symmetry_equator_antipode_and_explicit_metres():
    first = validate_coordinates(0, 0)
    one_degree = validate_coordinates(0, 1)
    assert surface_distance_m(first, first, RADIUS_M) == 0
    expected = RADIUS_M * math.pi / 180
    assert surface_distance_m(first, one_degree, RADIUS_M) == pytest.approx(expected, abs=1e-8)
    assert surface_distance_m(one_degree, first, RADIUS_M) == pytest.approx(expected, abs=1e-8)
    assert surface_distance_m(first, validate_coordinates(0, 180), RADIUS_M) == pytest.approx(math.pi*RADIUS_M)
    assert surface_distance_m(first, one_degree, RADIUS_M/1000) == pytest.approx(expected/1000)
    # The function never silently treats a kilometre-valued radius as metres*1000.


def test_distance_near_pole_wrap_and_very_short_arc():
    first, second = validate_coordinates(-89.9, 0), validate_coordinates(-89.9, 90)
    expected = RADIUS_M * math.acos(math.sin(math.radians(-89.9))**2)
    assert surface_distance_m(first, second, RADIUS_M) == pytest.approx(expected, abs=1e-5)
    wrap = surface_distance_m(validate_coordinates(0, 359.9), validate_coordinates(0, .1), RADIUS_M)
    assert wrap == pytest.approx(RADIUS_M * math.radians(.2), abs=1e-7)
    short = surface_distance_m(validate_coordinates(0, 0), validate_coordinates(0, 1e-7), RADIUS_M)
    assert short == pytest.approx(RADIUS_M * math.radians(1e-7), rel=1e-8)


def test_projection_scale_is_not_surface_distance(tmp_path):
    with open_local(raster(tmp_path/"test.tif")) as ds: grid = LunarGrid(ds)
    first, second = validate_coordinates(-60, 0), validate_coordinates(-60, 1)
    planar = math.dist(grid.geographic_to_xy(first), grid.geographic_to_xy(second))
    geodesic = surface_distance_m(first, second, RADIUS_M)
    assert planar > geodesic * 1.05


@pytest.mark.parametrize("radius", [0, -1, float('nan'), float('inf')])
def test_invalid_distance_radius(radius):
    point = validate_coordinates(0, 0)
    with pytest.raises(DemError, match="INVALID_REFERENCE_RADIUS"): surface_distance_m(point, point, radius)


@pytest.mark.parametrize("crs", [None, "EPSG:3031", "EPSG:4326"])
def test_grid_never_infers_earth_or_missing_crs(tmp_path, crs):
    with open_local(raster(tmp_path/"test.tif", crs=crs)) as ds:
        with pytest.raises(DemError, match="UNSUPPORTED_CRS"): LunarGrid(ds)
