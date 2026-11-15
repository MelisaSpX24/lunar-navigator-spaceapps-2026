"""Same-time lunar neighbourhood search; bounded prototype terrain screening."""

from typing import Literal
from pydantic import Field
from app.models.analysis import Model, AnalysisRequest, Coordinates
from app.science.operation_models import Policy, OperationEvaluationResult
from app.science.window_models import WindowSearchRequest


class LocalSiteOptimizationRequest(Model):
    baseline_analysis: AnalysisRequest
    window_template: WindowSearchRequest
    evaluation_policy: Policy = "STRICT_EVIDENCE"
    selection_strategy: Literal["SLOPE_ONLY", "TERRAIN_DIVERSE"] = "SLOPE_ONLY"
    search_radius_m: float = Field(default=5000, gt=0, le=5000)
    coarse_step_m: float = Field(default=500, ge=100, le=1000)
    refinement_step_m: float = Field(default=100, ge=10, le=250)
    max_generated_candidates: int = Field(default=32, ge=2, le=128)
    max_detailed_candidates: int = Field(default=2, ge=1, le=8)
    max_recommendations: int = Field(default=3, ge=1, le=3)
    max_slope_deg: float = Field(default=10, ge=0, le=45)


class LocalSiteCandidate(Model):
    candidate_id: str
    location: Coordinates
    distance_m: float
    bearing_deg: float | None = None
    stage: str
    terrain: dict = Field(default_factory=dict)
    operation: OperationEvaluationResult | None = None
    metrics: dict = Field(default_factory=dict)
    evidence_sha256: str | None = None
    reason_codes: list[str] = Field(default_factory=list)


class LocalSiteOptimizationResult(Model):
    schema_version: str = "command-10-local-v1"
    request: LocalSiteOptimizationRequest
    baseline: LocalSiteCandidate
    candidates: list[LocalSiteCandidate]
    recommendations: list[LocalSiteCandidate]
    comparisons: list[dict]
    outcome: str
    search_status: str
    scope: dict
    resource_consumption: dict
    limitations: list[str]
    data_origin: Literal["LIVE_COMPUTED", "PRECOMPUTED"] | None = None
    scientific_resources: dict = Field(default_factory=dict)
    new_scientific_resources: dict = Field(default_factory=dict)
    checkpoint_scientific_resources: dict = Field(default_factory=dict)
    checkpoint_reused: int = 0
    science_ready: Literal[False] = False
