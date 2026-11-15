"""Real loopback HTTP validation. Long calls poll durable jobs, not one open HTTP request."""

import argparse, json, time
from pathlib import Path
import httpx
from app.models.analysis import AnalysisResult
from app.jobs.models import (
    ScientificJobAccepted,
    ScientificJobStatus,
    ScientificJobResult,
)
from app.science.window_models import WindowSearchResult
from app.services.scientific_runner import template
from app.models.analysis import AnalysisRequest


def run(base, output, previous):
    output = Path(output)
    if output.exists():
        raise ValueError("Refusing overwrite")
    c = httpx.Client(base_url=base, timeout=20)
    evidence = {
        "origin": "REAL_SCIENTIFIC_HTTP_EXECUTION",
        "runs": {},
        "science_ready": False,
    }

    def save():
        output.write_text(json.dumps(evidence, indent=2, allow_nan=False))

    def wait(job, name):
        statuses = []
        t = time.perf_counter()
        while True:
            r = c.get("/api/v1/jobs/" + job)
            r.raise_for_status()
            s = ScientificJobStatus.model_validate(r.json())
            if not statuses or statuses[-1] != [s.status, s.progress.stage]:
                statuses.append([s.status, s.progress.stage])
            if s.status in (
                "COMPLETED",
                "PARTIAL",
                "FAILED",
                "CANCELLED",
                "INTERRUPTED",
            ):
                break
            time.sleep(0.5)
        result = c.get("/api/v1/jobs/" + job + "/result")
        value = result.json() if result.status_code == 200 else None
        if value:
            ScientificJobResult.model_validate(value)
        evidence["runs"][name] = {
            "job_id": job,
            "status": s.model_dump(mode="json"),
            "observed_states": statuses,
            "poll_seconds": time.perf_counter() - t,
            "http_result_status": result.status_code,
            "result": value,
        }
        save()
        print(name, s.status, flush=True)
        return value

    def submit(path, payload, name):
        t = time.perf_counter()
        r = c.post(path, json=payload)
        r.raise_for_status()
        a = ScientificJobAccepted.model_validate(r.json())
        assert r.status_code == 202
        evidence["runs"][name + "_accepted"] = {
            "http": r.status_code,
            "seconds": time.perf_counter() - t,
            "accepted": a.model_dump(mode="json"),
        }
        save()
        return a.job_id

    evidence["health"] = c.get("/api/v1/health").json()
    evidence["capabilities"] = c.get("/api/v1/capabilities").json()
    if previous:
        evidence["completed_survived_restart"] = (
            c.get("/api/v1/jobs/" + previous).json()["status"] == "COMPLETED"
        )
    a = {
        "options": {"include_full_horizon": False},
        "site": {
            "kind": "COORDINATES",
            "latitude_deg": -89.468,
            "longitude_deg_east": 222.6,
        },
        "time": {"start_utc": "2026-11-20T08:00:00Z", "duration_s": 3600},
        "operation": {
            "profile": "SOLAR_POWERED_EXPERIMENT",
            "requirements": {"min_sun_visible_s": 600},
        },
    }
    if not previous:
        previous = submit(
            "/api/v1/analyses/jobs",
            {
                "analysis": a,
                "registration": "PROTOTYPE",
                "evaluation_policy": "PROTOTYPE_SAMPLED_ESTIMATE",
            },
            "initial_analysis",
        )
        initial = wait(previous, "initial_analysis")
        AnalysisResult.model_validate(initial["result"]["analysis"])
    if previous:
        job = submit(
            "/api/v1/analyses/jobs",
            {
                "analysis": a,
                "registration": "PROTOTYPE",
                "evaluation_policy": "PROTOTYPE_SAMPLED_ESTIMATE",
                "resume_from": previous,
            },
            "resume_analysis",
        )
        r = wait(job, "resume_analysis")
        assert r["result"]["checkpoint_reused"] == 2
        AnalysisResult.model_validate(r["result"]["analysis"])
    # Cancel a running, real six-hour science task at an atomic-call boundary.
    longer = json.loads(json.dumps(a))
    longer["time"]["duration_s"] = 21600
    job = submit(
        "/api/v1/analyses/jobs",
        {
            "analysis": longer,
            "registration": "PROTOTYPE",
            "evaluation_policy": "PROTOTYPE_SAMPLED_ESTIMATE",
        },
        "cancel_analysis",
    )
    for _ in range(200):
        state = c.get("/api/v1/jobs/" + job).json()
        if state["progress"]["stage"] == "COMPUTING_VISIBILITY":
            break
        time.sleep(0.1)
    evidence["cancellation_response"] = c.post("/api/v1/jobs/" + job + "/cancel").json()
    wait(job, "cancel_analysis")
    aa = AnalysisRequest.model_validate(a)
    w = template(aa, "PROTOTYPE")
    local = {
        "baseline_analysis": a,
        "window_template": w.model_dump(mode="json"),
        "evaluation_policy": "PROTOTYPE_SAMPLED_ESTIMATE",
        "search_radius_m": 5000,
        "coarse_step_m": 1000,
        "max_generated_candidates": 16,
        "max_detailed_candidates": 2,
    }
    job = submit(
        "/api/v1/optimizations/local",
        {
            "optimization": local,
            "resources": {"max_visibility_evaluations": 4, "max_wall_time_s": 300},
        },
        "local",
    )
    wait(job, "local")
    # Canonical six-hour search: all discovered starts remain in the batch ledger.
    original = json.loads(
        Path("data_pipeline/evidence/command-09-temporal-optimizer.json").read_text()
    )["live_result"]["request"]
    original["selection_strategy"] = "COVERAGE_AWARE"
    original["max_detailed_candidates"] = 4
    job = submit(
        "/api/v1/optimizations/temporal",
        {
            "optimization": original,
            "max_candidate_evaluations": 31,
            "resources": {
                "max_visibility_evaluations": 21,
                "max_wall_time_s": 720,
                "max_horizon_rays": 3000,
            },
        },
        "temporal",
    )
    wait(job, "temporal")
    evidence["status"] = "FINISHED"
    save()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8010")
    p.add_argument("--output", required=True)
    p.add_argument("--previous-job")
    a = p.parse_args()
    run(a.base_url, a.output, a.previous_job)
