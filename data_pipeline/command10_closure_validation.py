"""Operator-owned bounded HTTP closure experiments; never invent live results."""

import argparse, json, time
from pathlib import Path
import httpx
from app.models.analysis import AnalysisRequest
from app.services.scientific_runner import template
from app.services.models import TemporalBatchResult
from app.optimization.local_site_models import LocalSiteOptimizationResult


def canonical():
    q = json.loads(
        Path("data_pipeline/evidence/command-09-temporal-optimizer.json").read_text()
    )["live_result"]["request"]
    q["selection_strategy"] = "COVERAGE_AWARE"
    q["max_detailed_candidates"] = 4
    return q


def run(base, mode, resume, output, ab_workload="cold-one-hour"):
    if output.exists():
        raise ValueError("Refusing overwrite")
    client = httpx.Client(base_url=base, timeout=20)
    report = {
        "mode": mode,
        "resume_requested": bool(resume),
        "health": client.get("/api/v1/health").json(),
        "capabilities": client.get("/api/v1/capabilities").json(),
        "runs": [],
    }

    def execute(endpoint, payload):
        start = time.perf_counter()
        r = client.post("/api/v1/optimizations/" + endpoint, json=payload)
        r.raise_for_status()
        assert r.status_code == 202
        item = {
            "request": payload,
            "accepted": r.json(),
            "admission_s": time.perf_counter() - start,
        }
        report["runs"].append(item)
        job = r.json()["job_id"]
        lastlog = time.monotonic()
        while True:
            state = client.get("/api/v1/jobs/" + job)
            state.raise_for_status()
            state = state.json()
            if time.monotonic() - lastlog > 30:
                print(job, state["status"], state["progress"], flush=True)
                lastlog = time.monotonic()
            if state["status"] not in ("QUEUED", "RUNNING", "CANCEL_REQUESTED"):
                break
            time.sleep(1)
        reply = client.get("/api/v1/jobs/" + job + "/result")
        reply.raise_for_status()
        item.update(
            status=state,
            result=reply.json(),
            total_poll_and_execution_s=time.perf_counter() - start,
        )
        with output.open("w") as f:
            json.dump(report, f, indent=2, allow_nan=False)
        value = item["result"]["result"]
        if "schema_version" in value:
            (
                TemporalBatchResult
                if endpoint == "temporal"
                else LocalSiteOptimizationResult
            ).model_validate(value)
        return value

    if mode == "local":
        a = AnalysisRequest.model_validate(
            {
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
        )
        payload = {
            "optimization": {
                "baseline_analysis": a.model_dump(mode="json", exclude_unset=True),
                "window_template": template(a, "PROTOTYPE").model_dump(mode="json"),
                "evaluation_policy": "PROTOTYPE_SAMPLED_ESTIMATE",
                "search_radius_m": 5000,
                "coarse_step_m": 1000,
                "max_generated_candidates": 16,
                "max_detailed_candidates": 4,
                "selection_strategy": "TERRAIN_DIVERSE",
            },
            "resources": {
                "max_wall_time_s": 600,
                "max_visibility_evaluations": 12,
                "max_horizon_rays": 2000,
                "max_terrain_samples": 1200000,
                "max_cache_entries": 2048,
            },
        }
        if resume:
            payload["resume_from"] = resume
        execute("local", payload)
    else:
        optimization = canonical()
        if mode == "grid-ab" and ab_workload == "cold-one-hour":
            if resume:
                raise ValueError(
                    "Cold exact-cache A/B does not accept a checkpoint seed"
                )
            from datetime import timedelta

            a = AnalysisRequest.model_validate(
                {
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
            )
            optimization = {
                "baseline_analysis": a.model_dump(mode="json", exclude_unset=True),
                "window_template": template(a, "PROTOTYPE").model_dump(mode="json"),
                "search_start_utc": a.time.start_utc.isoformat(),
                "search_end_utc": (a.time.start_utc + timedelta(hours=2)).isoformat(),
                "coarse_start_step_s": 3600,
                "selection_strategy": "COVERAGE_AWARE",
                "max_detailed_candidates": 2,
                "evaluation_policy": "PROTOTYPE_SAMPLED_ESTIMATE",
            }
        payload = {
            "optimization": optimization,
            "max_candidate_evaluations": 31 if mode == "temporal" else 2,
            "resources": {
                "max_wall_time_s": 3300 if mode == "temporal" else 600,
                "max_visibility_evaluations": 256,
                "max_horizon_rays": 50000,
                "max_terrain_samples": 20000000,
                "max_cache_entries": 4096,
            },
        }
        if resume:
            payload["resume_from"] = resume
        if mode == "temporal":
            execute("temporal", payload)
        else:
            if ab_workload == "checkpoint-seeded-canonical" and not resume:
                raise ValueError(
                    "Checkpoint-seeded A/B requires the same seed for both arms"
                )
            a = execute("temporal", payload | {"screening_strategy": "EXACT_ONLY"})
            b = execute(
                "temporal",
                payload
                | {"screening_strategy": "HORIZON_GRID", "grid_spacing_deg": 1.0},
            )

            def science(v):
                return {
                    c["start_utc"]: {
                        "metrics": c["metrics"],
                        "decision": c["operation"]["decision"],
                        "score": c["operation"]["score"],
                    }
                    for c in [v["baseline"]] + v["candidates"]
                    if c.get("operation")
                }

            report["comparison"] = {
                "same_generated_candidate_set": sorted(
                    c["candidate_id"] for c in a["candidates"]
                )
                == sorted(c["candidate_id"] for c in b["candidates"]),
                "same_detailed_scientific_results": science(a) == science(b),
                "speedup_in_this_measured_workload": a["pipeline_seconds"]
                / b["pipeline_seconds"],
                "scope": (
                    "COLD_SCIENTIFIC_ENGINE_CACHES_ONE_HOUR_OPERATION_SHARED_OS_FILE_CACHE"
                    if ab_workload == "cold-one-hour"
                    else "SAME_SOURCE_AND_EXACT_UTC_CHECKPOINT_SEED_NOT_NEW_VISIBILITY"
                ),
                "ab_workload": ab_workload,
                "default_strategy_changed": False,
            }
    with output.open("w") as f:
        json.dump(report, f, indent=2, allow_nan=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8010")
    p.add_argument("--mode", choices=["temporal", "local", "grid-ab"], required=True)
    p.add_argument("--resume-from")
    p.add_argument(
        "--ab-workload",
        choices=["cold-one-hour", "checkpoint-seeded-canonical"],
        default="cold-one-hour",
    )
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    run(a.base_url, a.mode, a.resume_from, a.output, a.ab_workload)
