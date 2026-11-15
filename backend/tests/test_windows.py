"""Independent deterministic temporal fixtures, never NASA observations."""

from datetime import timedelta
import itertools
import pytest
from app.science.window_models import WindowSearchRequest, TemporalConditionSample
from app.science.windows import (
    search,
    solar_condition,
    earth_condition,
    joint_condition,
    definition_id,
)
from data_pipeline.visibility_validation import pilot


def request(**kw):
    d = dict(
        visibility=pilot(),
        start_utc="2026-11-20T08:00:00Z",
        duration_s=3600,
        step_s=900,
        max_visibility_evaluations=64,
        max_refinements=30,
        event_resolution_s=1,
    )
    d.update(kw)
    return WindowSearchRequest(**d)


def simulate(fn, **kw):
    q = request(**kw)

    def evaluate(t):
        s = fn((t - q.start_utc).total_seconds())
        return TemporalConditionSample(time_utc=t, sun=s, earth="MET", joint=s)

    return search(q, evaluate)


@pytest.mark.parametrize("state", ["MET", "NOT_MET", "UNKNOWN"])
def test_constant(state):
    r = simulate(lambda t: state)
    assert len(r.segments["sun"]) == 1 and not r.brackets
    p = r.segments["sun"][0]
    assert p.condition == state and p.start_censored == (state == "MET")
    assert p.end_censored == (state == "MET")
    assert r.metrics["sun"].duration_lower_bound_s is None
    assert r.sampled_windows["sun"] == (
        [] if state == "NOT_MET" else None if state == "UNKNOWN" else [p]
    )


@pytest.mark.parametrize(
    "fn,types",
    [
        (lambda t: "MET" if t >= 1200 else "NOT_MET", ["START"]),
        (lambda t: "MET" if t < 1200 else "NOT_MET", ["LOSS"]),
        (lambda t: "MET" if 900 <= t < 2700 else "NOT_MET", ["START", "LOSS"]),
        (lambda t: "NOT_MET" if 900 <= t < 2700 else "MET", ["LOSS", "START"]),
    ],
)
def test_crossings(fn, types):
    r = simulate(fn)
    e = [b for b in r.brackets if b.family == "sun"]
    assert [b.event_type for b in e] == types
    assert all(b.width_s <= 1 and b.status == "EVENT_BRACKETED" for b in e)
    assert all(p.end_utc > p.start_utc for p in r.segments["sun"])


def test_unknown_middle_does_not_merge():
    r = simulate(lambda t: "UNKNOWN" if t == 1800 else "MET")
    assert [p.condition for p in r.segments["sun"]] == ["MET", "UNKNOWN", "MET"]
    assert r.sampled_windows["sun"] is None
    assert not r.brackets


def test_unknown_boundary_no_event():
    r = simulate(lambda t: "UNKNOWN" if t == 0 else "MET")
    assert not r.brackets and r.next_events["sun_start"]["event_utc"] is None


def test_double_crossing_adaptive_and_missed_short_event():
    fn = lambda t: "NOT_MET" if 1700 < t < 1900 else "MET"
    coarse = simulate(fn, step_s=3600)
    assert (
        not coarse.brackets and coarse.scientific_evidence_status == "SAMPLED_ESTIMATE"
    )
    fine = simulate(fn, step_s=3600, midpoint_depth=1)
    assert len([b for b in fine.brackets if b.family == "sun"]) == 2
    missed = simulate(lambda t: "NOT_MET" if 1320 < t < 1440 else "MET")
    assert not missed.brackets
    assert any("short events" in x for x in missed.limitations)


@pytest.mark.parametrize(
    "a,b", list(itertools.product(["MET", "NOT_MET", "UNKNOWN"], repeat=2))
)
def test_truth_table(a, b):
    expected = (
        "NOT_MET"
        if a == "NOT_MET" or b == "NOT_MET"
        else "MET" if a == b == "MET" else "UNKNOWN"
    )
    assert joint_condition(a, b) == expected


@pytest.mark.parametrize(
    "lo,hi,t,expected",
    [
        (0, 0, 0.5, "NOT_MET"),
        (0.5, 0.5, 0.5, "MET"),
        (1, 1, 0.5, "MET"),
        (0, 1, 0.5, "UNKNOWN"),
        (0.5, 1, 0.5, "MET"),
        (0, 0.499999999, 0.5, "NOT_MET"),
        (None, None, 0.5, "UNKNOWN"),
    ],
)
def test_solar_threshold(lo, hi, t, expected):
    assert solar_condition(lo, hi, t) == expected


@pytest.mark.parametrize(
    "v,m,s",
    [
        (1, 0, "MET"),
        (-1, 0, "NOT_MET"),
        (0, 0, "MET"),
        (None, 0, "UNKNOWN"),
        (1, 2, "NOT_MET"),
    ],
)
def test_earth_margin(v, m, s):
    assert earth_condition(v, m) == s


@pytest.mark.parametrize(
    "kw",
    [
        {"duration_s": 0},
        {"duration_s": -1},
        {"start_utc": "bad"},
        {"start_utc": "2026-11-20T08:00:00"},
        {"start_utc": "2026-11-20T08:00:00+03:00"},
        {"step_s": 0},
        {"max_temporal_samples": 2},
    ],
)
def test_invalid_requests(kw):
    with pytest.raises(ValueError):
        request(**kw)


def test_budget_preserves_unknown_and_confinement():
    r = simulate(lambda t: "MET", max_visibility_evaluations=2)
    assert r.execution_status == "PARTIAL" and r.sampled_windows["sun"] is None
    assert r.metrics["sun"].unknown_duration_s == 3600
    assert r.segments["sun"][0].start_utc == r.request.start_utc
    assert r.segments["sun"][-1].end_utc == r.request.end_utc


def test_budget_midpoint_does_not_certify_interval():
    r = simulate(lambda t: "MET", step_s=3600, midpoint_depth=1, max_temporal_samples=2)
    assert r.segments["sun"][0].condition == "UNKNOWN"


def test_definition_and_microseconds():
    a = request(start_utc="2026-11-20T08:00:00.123456Z")
    b = request(solar_fraction=0.8)
    assert definition_id(a, "sun", "x") != definition_id(b, "sun", "x")
    assert definition_id(a, "sun", "x") != definition_id(a, "sun", "y")
    assert a.start_utc.microsecond == 123456


def test_unrefined_bracket_and_joint_disabled():
    r = simulate(
        lambda t: "MET" if t > 1000 else "NOT_MET", max_refinements=0, joint=False
    )
    assert r.brackets[0].status == "EVENT_BRACKET_NOT_REFINED"
    assert "joint" not in r.segments


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_conditions_rejected(bad):
    with pytest.raises(ValueError):
        solar_condition(0, 1, bad)
    with pytest.raises(ValueError):
        earth_condition(bad, 0)
