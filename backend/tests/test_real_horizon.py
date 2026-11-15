"""Opt-in actual NASA terrain tests. No generated files replace NASA sources."""
import os
import pytest
from app.science.horizon import TerrainHorizonEngine
from app.data.fusion import TerrainPolicy
from app.science.horizon_models import Sampling
from data_pipeline.horizon_cli import terrain_session
from data_pipeline.horizon_validation import request

@pytest.fixture(scope='module')
def real():
    if not os.environ.get('NASA_LOLA_VALIDATION_DIR'): pytest.skip('Actual LOLA package absent')
    with terrain_session() as terrain:
        engine=TerrainHorizonEngine(terrain)
        req=request(mode='FULL_HORIZON',azimuth_step_deg=90,sampling=Sampling(resolution_factor=8,max_step_m=640))
        yield engine,req,engine.calculate(req)


def test_real_observer_and_cardinal_horizons(real):
    _,_,result=real
    assert result.observer_surface.surface_elevation_m==pytest.approx(1942.1014404296875)
    assert result.data_origin=='REAL_NASA_PROTOTYPE' and not result.science_ready
    assert [r.azimuth_deg for r in result.rays]==[0,90,180,270]
    assert result.overall_status=='COMPLETE_SAMPLED_RANGE'
    assert all(r.obstruction is not None and r.horizon_elevation_deg is not None for r in result.rays)


def test_real_near_far_and_provenance(real):
    _,_,result=real
    for ray in result.rays:
        assert ray.source_transition_count>=1
        assert set(ray.source_counts)=={'Site01_final_adj_5mpp_surf.tif','LDEM_80S_80MPP_ADJ.TIF'}
        assert ray.resolutions_m==[5,80]
        assert 'ABSOLUTE_REGISTRATION_NOT_VERIFIED' in ray.warnings
        assert ray.obstruction.terrain.selected.raster_sha256


def test_real_sector_full_match_and_strict_unknown(real):
    engine,req,full=real
    sector=engine.calculate(req.model_copy(update={'mode':'SECTOR_HORIZON','sector_start_deg':0,'sector_end_deg':90}))
    assert sector.rays==full.rays[:2]
    strict=engine.calculate(req.model_copy(update={'policy':TerrainPolicy()}))
    assert strict.overall_status=='UNKNOWN'
    assert all(r.horizon_elevation_deg is None for r in strict.rays)


def test_real_device_heights_and_step_changes(real):
    engine,req,_=real
    # Same sampling lattice at each device height; elevation cannot increase.
    configs=[req.model_copy(update={'mode':'RAYS','azimuths_deg':[0],'device_height_m':h,'max_range_m':15000}) for h in [0,1,2,10]]
    results=[engine.calculate(r) for r in configs]
    angles=[r.rays[0].horizon_elevation_deg for r in results]
    assert angles==sorted(angles,reverse=True)
    finer=engine.calculate(configs[1].model_copy(update={'sampling':Sampling(resolution_factor=4)}))
    assert finer.rays[0].valid_sample_count>results[1].rays[0].valid_sample_count
    assert finer.identity!=results[1].identity
