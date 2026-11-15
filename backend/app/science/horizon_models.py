"""Backend-local sampled terrain horizons; no shared API or visibility changes."""
import math
from typing import Literal, Self
from pydantic import Field, model_validator, computed_field
from app.models.analysis import Model, Coordinates
from app.data.fusion import TerrainPolicy, TerrainSample

class Sampling(Model):
    start_m: float = Field(default=5, ge=0.1, le=1000)
    resolution_factor: float = Field(default=2, ge=0.25, le=16)
    min_step_m: float = Field(default=1, ge=0.1, le=100)
    max_step_m: float = Field(default=320, ge=1, le=1000)
    @model_validator(mode='after')
    def ordered(self)->Self:
        if self.min_step_m>self.max_step_m: raise ValueError('Inverted sampling limits')
        return self

class HorizonRequest(Model):
    location: Coordinates
    device_height_m: float = Field(default=1, ge=0, le=10000)
    policy: TerrainPolicy = Field(default_factory=TerrainPolicy)
    preferred_resolution_m: float = Field(default=5, gt=0)
    mode: Literal['FULL_HORIZON','SECTOR_HORIZON','RAYS'] = 'FULL_HORIZON'
    azimuth_step_deg: float = Field(default=5, ge=0.1, le=180)
    sector_start_deg: float = Field(default=0, ge=0, lt=360)
    sector_end_deg: float = Field(default=30, ge=0, lt=360)
    azimuths_deg: list[float] = Field(default_factory=list, max_length=3600)
    max_range_m: float = Field(default=150000, gt=0, le=150000)
    sampling: Sampling = Field(default_factory=Sampling)
    max_samples_per_ray: int = Field(default=100000, ge=1, le=500000)
    max_total_samples: int = Field(default=2000000, ge=1, le=5000000)
    @model_validator(mode='after')
    def check(self)->Self:
        if self.sampling.start_m>=self.max_range_m: raise ValueError('Start must precede end')
        if self.mode=='SECTOR_HORIZON' and self.sector_start_deg==self.sector_end_deg: raise ValueError('Empty sector; use FULL_HORIZON')
        if any(not math.isfinite(a) or not 0<=a<360 for a in self.azimuths_deg): raise ValueError('Azimuth outside [0,360)')
        if self.mode=='RAYS' and (not self.azimuths_deg or len(set(self.azimuths_deg))!=len(self.azimuths_deg)): raise ValueError('Unique rays required')
        return self
    def directions(self):
        if self.mode=='RAYS': return sorted(self.azimuths_deg)
        span=360 if self.mode=='FULL_HORIZON' else (self.sector_end_deg-self.sector_start_deg)%360
        start=0 if self.mode=='FULL_HORIZON' else self.sector_start_deg
        # Full range is half-open; sectors include both requested endpoints.
        values=[(start+i*self.azimuth_step_deg)%360 for i in range(math.ceil(span/self.azimuth_step_deg))]
        if self.mode=='SECTOR_HORIZON': values.append(self.sector_end_deg)
        return sorted(set(values))

class Obstruction(Model):
    distance_m: float
    location: Coordinates
    elevation_deg: float
    terrain: TerrainSample

class HorizonRay(Model):
    azimuth_deg: float
    coverage_status: Literal['COMPLETE_SAMPLED_RANGE','INCOMPLETE','UNKNOWN']
    horizon_elevation_deg: float | None = None
    partial_max_obstruction_deg: float | None = None
    obstruction: Obstruction | None = None
    requested_range_m: float
    sampled_range_m: float = 0
    valid_sample_count: int = 0
    missing_sample_count: int = 0
    outside_sample_count: int = 0
    conflict_sample_count: int = 0
    reported_conflict_count: int = 0
    read_error_count: int = 0
    source_transition_count: int = 0
    source_counts: dict[str,int] = Field(default_factory=dict)
    resolutions_m: list[float] = Field(default_factory=list)
    quality_status_counts: dict[str,int] = Field(default_factory=dict)
    reason_counts: dict[str,int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    range_convergence_status: Literal['RANGE_CONVERGENCE_NOT_ESTABLISHED'] = 'RANGE_CONVERGENCE_NOT_ESTABLISHED'
    @model_validator(mode='after')
    def honest(self)->Self:
        if self.coverage_status=='COMPLETE_SAMPLED_RANGE':
            if self.obstruction is None or self.horizon_elevation_deg is None or self.partial_max_obstruction_deg is not None or self.missing_sample_count or not self.valid_sample_count: raise ValueError('Invalid complete ray')
        elif self.coverage_status=='INCOMPLETE':
            if self.obstruction is None or self.horizon_elevation_deg is not None or self.partial_max_obstruction_deg is None or not self.valid_sample_count or not self.missing_sample_count: raise ValueError('Invalid partial ray')
        elif self.valid_sample_count or self.horizon_elevation_deg is not None or self.partial_max_obstruction_deg is not None or self.obstruction is not None: raise ValueError('UNKNOWN cannot contain angles')
        return self
    @computed_field
    @property
    def unknown_fraction(self) -> float | None:
        n=self.valid_sample_count+self.missing_sample_count
        return self.missing_sample_count/n if n else None

class HorizonResult(Model):
    request: HorizonRequest
    observer_surface: TerrainSample
    reference_radius_m: Literal[1737400] = 1737400
    frame: Literal['MOON_ME_DE421'] = 'MOON_ME_DE421'
    data_origin: Literal['REAL_NASA_PROTOTYPE','SYNTHETIC_TEST','MIXED_OR_UNVERIFIED']
    algorithm_version: Literal['spherical-point-rays-v1'] = 'spherical-point-rays-v1'
    identity: str
    sources: dict
    rays: list[HorizonRay]
    overall_status: Literal['COMPLETE_SAMPLED_RANGE','INCOMPLETE','UNKNOWN']
    limitations: list[str]
    science_ready: Literal[False] = False
    def horizon_at_azimuth(self, azimuth_deg):
        if not math.isfinite(azimuth_deg) or not 0<=azimuth_deg<=360: raise ValueError('Azimuth outside [0,360]')
        azimuth_deg%=360
        # Exact sampled directions only; no implied knowledge between rays.
        return next((r for r in self.rays if abs(r.azimuth_deg-azimuth_deg)<1e-9),None)
