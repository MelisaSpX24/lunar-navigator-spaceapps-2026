"""Backend-local temporal evidence. No shared API contract promotion."""

from datetime import datetime, timedelta
from typing import Literal
import math
from pydantic import Field, field_validator, model_validator
from app.models.analysis import Model, utc_datetime
from app.science.visibility_models import VisibilityRequest

Condition = Literal["MET", "NOT_MET", "UNKNOWN"]


class WindowSearchRequest(Model):
    visibility: VisibilityRequest
    start_utc: datetime
    duration_s: float = Field(gt=0, le=2678400)
    solar_fraction: float = Field(default=0.5, ge=0, le=1)
    earth_margin_deg: float = Field(default=0, ge=0, le=90)
    joint: bool = True
    step_s: float = Field(default=3600, ge=1, le=86400)
    midpoint_depth: int = Field(default=0, ge=0, le=4)
    event_resolution_s: float = Field(default=60, ge=0.001, le=3600)
    max_temporal_samples: int = Field(default=512, ge=2, le=4096)
    max_visibility_evaluations: int = Field(default=32, ge=0, le=256)
    max_new_rays: int = Field(default=5000, ge=0, le=50000)
    max_terrain_samples: int = Field(default=3000000, ge=0, le=20000000)
    max_refinements: int = Field(default=24, ge=0, le=256)
    _utc = field_validator("start_utc", mode="before")(utc_datetime)

    @model_validator(mode="after")
    def limits(self):
        try:
            self.start_utc + timedelta(seconds=self.duration_s)
        except OverflowError as e:
            raise ValueError("End UTC out of range") from e
        if math.ceil(self.duration_s / self.step_s) + 1 > self.max_temporal_samples:
            raise ValueError("Coarse grid exceeds temporal budget")
        if self.start_utc + timedelta(seconds=self.duration_s) <= self.start_utc:
            raise ValueError("Duration below datetime resolution")
        return self

    @property
    def end_utc(self):
        return self.start_utc + timedelta(seconds=self.duration_s)


class TemporalConditionSample(Model):
    time_utc: datetime
    sun: Condition = "UNKNOWN"
    earth: Condition = "UNKNOWN"
    joint: Condition | None = "UNKNOWN"
    bodies: dict = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    source_identity: str | None = None
    evaluation_seconds: float = 0
    evidence_status: Literal["SAMPLED_ESTIMATE"] = "SAMPLED_ESTIMATE"
    _utc = field_validator("time_utc", mode="before")(utc_datetime)


class TemporalSegment(Model):
    start_utc: datetime
    end_utc: datetime
    condition: Condition
    definition_id: str
    evidence_status: Literal["SAMPLED_ESTIMATE", "TEMPORAL_INTERVAL_UNRESOLVED"]
    temporal_resolution_s: float
    start_censored: bool = False
    end_censored: bool = False
    reason_codes: list[str] = Field(default_factory=list)
    _utc = field_validator("start_utc", "end_utc", mode="before")(utc_datetime)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_utc <= self.start_utc:
            raise ValueError("Require [start,end) with positive duration")
        return self


class EventBracket(Model):
    definition_id: str
    family: Literal["sun", "earth", "joint"]
    event_type: Literal["START", "LOSS"]
    left_utc: datetime
    right_utc: datetime
    left_condition: Condition
    right_condition: Condition
    width_s: float
    evaluation_count: int
    status: Literal["EVENT_BRACKETED", "EVENT_BRACKET_NOT_REFINED"]
    evidence_status: Literal["SAMPLED_ESTIMATE"] = "SAMPLED_ESTIMATE"
    _utc = field_validator("left_utc", "right_utc", mode="before")(utc_datetime)

    @model_validator(mode="after")
    def valid_bracket(self):
        width = (self.right_utc - self.left_utc).total_seconds()
        if width <= 0 or self.width_s != width:
            raise ValueError("Bracket width must match positive UTC interval")
        if (
            self.left_condition == "UNKNOWN"
            or self.right_condition == "UNKNOWN"
            or self.left_condition == self.right_condition
        ):
            raise ValueError("Bracket requires opposite known endpoint conditions")
        if self.event_type != ("START" if self.right_condition == "MET" else "LOSS"):
            raise ValueError("Event type disagrees with endpoint conditions")
        return self


class WindowMetrics(Model):
    estimated_duration_s: float
    estimated_longest_continuous_s: float
    estimated_interruption_s: float
    estimated_longest_interruption_s: float
    unknown_duration_s: float
    duration_lower_bound_s: float | None = None
    duration_upper_bound_s: float | None = None
    duration_evidence_status: Literal["SAMPLED_ESTIMATE"] = "SAMPLED_ESTIMATE"
    number_of_windows: int
    number_of_brackets: int
    temporal_resolution_s: float


class WindowSearchResult(Model):
    schema_version: str = "command-07-v1"
    request: WindowSearchRequest
    timeline: list[TemporalConditionSample]
    segments: dict[str, list[TemporalSegment]]
    sampled_windows: dict[str, list[TemporalSegment] | None]
    brackets: list[EventBracket]
    metrics: dict[str, WindowMetrics]
    next_events: dict
    source_evidence: dict
    execution_status: Literal["COMPLETED", "PARTIAL"]
    data_origin: str
    scientific_evidence_status: Literal["SAMPLED_ESTIMATE"] = "SAMPLED_ESTIMATE"
    science_ready: Literal[False] = False
    performance: dict
    limitations: list[str]
