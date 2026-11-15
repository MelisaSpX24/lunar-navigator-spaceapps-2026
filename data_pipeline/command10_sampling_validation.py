"""One-hour sampling sensitivity; shared exact-UTC checkpoints avoid repeated rays."""

import argparse, json, os, time
from pathlib import Path
from app.jobs.store import JobStore
from app.jobs.manager import JobManager, JobContext
from app.services.models import ResourcePolicy
from app.services.scientific_runner import BudgetedEngine, template
from app.models.analysis import AnalysisRequest
from app.science.visibility import VisibilityEngine
from app.science.kernels import KernelSession
from data_pipeline.visibility_cli import visibility_terrain


def run(output, db):
    output = Path(output)
    if output.exists():
        raise ValueError("Refusing overwrite")
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
    store = JobStore(db)
    job = store.submit("ANALYSIS", {}).job_id
    ctx = JobContext(JobManager(store, None), job)
    rows = []
    with KernelSession(
        os.environ["NASA_KERNEL_DIR"], os.environ["NASA_KERNEL_INDEX"]
    ) as session, visibility_terrain() as terrain:
        e = BudgetedEngine(
            VisibilityEngine(session, terrain, 4096),
            ResourcePolicy(
                max_visibility_evaluations=12,
                max_horizon_rays=1600,
                max_wall_time_s=400,
            ),
            ctx,
        )
        for step in (3600, 1800, 900):
            t = time.perf_counter()
            op, w = e.evaluate(
                a, template(a, "PROTOTYPE", step), "PROTOTYPE_SAMPLED_ESTIMATE"
            )
            rows.append(
                {
                    "step_s": step,
                    "seconds": time.perf_counter() - t,
                    "timeline_samples": len(w.timeline),
                    "metrics": {k: m.model_dump() for k, m in w.metrics.items()},
                    "brackets": [b.model_dump(mode="json") for b in w.brackets],
                    "decision": op.decision.model_dump(),
                    "score": op.score.model_dump(),
                    "source_evidence": w.source_evidence,
                }
            )
        report = {
            "mode": "LIVE_NASA_ONE_HOUR_SENSITIVITY",
            "rows": rows,
            "resources": e.used(),
            "reused_exact_utc_samples": e.reused,
            "limitations": [
                "One-hour scenario only, not six-hour temporal continuity proof.",
                "Ten-minute sampling not run to bound live computation.",
            ],
        }
    with output.open("x") as f:
        json.dump(report, f, indent=2, allow_nan=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--db", required=True)
    a = p.parse_args()
    run(a.output, a.db)
