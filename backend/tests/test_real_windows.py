"""Assertions against a freshly generated real NASA CLI run; not synthetic/live reruns."""

import json, os
from pathlib import Path
import pytest
from app.science.window_models import WindowSearchResult


@pytest.fixture(scope="module")
def evidence():
    path = os.environ.get("NASA_WINDOWS_EVIDENCE")
    if not path:
        pytest.skip("Set NASA_WINDOWS_EVIDENCE to a fresh windows_cli real NASA result")
    return WindowSearchResult.model_validate_json(Path(path).read_text())


def test_real_timeline(evidence):
    assert len(evidence.timeline) == 7
    assert [s.time_utc.hour for s in evidence.timeline] == list(range(8, 15))
    assert all(s.source_identity and s.bodies for s in evidence.timeline)


def test_real_sources(evidence):
    assert evidence.source_evidence["kernel_ids"]
    assert evidence.source_evidence["dem"]
    assert not evidence.science_ready


def test_real_windows(evidence):
    assert evidence.execution_status == "COMPLETED"
    assert all(
        s.sun == "NOT_MET" and s.earth == "MET" and s.joint == "NOT_MET"
        for s in evidence.timeline
    )
    assert evidence.sampled_windows["sun"] == []
    assert evidence.sampled_windows["joint"] == []
    assert len(evidence.sampled_windows["earth"]) == 1


def test_real_estimate_limits(evidence):
    assert evidence.metrics["earth"].estimated_duration_s == 21600
    assert all(
        m.duration_lower_bound_s is None and m.duration_upper_bound_s is None
        for m in evidence.metrics.values()
    )
    assert evidence.sampled_windows["earth"][0].start_censored
    assert evidence.sampled_windows["earth"][0].end_censored
    assert not evidence.brackets


def test_real_budget(evidence):
    assert evidence.performance["visibility_evaluations"] == 7
    assert evidence.performance["visibility_accounting"]["dem_samples"] > 0
    assert (
        evidence.performance["visibility_accounting"]["attempted_rays"]
        <= evidence.request.max_new_rays
    )
