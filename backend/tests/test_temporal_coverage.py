"""Coverage is discovery/selection diversity, never a fabricated NASA evaluation."""

from datetime import timedelta
import pytest
from test_temporal_optimizer import config, changed, dataset
from app.science.temporal_optimizer import discover, optimize, RecordedProvider
from app.science.window_models import EventBracket


def hint(q):
    w = dataset(q)[0]
    t = q.search_start_utc + timedelta(hours=8)
    w.brackets = [
        EventBracket(
            definition_id="synthetic",
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
    return w


@pytest.mark.parametrize("cap", [1, 2, 4, 8])
def test_bounded_deterministic_full_horizon_pool(config, cap):
    q = changed(
        config,
        selection_strategy="COVERAGE_AWARE",
        max_coarse_candidates=cap,
        search_end_utc=config.search_start_utc + timedelta(days=7),
    )
    a, info = discover(q)
    b, _ = discover(q)
    assert a == b and len(a) <= cap and len({t for t, s in a}) == len(a)
    assert all(
        q.search_start_utc <= t and t + timedelta(hours=6) <= q.search_end_utc
        for t, s in a
    )
    if cap >= 2:
        assert max(t for t, s in a) >= q.search_end_utc - timedelta(hours=6)


def test_diverse_prefix_beats_event_cluster(config):
    base = changed(
        config,
        max_detailed_candidates=4,
        search_end_utc=config.search_start_utc + timedelta(days=7),
    )
    w = hint(base)
    old, _ = discover(base, [w])
    q = changed(base, selection_strategy="COVERAGE_AWARE")
    new, info = discover(q, [w])
    span = lambda rows: (
        max(t for t, s in rows[:3]) - min(t for t, s in rows[:3])
    ).total_seconds()
    assert span(new) > span(old)
    assert "EVENT_BRACKET_POST_REFINEMENT" in new[0][1]
    assert info["selected_span_s"] == span(new)
    assert new == discover(q, [w, w])[0]


def test_not_selected_distinct_from_resource_limit(config):
    q = changed(config, selection_strategy="COVERAGE_AWARE", max_detailed_candidates=2)
    r = optimize(q, RecordedProvider(dataset(q)))
    assert r.search_scope["detailed_attempts_including_baseline"] == 2
    assert r.search_scope["selected_for_detailed_including_baseline"] == 2
    assert r.search_scope["not_selected"] > 0
    assert r.search_scope["not_evaluated_resource_limit"] == 0
    assert r.search_status == "SEARCH_PARTIAL_SELECTION_LIMIT"
    for c in r.candidates:
        if c.evaluation_status == "NOT_SELECTED_FOR_DETAILED_EVALUATION":
            assert c.operation is None and c.reason_codes == [
                "CANDIDATE_STRATEGY_NOT_SELECTED"
            ]


def test_cap_spans_search_end_vs_legacy(config):
    base = changed(
        config,
        max_coarse_candidates=8,
        search_end_utc=config.search_start_utc + timedelta(days=7),
    )
    a, _ = discover(base)
    b, _ = discover(changed(base, selection_strategy="COVERAGE_AWARE"))
    assert max(t for t, s in b) > max(t for t, s in a)


@pytest.mark.parametrize("strategy", ["LEGACY", "COVERAGE_AWARE"])
def test_same_science_and_requirements(config, strategy):
    q = changed(config, selection_strategy=strategy, max_detailed_candidates=2)
    r = optimize(q, RecordedProvider(dataset(q)))
    for c in [r.baseline] + r.candidates:
        if c.operation:
            assert (
                c.operation.request.analysis.operation == q.baseline_analysis.operation
            )
            assert (
                c.operation.request.analysis.time.duration_s
                == q.baseline_analysis.time.duration_s
            )
    assert len(r.recommendations) <= q.max_recommendations


def test_benchmark_recorded_json_and_overwrite(tmp_path):
    import json
    from data_pipeline.temporal_optimizer_benchmark import run

    path = tmp_path / "recorded.json"
    run("recorded", path)
    value = json.loads(path.read_text())
    assert value["mode"] == "recorded" and value["outcome"] == "CANDIDATES_FOUND"
    with pytest.raises(ValueError, match="Refusing overwrite"):
        run("recorded", path)


def test_pool_truncation_is_not_missing_evidence(config):
    q = changed(
        config,
        selection_strategy="COVERAGE_AWARE",
        max_coarse_candidates=1,
        max_detailed_candidates=3,
    )
    r = optimize(q, RecordedProvider(dataset(q)))
    assert r.search_scope["evidence_unavailable"] == 0
    assert r.search_scope["not_selected"] == 0
    assert r.search_status == "SEARCH_PARTIAL_SELECTION_LIMIT"
