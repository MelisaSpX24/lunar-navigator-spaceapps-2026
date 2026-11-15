"""Prepare an observer input with DEM evidence; performs no SPICE calculation."""
from typing import Literal

from app.data.dem_models import DemSample
from app.data.errors import DemError
from app.models.analysis import Model
from app.science.geometry import Observer


class ObserverPreparation(Model):
    observer: Observer
    dem_sample: DemSample
    frame_status: str
    reason_codes: list[str]
    science_ready: Literal[False] = False


def prepare_observer(sample: DemSample, device_height_m: float) -> ObserverPreparation:
    if sample.status != "VALID" or sample.surface_elevation_m is None:
        raise DemError("INVALID_DEM_OBSERVER", "No observer elevation can be prepared from a missing/outside cell")
    if sample.reference.frame_status == "INCOMPATIBLE":
        raise DemError("INCOMPATIBLE_FRAME", "Cannot prepare an observer from an incompatible reference")
    if not sample.reference.product_specific_frame_verified and not sample.prototype_registration_assumption_used:
        raise DemError("FRAME_NOT_PRODUCT_VERIFIED", "Explicit prototype registration assumption is required")
    observer = Observer(
        **sample.location.model_dump(), surface_elevation_m=sample.surface_elevation_m,
        device_height_m=device_height_m, reference_radius_m=sample.reference.declared_lunar_radius_m,
        height_datum="VERIFIED_REFERENCE_SPHERE" if sample.reference.product_specific_frame_verified
        else "ASSUMED_REFERENCE_SPHERE")
    return ObserverPreparation(observer=observer, dem_sample=sample,
                               frame_status=sample.reference.frame_status, reason_codes=sample.reason_codes)
