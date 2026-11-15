"""Surface-observer centre directions. No terrain or visibility decisions."""
from datetime import datetime
from typing import Literal

import spiceypy as spice

from app.models.analysis import Model, utc_datetime, Azimuth, Elevation
from app.science.geometry import FRAME, Observer, direction_angles, observer_position_km
from app.science.kernels import KernelSession


class Direction(Model):
    azimuth_deg: Azimuth | None
    elevation_deg: Elevation
    distance_km: float


class GeometryResult(Model):
    schema_version: Literal["1.0"] = "1.0"
    geometry_status: Literal["COMPUTED"] = "COMPUTED"
    science_ready: Literal[False] = False
    time_utc: str
    observer: Observer
    frame: Literal["MOON_ME_DE421"] = FRAME
    correction: Literal["NONE", "LT+S"]
    frame_evaluation: Literal["OBSERVER"] = "OBSERVER"
    sun: Direction
    earth: Direction
    kernel_ids: list[str]
    limitations: list[str]


def utc_to_et(session: KernelSession, utc: str | datetime) -> float:
    value = utc_datetime(utc)
    with session.call():
        return float(spice.str2et(value.strftime("%Y-%m-%d %H:%M:%S.%f UTC")))


def et_to_utc(session: KernelSession, et: float) -> str:
    import math
    if not math.isfinite(et):
        raise ValueError("ET must be finite")
    with session.call():
        return spice.et2utc(et,"ISOC",6) + "Z"


def calculate(session: KernelSession, observer: Observer, utc: str | datetime,
              correction: Literal["NONE", "LT+S"] = "NONE") -> GeometryResult:
    if correction not in ("NONE", "LT+S"):
        raise ValueError("Correction must be NONE or LT+S")
    et = utc_to_et(session, utc)
    position = observer_position_km(observer)
    with session.call():
        session.check_epoch(et)
        directions = []
        for target in ("SUN", "EARTH"):
            state, _ = spice.spkcpo(target,et,FRAME,"OBSERVER",correction,position,"MOON",FRAME)
            azimuth, elevation, distance = direction_angles(state[:3],observer)
            directions.append(Direction(azimuth_deg=azimuth,elevation_deg=elevation,distance_km=distance))
    limitations = ["No terrain, horizon dip, disk fraction, power or radio-link assessment.",
                   "Reference sphere 1737400 m; local Up is radial, not a terrain normal.",
                   "Geometric NONE is default; LT+S is optional reception light-time/stellar-aberration geometry.",
                   "Kernel integrity checks are not proof of source authenticity or independent scientific validation."]
    if observer.height_datum == "ASSUMED_REFERENCE_SPHERE":
        limitations.append("Surface elevation datum is an explicit assumption; not verified DEM elevation.")
    return GeometryResult(time_utc=et_to_utc(session,et),observer=observer,correction=correction,
                          sun=directions[0],earth=directions[1],
                          kernel_ids=[r["filename"]+":"+r["sha256"] for r in session.records],limitations=limitations)
