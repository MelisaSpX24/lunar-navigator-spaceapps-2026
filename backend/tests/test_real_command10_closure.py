"""Derived real JPL/NASA artifacts: assertions are not fresh live calculations."""

import json
from pathlib import Path
from data_pipeline.horizons_reference_validation import angular_difference, statistics

ROOT = Path("data_pipeline/evidence")


def test_uploaded_horizons_diagnostic_is_not_false_equivalence_pass():
    data = json.loads((ROOT / "command-10-horizons-reference.json").read_text())
    assert data["status"] == "CONFIGURATION_MISMATCH"
    assert (
        data["exact_common_utc_count"] == 17 and data["equivalent_matched_samples"] == 0
    )
    assert (
        data["references"]["sun"]["sha256"]
        == "9deb71fadaeba15150d2fb82d1806d51f1cd87695f88af3652a8f06817a25a12"
    )
    assert (
        data["references"]["earth"]["sha256"]
        == "d8f8b531f237e5e4bbc888a0736ee81f613fa01daeffb94765a17a58cca783ac"
    )
    assert (
        data["requested_utc_alignment"]["2026-11-23T17:26:15Z"]
        == "REJECTED_NO_EXACT_REFERENCE_UTC"
    )
    assert (
        data["requested_utc_alignment"]["2026-11-27T02:00:00Z"]
        == "REJECTED_NO_EXACT_REFERENCE_UTC"
    )
    aligned = [
        x
        for x in data["comparisons"]
        if x["mode"] == "REFERENCE_ALIGNED_DIAGNOSTIC" and x["correction"] == "LT+S"
    ]
    assert len(aligned) == 17
    for row in aligned:
        assert (
            row["observer_altitude_m"]
            == 1000 * data["references"]["sun"]["altitude_km"]
        )
        for body in row["bodies"].values():
            assert body["azimuth_difference_deg"] == angular_difference(
                body["backend_azimuth_deg"], body["reference_azimuth_deg"]
            )
            assert body["numeric_acceptance"] == "CONFIGURATION_MISMATCH"
            assert "OBSERVER_ALTITUDE_MISMATCH" not in body["configuration_reasons"]
            assert (
                "GRAVITATIONAL_DEFLECTION_NOT_MODELED_BY_LT_S"
                in body["configuration_reasons"]
            )
    for name in ("sun", "earth"):
        residual = [x["bodies"][name]["elevation_difference_deg"] for x in aligned]
        assert (
            statistics(residual)
            == data["diagnostic_statistics"]["REFERENCE_ALIGNED_DIAGNOSTIC:LT+S"][name][
                "elevation"
            ]
        )


def test_live_20m_comparison_preserves_default_and_registration_limits():
    data = json.loads((ROOT / "command-10-source-comparison.json").read_text())
    assert not data["default_changed"]
    assert len(data["rows"]) == 16
    ref = data["source_identities"]["20m"]
    assert (
        ref["sha256"]
        == "09b7ca80f9e6a146f970225d18af72fc02787669b3ef51b888e347d2b6845649"
    )
    assert ref["resolution_m"] == [20, 20] and ref["shape"] == [30400, 30400]
    assert not ref["reference"]["product_specific_frame_verified"]
    for role in ("5m", "20m", "80m"):
        assert data["summary"][role]["valid_points"] == 16
        assert data["summary"][role]["slope_known"] == 16
        cov = data["sampled_5km_disk_coverage"][role]
        assert cov["status"] == "COMPLETE_SAMPLED_DISK"
        assert cov["disk_pixel_centres"] == cov["valid_height_pixels"]
    assert (
        data["rows"][0]["sources"]["20m"]["surface_elevation_m"]
        != data["rows"][0]["sources"]["80m"]["surface_elevation_m"]
    )


def test_complete_canonical_batch_is_not_equated_with_suitability():
    from app.services.models import TemporalBatchResult

    data = json.loads((ROOT / "command-10-closure.json").read_text())
    t = data["temporal"]
    r = TemporalBatchResult.model_validate(t["result"])
    assert t["canonical_utc_and_id_set_preserved"] and len(r.candidates) == 30
    assert (
        r.detailed_evaluated_including_baseline
        == r.detailed_completed_including_baseline
        == 31
    )
    assert r.not_evaluated_alternatives == 0
    assert t["decision_counts_including_baseline"] == {
        "MET": 16,
        "NOT_MET": 13,
        "INCOMPLETE": 2,
    }
    assert (
        r.baseline.operation.decision.status == "NOT_MET"
        and r.baseline.operation.score.value == 0
    )
    assert r.recommendations[0]["start_utc"] == "2026-11-23T16:26:15Z"
    assert all(c["operation"]["decision"]["status"] == "MET" for c in r.recommendations)
    assert all(
        c.operation.score.value is None
        for c in r.candidates
        if c.operation.decision.status == "INCOMPLETE"
    )
    assert t["checkpoint_audit"]["checkpoint_counts"] == {"candidate": 31, "utc": 189}
    assert t["new_live_visibility_calls_total"] == 161
    for k, v in r.new_resources.items():
        assert v + r.checkpoint_resources.get(k, 0) == r.resources[k]


def test_real_grid_optimizer_ab_preserves_exact_results_without_fake_speedup():
    data = json.loads((ROOT / "command-10-closure.json").read_text())["grid_ab"]
    assert data["comparison"]["same_generated_candidate_set"]
    assert data["comparison"]["same_detailed_scientific_results"]
    assert not data["comparison"]["default_strategy_changed"]
    a, b = [x["result"]["result"] for x in data["runs"]]
    assert a["request"] == b["request"]
    assert (
        a["new_resources"]["visibility_evaluations"]
        == b["new_resources"]["visibility_evaluations"]
        == 3
    )
    assert b["screening"]["new_grid_resources"]["completed_rays"] == 360
    assert b["pipeline_seconds"] >= b["screening"]["preparation_seconds"]
    assert b["pipeline_seconds"] > a["pipeline_seconds"]
    assert all(
        c["evidence_mode"] == "LIVE"
        for v in (a, b)
        for c in [v["baseline"]] + v["candidates"]
    )


def test_more_local_candidates_and_real_partial_api_remain_honest():
    from app.models.analysis import AnalysisResult
    from app.optimization.local_site_models import LocalSiteOptimizationResult

    data = json.loads((ROOT / "command-10-closure.json").read_text())
    local = LocalSiteOptimizationResult.model_validate(
        data["local"]["runs"][0]["result"]["result"]
    )
    assert local.scope["selection_strategy"] == "TERRAIN_DIVERSE"
    assert local.scope["detailed_attempts_including_baseline"] == 4
    assert len(local.recommendations) == 3
    assert (
        local.new_scientific_resources["visibility_evaluations"] == 4
        and local.checkpoint_reused == 4
    )
    assert all(
        c.operation.decision.status == "MET" and c.distance_m <= 5000 + 1e-7
        for c in local.recommendations
    )
    assert local.baseline.operation.request.analysis.time.duration_s == 3600
    api = data["api_acceptance"]
    assert api["checks"]["queue_capacity_http"] == 429
    result = api["resumed_analysis_result"]["result"]
    a = AnalysisResult.model_validate(result["analysis"])
    assert a.data_origin == "PRECOMPUTED" and len(a.horizons[0].points) == 360
    partial = data["partial_api"]
    assert partial["status"]["status"] == "PARTIAL"
    assert partial["result"]["result"]["analysis"] is None
    assert partial["result"]["result"]["operation_evidence"]["score"]["value"] is None
    assert len(data["profiles"]["rows"]) == 8
