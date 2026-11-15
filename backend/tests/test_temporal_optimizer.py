"""Deterministic synthetic UTC search and decision-first ranking regressions."""

import json
from datetime import timedelta
from pathlib import Path
import pytest
from app.science.window_models import WindowSearchResult
from app.science.temporal_optimizer_models import TemporalOptimizationRequest
from app.science.temporal_optimizer import (
    RecordedProvider,
    LiveProvider,
    optimize,
    discover,
    shifted_requests,
    candidate_rank,
    compare,
)
from app.science.windows import search
from app.science.window_models import TemporalConditionSample
from app.science.operations import evidence_identity


@pytest.fixture
def config():
    w = WindowSearchResult.model_validate(
        json.loads(Path("data_pipeline/evidence/command-07-windows.json").read_text())[
            "pilot"
        ]
    )
    return TemporalOptimizationRequest(
        baseline_analysis={
            "site": {
                "kind": "COORDINATES",
                **w.request.visibility.terrain.location.model_dump(),
            },
            "time": {"start_utc": w.request.start_utc, "duration_s": 21600},
            "operation": {
                "profile": "SOLAR_POWERED_EXPERIMENT",
                "requirements": {"min_sun_visible_s": 3600},
            },
        },
        window_template=w.request,
        evaluation_policy="PROTOTYPE_SAMPLED_ESTIMATE",
        search_start_utc=w.request.start_utc,
        search_end_utc=w.request.start_utc + timedelta(days=1),
        max_detailed_candidates=5,
    )


def fixture_window(q, utc, sun="MET", earth="MET"):
    _, w = shifted_requests(q, utc)

    def sample(t):
        joint = (
            "NOT_MET"
            if "NOT_MET" in (sun, earth)
            else "MET" if sun == earth == "MET" else "UNKNOWN"
        )
        return TemporalConditionSample(
            time_utc=t,
            sun=sun,
            earth=earth,
            joint=joint,
            source_identity="synthetic-fixture",
        )

    return search(
        w,
        sample,
        source_evidence={
            "dem": {"synthetic": "fixture"},
            "kernel_ids": ["synthetic"],
            "data_origin": "SYNTHETIC_TEST",
        },
    )


def dataset(q, first="NOT_MET", later="MET"):
    starts = [q.baseline_analysis.time.start_utc] + [t for t, _ in discover(q)[0]]
    return [
        fixture_window(q, t, first if i == 0 else later) for i, t in enumerate(starts)
    ]


def changed(q, **kw):
    return TemporalOptimizationRequest.model_validate(
        q.model_dump(exclude_unset=True) | kw
    )


def test_improvement_hash_and_fixed_requirements(config):
    windows = dataset(config)
    r = optimize(config, RecordedProvider(windows))
    assert (
        r.baseline.operation.decision.status == "NOT_MET"
        and r.baseline.operation.score.value == 0
    )
    assert r.outcome == "CANDIDATES_FOUND" and len(r.recommendations) == 3
    assert r.recommendations[0].operation.decision.status == "MET"
    assert r.comparisons[0].score_delta == 100
    assert r.baseline.evidence_sha256 != r.recommendations[0].evidence_sha256
    assert r.recommendations[0].evidence_sha256 == evidence_identity(windows[1])
    for c in [r.baseline] + r.candidates:
        a = c.operation.request.analysis
        assert (
            a.site == config.baseline_analysis.site
            and a.observer == config.baseline_analysis.observer
        )
        assert (
            a.operation == config.baseline_analysis.operation
            and a.time.duration_s == 21600
        )
        assert a.operation.requirements.model_fields_set == {"min_sun_visible_s"}
        assert c.end_utc - c.start_utc == timedelta(hours=6)


@pytest.mark.parametrize(
    "policy,first,later,outcome",
    [
        ("STRICT_EVIDENCE", "NOT_MET", "MET", "ONLY_INCOMPLETE_CANDIDATES"),
        ("PROTOTYPE_SAMPLED_ESTIMATE", "MET", "MET", "KEEP_CURRENT_PLAN"),
        (
            "PROTOTYPE_SAMPLED_ESTIMATE",
            "NOT_MET",
            "NOT_MET",
            "NO_ELIGIBLE_CANDIDATE_IN_EVALUATED_SET",
        ),
        (
            "PROTOTYPE_SAMPLED_ESTIMATE",
            "UNKNOWN",
            "UNKNOWN",
            "ONLY_INCOMPLETE_CANDIDATES",
        ),
    ],
)
def test_outcomes(config, policy, first, later, outcome):
    q = changed(config, evaluation_policy=policy)
    r = optimize(q, RecordedProvider(dataset(q, first, later)))
    assert r.outcome == outcome and not r.recommendations
    if first == "MET":
        assert all(x.classification == "EQUIVALENT_ALTERNATIVE" for x in r.comparisons)


@pytest.mark.parametrize("budget", [1, 2, 3])
def test_detailed_limit(config, budget):
    q = changed(config, max_detailed_candidates=budget)
    r = optimize(q, RecordedProvider(dataset(q)))
    assert r.search_scope["detailed_attempts_including_baseline"] == budget
    assert r.search_status == "SEARCH_PARTIAL_RESOURCE_LIMIT"
    assert sum(c.operation is not None for c in r.candidates) == budget - 1
    assert all(
        c.operation is None
        for c in r.candidates
        if c.evaluation_status == "NOT_EVALUATED_RESOURCE_LIMIT"
    )


def test_missing_recorded_not_synthetic(config):
    r = optimize(config, RecordedProvider([]))
    assert r.baseline.operation is None and r.baseline.evidence_mode is None
    assert (
        not r.recommendations
        and r.search_status == "SEARCH_PARTIAL_EVIDENCE_UNAVAILABLE"
    )


def test_no_repeated_utc_and_deterministic(config):
    hints = dataset(config)
    rows, _ = discover(config, hints + hints)
    assert len({t for t, s in rows}) == len(rows)
    a = optimize(config, RecordedProvider(hints))
    b = optimize(config, RecordedProvider(hints))
    assert a.ranked_suggestions == b.ranked_suggestions
    assert [c.reason_codes for c in a.candidates] == [
        c.reason_codes for c in b.candidates
    ]
    assert [c.start_utc for c in a.recommendations] == sorted(
        c.start_utc for c in a.recommendations
    )


def test_ranking_mandatory_first(config):
    r = optimize(config, RecordedProvider(dataset(config)))
    good = r.recommendations[0].model_copy(deep=True)
    bad = r.baseline.model_copy(deep=True)
    good.operation.score.value = 82
    bad.operation.score.value = 95
    assert candidate_rank(good) < candidate_rank(bad)
    bad.operation.decision.status = "INCOMPLETE"
    bad.operation.score.value = 100
    assert candidate_rank(good) < candidate_rank(bad)


@pytest.mark.parametrize(
    "field,value",
    [
        ("search_end_utc", "2026-11-20T09:00:00Z"),
        ("search_end_utc", "invalid"),
        ("search_start_utc", "2026-11-20T08:00:00"),
        ("search_start_utc", "2026-11-20T08:00:00+03:00"),
        ("max_detailed_candidates", 0),
        ("coarse_start_step_s", 0),
        ("max_wall_time_s", float("nan")),
    ],
)
def test_invalid_requests(config, field, value):
    with pytest.raises(ValueError):
        changed(config, **{field: value})


def test_horizon_fits_and_baseline_off_grid(config):
    q = changed(config, search_start_utc=config.search_start_utc + timedelta(minutes=1))
    rows, _ = discover(q)
    assert all(t + timedelta(hours=6) <= q.search_end_utc for t, _ in rows)
    r = optimize(q, RecordedProvider(dataset(q)))
    assert r.baseline.start_utc == config.baseline_analysis.time.start_utc


def test_coarse_limit_not_not_met(config):
    q = changed(config, max_coarse_candidates=1, max_detailed_candidates=1)
    r = optimize(q, RecordedProvider(dataset(q)))
    assert len(r.candidates) <= 1 and not r.recommendations
    assert r.search_status == "SEARCH_PARTIAL_RESOURCE_LIMIT"
    assert all(c.operation is None for c in r.candidates)


@pytest.mark.parametrize(
    "mutation", ["source", "sampling", "height", "threshold", "utc", "duration"]
)
def test_incompatible_candidate(config, mutation):
    windows = dataset(config)
    w = windows[1]
    if mutation == "source":
        w.source_evidence["dem"] = {"different": "source"}
    if mutation == "sampling":
        w.request.step_s = 1800
    if mutation == "height":
        w.request.visibility.solar_height_above_surface_m = 2
    if mutation == "threshold":
        w.request.solar_fraction = 0.8
    if mutation == "utc":
        w.request.start_utc += timedelta(seconds=1)
    if mutation == "duration":
        w.request.duration_s = 10800
    # Keep dictionary keyed at the intended UTC to simulate a mismatched provider.
    p = RecordedProvider(dataset(config))
    p.windows[windows[0].request.start_utc + timedelta(hours=6)] = w
    r = optimize(config, p)
    c = r.candidates[0]
    assert c.candidate_id not in [x.candidate_id for x in r.recommendations]
    assert (
        c.comparison_validity == "COMPARISON_NOT_EQUIVALENT"
        or c.evaluation_status in ("INVALID", "PARTIAL")
    )


def test_requirement_override_7200_preserved(config):
    a = config.baseline_analysis.model_dump(exclude_unset=True)
    a["operation"]["requirements"]["min_sun_visible_s"] = 7200
    q = changed(config, baseline_analysis=a)
    r = optimize(q, RecordedProvider(dataset(q)))
    assert all(
        c.operation.request.analysis.operation.requirements.min_sun_visible_s == 7200
        for c in r.candidates
    )


@pytest.mark.parametrize(
    "profile,requirements",
    [
        ("EARTH_DATA_TRANSMISSION", {"min_earth_continuous_s": 3600}),
        ("SHORT_SURFACE_OBSERVATION", {"min_earth_continuous_s": 3600}),
        (
            "CUSTOM_OPERATION",
            {"require_simultaneous": True, "min_joint_continuous_s": 1800},
        ),
    ],
)
def test_profiles(config, profile, requirements):
    a = config.baseline_analysis.model_dump(exclude_unset=True)
    a["operation"] = {"profile": profile, "requirements": requirements}
    q = changed(config, baseline_analysis=a)
    r = optimize(q, RecordedProvider(dataset(q)))
    if profile == "CUSTOM_OPERATION":
        assert r.recommendations
    else:
        assert (
            r.outcome == "KEEP_CURRENT_PLAN" and r.baseline.operation.score.value == 100
        )


def test_recorded_duplicate_rejected(config):
    w = dataset(config)[0]
    with pytest.raises(ValueError):
        RecordedProvider([w, w])


@pytest.mark.parametrize("change", ["score_version", "policy", "weights", "observer"])
def test_comparison_rejects_non_equivalent_evidence(config, change):
    windows = dataset(config)
    r = optimize(config, RecordedProvider(windows))
    c = r.recommendations[0]
    if change == "score_version":
        c.operation.score.model_version = "different"
    if change == "policy":
        c.operation.request.evaluation_policy = "STRICT_EVIDENCE"
    if change == "weights":
        c.operation.score.components[0].weight = 0.1
    if change == "observer":
        windows[1].timeline[0].bodies = {
            "sun": {"observer": {"surface_elevation_m": 999}}
        }
    result = compare(r.baseline, c, windows[0], windows[1])
    assert result.validity == "COMPARISON_NOT_EQUIVALENT" and result.score_delta is None
    assert not result.duration_deltas_s


def test_discovery_hints_are_not_certified_decisions(config):
    from app.science.window_models import EventBracket

    w = dataset(config)[0]
    t = w.request.start_utc + timedelta(hours=8)
    w.brackets = [
        EventBracket(
            definition_id="fixture",
            family="sun",
            event_type="START",
            left_utc=t,
            right_utc=t + timedelta(seconds=675),
            left_condition="NOT_MET",
            right_condition="MET",
            width_s=675,
            evaluation_count=0,
            status="EVENT_BRACKET_NOT_REFINED",
        )
    ]
    rows, info = discover(config, [w])
    assert rows[0][0] == t + timedelta(seconds=675 + 3600)
    r = optimize(config, RecordedProvider([w]), hints=[w])
    assert not r.recommendations
    assert all(c.operation is None for c in r.candidates)


def test_incomplete_baseline_can_have_verified_alternative(config):
    r = optimize(config, RecordedProvider(dataset(config, "UNKNOWN", "MET")))
    assert (
        r.baseline.operation.decision.status == "INCOMPLETE"
        and r.baseline.operation.score.value is None
    )
    assert r.recommendations and r.comparisons[0].score_delta is None
    assert r.comparisons[0].duration_deltas_s["sun"] is None
