"""Synthetic SPICE/terrain integration of optimizer-level global guards."""

import pytest
from test_visibility import fake, Session
from test_horizon import synthetic, req
from test_temporal_optimizer import config, changed, dataset
from app.science.temporal_optimizer import LiveProvider, optimize, RecordedProvider
from app.science.visibility import VisibilityEngine
from app.science.window_models import WindowSearchRequest


@pytest.mark.parametrize("visibility_limit", [0, 1, 2])
def test_global_visibility_limit(tmp_path, fake, config, monkeypatch, visibility_limit):
    monkeypatch.setattr(
        "app.science.astronomy.utc_to_et", lambda session, utc: utc.timestamp()
    )
    with synthetic(tmp_path) as h:
        v = config.window_template.model_dump()
        v["visibility"]["terrain"] = req(max_range_m=100).model_dump()
        v["step_s"] = 21600
        q = changed(
            config,
            window_template=WindowSearchRequest.model_validate(v),
            baseline_analysis=config.baseline_analysis.model_dump(exclude_unset=True)
            | {"site": {"kind": "COORDINATES", **req().location.model_dump()}},
            max_window_evaluations=visibility_limit,
            max_detailed_candidates=2,
        )
        engine = VisibilityEngine(Session(), h.terrain)
        engine.horizon = h
        r = optimize(q, LiveProvider(engine, q))
        assert r.resource_consumption["visibility_evaluations"] <= visibility_limit
        assert r.resource_consumption["dem_samples"] <= q.max_terrain_samples
        if visibility_limit == 2:
            assert engine.hits >= 130  # static mocked geometry reuses exact azimuths
        else:
            assert not r.recommendations


@pytest.mark.parametrize("rays,points", [(0, 10000), (130, 0), (1, 1), (5, 10000)])
def test_global_ray_and_point_limits(tmp_path, fake, config, monkeypatch, rays, points):
    monkeypatch.setattr(
        "app.science.astronomy.utc_to_et", lambda session, utc: utc.timestamp()
    )
    with synthetic(tmp_path) as h:
        v = config.window_template.model_dump()
        v["visibility"]["terrain"] = req(max_range_m=100).model_dump()
        v["step_s"] = 21600
        q = changed(
            config,
            window_template=WindowSearchRequest.model_validate(v),
            baseline_analysis=config.baseline_analysis.model_dump(exclude_unset=True)
            | {"site": {"kind": "COORDINATES", **req().location.model_dump()}},
            max_new_horizon_rays=rays,
            max_terrain_samples=points,
            max_detailed_candidates=2,
        )
        e = VisibilityEngine(Session(), h.terrain)
        e.horizon = h
        r = optimize(q, LiveProvider(e, q))
        assert e.misses <= rays and e.dem_samples <= points
        assert not r.recommendations


def test_cache_capacity_guard(tmp_path, fake, config):
    with synthetic(tmp_path) as h:
        q = changed(config, max_cache_entries=1)
        with pytest.raises(ValueError):
            LiveProvider(VisibilityEngine(Session(), h.terrain, cache_size=2), q)


def test_wall_admission_preserves_baseline(config, monkeypatch):
    q = changed(config, max_wall_time_s=0.5)
    p = RecordedProvider(dataset(q))
    old = p.get
    clock = [0]
    monkeypatch.setattr(
        "app.science.temporal_optimizer.time.perf_counter", lambda: clock[0]
    )

    def slow(w):
        result = old(w)
        clock[0] += 1
        return result

    p.get = slow
    r = optimize(q, p)
    assert r.baseline.operation is not None and not r.recommendations
    assert all(
        c.evaluation_status == "NOT_EVALUATED_RESOURCE_LIMIT" for c in r.candidates
    )
