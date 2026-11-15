"""Mathematical source-grid transforms, not proof of SPICE registration."""
from dataclasses import dataclass
import math

from pydantic import ValidationError
from pyproj import Geod, Transformer

from app.data.errors import DemError
from app.data.raster import validate_lunar_crs
from app.models.analysis import Coordinates


def validate_coordinates(latitude_deg: float, longitude_deg_east: float) -> Coordinates:
    try:
        return Coordinates(latitude_deg=latitude_deg, longitude_deg_east=longitude_deg_east)
    except ValidationError as exc:
        raise DemError("INVALID_COORDINATE", "Planetocentric latitude must be in (-90,90); east longitude in [0,360)") from exc


def surface_distance_m(first: Coordinates, second: Coordinates, reference_radius_m: float) -> float:
    """Shortest geodesic on the explicitly supplied sphere; never planar metres."""
    if not math.isfinite(reference_radius_m) or reference_radius_m <= 0:
        raise DemError("INVALID_REFERENCE_RADIUS", "Supply a finite positive sphere radius in metres")
    geod = Geod(a=reference_radius_m, b=reference_radius_m)
    return float(geod.inv(first.longitude_deg_east, first.latitude_deg,
                          second.longitude_deg_east, second.latitude_deg)[2])


@dataclass(frozen=True)
class PixelIndex:
    row_zero_based: int
    column_zero_based: int
    inside_raster: bool


class LunarGrid:
    """Uses the actual dataset CRS/affine. Geographic tuples are in SOURCE CRS.

    These mathematical functions never assert product-specific frame alignment.
    Exact poles are rejected consistently with the existing observer convention.
    """
    def __init__(self, ds):
        try:
            self.crs = validate_lunar_crs(ds.crs)
        except ValueError as exc:
            raise DemError("UNSUPPORTED_CRS", str(exc)) from exc
        if any(abs(r-1737400) > 1e-6 for r in
               (self.crs.ellipsoid.semi_major_metre, self.crs.ellipsoid.semi_minor_metre)):
            raise DemError("UNSUPPORTED_CRS", "Only the declared 1737400 m lunar sphere is supported")
        if self.crs.prime_meridian.longitude != 0:
            raise DemError("UNSUPPORTED_CRS", "Nonzero prime meridian needs an explicit documented conversion")
        self.transform, self.width, self.height = ds.transform, ds.width, ds.height
        if (self.transform.b or self.transform.d or self.transform.a <= 0 or self.transform.e >= 0
                or not all(math.isfinite(v) for v in list(self.transform)[:6])):
            raise DemError("UNSUPPORTED_GRID", "Only finite north-up unrotated affine grids are supported")
        self.forward = Transformer.from_crs(self.crs.geodetic_crs, self.crs, always_xy=True)
        self.reverse = Transformer.from_crs(self.crs, self.crs.geodetic_crs, always_xy=True)

    def geographic_to_xy(self, location: Coordinates) -> tuple[float, float]:
        return self._finite_xy(*self.forward.transform(location.longitude_deg_east, location.latitude_deg))

    @staticmethod
    def _finite_xy(x_m, y_m):
        if not all(math.isfinite(v) for v in (x_m, y_m)):
            raise DemError("INVALID_COORDINATE", "Projected X/Y must be finite metres")
        return x_m, y_m

    def xy_to_geographic(self, x_m: float, y_m: float) -> tuple[float, float]:
        x_m, y_m = self._finite_xy(x_m, y_m)
        longitude, latitude = self.reverse.transform(x_m, y_m)
        if not all(math.isfinite(v) for v in (latitude, longitude)):
            raise DemError("INVALID_COORDINATE", "Inverse projection did not produce finite coordinates")
        longitude %= 360
        if longitude >= 360: longitude = 0.0  # floating-point wrap next to zero
        point = validate_coordinates(latitude, longitude)
        return point.latitude_deg, point.longitude_deg_east

    def xy_to_pixel(self, x_m: float, y_m: float) -> PixelIndex:
        x_m, y_m = self._finite_xy(x_m, y_m)
        inverse = ~self.transform
        column = inverse.a*x_m + inverse.b*y_m + inverse.c
        row = inverse.d*x_m + inverse.e*y_m + inverse.f
        row, column = math.floor(row), math.floor(column)
        return PixelIndex(row, column, 0 <= row < self.height and 0 <= column < self.width)

    def pixel_center_xy(self, row_zero_based: int, column_zero_based: int) -> tuple[float, float]:
        if type(row_zero_based) is not int or type(column_zero_based) is not int:
            raise DemError("INVALID_PIXEL_INDEX", "Pixel indices must be zero-based integers")
        if not (0 <= row_zero_based < self.height and 0 <= column_zero_based < self.width):
            raise DemError("OUT_OF_RASTER_BOUNDS", "No pixel centre is available outside this raster")
        col, row = column_zero_based+.5, row_zero_based+.5
        return (self.transform.a*col + self.transform.b*row + self.transform.c,
                self.transform.d*col + self.transform.e*row + self.transform.f)

    def pixel_center_geographic(self, row_zero_based: int, column_zero_based: int) -> tuple[float, float]:
        return self.xy_to_geographic(*self.pixel_center_xy(row_zero_based, column_zero_based))
