"""Bounded same-site UTC search, separate discovery and scientific decisions."""

from datetime import datetime, timedelta
from typing import Literal
from pydantic import Field, field_validator, model_validator
from app.models.analysis import Model, AnalysisRequest, ResolvedSite, utc_datetime
from app.science.operation_models import Policy, OperationEvaluationResult
from app.science.window_models import WindowSearchRequest


class TemporalOptimizationRequest(Model):
    baseline_analysis: AnalysisRequest
    window_template: WindowSearchRequest
    selection_strategy: Literal["LEGACY", "COVERAGE_AWARE"] = "LEGACY"
    evaluation_policy: Policy = "STRICT_EVIDENCE"
    search_start_utc: datetime
    search_end_utc: datetime
    coarse_start_step_s: int = Field(default=21600, ge=1, le=86400)
    refinement_step_s: int = Field(default=3600, ge=1, le=86400)
    max_coarse_candidates: int = Field(default=64, ge=1, le=512)
    max_detailed_candidates: int = Field(default=3, ge=1, le=8)
    max_recommendations: int = Field(default=3, ge=1, le=3)
    max_window_evaluations: int = Field(default=24, ge=0, le=256)
    max_new_horizon_rays: int = Field(default=4000, ge=0, le=50000)
    max_terrain_samples: int = Field(default=3000000, ge=0, le=20000000)
    max_wall_time_s: float = Field(default=1200, gt=0, le=3600)
    max_cache_entries: int = Field(default=2048, ge=1, le=4096)
    resolved_site: ResolvedSite | None = None
    resolved_site_id: str | None = None
    _utc = field_validator("search_start_utc", "search_end_utc", mode="before")(
        utc_datetime
    )

    @model_validator(mode="after")
    def valid_range(self):
        if (
            self.search_end_utc - self.search_start_utc
        ).total_seconds() < self.baseline_analysis.time.duration_s:
            raise ValueError("Search interval shorter than operation")
        if (self.search_end_utc - self.search_start_utc).total_seconds() > 31 * 86400:
            raise ValueError("Search confined to 31 days")
        if (
            self.window_template.start_utc != self.baseline_analysis.time.start_utc
            or self.window_template.duration_s != self.baseline_analysis.time.duration_s
        ):
            raise ValueError("Baseline/template time mismatch")
        # Reuse the operation matching validator without inventing new geometry.
        from app.science.operation_models import OperationEvaluationRequest
        from app.science.operations import effective_requirements

        q = OperationEvaluationRequest(
            analysis=self.baseline_analysis,
            window_evidence_sha256="0" * 64,
            resolved_site=self.resolved_site,
            resolved_site_id=self.resolved_site_id,
        )
        r = effective_requirements(q)
        w = self.window_template
        v = w.visibility
        site = self.baseline_analysis.site
        if site.kind == "SITE_ID":
            if self.resolved_site is None or self.resolved_site_id != site.site_id:
                raise ValueError("Named site needs explicit resolution evidence")
            site = self.resolved_site
        if any(
            (
                site.latitude_deg != v.terrain.location.latitude_deg,
                site.longitude_deg_east != v.terrain.location.longitude_deg_east,
                site.frame != v.terrain.location.frame,
                r.min_solar_disk_visible_fraction != w.solar_fraction,
                r.earth_clearance_margin_deg != w.earth_margin_deg,
                self.baseline_analysis.observer.solar_height_above_surface_m
                != v.solar_height_above_surface_m,
                self.baseline_analysis.observer.earth_height_above_surface_m
                != v.earth_height_above_surface_m,
                r.require_simultaneous and not w.joint,
            )
        ):
            raise ValueError("Baseline/template scientific configuration mismatch")
        return self


class TemporalCandidate(Model):
    candidate_id: str
    start_utc: datetime
    end_utc: datetime
    discovery_sources: list[str]
    evaluation_status: Literal[
        "DISCOVERED",
        "DETAILED_EVALUATED",
        "PARTIAL",
        "NOT_SELECTED_FOR_DETAILED_EVALUATION",
        "NOT_EVALUATED_RESOURCE_LIMIT",
        "INVALID",
    ] = "DISCOVERED"
    operation: OperationEvaluationResult | None = None
    metrics: dict = Field(default_factory=dict)
    evidence_sha256: str | None = None
    evidence_mode: Literal["RECORDED", "LIVE", "SYNTHETIC"] | None = None
    comparison_validity: str = "NOT_COMPARED"
    reason_codes: list[str] = Field(default_factory=list)
    seconds: float = 0
    resource_consumption: dict = Field(default_factory=dict)


class TemporalCandidateComparison(Model):
    baseline_id: str
    candidate_id: str
    validity: str
    classification: str
    decision_change: list[str] | None = None
    score_delta: float | None = None
    duration_deltas_s: dict = Field(default_factory=dict)
    unknown_deltas_s: dict = Field(default_factory=dict)
    explanation: str


class TemporalOptimizationResult(Model):
    schema_version: str = "command-09-v1"
    request: TemporalOptimizationRequest
    baseline: TemporalCandidate
    candidates: list[TemporalCandidate]
    recommendations: list[TemporalCandidate]
    ranked_suggestions: list[str]
    comparisons: list[TemporalCandidateComparison]
    search_status: str
    outcome: str
    resource_consumption: dict
    search_scope: dict
    limitations: list[str]
    science_ready: Literal[False] = False
