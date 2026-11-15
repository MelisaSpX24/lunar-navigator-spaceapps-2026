"""Server-owned execution settings and bounded HTTP job payloads."""

from typing import Literal
from pydantic import Field, model_validator
from app.models.analysis import Model, AnalysisRequest
from app.science.operation_models import Policy
from app.science.temporal_optimizer_models import (
    TemporalOptimizationRequest,
    TemporalCandidate,
)
from app.science.window_models import WindowSearchRequest
from app.optimization.local_site_models import LocalSiteOptimizationRequest


class ResourcePolicy(Model):
    max_wall_time_s: float = Field(default=900, gt=0, le=3600)
    max_visibility_evaluations: int = Field(default=24, ge=1, le=256)
    max_horizon_rays: int = Field(default=5000, ge=0, le=50000)
    max_terrain_samples: int = Field(default=3000000, ge=1, le=20000000)
    max_cache_entries: int = Field(default=2048, ge=1, le=4096)


class AnalysisJobRequest(Model):
    analysis: AnalysisRequest
    evaluation_policy: Policy = "STRICT_EVIDENCE"
    registration: Literal["STRICT", "PROTOTYPE"] = "STRICT"
    step_s: int = Field(default=3600, ge=600, le=3600)
    disk_samples: Literal[64, 256] = 64
    resources: ResourcePolicy = Field(default_factory=ResourcePolicy)
    resume_from: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")


class TemporalJobRequest(Model):
    screening_strategy: Literal["EXACT_ONLY", "HORIZON_GRID"] = "EXACT_ONLY"
    grid_spacing_deg: Literal[1.0, 0.5] = 1.0
    optimization: TemporalOptimizationRequest
    max_candidate_evaluations: int = Field(default=4, ge=1, le=31)
    resources: ResourcePolicy = Field(default_factory=ResourcePolicy)
    resume_from: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")


class LocalJobRequest(Model):
    optimization: LocalSiteOptimizationRequest
    resources: ResourcePolicy = Field(default_factory=ResourcePolicy)
    resume_from: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")

    @model_validator(mode="after")
    def matching(self):
        from datetime import timedelta

        o = self.optimization
        TemporalOptimizationRequest(
            baseline_analysis=o.baseline_analysis,
            window_template=o.window_template,
            search_start_utc=o.baseline_analysis.time.start_utc,
            search_end_utc=o.baseline_analysis.time.start_utc
            + timedelta(seconds=o.baseline_analysis.time.duration_s),
        )
        if o.baseline_analysis.site.kind != "COORDINATES":
            raise ValueError("Resolved coordinates required")
        return self


class TemporalBatchResult(Model):
    schema_version: Literal["command-10-temporal-batch-v2"] = (
        "command-10-temporal-batch-v2"
    )
    request: TemporalOptimizationRequest
    baseline: TemporalCandidate
    candidates: list[TemporalCandidate]
    comparisons: list[dict]
    recommendations: list[dict]
    discovery: dict = Field(default_factory=dict)
    screening: dict = Field(default_factory=dict)
    pipeline_seconds: float | None = None
    generated_alternatives: int
    detailed_evaluated_including_baseline: int = 0
    scientifically_incomplete_including_baseline: int = 0
    not_evaluated_alternatives: int = 0
    detailed_completed_including_baseline: int
    search_status: str
    seconds: float
    resources: dict
    new_resources: dict = Field(default_factory=dict)
    checkpoint_resources: dict = Field(default_factory=dict)
    checkpoint_reused: int
    science_ready: Literal[False] = False
    limitations: list[str]
    scientific_window_template: WindowSearchRequest
    data_origin: Literal["LIVE_COMPUTED", "PRECOMPUTED"] | None = None
