"""Counter and planning regressions with explicitly synthetic terrain."""
import pytest
from test_visibility import fake,Session
from test_horizon import synthetic,req
from app.science.visibility import VisibilityEngine
from app.science.visibility_models import VisibilityRequest


def test_inflight_budget_accounting_no_cache(tmp_path,fake):
    with synthetic(tmp_path) as h:
        e=VisibilityEngine(Session(),h.terrain);e.horizon=h
        q=req(max_range_m=100,max_samples_per_ray=3)
        # Min-step ray needs ten points; loose max-step lower bound allows start.
        q=type(q).model_validate(q.model_dump()|{'sampling':{'start_m':10,'min_step_m':10,'max_step_m':1000}})
        budget=[1,100]
        ray,identity,reason=e._ray(q,0.,budget)
        assert ray is None and identity is None and reason=='COMPUTATION_BUDGET_EXCEEDED'
        assert e.completed==0 and e.misses==1 and e.failed==1 and e.dem_samples==3
        assert budget==[0,97] and not e.cache
        assert e.last_budget_stage=='PER_RAY_POINT_LIMIT'
        e._ray(q,1.,budget)
        assert e.misses==1 and e.cache_misses==2 and e.rejected==2
        assert e.last_budget_stage=='NEW_RAY_LIMIT'


def test_plan_and_completion(tmp_path,fake):
    with synthetic(tmp_path) as h:
        e=VisibilityEngine(Session(),h.terrain);e.horizon=h
        q=VisibilityRequest(terrain=req(max_range_m=100),utc='2026-11-20T08:00:00Z')
        p=e.preflight(q)
        assert p['required_new_rays']==130 and p['ray_budget_sufficient']
        r=e.run(q);a=r.performance['accounting']
        assert a['attempted_rays']==a['completed_rays']==130
        assert a['failed_budget_attempts']==a['budget_rejected_rays']==0
        assert e.preflight(q)['required_new_rays']==0
        assert e.preflight(VisibilityRequest.model_validate(q.model_dump()|{'utc':'2026-11-20T09:00:00Z'}))['required_new_rays']==0 # mock centres deliberately static
        assert e.run(q).performance['accounting']['cache_hits']==130

@pytest.mark.parametrize('change',[{'device_height_m':2},{'max_range_m':90},{'policy':{'registration':'STRICT'}},{'location':{'latitude_deg':-89.469,'longitude_deg_east':222.6}},{'sampling':{'start_m':5}}])
def test_exact_cache_configuration_separation(tmp_path,fake,change):
    with synthetic(tmp_path) as h:
        e=VisibilityEngine(Session(),h.terrain);e.horizon=h;q=req(max_range_m=100)
        e._ray(q,0.,[1,1000]);e._ray(q,.000000001,[1,1000])
        assert e.completed==2
        changed=type(q).model_validate(q.model_dump()|change)
        e._ray(changed,0.,[1,1000]);assert e.completed==3


def test_data_identity_namespace(tmp_path,fake):
    with synthetic(tmp_path) as h:
        a=VisibilityEngine(Session(),h.terrain)
        source=h.terrain.sources['SITE01'].dem
        source.reference=source.reference.model_copy(update={'raster_sha256':'a'*64})
        b=VisibilityEngine(Session(),h.terrain)
        assert a.namespace!=b.namespace


def test_lru_and_immediate_rejection(tmp_path,fake):
    with synthetic(tmp_path) as h:
        e=VisibilityEngine(Session(),h.terrain,cache_size=2);e.horizon=h;q=req(max_range_m=100)
        for az in [0.,1.,2.,0.]:e._ray(q,az,[1,1000])
        assert e.completed==4 and e.evictions==2 and len(e.cache)==2
        e._ray(q,0.,[0,0]);assert e.hits==1
        e._ray(q,9.,[0,0]);assert e.rejected==1 and e.misses==4


def test_preflight_insufficient_ray_budget(tmp_path,fake):
    with synthetic(tmp_path) as h:
        e=VisibilityEngine(Session(),h.terrain)
        q=VisibilityRequest(terrain=req(),utc='2026-11-20T08:00:00Z',max_new_rays=8)
        assert not e.preflight(q)['ray_budget_sufficient']


def test_impossible_minimum_rejected_without_attempt(tmp_path,fake):
    with synthetic(tmp_path) as h:
        e=VisibilityEngine(Session(),h.terrain);e.horizon=h
        budget=[1,1]
        assert e._ray(req(),0.,budget)[0] is None
        assert budget==[1,1] and e.misses==e.completed==e.dem_samples==0
        assert e.rejected==1 and e.last_budget_stage=='MINIMUM_POINT_PREFLIGHT'
