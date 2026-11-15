"""Synthetic integration, budgets and exact-ray caching regressions."""
from contextlib import contextmanager
from types import SimpleNamespace
import pytest
from app.science.visibility import VisibilityEngine
from app.science.visibility_models import VisibilityRequest
from app.science.astronomy import Direction
from app.science.kernels import ScienceError
from test_horizon import synthetic,req

class Session:
    @contextmanager
    def call(self):yield

@pytest.fixture
def fake(monkeypatch):
    calls=[]
    def calculate(s,o,t,c):
        calls.append(o)
        return SimpleNamespace(sun=Direction(azimuth_deg=0,elevation_deg=10,distance_km=1000000),earth=Direction(azimuth_deg=90,elevation_deg=-10,distance_km=100000),time_utc=t.isoformat(),kernel_ids=['pck00011.tpc:synthetic'])
    monkeypatch.setattr('app.science.visibility.calculate',calculate)
    monkeypatch.setattr('app.science.visibility.spice.bodvrd',lambda *a:(3,[100,100,100]))
    return calls

@pytest.mark.parametrize('solar,earth',[(1,1),(2,1),(1,2),(0,0)])
def test_height_cache_and_series(tmp_path,fake,solar,earth):
    with synthetic(tmp_path) as horizon:
        engine=VisibilityEngine(Session(),horizon.terrain);engine.horizon=horizon
        request=VisibilityRequest(terrain=req(max_range_m=100),utc='2026-11-20T08:00:00Z',solar_height_above_surface_m=solar,earth_height_above_surface_m=earth)
        a=engine.run(request);b=engine.run(request)
        assert a.sun.observer.device_height_m==solar and a.earth.observer.device_height_m==earth
        assert a.sun.state=='FULL' and a.earth.state=='NONE'
        assert b.performance['new_rays']==0 and b.performance['cache_hits']==130
        assert a.sun.horizon_ids==b.sun.horizon_ids
        assert {o.device_height_m for o in fake}=={solar,earth}
        series=engine.series(request,2,60)
        assert series.samples[0].request.utc<series.samples[1].request.utc
        assert series.performance['new_rays']==0
        changed=engine.run(VisibilityRequest.model_validate(request.model_dump()|{'solar_height_above_surface_m':solar+3}))
        assert changed.sun.horizon_ids!=a.sun.horizon_ids
        assert not changed.science_ready

@pytest.mark.parametrize('budget',[0,1,3])
def test_budget_unknown(tmp_path,fake,budget):
    with synthetic(tmp_path) as h:
        e=VisibilityEngine(Session(),h.terrain);e.horizon=h
        r=e.run(VisibilityRequest(terrain=req(max_range_m=100),utc='2026-11-20T08:00:00Z',max_new_rays=budget))
        assert r.sun.state==r.earth.state=='UNKNOWN'
        assert r.sun.visible_fraction is None and r.earth.visible_fraction is None
        assert r.performance['new_rays']<=budget
        assert 'COMPUTATION_BUDGET_EXCEEDED' in r.earth.reason_codes

@pytest.mark.parametrize('count,step',[(0,1),(13,1),(2,0),(2,86401)])
def test_series_limits(tmp_path,fake,count,step):
    with synthetic(tmp_path) as h:
        e=VisibilityEngine(Session(),h.terrain)
        with pytest.raises(ValueError):e.series(None,count,step)

def test_strict_observer_rejected(tmp_path,fake):
    from app.data.fusion import TerrainPolicy
    with synthetic(tmp_path) as h:
        e=VisibilityEngine(Session(),h.terrain)
        with pytest.raises(ScienceError,match='INVALID_OBSERVER'):
            e.run(VisibilityRequest(terrain=req(policy=TerrainPolicy()),utc='2026-11-20T08:00:00Z'))

def test_closed_session_cache_rejected(tmp_path,fake):
    with synthetic(tmp_path) as h:
        e=VisibilityEngine(Session(),h.terrain);e.horizon=h
        request=VisibilityRequest(terrain=req(max_range_m=100),utc='2026-11-20T08:00:00Z')
        e.run(request)
    with pytest.raises(Exception):e.run(request)

@pytest.mark.parametrize('utc',['bad','2026-11-20T08:00:00','2026-11-20T08:00:00+03:00'])
def test_invalid_utc(utc):
    with pytest.raises(ValueError):VisibilityRequest(terrain=req(),utc=utc)

def test_cache_bound_policy_and_sampling(tmp_path,fake):
    with synthetic(tmp_path) as h:
        e=VisibilityEngine(Session(),h.terrain,cache_size=2);e.horizon=h
        q=req(max_range_m=100)
        for az in [0.,1.,2.]:e._ray(q,az,[1,1000])
        assert len(e.cache)==2
        misses=e.misses
        e._ray(q,0.,[1,1000]);assert e.misses==misses+1
        changed=type(q).model_validate(q.model_dump()|{'max_range_m':90})
        e._ray(changed,0.,[1,1000]);assert e.misses==misses+2

def test_sample_budget_is_total(tmp_path,fake):
    with synthetic(tmp_path) as h:
        e=VisibilityEngine(Session(),h.terrain);e.horizon=h
        r=e.run(VisibilityRequest(terrain=req(max_range_m=100,max_total_samples=10),utc='2026-11-20T08:00:00Z'))
        assert r.performance['dem_samples']<=10 and r.sun.state=='UNKNOWN'

def test_unavailable_radius(tmp_path,fake,monkeypatch):
    monkeypatch.setattr('app.science.visibility.spice.bodvrd',lambda *a:(3,[float('nan'),1,1]))
    with synthetic(tmp_path) as h:
        with pytest.raises(ScienceError,match='DISK_RADIUS_UNAVAILABLE'):
            VisibilityEngine(Session(),h.terrain).run(VisibilityRequest(terrain=req(),utc='2026-11-20T08:00:00Z'))
