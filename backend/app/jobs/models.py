"""Backend-owned durable job envelopes; public AnalysisRequest remains 1.0."""

from datetime import datetime
from typing import Literal
from pydantic import Field
from app.models.analysis import Model

JobState = Literal[
    "QUEUED",
    "RUNNING",
    "COMPLETED",
    "PARTIAL",
    "FAILED",
    "CANCEL_REQUESTED",
    "CANCELLED",
    "INTERRUPTED",
]
JobType = Literal["ANALYSIS", "TEMPORAL", "LOCAL"]
TERMINAL = {"COMPLETED", "PARTIAL", "FAILED", "CANCELLED", "INTERRUPTED"}


class ScientificJobProgress(Model):
    stage: str = "QUEUED"
    progress_percent: float | None = Field(default=None, ge=0, le=100)
    completed_candidates: int = 0
    total_candidates: int | None = None
    completed_visibility_evaluations: int = 0


class ScientificJobError(Model):
    code: str
    error_class: str
    message: str


class ScientificJobStatus(Model):
    job_id: str
    job_type: JobType
    status: JobState
    request_identity: str
    created_at_utc: str
    started_at_utc: str | None = None
    updated_at_utc: str
    finished_at_utc: str | None = None
    progress: ScientificJobProgress
    reason_codes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    result_available: bool = False
    error: ScientificJobError | None = None


class ScientificJobAccepted(Model):
    job_id: str
    job_type: JobType
    status: JobState
    submitted_at_utc: str
    status_url: str
    result_url: str
    cancellation_url: str
    request_identity: str
    scientific_mode: str = "LIVE_PROTOTYPE"
    resource_policy: dict


class ScientificJobResult(Model):
    job_id: str
    job_type: JobType
    status: JobState
    result: dict
