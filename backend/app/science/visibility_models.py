"""Backend-local visibility schemas; shared analysis contracts remain unchanged."""
from datetime import datetime
from typing import Literal
from pydantic import Field, field_validator
from app.models.analysis import Model, Fraction, utc_datetime
from app.science.horizon_models import HorizonRequest
from app.science.geometry import Observer
from app.science.astronomy import Direction


class VisibilityRequest(Model):
    terrain: HorizonRequest
    utc: datetime
    solar_height_above_surface_m: float = Field(default=1,ge=0,le=10000)
    earth_height_above_surface_m: float = Field(default=1,ge=0,le=10000)
    correction: Literal['NONE','LT+S']='NONE'
    disk_samples: Literal[64,256,1024]=64
    max_new_rays: int = Field(default=132,ge=0,le=2050)
    _utc=field_validator('utc',mode='before')(utc_datetime)


class BodyVisibility(Model):
    body: Literal['SUN','EARTH']
    utc: str
    observer: Observer
    direction: Direction
    angular_radius_deg: float
    radii_km: list[float]
    effective_radius_km: float
    radius_kernel: str
    center_horizon_deg: float | None
    center_clearance_deg: float | None
    state: Literal['FULL','PARTIAL','NONE','UNKNOWN']
    visible_fraction: Fraction | None
    known_visible_fraction: Fraction
    known_blocked_fraction: Fraction
    unknown_fraction: Fraction
    visible_fraction_lower_bound: Fraction
    visible_fraction_upper_bound: Fraction
    horizon_ids: list[str]
    sampling_method: Literal['ANTIPODAL_EQUAL_PROJECTED_AREA']='ANTIPODAL_EQUAL_PROJECTED_AREA'
    disk_sample_count: int
    performance: dict
    reason_codes: list[str]


class VisibilityResult(Model):
    schema_version: Literal['1.0']='1.0'
    request: VisibilityRequest
    sun: BodyVisibility
    earth: BodyVisibility
    sources: dict
    kernel_ids: list[str]
    frame: Literal['MOON_ME_DE421']='MOON_ME_DE421'
    execution_status: Literal['COMPLETED']='COMPLETED'
    science_ready: Literal[False]=False
    scientific_evidence_status: Literal['SAMPLED_MODEL_ONLY']='SAMPLED_MODEL_ONLY'
    data_origin: str
    limitations: list[str]
    performance: dict


class VisibilitySeries(Model):
    samples: list[VisibilityResult]
    step_seconds: int
    performance: dict
    science_ready: Literal[False]=False
    limitations: list[str]
