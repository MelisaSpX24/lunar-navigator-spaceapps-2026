"""Backend-local scientific job API. Health 1.0 remains scientifically unready."""

from typing import Literal
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from app.models.analysis import (
    AnalysisRequest,
    AnalysisResult,
    Decision,
    HealthResponse,
)
from app.services.models import AnalysisJobRequest, TemporalJobRequest, LocalJobRequest
from app.services.scientific_runner import validate_analysis, unavailable
from app.jobs.models import (
    ScientificJobAccepted,
    ScientificJobStatus,
    ScientificJobResult,
    TERMINAL,
)
from app.jobs.store import StoreError
from app.science.kernels import ScienceError

router = APIRouter(prefix="/api/v1")


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()


@router.get("/capabilities")
def capabilities(request: Request):
    manager = request.app.state.manager
    error = unavailable()
    available = bool(manager and manager.thread and manager.thread.is_alive())
    return {
        "api_reachable": True,
        "scientific_job_runner_available": manager is not None
        and manager.thread is not None
        and manager.thread.is_alive(),
        "configured_science_files_available": error is None,
        "source_validation": "SHA256_AND_METADATA_CHECKED_AT_JOB_EXECUTION",
        "bounded_live_prototype_supported": available and error is None,
        "recorded_prototype_supported": True,
        "fully_independently_validated_science_ready": False,
        "science_ready": False,
        "job_types": ["ANALYSIS", "TEMPORAL", "LOCAL"],
        "worker_count": 1 if available else 0,
        "limits": {
            "active_jobs": manager.store.max_active if manager else 0,
            "max_output_bytes": manager.store.max_bytes if manager else 0,
            "max_wall_time_s": 3600,
            "max_local_radius_m": 5000,
        },
        "reason_codes": [error] if error else [],
    }


def manager_or_503(request):
    manager = request.app.state.manager
    if manager is None:
        raise HTTPException(503, detail={"code": "SCIENTIFIC_JOB_RUNNER_DISABLED"})
    if manager.thread is None or not manager.thread.is_alive():
        raise HTTPException(503, detail={"code": "SCIENTIFIC_WORKER_UNAVAILABLE"})
    return manager


def submit(request, kind, model):
    a = model.analysis if kind == "ANALYSIS" else model.optimization.baseline_analysis
    try:
        validate_analysis(a)
    except ScienceError as exc:
        raise HTTPException(503, detail={"code": exc.code})
    except ValueError:
        raise HTTPException(
            422, detail={"code": "REQUIRED_PARAMETERS_MISSING_OR_UNSUPPORTED"}
        )
    if kind != "ANALYSIS":
        visibility = model.optimization.window_template.visibility
        if visibility.disk_samples not in (64, 256):
            raise HTTPException(422, detail={"code": "DISK_SAMPLE_LIMIT"})
        if visibility.terrain.policy.enable_lroc:
            raise HTTPException(
                422, detail={"code": "LROC_NOT_ENABLED_IN_SERVER_CONFIGURATION"}
            )
    manager = manager_or_503(request)
    if manager.runner_requires_sources:
        error = unavailable()
        if error:
            raise HTTPException(503, detail={"code": error})
    if model.resume_from:
        try:
            old = manager.store.row(model.resume_from)
        except KeyError:
            raise HTTPException(404, detail={"code": "RESUME_JOB_NOT_FOUND"})
        if old["kind"] != kind or old["status"] not in TERMINAL:
            raise HTTPException(409, detail={"code": "RESUME_STATE_MISMATCH"})
        import json

        old_model = type(model).model_validate(json.loads(old["payload"]))

        def identity(value):
            data = value.model_dump()
            analysis = (
                value.analysis
                if kind == "ANALYSIS"
                else value.optimization.baseline_analysis
            )
            target = (
                data["analysis"]
                if kind == "ANALYSIS"
                else data["optimization"]["baseline_analysis"]
            )
            target["operation"]["requirements"] = (
                analysis.operation.requirements.model_dump(exclude_unset=True)
            )
            return data

        previous = identity(old_model)
        current = identity(model)
        for obj in (previous, current):
            for key in ("resources", "resume_from", "max_candidate_evaluations"):
                obj.pop(key, None)
            # Discovery/admission settings never identify an exact scientific sample.
            # Grid keys and candidate requests retain their own full source/config binding.
            if kind == "TEMPORAL":
                obj.pop("screening_strategy", None)
                obj.pop("grid_spacing_deg", None)
            if kind == "LOCAL":
                for key in (
                    "selection_strategy",
                    "max_detailed_candidates",
                    "max_recommendations",
                ):
                    obj["optimization"].pop(key, None)
        if previous != current:
            raise HTTPException(409, detail={"code": "RESUME_REQUEST_MISMATCH"})
        # Checkpoint keys re-bind exact candidate requests and source signatures in a new validated session.
    try:
        status = manager.store.submit(
            kind, model.model_dump(mode="json", exclude_unset=True)
        )
    except StoreError as exc:
        raise HTTPException(429, detail={"code": str(exc)})
    job = status.job_id
    base = "/api/v1/jobs/" + job
    accepted = ScientificJobAccepted(
        job_id=job,
        job_type=kind,
        status=status.status,
        submitted_at_utc=status.created_at_utc,
        status_url=base,
        result_url=base + "/result",
        cancellation_url=base + "/cancel",
        request_identity=status.request_identity,
        resource_policy=model.resources.model_dump(),
    )
    return JSONResponse(status_code=202, content=accepted.model_dump(mode="json"))


@router.post(
    "/analyses",
    responses={
        200: {"model": AnalysisResult},
        202: {"model": ScientificJobAccepted},
        503: {"model": AnalysisResult},
    },
)
def analyse(
    a: AnalysisRequest,
    request: Request,
    mode: Literal["live", "recorded"] = "live",
    evaluation_policy: Literal[
        "STRICT_EVIDENCE", "PROTOTYPE_SAMPLED_ESTIMATE"
    ] = "STRICT_EVIDENCE",
    registration: Literal["STRICT", "PROTOTYPE"] = "STRICT",
    step_s: int = 3600,
):
    from pydantic import ValidationError

    try:
        model = AnalysisJobRequest(
            analysis=a,
            evaluation_policy=evaluation_policy,
            registration=registration,
            step_s=step_s,
        )
    except ValidationError:
        raise HTTPException(422, detail={"code": "INVALID_SCIENCE_SETTINGS"})
    if mode == "recorded":
        from app.services.recorded import find_recorded

        try:
            r = find_recorded(model)
        except (ValueError, ScienceError):
            r = None
        if r is None:
            raise HTTPException(404, detail={"code": "RECORDED_REQUEST_NOT_FOUND"})
        return JSONResponse(status_code=200, content=r.model_dump(mode="json"))
    if request.app.state.manager is None:
        result = AnalysisResult(
            analysis_id="not-run",
            execution_status="NOT_RUN",
            request=a,
            decision=Decision(reason_codes=["SCIENCE_ENGINE_NOT_READY"]),
        )
        return JSONResponse(status_code=503, content=result.model_dump(mode="json"))
    return submit(request, "ANALYSIS", model)


@router.post("/analyses/jobs", status_code=202)
def analysis_job(model: AnalysisJobRequest, request: Request):
    return submit(request, "ANALYSIS", model)


@router.post("/optimizations/temporal", status_code=202)
def temporal(model: TemporalJobRequest, request: Request):
    return submit(request, "TEMPORAL", model)


@router.post("/optimizations/local", status_code=202)
def local(model: LocalJobRequest, request: Request):
    return submit(request, "LOCAL", model)


@router.get("/jobs/{job_id}", response_model=ScientificJobStatus)
def status(job_id: str, request: Request):
    try:
        return manager_or_503(request).store.status(job_id)
    except KeyError:
        raise HTTPException(404, detail={"code": "JOB_NOT_FOUND"})


@router.get("/jobs/{job_id}/result", response_model=ScientificJobResult)
def result(job_id: str, request: Request):
    manager = manager_or_503(request)
    try:
        state = manager.store.status(job_id)
        if state.status not in TERMINAL or not state.result_available:
            raise HTTPException(
                409, detail={"code": "RESULT_NOT_AVAILABLE", "status": state.status}
            )
        value = manager.store.result(job_id)
        return ScientificJobResult(
            job_id=job_id, job_type=state.job_type, status=state.status, result=value
        )
    except KeyError:
        raise HTTPException(404, detail={"code": "JOB_NOT_FOUND"})
    except StoreError:
        raise HTTPException(500, detail={"code": "RESULT_INTEGRITY_FAILED"})


@router.post("/jobs/{job_id}/cancel", response_model=ScientificJobStatus)
def cancel(job_id: str, request: Request):
    try:
        return manager_or_503(request).store.cancel(job_id)
    except KeyError:
        raise HTTPException(404, detail={"code": "JOB_NOT_FOUND"})


@router.get("/result-schemas")
def result_schemas():
    from app.services.models import TemporalBatchResult
    from app.optimization.local_site_models import LocalSiteOptimizationResult

    return {
        "analysis_result_path": "result.analysis",
        "optimizer_result_path": "result",
        "ANALYSIS": AnalysisResult.model_json_schema(),
        "TEMPORAL": TemporalBatchResult.model_json_schema(),
        "LOCAL": LocalSiteOptimizationResult.model_json_schema(),
    }
