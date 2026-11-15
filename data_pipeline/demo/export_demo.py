"""Deterministic recorded-evidence export. No science engines or live sessions."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
from app.models.analysis import AnalysisRequest, Decision, Score
from app.science.window_models import WindowMetrics
from app.services.models import TemporalBatchResult
from app.optimization.local_site_models import LocalSiteOptimizationResult

ROOT = Path(__file__).resolve().parents[2]
CLOSURE = "data_pipeline/evidence/command-10-closure.json"
INITIAL = "data_pipeline/evidence/command-10-validation.json"


def encoded(value):
    return (
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build(root=ROOT):
    raw = (root / CLOSURE).read_bytes()
    initial_raw = (root / INITIAL).read_bytes()
    evidence = json.loads(raw)
    assert (
        json.loads(initial_raw)["latest_validation"]["evidence"]
        == "command-10-closure.json"
    )
    t = TemporalBatchResult.model_validate(evidence["temporal"]["result"])
    l = LocalSiteOptimizationResult.model_validate(
        evidence["local"]["runs"][0]["result"]["result"]
    )
    # Retain original JSON rather than expanding unset Requirements fields.
    tr = evidence["temporal"]["result"]
    lr = evidence["local"]["runs"][0]["result"]["result"]
    source = t.baseline.operation.provenance["sources"]
    source_id = sha(encoded(source))
    provenance = {
        "id": source_id,
        "full_source_evidence_sha256": source_id,
        "hash_encoding": "sorted indent=2 finite JSON plus newline",
        "dem": {
            k: {
                "product": v["reference"]["product_id"],
                "sha256": v["reference"]["raster_sha256"],
                "version": v["reference"]["product_version"],
                "source_url": v["reference"]["source_url"],
                "resolution_m": v["resolution_m"],
                "product_specific_frame_verified": v["reference"][
                    "product_specific_frame_verified"
                ],
                "quality_layers": v["quality"],
            }
            for k, v in source["dem"].items()
        },
        "kernel_ids": source["kernel_ids"],
        "frame": "MOON_ME_DE421",
        "absolute_registration": "UNVERIFIED",
    }

    def candidate(c, request, temporal):
        op = c["operation"]
        assert (
            op
            and c["evaluation_status" if temporal else "stage"] == "DETAILED_EVALUATED"
        )
        assert op["provenance"]["sources"] == source
        assert c["evidence_sha256"] == op["provenance"]["window_evidence_sha256"]
        a = AnalysisRequest.model_validate(request)
        assert a == AnalysisRequest.model_validate(op["request"]["analysis"])
        Decision.model_validate(op["decision"])
        Score.model_validate(op["score"])
        for metric in c["metrics"].values():
            WindowMetrics.model_validate(metric)
        return {
            "candidate_id": c["candidate_id"],
            "source_request": request,
            "explicit_requirement_fields": sorted(request["operation"]["requirements"]),
            "evaluation_status": c["evaluation_status" if temporal else "stage"],
            "evaluation_policy": op["request"]["evaluation_policy"],
            "decision": op["decision"],
            "planning_score": op["score"],
            "rule_evidence": op["rule_evidence"],
            "metrics": c["metrics"],
            "source_identity": source_id,
            "window_evidence_sha256": c["evidence_sha256"],
            "scientific_data_origin": op["data_origin"],
            "delivery_data_origin": "RECORDED_EVIDENCE_EXPORT",
            "scientific_evidence_status": "SAMPLED_ESTIMATE",
            "data_quality": op["quality"],
            "limitations": op["limitations"],
            "terrain": (
                None
                if temporal
                else {
                    k: v
                    for k, v in c["terrain"].items()
                    if k
                    in (
                        "status",
                        "eligible",
                        "surface_elevation_m",
                        "slope_deg",
                        "slope_method",
                        "product_id",
                        "sha256",
                        "resolution_m",
                        "quality",
                        "overlap_spread_m",
                        "warnings",
                    )
                }
            ),
            "distance_m": None if temporal else c["distance_m"],
            "bearing_deg": None if temporal else c["bearing_deg"],
            "analysis_result": None,
            "horizon_profile": None,
            "time_series": None,
            "window_segments": None,
        }

    temporal_base = copy.deepcopy(tr["request"]["baseline_analysis"])
    temporal_alt = next(
        c for c in tr["candidates"] if c["start_utc"] == "2026-11-23T16:26:15Z"
    )
    alt_request = copy.deepcopy(temporal_base)
    alt_request["time"]["start_utc"] = temporal_alt["start_utc"]
    local_base = copy.deepcopy(
        evidence["local"]["runs"][0]["request"]["optimization"]["baseline_analysis"]
    )
    local_alts = []
    for c in lr["recommendations"]:
        request = copy.deepcopy(local_base)
        request["site"] = {"kind": "COORDINATES", **c["location"]}
        local_alts.append(candidate(c, request, False))
    common = {
        "schema_version": "24and28-demo-evidence-v1",
        "source_reference": {"file": CLOSURE, "sha256": sha(raw)},
        "source_provenance": provenance,
        "science_ready": False,
        "unavailable_fields_reason": "Optimizer summary exports are not AnalysisResult 1.0; full profiles, timelines and window segments are not provided by this package.",
    }
    temporal = common | {
        "scenario_id": "cr1-same-site-better-time",
        "comparison_dimension": "START_UTC_ONLY",
        "source_pointer": "/temporal/result",
        "source_optimizer_request": tr["request"],
        "baseline": candidate(tr["baseline"], temporal_base, True),
        "alternatives": [candidate(temporal_alt, alt_request, True)],
        "limitations": tr["limitations"],
    }
    local = common | {
        "scenario_id": "cr1-same-time-better-site",
        "comparison_dimension": "COORDINATES_AND_DEM_SURFACE_ONLY",
        "source_pointer": "/local/runs/0/result/result",
        "source_optimizer_request": evidence["local"]["runs"][0]["request"][
            "optimization"
        ],
        "baseline": candidate(lr["baseline"], local_base, False),
        "alternatives": local_alts,
        "search_scope": lr["scope"],
        "search_status": lr["search_status"],
        "limitations": lr["limitations"],
    }
    assert (
        temporal["baseline"]["decision"]["status"] == "NOT_MET"
        and temporal["baseline"]["planning_score"]["value"] == 0
    )
    assert (
        temporal["alternatives"][0]["decision"]["status"] == "MET"
        and temporal["alternatives"][0]["planning_score"]["value"] == 100
    )
    assert len(local_alts) == 3 and all(
        c["decision"]["status"] == "MET" for c in local_alts
    )
    files = {"temporal_demo.json": encoded(temporal), "local_demo.json": encoded(local)}
    manifest = {
        "schema_version": "24and28-demo-manifest-v1",
        "delivery_data_origin": "RECORDED_EVIDENCE_EXPORT",
        "new_live_calculations": False,
        "science_ready": False,
        "sources": [
            {"file": CLOSURE, "sha256": sha(raw)},
            {"file": INITIAL, "sha256": sha(initial_raw)},
        ],
        "files": {k: {"sha256": sha(v), "bytes": len(v)} for k, v in files.items()},
        "contract": "Backend-local demo projection; not AnalysisResult 1.0 or a complete optimizer API response.",
        "limitations": [
            "Prototype sampled estimates are not physical continuity, electrical power, RF success or landing certification.",
            "Temporal six-hour and spatial one-hour comparisons must remain separate.",
            "Only the selected evaluated alternatives are exported; no global optimality claim.",
        ],
    }
    files["manifest.json"] = encoded(manifest)
    return files


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    p.add_argument(
        "--check",
        action="store_true",
        help="Validate exact deterministic bytes against checked-in package",
    )
    args = p.parse_args()
    files = build()
    if args.check:
        for name, raw in files.items():
            if (args.output_dir / name).read_bytes() != raw:
                raise ValueError("Demo differs from evidence: " + name)
    else:
        if any((args.output_dir / name).exists() for name in files):
            raise ValueError("Refusing overwrite")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, raw in files.items():
            with (args.output_dir / name).open("xb") as f:
                f.write(raw)
    print("Validated recorded demo package; no live science executed.")


if __name__ == "__main__":
    main()
