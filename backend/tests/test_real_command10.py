"""Assertions on actual HTTP/CLI NASA artifacts; not new live executions per test."""

import json
from pathlib import Path
import pytest
from app.models.analysis import AnalysisResult
from app.jobs.models import ScientificJobResult
from app.services.models import TemporalBatchResult
from app.optimization.local_site_models import LocalSiteOptimizationResult


@pytest.fixture(scope="module")
def evidence():
    return json.loads(
        Path("data_pipeline/evidence/command-10-validation.json").read_text()
    )


def test_real_http_analysis(evidence):
    r = ScientificJobResult.model_validate(evidence["initial_live_http_analysis"])
    a = AnalysisResult.model_validate(r.result["analysis"])
    assert r.status == "COMPLETED" and a.data_origin == "LIVE_COMPUTED"
    assert a.sources and a.series and a.decision.status == "NOT_MET"
    assert not evidence["http_lifecycle"]["health"]["science_ready"]


def test_real_local(evidence):
    r = evidence["http_lifecycle"]["runs"]["local"]["result"]["result"]
    assert (
        r["scope"]["generated_including_baseline"] == 16
        and r["scope"]["slopes_known"] == 16
    )
    assert (
        r["scope"]["terrain_eligible"] == 8
        and r["scope"]["detailed_attempts_including_baseline"] == 2
    )
    LocalSiteOptimizationResult.model_validate(r)
    c = r["recommendations"][0]
    b = r["baseline"]
    assert 0 < c["distance_m"] <= 5000 and c["terrain"]["slope_deg"] <= 10
    assert (
        c["operation"]["decision"]["status"] == "MET"
        and b["operation"]["decision"]["status"] == "NOT_MET"
    )
    assert (
        c["operation"]["provenance"]["sources"]
        == b["operation"]["provenance"]["sources"]
    )


def test_real_temporal_and_chained_resume(evidence):
    r = evidence["restart_chained_replay"]["result"]["result"]
    assert (
        r["generated_alternatives"] == 30
        and r["detailed_completed_including_baseline"] == 4
    )
    assert r["resources"]["attempted_rays"] == r["resources"]["completed_rays"] == 3640
    assert r["data_origin"] == "PRECOMPUTED" and r["checkpoint_reused"] >= 28
    assert len(r["recommendations"]) == 2
    typed = evidence["typed_temporal_http"]
    current = TemporalBatchResult.model_validate(typed["result"]["result"])
    assert typed["result_schema_http"] == 200
    assert current.detailed_completed_including_baseline == 4
    assert current.data_origin == "PRECOMPUTED"
    assert evidence["temporal_resume"]["result"]["checkpoint_reused"] >= 21


def test_real_cancel_restart(evidence):
    e = evidence["http_lifecycle"]
    assert e["completed_survived_restart"]
    assert e["runs"]["cancel_analysis"]["status"]["status"] == "CANCELLED"
    assert e["runs"]["cancel_analysis"]["result"]["result"][
        "partial_single_utc_visibility"
    ]
    assert e["runs"]["resume_analysis"]["result"]["result"]["checkpoint_reused"] == 2


def test_real_grid(evidence):
    r = evidence["horizon_grid"]
    assert r["runs"]["1.0"]["known_directions"] == 360
    assert r["runs"]["0.5"]["known_directions"] == 720
    assert r["exact_disk_verification"]["sun_state"] == "NONE"
    for data in r["runs"].values():
        assert data["complete_scheduled_grid"]
        assert all(
            not x["lookup"]["strict_visibility_evidence"]
            for x in data["exact_comparisons"]
        )


def test_real_sources_sampling_and_reference_limits(evidence):
    assert (
        evidence["lola20"]["status"] == "AVAILABLE"
        and evidence["lola20"]["expected_sha256_match"]
    )
    assert not evidence["lola20"]["used_as_default"]
    assert evidence["external_reference_access"]["horizons_status"] == "INCONCLUSIVE"
    rows = evidence["temporal_sampling"]["rows"]
    assert [r["step_s"] for r in rows] == [3600, 1800, 900]
    assert all(
        r["metrics"]["sun"]["estimated_duration_s"] == 0
        and r["metrics"]["earth"]["estimated_duration_s"] == 3600
        for r in rows
    )


def test_real_http_requested_horizon(evidence):
    data = evidence["live_horizon_analysis"]["result"]["result"]
    a = AnalysisResult.model_validate(data["analysis"])
    assert a.horizons and len(a.horizons[0].points) == 360
    assert a.horizons[0].coverage_complete and a.data_origin == "LIVE_COMPUTED"
    assert all(s.sun.horizon_id == a.horizons[0].id for s in a.series)
    assert all(
        x["http_status"] == 200 for x in evidence["api_profile_regression"]["rows"]
    )
    assert (
        evidence["api_profile_regression"]["unavailable_full_horizon_recorded_http"]
        == 404
    )
