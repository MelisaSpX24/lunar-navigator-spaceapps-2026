"""Version 1 draft contracts. No scientific computations are performed here."""

from datetime import datetime, timedelta
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


Nonnegative = Annotated[float, Field(ge=0)]
Fraction = Annotated[float, Field(ge=0, le=1)]
Azimuth = Annotated[float, Field(ge=0, lt=360)]
Elevation = Annotated[float, Field(ge=-90, le=90)]
Profile = Literal["SOLAR_POWERED_EXPERIMENT", "EARTH_DATA_TRANSMISSION",
                  "SHORT_SURFACE_OBSERVATION", "CUSTOM_OPERATION"]
DecisionStatus = Literal["MET", "NOT_MET", "INCOMPLETE"]


def utc_datetime(value: object) -> object:
    # Reject timestamps/numbers, naive strings and non-zero offsets explicitly.
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Use an ISO 8601 UTC datetime with Z or +00:00") from exc
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
        raise ValueError("Use an ISO 8601 UTC datetime with Z or +00:00")
    return value


class Coordinates(Model):
    latitude_deg: Annotated[float, Field(gt=-90, lt=90)]
    longitude_deg_east: Azimuth
    frame: Literal["MOON_ME_DE421"] = "MOON_ME_DE421"
    latitude_type: Literal["PLANETOCENTRIC"] = "PLANETOCENTRIC"


class CoordinateSite(Coordinates):
    kind: Literal["COORDINATES"]


class NamedSite(Model):
    kind: Literal["SITE_ID"]
    site_id: Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z0-9_-]+$")]


class Observer(Model):
    surface_elevation_mode: Literal["DEM"] = "DEM"
    solar_height_above_surface_m: Nonnegative = 1.0
    earth_height_above_surface_m: Nonnegative = 1.0


class TimeRange(Model):
    start_utc: datetime
    duration_s: Annotated[int, Field(gt=0, strict=True)]
    _utc = field_validator("start_utc", mode="before")(utc_datetime)

    @model_validator(mode="after")
    def representable_end(self) -> Self:
        try:
            self.start_utc + timedelta(seconds=self.duration_s)
        except OverflowError as exc:
            raise ValueError("Operation end is outside the supported datetime range") from exc
        return self


class Requirements(Model):
    min_solar_disk_visible_fraction: Fraction = 0.5
    min_sun_visible_s: Nonnegative | None = None
    max_dark_gap_s: Nonnegative | None = None
    min_earth_continuous_s: Nonnegative | None = None
    earth_clearance_margin_deg: Annotated[float, Field(ge=0, le=90)] = 0.0
    require_simultaneous: bool = False
    min_joint_continuous_s: Nonnegative | None = None

    @model_validator(mode="after")
    def simultaneous_consistency(self) -> Self:
        if self.min_joint_continuous_s is not None and not self.require_simultaneous:
            raise ValueError("min_joint_continuous_s requires require_simultaneous=true")
        return self


class Operation(Model):
    profile: Profile
    requirements: Requirements


class AnalysisOptions(Model):
    include_full_horizon: bool = True
    include_earth_disk_fraction: bool = True
    event_lookahead_s: Annotated[int, Field(ge=0, strict=True)] = 86400


class AnalysisRequest(Model):
    schema_version: Literal["1.0"] = "1.0"
    site: Annotated[CoordinateSite | NamedSite, Field(discriminator="kind")]
    observer: Observer = Field(default_factory=Observer)
    time: TimeRange
    operation: Operation
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)

    @model_validator(mode="after")
    def duration_consistency(self) -> Self:
        requirements = self.operation.requirements
        for name in ("min_sun_visible_s", "min_earth_continuous_s", "min_joint_continuous_s"):
            value = getattr(requirements, name)
            if value is not None and value > self.time.duration_s:
                raise ValueError(f"{name} cannot exceed duration_s")
        return self


class ResolvedSite(Coordinates):
    surface_elevation_m: float | None = None
    height_datum_id: str | None = None


class BodySample(Model):
    azimuth_deg: Azimuth | None = None
    elevation_deg: Elevation | None = None
    angular_radius_deg: Annotated[float, Field(gt=0, le=90)] | None = None
    horizon_id: str | None = None
    center_clearance_deg: float | None = None
    disk_visible_fraction: Fraction | None = None
    disk_state: Literal["FULL", "PARTIAL", "NONE", "UNKNOWN"] = "UNKNOWN"
    condition_met: bool | None = None


class TimeSample(Model):
    time_utc: datetime
    sun: BodySample
    earth: BodySample
    joint_condition_met: bool | None = None
    _utc = field_validator("time_utc", mode="before")(utc_datetime)


class HorizonPoint(Model):
    azimuth_deg: Azimuth
    elevation_deg: Elevation | None


class HorizonProfile(Model):
    id: str
    observer_height_m: Nonnegative
    range_m: Annotated[float, Field(gt=0)]
    points: list[HorizonPoint]
    coverage_complete: bool
    dem_source_ids: list[str]


class Window(Model):
    start_utc: datetime
    end_utc: datetime
    definition_id: str
    start_censored: bool = False
    end_censored: bool = False
    _utc = field_validator("start_utc", "end_utc", mode="before")(utc_datetime)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end_utc <= self.start_utc:
            raise ValueError("Window end must follow start; intervals are [start, end)")
        return self


class Windows(Model):
    # null = not calculated; [] = calculated with no windows.
    sun: list[Window] | None = None
    earth: list[Window] | None = None
    joint: list[Window] | None = None


class RuleResult(Model):
    code: str
    status: DecisionStatus
    required: float | bool | None = None
    actual: float | bool | None = None
    message: str


class Decision(Model):
    status: DecisionStatus = "INCOMPLETE"
    rules: list[RuleResult] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class ScoreComponent(Model):
    name: str
    raw_value: float
    normalized_value: Fraction
    weight: Fraction


class Score(Model):
    value: Annotated[float, Field(ge=0, le=100)] | None = None
    model_version: str | None = None
    components: list[ScoreComponent] | None = None


class DataQuality(Model):
    status: Literal["NOT_ASSESSED", "SUFFICIENT", "LIMITED", "INSUFFICIENT"] = "NOT_ASSESSED"
    coverage_complete: bool | None = None
    limitations: list[str] = Field(default_factory=list)


class Source(Model):
    id: str
    kind: Literal["DEM", "SPK", "PCK", "FK", "LSK", "REFERENCE"]
    product: str
    version: str
    url: str
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class AnalysisResult(Model):
    schema_version: Literal["1.0"] = "1.0"
    analysis_id: str
    execution_status: Literal["NOT_RUN", "RUNNING", "COMPLETED", "FAILED"]
    data_origin: Literal["PRECOMPUTED", "LIVE_COMPUTED", "TEST_FIXTURE"] | None = None
    request: AnalysisRequest
    resolved_site: ResolvedSite | None = None
    series: list[TimeSample] | None = None
    horizons: list[HorizonProfile] | None = None
    windows: Windows = Field(default_factory=Windows)
    decision: Decision = Field(default_factory=Decision)
    score: Score = Field(default_factory=Score)
    quality: DataQuality = Field(default_factory=DataQuality)
    sources: list[Source] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class HealthResponse(Model):
    status: Literal["ok"] = "ok"
    science_ready: Literal[False] = False
    dem_ready: Literal[False] = False
    kernels_ready: Literal[False] = False
    reason_codes: list[str] = Field(default_factory=lambda: ["SCIENCE_ENGINE_NOT_READY"])
