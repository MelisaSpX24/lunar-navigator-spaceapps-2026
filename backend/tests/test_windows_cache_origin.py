"""Exact-cache integration uses synthetic terrain; no NASA evidence is rewritten."""

import pytest
from app.science.visibility import VisibilityEngine
from app.science.visibility_models import VisibilityRequest
from app.science.window_models import WindowSearchRequest
from app.science.windows import VisibilityEvaluator, run_windows, search
from app.science.kernels import ScienceError
from test_visibility import Session, fake
from test_horizon import synthetic, req


def request(**changes):
    values = dict(
        visibility=VisibilityRequest(
            terrain=req(max_range_m=100), utc="2026-11-20T08:00:00Z"
        ),
        start_utc="2026-11-20T08:00:00Z",
        duration_s=3600,
    )
    return WindowSearchRequest(**(values | changes))


@pytest.mark.parametrize(
    "budget",
    [
        {"max_new_rays": 0},
        {"max_terrain_samples": 0},
        {"max_new_rays": 0, "max_terrain_samples": 0},
    ],
)
@pytest.mark.parametrize("warm", [True, False])
def test_zero_budget_exact_cache(tmp_path, fake, budget, warm):
    with synthetic(tmp_path) as h:
        e = VisibilityEngine(Session(), h.terrain)
        e.horizon = h
        q = request(**budget)
        if warm:
            e.run(q.visibility)
        before = e.counters()
        sample = VisibilityEvaluator(e, q)(q.start_utc)
        after = e.counters()
        assert after["attempted_rays"] == before["attempted_rays"]
        assert after["dem_samples"] == before["dem_samples"]
        if warm:
            assert sample.sun == "MET" and sample.earth == "NOT_MET"
            assert after["cache_hits"] - before["cache_hits"] == 130
        else:
            assert sample.sun == sample.earth == "UNKNOWN"
            assert "COMPUTATION_BUDGET_EXCEEDED" in sample.reason_codes


def test_partial_cache_does_not_generate_rays(tmp_path, fake):
    with synthetic(tmp_path) as h:
        e = VisibilityEngine(Session(), h.terrain)
        e.horizon = h
        q = request(max_new_rays=0)
        e.run(q.visibility)
        e.cache.popitem()
        before = e.counters()
        s = VisibilityEvaluator(e, q)(q.start_utc)
        assert s.earth == "UNKNOWN" or "COMPUTATION_BUDGET_EXCEEDED" in s.reason_codes
        assert e.counters()["attempted_rays"] == before["attempted_rays"]
        assert e.counters()["dem_samples"] == before["dem_samples"]
        assert e.counters()["cache_hits"] > before["cache_hits"]


@pytest.mark.parametrize("mode", ["no_evaluations", "source_error", "completed"])
def test_live_origin_never_defaults_to_synthetic(tmp_path, fake, monkeypatch, mode):
    monkeypatch.setattr(
        "app.science.astronomy.utc_to_et", lambda session, utc: utc.timestamp()
    )
    with synthetic(tmp_path) as h:
        e = VisibilityEngine(Session(), h.terrain)
        e.horizon = h
        q = request(max_visibility_evaluations=0 if mode == "no_evaluations" else 32)
        if mode == "source_error":

            def fail(q):
                raise ScienceError("DEM_SOURCE_UNAVAILABLE", "fixture failure")

            monkeypatch.setattr(e, "run", fail)
        if mode == "completed":
            original = e.run

            def tagged(q):
                return original(q).model_copy(
                    update={"data_origin": "REAL_NASA_PROTOTYPE"}
                )

            monkeypatch.setattr(
                e, "run", tagged
            )  # provenance routing test, NOT a real NASA execution
        r = run_windows(e, q)
        assert r.data_origin == (
            "REAL_NASA_PROTOTYPE" if mode == "completed" else "MIXED_OR_UNVERIFIED"
        )
        assert not r.science_ready


def test_synthetic_and_unverified_search_origins():
    q = request(max_visibility_evaluations=0)

    def unused(t):
        raise AssertionError("budget should prevent calls")

    assert search(q, unused).data_origin == "SYNTHETIC_TEST"
    assert (
        search(q, unused, source_identity="live-source").data_origin
        == "MIXED_OR_UNVERIFIED"
    )
