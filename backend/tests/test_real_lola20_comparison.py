"""Real source comparison on an identical fixed distance lattice."""
import os
import pytest
from app.science.horizon import TerrainHorizonEngine
from app.science.horizon_models import HorizonRequest,Sampling
from data_pipeline.visibility_cli import visibility_terrain,LOLA20_HASH
from data_pipeline.visibility_validation import pilot

def test_real_twenty_and_eighty_same_observer():
    if not all(os.environ.get(k) for k in ['NASA_PRODUCT90_DEM','NASA_LOLA_VALIDATION_DIR']):pytest.skip('Real 20 m comparison data absent')
    results=[]
    for twenty in [False,True]:
        with visibility_terrain(twenty) as terrain:
            far=terrain.sources['PRODUCT90'].dem
            assert far.reference.source_product_family=='PGDA Product 90'
            assert far.ds.res==((20.,20.) if twenty else (80.,80.))
            if twenty:
                assert far.reference.raster_sha256==LOLA20_HASH
                assert far.crs.ellipsoid.semi_major_metre==1737400
                assert far.ds.width==far.ds.height==30400
                sample=far.sample(pilot().terrain.location,allow_unverified_registration=True)
                assert sample.status=='VALID' and sample.surface_elevation_m==pytest.approx(1942.38525390625)
            q=HorizonRequest.model_validate(pilot().terrain.model_dump()|{'mode':'RAYS','azimuths_deg':[0.],'sampling':Sampling(min_step_m=100,max_step_m=100).model_dump()})
            results.append(TerrainHorizonEngine(terrain).calculate(q))
    a,b=results
    assert a.observer_surface.surface_elevation_m==b.observer_surface.surface_elevation_m
    assert a.rays[0].valid_sample_count==b.rays[0].valid_sample_count
    assert a.identity!=b.identity

@pytest.mark.parametrize('exists',[False,True])
def test_real_optional_source_fail_safe(monkeypatch,tmp_path,exists):
    from app.science.kernels import ScienceError
    if not os.environ.get('NASA_LOLA_VALIDATION_DIR'):pytest.skip('Baseline NASA package absent')
    path=tmp_path/'bad.tif'
    if exists:path.write_bytes(b'not NASA data')
    monkeypatch.setenv('NASA_PRODUCT90_DEM',str(path))
    with pytest.raises(ScienceError,match='LOLA20_HASH_MISMATCH' if exists else 'LOLA20_SOURCE_UNAVAILABLE'):
        with visibility_terrain(True):pass
