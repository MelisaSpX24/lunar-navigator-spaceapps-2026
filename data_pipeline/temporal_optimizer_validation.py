"""Summarize a fresh live run and reuse its exact windows for four profile replays."""

import argparse, json, time
from pathlib import Path
from app.science.temporal_optimizer_models import (
    TemporalOptimizationRequest,
    TemporalOptimizationResult,
)
from app.science.temporal_optimizer import optimize, RecordedProvider
from data_pipeline.operations_cli import load_windows


def run(live_result, window_dir, hint_path, output):
    output = Path(output)
    if output.exists():
        raise ValueError("Refusing overwrite")
    live = TemporalOptimizationResult.model_validate_json(Path(live_result).read_text())
    windows = [load_windows(p) for p in sorted(Path(window_dir).glob("*.json"))]
    hint = load_windows(hint_path)
    reports = {}
    for name, profile, requirements in [
        ("solar", "SOLAR_POWERED_EXPERIMENT", {"min_sun_visible_s": 3600}),
        ("earth", "EARTH_DATA_TRANSMISSION", {"min_earth_continuous_s": 3600}),
        (
            "joint",
            "CUSTOM_OPERATION",
            {"require_simultaneous": True, "min_joint_continuous_s": 1800},
        ),
        ("short", "SHORT_SURFACE_OBSERVATION", {"min_earth_continuous_s": 3600}),
    ]:
        for policy in ("STRICT_EVIDENCE", "PROTOTYPE_SAMPLED_ESTIMATE"):
            values = live.request.model_dump(exclude_unset=True)
            values["baseline_analysis"]["operation"] = {
                "profile": profile,
                "requirements": requirements,
            }
            values["evaluation_policy"] = policy
            q = TemporalOptimizationRequest.model_validate(values)
            ts = time.perf_counter()
            r = optimize(q, RecordedProvider(windows), hints=[hint])
            detailed = [c for c in r.candidates if c.operation]
            reports[name + "_" + policy] = {
                "mode": "RECORDED_REPLAY_OF_NEW_LIVE_WINDOWS",
                "seconds": time.perf_counter() - ts,
                "outcome": r.outcome,
                "search_status": r.search_status,
                "baseline_decision": r.baseline.operation.decision.status,
                "baseline_score": r.baseline.operation.score.value,
                "candidate_decisions": [
                    (
                        c.start_utc.isoformat(),
                        c.operation.decision.status,
                        c.operation.score.value,
                    )
                    for c in detailed
                ],
                "recommendation_utc": [
                    c.start_utc.isoformat() for c in r.recommendations
                ],
                "comparisons": [c.model_dump(mode="json") for c in r.comparisons],
            }
    report = {
        "status": "COMMAND_09_COMPLETE_WITH_LIMITATIONS",
        "assumptions": ["EXAMPLE_OPERATION_ASSUMPTION"],
        "live_result": live.model_dump(mode="json"),
        "live_windows": [w.model_dump(mode="json") for w in windows],
        "recorded_profile_replays": reports,
        "recorded_previous_pilot_source": "data_pipeline/evidence/command-07-windows.json",
        "hint": {
            "source": "Command 07 recorded real bracket",
            "left_utc": "2026-11-23T16:15:00Z",
            "right_utc": "2026-11-23T16:26:15Z",
            "width_s": 675,
            "status": "EVENT_BRACKET_NOT_REFINED",
            "interpretation": "Discovery hint only; not certified sunrise or operation eligibility",
        },
        "limitations": [
            "Only one alternative received full new live verification; all other generated starts remain unevaluated.",
            "Global optimality and physical continuity are not established.",
            "Four-profile/strict comparisons reuse the two new live artifacts and do not represent eight additional NASA executions.",
        ],
    }
    with output.open("x") as f:
        json.dump(report, f, indent=2, allow_nan=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--live-result", required=True)
    p.add_argument("--window-dir", required=True)
    p.add_argument("--hint", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    run(a.live_result, a.window_dir, a.hint, a.output)
