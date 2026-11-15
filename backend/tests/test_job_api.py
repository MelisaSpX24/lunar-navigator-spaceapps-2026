"""Actual FastAPI app and durable worker, with explicitly synthetic runner results."""

import time
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.jobs.models import (
    ScientificJobAccepted,
    ScientificJobStatus,
    ScientificJobResult,
)
from app.services.models import AnalysisJobRequest


def poll(client, job):
    for _ in range(200):
        s = client.get("/api/v1/jobs/" + job).json()
        if s["status"] in ("COMPLETED", "PARTIAL", "CANCELLED", "FAILED"):
            return s
        time.sleep(0.01)
    raise AssertionError(s)


def test_api_lifecycle_actual_app(tmp_path, request_data):
    def runner(kind, payload, ctx):
        ctx.update("EVALUATING_OPERATION")
        return {"data_origin": "TEST_FIXTURE", "request": payload}, "COMPLETED"

    with TestClient(create_app(job_path=tmp_path / "db.sqlite", runner=runner)) as c:
        assert c.get("/api/v1/health").json()["science_ready"] is False
        assert c.get("/api/v1/capabilities").json()["scientific_job_runner_available"]
        r = c.post("/api/v1/analyses", json=request_data)
        assert r.status_code == 202
        accepted = ScientificJobAccepted.model_validate(r.json())
        job = accepted.job_id
        assert poll(c, job)["status"] == "COMPLETED"
        ScientificJobStatus.model_validate(c.get(accepted.status_url).json())
        result = ScientificJobResult.model_validate(c.get(accepted.result_url).json())
        assert result.result["data_origin"] == "TEST_FIXTURE"
        assert c.get("/api/v1/jobs/unknown").status_code == 404
        assert c.post("/api/v1/jobs/unknown/cancel").status_code == 404
        assert c.post("/api/v1/analyses", json={}).status_code == 422
    with TestClient(create_app(job_path=tmp_path / "db.sqlite", runner=runner)) as c:
        assert c.get("/api/v1/jobs/" + job).json()["status"] == "COMPLETED"
        assert c.get("/api/v1/jobs/" + job + "/result").status_code == 200


def test_queue_cancel_and_result_not_ready(tmp_path, request_data):
    def runner(k, p, ctx):
        while True:
            ctx.check()
            time.sleep(0.005)

    with TestClient(
        create_app(job_path=tmp_path / "db.sqlite", runner=runner, queue_capacity=1)
    ) as c:
        r = c.post("/api/v1/analyses", json=request_data)
        job = r.json()["job_id"]
        assert c.post("/api/v1/analyses", json=request_data).status_code == 429
        assert c.get("/api/v1/jobs/" + job + "/result").status_code == 409
        assert c.post("/api/v1/jobs/" + job + "/cancel").status_code == 200
        assert poll(c, job)["status"] == "CANCELLED"


def test_optimizer_routes_and_resume_binding(tmp_path, request_data):
    import json
    from pathlib import Path
    from app.science.window_models import WindowSearchResult

    def runner(k, p, ctx):
        return {"kind": k, "data_origin": "TEST_FIXTURE"}, "PARTIAL"

    w = WindowSearchResult.model_validate(
        json.loads(Path("data_pipeline/evidence/command-07-windows.json").read_text())[
            "pilot"
        ]
    )
    base = {
        "baseline_analysis": request_data,
        "window_template": w.request.model_dump(mode="json"),
    }
    temporal = base | {
        "search_start_utc": request_data["time"]["start_utc"],
        "search_end_utc": "2026-11-27T08:00:00Z",
    }
    with TestClient(create_app(job_path=tmp_path / "db.sqlite", runner=runner)) as c:
        for path, payload in [
            ("/optimizations/temporal", {"optimization": temporal}),
            ("/optimizations/local", {"optimization": base}),
        ]:
            r = c.post("/api/v1" + path, json=payload)
            assert r.status_code == 202, r.text
            job = r.json()["job_id"]
            assert poll(c, job)["status"] == "PARTIAL"
            assert c.get("/api/v1/jobs/" + job + "/result").status_code == 200
            resumed = c.post("/api/v1" + path, json=payload | {"resume_from": job})
            assert resumed.status_code == 202
        bad = {"optimization": base | {"search_radius_m": 5001}}
        assert c.post("/api/v1/optimizations/local", json=bad).status_code == 422


def test_recorded_matching_and_missing_sources(tmp_path, request_data, monkeypatch):
    request_data["options"] = {"include_full_horizon": False}
    from app.models.analysis import AnalysisResult

    with TestClient(create_app()) as c:
        r = c.post(
            "/api/v1/analyses?mode=recorded&registration=PROTOTYPE&evaluation_policy=PROTOTYPE_SAMPLED_ESTIMATE",
            json=request_data,
        )
        assert r.status_code == 200, r.text
        assert AnalysisResult.model_validate(r.json()).data_origin == "PRECOMPUTED"
        request_data["time"]["start_utc"] = "2026-11-20T08:00:01Z"
        assert (
            c.post(
                "/api/v1/analyses?mode=recorded&registration=PROTOTYPE",
                json=request_data,
            ).status_code
            == 404
        )
    monkeypatch.delenv("NASA_KERNEL_DIR", raising=False)
    with TestClient(create_app(job_path=tmp_path / "db.sqlite")) as c:
        r = c.post("/api/v1/analyses", json=request_data)
        assert r.status_code == 503 and "SCIENCE" in r.json()["detail"]["code"]


def test_request_size_limit_and_explicit_cors(monkeypatch):
    monkeypatch.setenv("LUNAR_ALLOWED_ORIGINS", "http://localhost:5173")
    with TestClient(create_app()) as c:
        assert c.post("/api/v1/analyses", content="x" * 131073).status_code == 413
        r = c.options(
            "/api/v1/analyses",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
