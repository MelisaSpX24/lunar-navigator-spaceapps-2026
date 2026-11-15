"""Recorded real NASA artifact evaluation; no fresh astronomy calculations."""

import json
from pathlib import Path
import pytest
from app.science.window_models import WindowSearchResult
from app.science.operations import evaluate_operation
from test_operations import operation


@pytest.fixture
def real_windows():
    return WindowSearchResult.model_validate(
        json.loads(Path("data_pipeline/evidence/command-07-windows.json").read_text())[
            "pilot"
        ]
    )


@pytest.mark.parametrize(
    "profile,requirements,status,score",
    [
        ("EARTH_DATA_TRANSMISSION", {"min_earth_continuous_s": 3600}, "MET", 100),
        ("SOLAR_POWERED_EXPERIMENT", {"min_sun_visible_s": 3600}, "NOT_MET", 0),
        (
            "CUSTOM_OPERATION",
            {"require_simultaneous": True, "min_joint_continuous_s": 1800},
            "NOT_MET",
            0,
        ),
        ("SHORT_SURFACE_OBSERVATION", {"min_earth_continuous_s": 3600}, "MET", 100),
    ],
)
def test_real_profiles(real_windows, profile, requirements, status, score):
    r = evaluate_operation(
        operation(real_windows, requirements, profile=profile), real_windows
    )
    assert r.decision.status == status and r.score.value == score
    assert r.quality.status == "LIMITED"
    assert (
        r.provenance["sources"]["kernel_ids"]
        == real_windows.source_evidence["kernel_ids"]
    )
    assert r.data_origin == "REAL_NASA_PROTOTYPE"
    strict = evaluate_operation(
        operation(
            real_windows, requirements, profile=profile, policy="STRICT_EVIDENCE"
        ),
        real_windows,
    )
    assert strict.decision.status == "INCOMPLETE" and strict.score.value is None
