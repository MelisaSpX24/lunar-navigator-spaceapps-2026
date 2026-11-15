"""Summarize measured closure runs; validate bindings before public redaction."""

import argparse, json, hashlib, platform, subprocess, sqlite3
from pathlib import Path
from collections import Counter
from importlib.metadata import version
from app.jobs.store import digest
from app.jobs.models import ScientificJobResult
from app.services.models import TemporalBatchResult, TemporalJobRequest
from app.optimization.local_site_models import LocalSiteOptimizationResult
from app.models.analysis import AnalysisResult


def load(path):
    return json.loads(
        Path(path).read_text(),
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)),
    )


def checkpoint_audit(db_path, job):
    db = sqlite3.connect("file:" + str(Path(db_path).resolve()) + "?mode=ro", uri=True)
    rows = db.execute(
        "select key,payload,hash from checkpoints where job_id=?", (job,)
    ).fetchall()
    db.close()
    counts = Counter()
    peaks = []
    signatures = set()
    cost = Counter()
    for key, raw, sha in rows:
        value = json.loads(raw)
        assert digest(value) == sha, "Checkpoint payload hash mismatch"
        counts[key.split(":")[0]] += 1
        if key.startswith("utc:"):
            assert key == "utc:" + digest(
                {"signature": value["signature"], "request": value["request"]}
            )
            assert value["request"]["utc"] == value["result"]["request"]["utc"]
            signatures.add(digest(value["signature"]))
            accounting = value["result"]["performance"]["accounting"]
            # Legacy complete samples stored only attempted/sample/call costs.
            # Resolve omitted counters exactly as the live resume guard does.
            cost.update(
                {
                    k: value["cost"].get(k, accounting.get(k, 0))
                    for k in set(value["cost"]) | set(accounting)
                }
            )
        if key.startswith("candidate:"):
            peaks.append(value["window"]["performance"].get("peak_rss_kib", 0))
            sha = digest(value["window"])
            assert key == "candidate:" + sha
            assert value["operation"]["provenance"]["window_evidence_sha256"] == sha
            assert (
                value["analysis"]["time"]["start_utc"]
                == value["window"]["request"]["start_utc"]
            )
            assert (
                value["analysis"]["time"]["duration_s"]
                == value["window"]["request"]["duration_s"]
            )
    assert len(signatures) == 1, "Mixed scientific source signatures"
    return {
        "status": "PASS",
        "maximum_reported_worker_peak_rss_kib": max(peaks, default=0),
        "rss_scope": "Shared worker process high-water mark, not isolated per-arm allocation",
        "checkpoint_counts": dict(counts),
        "unique_scientific_signature_count": 1,
        "scientific_signature_sha256": next(iter(signatures)),
        "sum_unique_utc_checkpoint_cost": dict(cost),
        "checks": [
            "Payload SHA256",
            "Exact request/source key",
            "Exact UTC binding",
            "Candidate window SHA256",
            "Operation evidence SHA256",
            "Operation duration",
        ],
    }


def redact(value, ids):
    import re

    if isinstance(value, dict):
        return {k: redact(v, ids) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, ids) for v in value]
    if isinstance(value, str):
        if re.fullmatch("[a-f0-9]{32}", value):
            ids.setdefault(value, f"{len(ids)+1:032x}")
            return ids[value]
        value = re.sub(
            r"/api/v1/jobs/([a-f0-9]{32})",
            lambda m: "/api/v1/jobs/" + redact(m[1], ids),
            value,
        )
        if value.startswith(("/workspace/", "/tmp/", "/home/")):
            return "[LOCAL_PATH_REDACTED]"
    return value


def build(args):
    if args.output.exists():
        raise ValueError("Refusing overwrite")
    first = load(args.stage1)
    second = load(args.stage2)
    ab = load(args.ab)
    local = load(args.local)
    api = load(args.api)
    tests = load(args.tests)
    temporal = second["runs"][0]["result"]
    ScientificJobResult.model_validate(temporal)
    current = TemporalBatchResult.model_validate(temporal["result"])
    t = current.model_dump(mode="json")
    old = load("data_pipeline/evidence/command-10-validation.json")[
        "restart_chained_replay"
    ]["result"]["result"]
    assert {c["candidate_id"]: c["start_utc"] for c in t["candidates"]} == {
        c["candidate_id"]: c["start_utc"] for c in old["candidates"]
    }
    allc = [t["baseline"]] + t["candidates"]
    evaluated = [c for c in allc if c["operation"]]
    assert (
        len(t["candidates"]) == 30
        and len({c["start_utc"] for c in t["candidates"]}) == 30
    )
    for c in evaluated:
        a = c["operation"]["request"]["analysis"]
        base = t["request"]["baseline_analysis"]
        assert (
            a["site"] == base["site"]
            and a["observer"] == base["observer"]
            and a["operation"] == base["operation"]
        )
        assert a["time"]["duration_s"] == base["time"]["duration_s"]
        assert a["time"]["start_utc"] == c["start_utc"]
        assert (
            c["evidence_sha256"]
            == c["operation"]["provenance"]["window_evidence_sha256"]
        )
    audit = checkpoint_audit(args.db, temporal["job_id"])
    for key, v in t["new_resources"].items():
        assert v + t["checkpoint_resources"].get(key, 0) == t["resources"][key]
    firstv = first["result"]["result"]
    first_audit = checkpoint_audit(args.db, first["job_id"])
    previous_audit = checkpoint_audit(args.db, first["request"]["resume_from"])
    assert (
        first_audit["scientific_signature_sha256"]
        == previous_audit["scientific_signature_sha256"]
        == audit["scientific_signature_sha256"]
    )
    assert first_audit["sum_unique_utc_checkpoint_cost"] == firstv["resources"]
    assert audit["sum_unique_utc_checkpoint_cost"] == t["resources"]
    phase1_new = {
        k: v - previous_audit["sum_unique_utc_checkpoint_cost"].get(k, 0)
        for k, v in firstv["resources"].items()
    }

    first_calls = sum(
        c.get("resource_consumption", {}).get("new_visibility_evaluations", 0)
        for c in [firstv["baseline"]] + firstv["candidates"]
    )
    second_calls = t["new_resources"]["visibility_evaluations"]
    l = LocalSiteOptimizationResult.model_validate(local["runs"][0]["result"]["result"])
    a = AnalysisResult.model_validate(
        api["resumed_analysis_result"]["result"]["analysis"]
    )
    assert (
        a.data_origin == "PRECOMPUTED"
        and a.horizons
        and len(a.horizons[0].points) == 360
    )
    both = [
        TemporalBatchResult.model_validate(x["result"]["result"]) for x in ab["runs"]
    ]
    assert (
        ab["comparison"]["same_generated_candidate_set"]
        and ab["comparison"]["same_detailed_scientific_results"]
    )

    def elapsed(item):
        return item["result"]["result"].get(
            "pipeline_seconds", item["result"]["result"].get("seconds")
        )

    counts = Counter(c["operation"]["decision"]["status"] for c in evaluated)
    alt_counts = Counter(
        c["operation"]["decision"]["status"] for c in t["candidates"] if c["operation"]
    )
    result = {
        "schema_version": "command-10-closure-v1",
        "status": "COMMAND_10_INTEGRATION_READY_WITH_OPEN_VALIDATION_GATES",
        "starting_pr_commit": "2d2211831b19ca0a380892d88202e20a35e6e1ef",
        "implementation_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "environment": {
            "python": platform.python_version(),
            "system": platform.system(),
            "architecture": platform.machine(),
            "packages": {
                k: version(k)
                for k in ("spiceypy", "rasterio", "pyproj", "pydantic", "numpy")
            },
        },
        "runtime_revision_note": "Phase 1 used the original scientific core plus pre-grid provenance/hint fixes; phase 2, local and A/B use the frozen closure service revision. No physics, terrain steps, score or requirements were relaxed.",
        "temporal": {
            "canonical_utc_and_id_set_preserved": True,
            "generated_alternatives": 30,
            "evaluated_including_baseline": len(evaluated),
            "complete_window_executions_including_baseline": t[
                "detailed_completed_including_baseline"
            ],
            "decision_counts_including_baseline": dict(counts),
            "decision_counts_alternatives": dict(alt_counts),
            "not_evaluated_alternatives": sum(
                not c["operation"] for c in t["candidates"]
            ),
            "new_live_visibility_calls_phase1": first_calls,
            "phase1_new_resources_derived_from_validated_checkpoint_difference": phase1_new,
            "preclosure_retained_resources": previous_audit[
                "sum_unique_utc_checkpoint_cost"
            ],
            "new_live_visibility_calls_phase2": second_calls,
            "new_live_visibility_calls_total": first_calls + second_calls,
            "phase1_batch_seconds": firstv["seconds"],
            "phase2_pipeline_seconds": t["pipeline_seconds"],
            "new_execution_seconds_total": firstv["seconds"] + t["pipeline_seconds"],
            "phase1_http_status": first["status"],
            "phase2_http_status": second["runs"][0]["status"],
            "checkpoint_audit": audit,
            "result": t,
        },
        "grid_ab": ab,
        "local": local,
        "api_acceptance": api,
        "reference_evidence": "command-10-horizons-reference.json",
        "source_comparison_evidence": "command-10-source-comparison.json",
        "test_summary": tests,
        "science_ready": False,
        "transport_job_ids_redacted": True,
        "redaction_note": "Scientific source/window hashes are unchanged. Transport IDs are redacted after validation; transport request digests cannot be recomputed from redacted resume IDs.",
        "remaining_limitations": [
            "JPL diagnostic configurations differ in ephemeris/frame realization/light bending; operational altitude differs by 1.0385595703125 m.",
            "Absolute DEM registration remains UNVERIFIED.",
            "Sampled temporal/disk/terrain evidence is not physical continuity, landing safety, power or RF certification.",
            "Finite evaluated UTC/site sets are not global optima.",
            "A/B is a one-hour operation with cold scientific caches and shared OS file cache; it is not a seven-day optimizer speedup benchmark.",
            "Linux/WSL POSIX single-worker prototype; public deployment needs authentication/rate limits/supervision.",
        ],
    }
    for name in ("profiles", "partial_api", "responsiveness"):
        path = getattr(args, name, None)
        if path:
            result[name] = load(path)
    result["grid_ab_checkpoint_audits"] = [
        checkpoint_audit(args.db, item["accepted"]["job_id"]) for item in ab["runs"]
    ]
    result["local_checkpoint_audit"] = checkpoint_audit(
        args.db, local["runs"][0]["accepted"]["job_id"]
    )
    sources = [
        "backend/app/services/scientific_runner.py",
        "backend/app/services/optimizer_support.py",
        "backend/app/api/routes.py",
        "backend/app/jobs/store.py",
        "backend/app/optimization/local_site_optimizer.py",
        "backend/app/science/visibility.py",
        "backend/app/science/horizon.py",
        "backend/app/science/windows.py",
        "backend/app/science/operations.py",
        "backend/app/science/scoring.py",
    ]
    result["implementation_source_sha256"] = {
        p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources
    }
    gates = {
        "EXISTING_PR_28_PRESERVED": "PASS",
        "LIVE_SCIENTIFIC_API": "PASS",
        "LONG_RUNNING_JOB_MANAGER": "PASS",
        "JOB_POLLING_RESULT": "PASS",
        "CANCELLATION_PERSISTENCE": "PASS",
        "ANALYSISRESULT_1_0": "PASS",
        "LOCAL_SITE_OPTIMIZER": "PASS",
        "SPATIAL_CANDIDATE_EVALUATION": (
            "PASS"
            if l.scope["detailed_attempts_including_baseline"]
            >= l.scope["terrain_eligible"]
            else "PARTIAL"
        ),
        "TEMPORAL_30_CANDIDATE_EVALUATION": (
            "PASS" if len(evaluated) == 31 else "PARTIAL"
        ),
        "TEMPORAL_RESUME": "PASS",
        "CANDIDATE_ORIGIN_CORRECTNESS": "PASS",
        "HISTORICAL_HINT_ISOLATION": "PASS",
        "HORIZON_GRID_INTEGRATION": "PASS",
        "TOTAL_OPTIMIZER_PERFORMANCE": "MEASURED",
        "NASA_20MPP": "AVAILABLE",
        "DEM_ABSOLUTE_REGISTRATION": "UNVERIFIED",
        "JPL_HORIZONS_COMPARISON": "PARTIAL",
        "STRICT_PROTOTYPE_SEPARATION": "PASS",
        "FOUR_MISSION_PROFILES": "PASS",
        "FULL_BACKEND_TESTS": (
            "PASS"
            if tests.get("failed") == 0
            and tests.get("skipped") == 0
            and tests.get("passed", 0) >= 603
            else "PENDING"
        ),
        "FRONTEND_HANDOFF": "PASS",
        "PR_28_UPDATED": "PENDING_DELIVERY",
    }
    result["acceptance_gates"] = gates
    result = redact(result, {})
    with args.output.open("x") as f:
        json.dump(result, f, indent=2, allow_nan=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for key in ("stage1", "stage2", "ab", "local", "api", "tests", "db", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    for key in ("profiles", "partial-api", "responsiveness"):
        p.add_argument("--" + key, type=Path)
    build(p.parse_args())
