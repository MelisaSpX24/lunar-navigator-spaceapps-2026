"""Genuine NASA tests; environment absent means SKIPPED, never mock substitution."""
import os
import pytest
import spiceypy as spice
from app.science.kernels import KernelSession,ScienceError
from app.science.visibility import VisibilityEngine
from app.science.visibility_models import VisibilityRequest
from data_pipeline.visibility_cli import visibility_terrain
from data_pipeline.visibility_validation import pilot

@pytest.fixture(scope='module')
def real():
    if not all(os.environ.get(k) for k in ['NASA_KERNEL_DIR','NASA_KERNEL_INDEX','NASA_LOLA_VALIDATION_DIR']):pytest.skip('Real NASA sources absent')
    with KernelSession(os.environ['NASA_KERNEL_DIR'],os.environ['NASA_KERNEL_INDEX']) as s,visibility_terrain() as t:
        e=VisibilityEngine(s,t);r=e.run(pilot());yield e,r
    assert spice.ktotal('ALL')==0

def test_actual_geometry_and_disks(real):
    e,r=real
    assert r.sun.observer.surface_elevation_m==pytest.approx(1942.1014404296875)
    assert .25<r.sun.angular_radius_deg<.29 and .8<r.earth.angular_radius_deg<1.1
    assert r.sun.state=='NONE' and r.earth.state=='FULL'
    assert r.sun.unknown_fraction==r.earth.unknown_fraction==0
    assert r.sun.radius_kernel.startswith('pck00011.tpc:')
    assert r.data_origin=='REAL_NASA_PROTOTYPE'

def test_actual_repeat_series_lt_and_epoch(real):
    e,r=real
    repeated=e.run(pilot());assert repeated.performance['new_rays']==0
    q=VisibilityRequest.model_validate(pilot().model_dump()|{'max_new_rays':0,'correction':'LT+S'})
    apparent=e.run(q)
    assert apparent.sun.direction!=r.sun.direction
    series=e.series(q,2,60)
    assert len(series.samples)==2 and series.samples[1].sun.state=='UNKNOWN'
    with pytest.raises(ScienceError,match='EPOCH_OUT_OF_COVERAGE'):
        e.run(VisibilityRequest.model_validate(q.model_dump()|{'utc':'2200-01-01T00:00:00Z'}))
