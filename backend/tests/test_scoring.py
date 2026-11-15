"""Scorer coefficient validation and finite mathematical output."""

import pytest
from app.science.scoring import compute_planning_score
from test_operations import windows


@pytest.mark.parametrize(
    "weights",
    [
        {"earth_availability": -1},
        {"earth_availability": 0},
        {"earth_availability": float("nan")},
        {"earth_availability": float("inf")},
        {"earth_availability": 0.9},
        {"unknown": 1},
    ],
)
def test_bad_weights(windows, weights):
    with pytest.raises(ValueError):
        compute_planning_score(windows, "PROTOTYPE_SAMPLED_ESTIMATE", weights)


@pytest.mark.parametrize("fraction", [0, 0.25, 0.5, 0.75, 1])
def test_linear_score(windows, fraction):
    windows.metrics["earth"].estimated_duration_s = (
        windows.request.duration_s * fraction
    )
    s, detail = compute_planning_score(
        windows, "PROTOTYPE_SAMPLED_ESTIMATE", {"earth_availability": 1}
    )
    assert s.value == 100 * fraction
    assert detail[0]["contribution_points"] == s.value
