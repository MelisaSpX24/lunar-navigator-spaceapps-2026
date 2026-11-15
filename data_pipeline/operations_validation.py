"""Recorded NASA evidence reuse and modest deterministic-operation benchmarks."""

import json, time, statistics
from pathlib import Path
from app.science.operations import evaluate_operation, evidence_identity
from app.science.operation_models import OperationEvaluationRequest
from app.science.scoring import compute_planning_score, weights_for
from data_pipeline.operations_cli import load_windows


def run(output):
    output = Path(output)
    if output.exists():
        raise ValueError("Refusing overwrite")
    w = load_windows("data_pipeline/evidence/command-07-windows.json")
    scenarios = {
        "earth": ("EARTH_DATA_TRANSMISSION", {"min_earth_continuous_s": 3600}),
        "solar": ("SOLAR_POWERED_EXPERIMENT", {"min_sun_visible_s": 3600}),
        "joint": (
            "CUSTOM_OPERATION",
            {"require_simultaneous": True, "min_joint_continuous_s": 1800},
        ),
        "short": ("SHORT_SURFACE_OBSERVATION", {"min_earth_continuous_s": 3600}),
    }
    results = {}
    requests = {}
    times = []
    for name, (profile, requirements) in scenarios.items():
        for policy in ("STRICT_EVIDENCE", "PROTOTYPE_SAMPLED_ESTIMATE"):
            q = OperationEvaluationRequest(
                analysis={
                    "site": {
                        "kind": "COORDINATES",
                        **w.request.visibility.terrain.location.model_dump(),
                    },
                    "time": {
                        "start_utc": w.request.start_utc,
                        "duration_s": int(w.request.duration_s),
                    },
                    "operation": {"profile": profile, "requirements": requirements},
                },
                evaluation_policy=policy,
                window_evidence_sha256=evidence_identity(w),
            )
            key = name + "_" + policy
            requests[key] = q.model_dump(mode="json", exclude_unset=True)
            t = time.perf_counter()
            r = evaluate_operation(q, w)
            times.append(time.perf_counter() - t)
            r.assumption_labels = ["EXAMPLE_OPERATION_ASSUMPTION"]
            results[key] = r.model_dump(mode="json")
    q = OperationEvaluationRequest.model_validate(
        requests["earth_PROTOTYPE_SAMPLED_ESTIMATE"]
    )

    def bench(fn):
        t = time.perf_counter()
        for _ in range(100):
            fn()
        return (time.perf_counter() - t) / 100

    timings = {
        "single_operation_mean_s": statistics.mean(times),
        "single_operation_max_s": max(times),
        "four_profile_evaluations_s": sum(times[1::2]),
        "score_mean_s": bench(
            lambda: compute_planning_score(
                w,
                q.evaluation_policy,
                weights_for(
                    q.analysis.operation.profile, q.analysis.operation.requirements
                ),
            )
        ),
        "pydantic_request_mean_s": bench(
            lambda: OperationEvaluationRequest.model_validate(
                requests["earth_PROTOTYPE_SAMPLED_ESTIMATE"]
            )
        ),
        "json_serialization_mean_s": bench(
            lambda: json.dumps(
                results["earth_PROTOTYPE_SAMPLED_ESTIMATE"], allow_nan=False
            )
        ),
    }
    report = {
        "status": "COMMAND_08_COMPLETE_WITH_LIMITATIONS",
        "data_origin": "RECORDED_REAL_NASA_EVIDENCE",
        "input_path": "data_pipeline/evidence/command-07-windows.json",
        "input_selector": "pilot (complete WindowSearchResult, not reconstructed summary)",
        "window_evidence_sha256": evidence_identity(w),
        "new_astronomy_computations": 0,
        "assumptions": ["EXAMPLE_OPERATION_ASSUMPTION"],
        "requests": requests,
        "results": results,
        "performance": timings,
        "note": "Rule explanation construction is included in single-operation wall time; no separate explanation benchmark.",
    }
    with output.open("x") as f:
        json.dump(report, f, indent=2, allow_nan=False)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    a = p.parse_args()
    run(a.output)
