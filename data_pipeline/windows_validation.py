"""Bounded real SPICE candidate scan; centre geometry is not disk visibility."""

import json, os, time
from pathlib import Path
from datetime import timedelta
from app.data.fusion import TerrainRequest
from app.data.observer import prepare_observer
from app.science.astronomy import calculate
from app.science.kernels import KernelSession, ScienceError
from app.science.visibility import VisibilityEngine
from app.science.windows import run_windows
from app.science.window_models import WindowSearchRequest
from data_pipeline.visibility_cli import visibility_terrain
from data_pipeline.visibility_validation import pilot


def candidate_scan(engine, request, count=15, step_hours=12):
    if not 2 <= count <= 64 or not 0 < step_hours <= 24:
        raise ValueError("Candidate scan budget invalid")
    q = request.visibility
    surface = engine.terrain.sample(
        TerrainRequest(
            location=q.terrain.location,
            policy=q.terrain.policy,
            preferred_resolution_m=q.terrain.preferred_resolution_m,
        )
    )
    if surface.selected is None:
        raise ScienceError("INVALID_OBSERVER", "No accepted surface")
    observer = prepare_observer(
        surface.selected, q.solar_height_above_surface_m
    ).observer
    rows = []
    started = time.perf_counter()
    for i in range(count):
        utc = request.start_utc + timedelta(hours=i * step_hours)
        g = calculate(engine.session, observer, utc, q.correction)
        rows.append(
            {
                "utc": utc.isoformat(),
                "sun": g.sun.model_dump(mode="json"),
                "earth": g.earth.model_dump(mode="json"),
            }
        )
    geometry_seconds = time.perf_counter() - started
    # Exact centre rays rank candidates only; they do not replace full disk evaluation.
    before = engine.counters()
    budget = [count, 500000]
    for row in rows:
        ray, identity, reason = engine._ray(
            q.terrain, row["sun"]["azimuth_deg"], budget
        )
        row["center_horizon_deg"] = ray.horizon_elevation_deg if ray else None
        row["reason"] = reason
        row["candidate_clearance_deg"] = (
            None
            if row["center_horizon_deg"] is None
            else row["sun"]["elevation_deg"] - row["center_horizon_deg"]
        )
    candidates = [
        (a, b)
        for a, b in zip(rows, rows[1:])
        if a["candidate_clearance_deg"] is not None
        and b["candidate_clearance_deg"] is not None
        and (a["candidate_clearance_deg"] >= 0) != (b["candidate_clearance_deg"] >= 0)
    ]
    event = None
    if candidates:
        a, b = candidates[0]
        r = WindowSearchRequest.model_validate(
            request.model_dump()
            | {
                "start_utc": a["utc"],
                "duration_s": step_hours * 3600,
                "step_s": step_hours * 3600,
                "max_visibility_evaluations": 8,
                "max_refinements": 6,
            }
        )
        event = run_windows(engine, r).model_dump(mode="json")
    return {
        "rows": rows,
        "geometry_seconds": geometry_seconds,
        "seconds": time.perf_counter() - started,
        "accounting": {k: v - before[k] for k, v in engine.counters().items()},
        "event_search": event,
        "status": "CANDIDATE_EVALUATED" if event else "NO_CANDIDATE_OBSERVED",
        "limitation": "Centre crossing is a candidate only; 12-hour scan can miss events. Earth geometry uses solar observer here only for equal-height pilot.",
    }


def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Refusing overwrite")
    request = WindowSearchRequest(
        visibility=pilot(), start_utc="2026-11-20T08:00:00Z", duration_s=21600
    )
    with KernelSession(
        os.environ["NASA_KERNEL_DIR"], os.environ["NASA_KERNEL_INDEX"]
    ) as session, visibility_terrain() as terrain:
        result = candidate_scan(VisibilityEngine(session, terrain, 2048), request)
    with a.output.open("x") as f:
        json.dump(result, f, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
