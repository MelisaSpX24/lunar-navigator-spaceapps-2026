"""Genuine NASA integrations: environment files required, never generated."""
import os
import pytest
import numpy as np
from rasterio.windows import Window
from app.data.coordinates import validate_coordinates
from app.data.fusion import TerrainRequest, TerrainPolicy
from data_pipeline.fusion_validation import real_engine, coordinate, request

@pytest.fixture(scope='module')
def real():
    if not all(os.environ.get(n) for n in ('NASA_LOLA_VALIDATION_DIR','NASA_LROC_CR1_DEM','NASA_LROC_CR1_LABEL')):
        pytest.skip('Genuine fusion originals not supplied')
    with real_engine() as e: yield e


def test_real_fusion_cr1_quality_and_overlap(real):
    r=real.sample(request(validate_coordinates(-89.468,222.6)))
    assert r.status=='VALID' and r.surface_elevation_m==pytest.approx(1942.1014404296875)
    assert r.attempts[0].source_role=='SITE01'
    assert r.attempts[1].sample.surface_elevation_m==pytest.approx(1942.8433837890625)
    assert r.selected.quality.status=='QUALITY_LAYERS_PRESENT'
    assert not r.selected.reference.product_specific_frame_verified


def test_real_site01_boundary_and_far_source(real):
    site=real.sources['SITE01'].dem
    for x,expected in [(site.ds.bounds.left+5,'SITE01'),(site.ds.bounds.left-5,'PRODUCT90'),(50000,'PRODUCT90')]:
        r=real.sample(request(coordinate(site,x,-12000)))
        assert r.status=='VALID'
        assert next(a.source_role for a in r.attempts if a.sample is r.selected or (a.sample and a.sample.product_id==r.selected.product_id))==expected


def test_real_lroc_nodata_falls_back_without_invention(real):
    lroc=real.sources['LROC'].dem
    found=False
    for row in range(0,lroc.ds.height,100):
        values,_=lroc.read_elevation_window(Window(0,row,lroc.ds.width,min(100,lroc.ds.height-row)))
        missing=np.argwhere(np.ma.getmaskarray(values))
        if len(missing):
            rr,cc=map(int,missing[len(missing)//2]);loc=validate_coordinates(*lroc.grid.pixel_center_geographic(row+rr,cc))
            r=real.sample(TerrainRequest(location=loc,preferred_resolution_m=2,
                policy=TerrainPolicy(registration='PROTOTYPE',enable_lroc=True)))
            assert r.attempts[0].status=='NODATA'
            assert r.selected and r.selected.product_id!=lroc.reference.product_id
            found=True;break
    assert found,'Expected genuine LROC NoData not found'


def test_real_lroc_comparison_and_strict_policy(real):
    loc=validate_coordinates(-89.468,222.6)
    r=real.sample(TerrainRequest(location=loc,preferred_resolution_m=2,
        policy=TerrainPolicy(registration='PROTOTYPE',enable_lroc=True)))
    assert r.surface_elevation_m==pytest.approx(1944.1400146484375)
    assert r.attempts[1].sample.surface_elevation_m-r.surface_elevation_m==pytest.approx(-2.03857421875)
    assert real.sample(TerrainRequest(location=loc)).status=='UNKNOWN'
