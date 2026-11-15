"""Local operation contracts; shared HTTP schemas stay unchanged."""

from typing import Literal
from pydantic import Field, model_validator
from app.models.analysis import (
    Model,
    AnalysisRequest,
    Decision,
    RuleResult,
    Score,
    DataQuality,
    ResolvedSite,
)

Policy = Literal["STRICT_EVIDENCE", "PROTOTYPE_SAMPLED_ESTIMATE"]


class OperationEvaluationRequest(Model):
    analysis: AnalysisRequest
    evaluation_policy: Policy = "STRICT_EVIDENCE"
    window_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    correction: Literal["NONE", "LT+S"] = "NONE"
    resolved_site: ResolvedSite | None = None
    resolved_site_id: str | None = None
    example_preset: Literal["SOLAR_1H", "EARTH_1H"] | None = None


class RuleEvidence(Model):
    rule: RuleResult
    policy: Policy
    evidence_status: str
    unit: str
    source_metric: str
    reason_codes: list[str]


class OperationEvaluationResult(Model):
    schema_version: str = "command-08-v1"
    request: OperationEvaluationRequest
    effective_requirements: dict
    assumption_labels: list[str]
    decision: Decision
    rule_evidence: list[RuleEvidence]
    score: Score
    score_evidence: str
    score_details: list[dict]
    quality: DataQuality
    provenance: dict
    execution_status: Literal["COMPLETED"] = "COMPLETED"
    data_origin: str
    science_ready: Literal[False] = False
    limitations: list[str]
