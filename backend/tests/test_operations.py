"""Deterministic synthetic operation/score regressions; real artifacts tested separately."""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.models.analysis import Requirements
from app.science.operation_models import OperationEvaluationRequest
from app.science.operations import evaluate_operation, evidence_identity
from app.science.window_models import WindowSearchResult


@pytest.fixture
def windows():
    # Explicit synthetic derivative, never reported as fresh NASA computation.
    value = json.loads(
        Path("data_pipeline/evidence/command-07-windows.json").read_text()
    )["pilot"]
    w = WindowSearchResult.model_validate(value)
    w.data_origin = "SYNTHETIC_TEST"
    w.source_evidence = {
        "dem": {"fixture": "synthetic derivative"},
        "kernel_ids": ["synthetic"],
    }
    return w


def operation(
    w,
    requirements=None,
    profile="CUSTOM_OPERATION",
    policy="PROTOTYPE_SAMPLED_ESTIMATE",
    **extra,
):
    a = {
        "site": {
            "kind": "COORDINATES",
            **w.request.visibility.terrain.location.model_dump(),
        },
        "time": {
            "start_utc": w.request.start_utc,
            "duration_s": int(w.request.duration_s),
        },
        "operation": {"profile": profile, "requirements": requirements or {}},
    }
    return OperationEvaluationRequest(
        analysis=a,
        evaluation_policy=policy,
        window_evidence_sha256=evidence_identity(w),
        **extra,
    )


@pytest.mark.parametrize(
    "profile",
    [
        "SOLAR_POWERED_EXPERIMENT",
        "EARTH_DATA_TRANSMISSION",
        "SHORT_SURFACE_OBSERVATION",
        "CUSTOM_OPERATION",
    ],
)
def test_empty_profile_is_incomplete(windows, profile):
    r = evaluate_operation(operation(windows, profile=profile), windows)
    assert r.decision.status == "INCOMPLETE" and r.score.value is None


@pytest.mark.parametrize(
    "requirements,status,score",
    [
        ({"min_sun_visible_s": 3600}, "NOT_MET", 0),
        ({"min_sun_visible_s": 0}, "MET", 0),
        ({"min_earth_continuous_s": 3600}, "MET", 100),
        ({"min_earth_continuous_s": 21600}, "MET", 100),
        ({"max_dark_gap_s": 21600}, "MET", 0),
        ({"max_dark_gap_s": 0}, "NOT_MET", 0),
        ({"require_simultaneous": True}, "NOT_MET", 0),
        ({"require_simultaneous": True, "min_joint_continuous_s": 1800}, "NOT_MET", 0),
        ({"earth_clearance_margin_deg": 0}, "MET", 100),
        ({"min_solar_disk_visible_fraction": 0.5}, "NOT_MET", 0),
    ],
)
def test_rules(windows, requirements, status, score):
    r = evaluate_operation(operation(windows, requirements), windows)
    assert r.decision.status == status and r.score.value == score
    assert all(
        x.policy == "PROTOTYPE_SAMPLED_ESTIMATE" and x.unit and x.source_metric
        for x in r.rule_evidence
    )
    assert all(
        "required" in x.rule.message and "sampled actual" in x.rule.message
        for x in r.rule_evidence
    )


@pytest.mark.parametrize(
    "requirements",
    [
        {"min_sun_visible_s": 3600},
        {"min_earth_continuous_s": 3600},
        {"max_dark_gap_s": 0},
        {"require_simultaneous": True},
        {"earth_clearance_margin_deg": 0},
    ],
)
def test_strict_null_bounds(windows, requirements):
    r = evaluate_operation(
        operation(windows, requirements, policy="STRICT_EVIDENCE"), windows
    )
    assert r.decision.status == "INCOMPLETE" and r.score.value is None


@pytest.mark.parametrize(
    "preset,explicit,expected",
    [("SOLAR_1H", {"min_sun_visible_s": 0}, 0), ("EARTH_1H", {}, 3600)],
)
def test_explicit_preset_override(windows, preset, explicit, expected):
    r = evaluate_operation(operation(windows, explicit, example_preset=preset), windows)
    key = "min_sun_visible_s" if preset == "SOLAR_1H" else "min_earth_continuous_s"
    assert r.effective_requirements[key] == expected
    assert r.assumption_labels == ["EXAMPLE_OPERATION_ASSUMPTION"]


@pytest.mark.parametrize(
    "change",
    [
        "time",
        "location",
        "height",
        "margin",
        "fraction",
        "correction",
        "source",
        "named",
    ],
)
def test_mismatch(windows, change):
    q = operation(windows, {"min_earth_continuous_s": 3600})
    v = q.model_dump(mode="json")
    if change == "time":
        v["analysis"]["time"]["duration_s"] = 10800
    if change == "location":
        v["analysis"]["site"]["latitude_deg"] = -89
    if change == "height":
        v["analysis"]["observer"]["solar_height_above_surface_m"] = 2
    if change == "margin":
        v["analysis"]["operation"]["requirements"]["earth_clearance_margin_deg"] = 2
    if change == "fraction":
        v["analysis"]["operation"]["requirements"][
            "min_solar_disk_visible_fraction"
        ] = 0.8
    if change == "correction":
        v["correction"] = "LT+S"
    if change == "source":
        v["window_evidence_sha256"] = "0" * 64
    if change == "named":
        v["analysis"]["site"] = {"kind": "SITE_ID", "site_id": "CR1"}
    r = evaluate_operation(OperationEvaluationRequest.model_validate(v), windows)
    assert r.decision.status == "INCOMPLETE" and r.score.value is None
    assert "ANALYSIS_WINDOW_MISMATCH" in r.decision.reason_codes


@pytest.mark.parametrize("bad", [-1, 21601, float("nan"), float("inf")])
def test_invalid_duration_metric(windows, bad):
    windows.metrics["earth"].estimated_duration_s = bad
    if not __import__("math").isfinite(bad):
        with pytest.raises(ValueError):
            operation(windows, {"min_earth_continuous_s": 3600})
    else:
        r = evaluate_operation(
            operation(windows, {"min_earth_continuous_s": 3600}), windows
        )
        assert r.score.value is None and r.decision.status == "INCOMPLETE"


def unknown_family(w, family):
    m = w.metrics[family]
    m.estimated_duration_s = 0
    m.estimated_longest_continuous_s = 0
    m.estimated_interruption_s = 0
    m.estimated_longest_interruption_s = 0
    m.unknown_duration_s = w.request.duration_s
    w.segments[family][0].condition = "UNKNOWN"
    w.sampled_windows[family] = None
    w.execution_status = "PARTIAL"


@pytest.mark.parametrize(
    "family,requirements",
    [
        ("sun", {"min_sun_visible_s": 3600}),
        ("earth", {"min_earth_continuous_s": 3600}),
        ("joint", {"require_simultaneous": True}),
    ],
)
def test_unknown_not_zero_score(windows, family, requirements):
    unknown_family(windows, family)
    r = evaluate_operation(operation(windows, requirements), windows)
    assert r.decision.status == "INCOMPLETE" and r.score.value is None


def test_unneeded_earth_does_not_block_short_solar(windows):
    unknown_family(windows, "earth")
    r = evaluate_operation(
        operation(
            windows, {"min_sun_visible_s": 0}, profile="SHORT_SURFACE_OBSERVATION"
        ),
        windows,
    )
    assert r.decision.status == "MET" and r.score.value == 0
    assert all("EARTH" not in x.code for x in r.decision.rules)


def test_not_met_dominates_unknown_and_score(windows):
    unknown_family(windows, "earth")
    r = evaluate_operation(
        operation(windows, {"min_sun_visible_s": 1, "min_earth_continuous_s": 1}),
        windows,
    )
    assert r.decision.status == "NOT_MET" and r.score.value is None


def test_high_score_cannot_hide_failure(windows):
    r = evaluate_operation(
        operation(
            windows,
            {"min_earth_continuous_s": 1, "min_sun_visible_s": 1},
            profile="EARTH_DATA_TRANSMISSION",
        ),
        windows,
    )
    assert r.score.value == 100 and r.decision.status == "NOT_MET"


def test_score_determinism_and_contributions(windows):
    q = operation(windows, {"min_sun_visible_s": 1, "min_earth_continuous_s": 1})
    a = evaluate_operation(q, windows)
    b = evaluate_operation(q, windows)
    assert a == b
    assert a.score.value == pytest.approx(100 * 2 / 3)
    assert sum(x.weight for x in a.score.components) == pytest.approx(1)
    assert sum(x["contribution_points"] for x in a.score_details) == a.score.value


def test_strict_total_bounds_only(windows):
    windows.metrics["sun"].duration_upper_bound_s = 0
    r = evaluate_operation(
        operation(windows, {"min_sun_visible_s": 1}, policy="STRICT_EVIDENCE"), windows
    )
    assert r.decision.status == "NOT_MET"
    windows.metrics["earth"].duration_lower_bound_s = 21600
    r = evaluate_operation(
        operation(windows, {"min_earth_continuous_s": 1}, policy="STRICT_EVIDENCE"),
        windows,
    )
    assert r.decision.status == "INCOMPLETE"  # total bound is not continuity bound


@pytest.mark.parametrize(
    "requirements",
    [
        {"min_joint_continuous_s": 1},
        {"earth_clearance_margin_deg": -1},
        {"min_sun_visible_s": 21601},
    ],
)
def test_invalid_requirements(windows, requirements):
    with pytest.raises(ValidationError):
        operation(windows, requirements)


def test_default_strict_and_missing_input(windows):
    with pytest.raises(ValidationError):
        OperationEvaluationRequest.model_validate({})
    q = operation(windows)
    v = q.model_dump()
    v.pop("evaluation_policy")
    assert (
        OperationEvaluationRequest.model_validate(v).evaluation_policy
        == "STRICT_EVIDENCE"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "source_missing",
        "source_hash",
        "origin",
        "segment_overlap",
        "metric_sum",
        "longest",
        "certified_bounds",
    ],
)
def test_bad_evidence_incomplete(windows, mutation):
    if mutation == "source_missing":
        windows.source_evidence = {}
    if mutation == "source_hash":
        windows.data_origin = "REAL_NASA_PROTOTYPE"
        windows.source_evidence = {
            "dem": {
                "X": {
                    "reference": {
                        "raster_sha256": "wrong",
                        "target_spice_frame": "MOON_ME_DE421",
                    }
                }
            },
            "kernel_ids": ["wrong"],
        }
    if mutation == "origin":
        windows.data_origin = "MIXED_OR_UNVERIFIED"
    if mutation == "segment_overlap":
        windows.segments["earth"].append(windows.segments["earth"][0])
    if mutation == "metric_sum":
        windows.metrics["earth"].estimated_duration_s = 100
    if mutation == "longest":
        windows.metrics["sun"].estimated_longest_continuous_s = 1
    if mutation == "certified_bounds":
        windows.metrics["sun"].duration_lower_bound_s = 100
        windows.metrics["sun"].duration_upper_bound_s = 0
    r = evaluate_operation(operation(windows, {"min_earth_continuous_s": 1}), windows)
    assert r.decision.status == "INCOMPLETE" and r.score.value is None


@pytest.mark.parametrize("margin", [0, 2, 90])
def test_matching_margin(windows, margin):
    windows.request.earth_margin_deg = margin
    r = evaluate_operation(
        operation(
            windows,
            {"earth_clearance_margin_deg": margin, "min_earth_continuous_s": 3600},
        ),
        windows,
    )
    assert r.decision.status == "MET"
    assert f"{margin}" in r.decision.rules[-1].message


def test_all_solar_components_one(windows):
    m = windows.metrics["sun"]
    m.estimated_duration_s = m.estimated_longest_continuous_s = 21600
    m.estimated_interruption_s = m.estimated_longest_interruption_s = 0
    windows.segments["sun"][0].condition = "MET"
    windows.sampled_windows["sun"] = windows.segments["sun"]
    r = evaluate_operation(
        operation(
            windows, {"min_sun_visible_s": 3600}, profile="SOLAR_POWERED_EXPERIMENT"
        ),
        windows,
    )
    assert r.score.value == 100
    assert [x.weight for x in r.score.components] == [0.45, 0.35, 0.20]


def test_unknown_gap_not_merged(windows):
    from datetime import timedelta

    p = windows.segments["earth"][0]
    a = p.start_utc
    b = a + timedelta(hours=2)
    c = b + timedelta(hours=2)
    windows.segments["earth"] = [
        p.model_copy(update={"end_utc": b}),
        p.model_copy(update={"start_utc": b, "end_utc": c, "condition": "UNKNOWN"}),
        p.model_copy(update={"start_utc": c}),
    ]
    m = windows.metrics["earth"]
    m.estimated_duration_s = 14400
    m.estimated_longest_continuous_s = 7200
    m.unknown_duration_s = 7200
    windows.sampled_windows["earth"] = None
    r = evaluate_operation(
        operation(windows, {"min_earth_continuous_s": 10800}), windows
    )
    assert r.decision.status == "INCOMPLETE" and r.score.value is None
    assert r.decision.rules[0].actual == 7200


def test_named_resolution_evidence(windows):
    from app.models.analysis import NamedSite, ResolvedSite

    q = operation(windows, {"min_earth_continuous_s": 3600})
    q.analysis.site = NamedSite(kind="SITE_ID", site_id="CR1")
    q.resolved_site = ResolvedSite(
        **windows.request.visibility.terrain.location.model_dump()
    )
    q.resolved_site_id = "CR1"
    assert evaluate_operation(q, windows).decision.status == "MET"


def test_unknown_mandatory_rule_blocks_even_unweighted_score(windows):
    unknown_family(windows, "sun")
    q = operation(
        windows,
        {"min_earth_continuous_s": 1, "min_sun_visible_s": 1},
        profile="EARTH_DATA_TRANSMISSION",
    )
    r = evaluate_operation(q, windows)
    assert r.decision.status == "INCOMPLETE" and r.score.value is None
