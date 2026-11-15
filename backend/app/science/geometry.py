"""Spherical reference-surface geometry, independent of terrain and SPICE."""
import numpy as np
import math
from pydantic import model_validator
from typing import Literal, Self

from app.models.analysis import Coordinates, Model, Nonnegative

FRAME = "MOON_ME_DE421"
REFERENCE_RADIUS_M = 1737400.0


class Observer(Coordinates):
    surface_elevation_m: float
    device_height_m: Nonnegative = 0
    height_datum: Literal["ASSUMED_REFERENCE_SPHERE", "VERIFIED_REFERENCE_SPHERE"] = "ASSUMED_REFERENCE_SPHERE"
    reference_radius_m: Literal[1737400.0] = REFERENCE_RADIUS_M

    @model_validator(mode="after")
    def positive_radius(self) -> Self:
        if (self.reference_radius_m + self.surface_elevation_m <= 0 or
            not math.isfinite(self.reference_radius_m + self.surface_elevation_m + self.device_height_m)):
            raise ValueError("Surface must be outside lunar centre")
        return self


def local_axes(observer: Observer) -> np.ndarray:
    lat, lon = np.deg2rad([observer.latitude_deg, observer.longitude_deg_east])
    # Rows transform body-fixed direction vectors to East, North, Up.
    return np.array([[-np.sin(lon), np.cos(lon), 0],
                     [-np.sin(lat)*np.cos(lon), -np.sin(lat)*np.sin(lon), np.cos(lat)],
                     [np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)]])


def observer_position_km(observer: Observer) -> np.ndarray:
    radius_km = (observer.reference_radius_m + observer.surface_elevation_m + observer.device_height_m)/1000
    return local_axes(observer)[2] * radius_km


def direction_angles(vector_km, observer: Observer):
    vector = np.asarray(vector_km, dtype=float)
    if vector.shape != (3,) or not np.isfinite(vector).all():
        raise ValueError("Expected a finite three-component direction vector")
    distance = float(np.linalg.norm(vector))
    if not np.isfinite(distance) or distance <= 0:
        raise ValueError("Direction distance must be finite and positive")
    east, north, up = local_axes(observer) @ (vector / distance)
    horizontal = float(np.hypot(east, north))
    # At zenith/nadir azimuth is undefined; do not invent north.
    azimuth = None if horizontal < 1e-14 else float(np.rad2deg(np.arctan2(east, north)) % 360)
    return azimuth, float(np.rad2deg(np.arctan2(up, horizontal))), distance
