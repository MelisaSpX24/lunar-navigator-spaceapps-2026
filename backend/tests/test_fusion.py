"""Synthetic selection tests; not NASA terrain."""
from contextlib import ExitStack
import numpy as np
import pytest
from rasterio.transform import from_origin
from app.data.fusion import MultiResolutionDem, TerrainSource, TerrainRequest, TerrainPolicy
from app.data.dem import open_dem
from app.data.raster import Limits
from test_dem import raster, reference, location


def engine(tmp_path, stack, near=10, far=12, **ref_changes):
    sources=[]
    for role,value,scale in [('SITE01',near,5),('PRODUCT90',far,80)]:
        path=raster(tmp_path/f'{role}.tif',np.full((20,20),value,dtype='float32'),transform=from_origin(-50,50,scale,scale))
        ref=reference(path,product_id=role,**ref_changes)
        sources.append(TerrainSource(role,stack.enter_context(open_dem(path,ref))))
    return MultiResolutionDem(sources)


def request(x=5,y=-5,**policy):
    return TerrainRequest(location=location(x,y),policy=TerrainPolicy(registration='PROTOTYPE',**policy))

@pytest.mark.parametrize('near,far,x,status,role',[(10,12,5,'VALID','SITE01'),(-9999,12,5,'VALID','PRODUCT90'),(-9999,-9999,5,'UNKNOWN',None),(10,12,100,'VALID','PRODUCT90'),(10,12,2000,'UNKNOWN',None)])
def test_selection_and_missing(tmp_path,near,far,x,status,role):
    with ExitStack() as stack:
        result=engine(tmp_path,stack,near,far).sample(request(x))
        assert result.status==status
        assert (result.selected.product_id if result.selected else None)==role
        assert not result.science_ready
        if role:
            assert result.selected.raster_sha256 and result.selected.sampling_method=='CONTAINING_CELL_NO_INTERPOLATION'
            assert result.selected.resolution_m==(5,5) if role=='SITE01' else result.selected.resolution_m==(80,80)
            assert 'ABSOLUTE_REGISTRATION_NOT_VERIFIED' in result.warnings


def test_strict_policy_and_conflict(tmp_path):
    with ExitStack() as stack:
        e=engine(tmp_path,stack,near=10,far=40)
        assert e.sample(TerrainRequest(location=location())).status=='UNKNOWN'
        r=e.sample(request(conflict='REJECT',conflict_threshold_m=20))
        assert r.status=='UNRESOLVED_SOURCE_CONFLICT' and r.surface_elevation_m is None
        assert r.overlap_spread_m==30 and len(r.attempts)==2
        assert e.sample(request()).selected.product_id=='SITE01'


def test_incompatible_frame_and_batch_budget(tmp_path):
    with ExitStack() as stack:
        e=engine(tmp_path,stack,source_frame_evidence='INCOMPATIBLE',declared_source_frame='MOON_PA')
        r=e.sample(request())
        assert r.status=='UNKNOWN' and all(a.status=='INCOMPATIBLE_FRAME' for a in r.attempts)
        e.max_batch=2
        with pytest.raises(ValueError,match='budget'): e.sample_batch(request() for _ in range(3))
        assert len(list(e.iter_samples(request() for _ in range(3))))==3


def test_lroc_requires_explicit_opt_in(tmp_path):
    with ExitStack() as stack:
        e=engine(tmp_path,stack)
        p=raster(tmp_path/'lroc.tif')
        e.sources['LROC']=TerrainSource('LROC',stack.enter_context(open_dem(p,reference(p,product_id='LROC'))))
        r=request();r.preferred_resolution_m=2
        assert e.sample(r).selected.product_id=='SITE01'
        r.policy.enable_lroc=True
        assert e.sample(r).selected.product_id=='LROC'
        assert not e.sample(r).selected.reference.product_specific_frame_verified


def test_bounded_read_failure_is_visible(tmp_path):
    with ExitStack() as stack:
        e=engine(tmp_path,stack)
        e.sources['SITE01'].dem.limits=Limits(max_working_bytes=1)
        r=e.sample(request())
        assert r.selected.product_id=='PRODUCT90' and r.attempts[0].status=='SOURCE_READ_ERROR'


def test_wrong_identity_units_and_datum_rejected(tmp_path):
    p=raster(tmp_path/'bad.tif')
    with pytest.raises(ValueError):
        with open_dem(p,reference(p,raster_sha256='0'*64)): pass
    for kw in ({'vertical_unit':'km'},{'vertical_reference':'UNKNOWN'},{'product_specific_frame_verified':True}):
        with pytest.raises(ValueError): reference(p,**kw)


def test_each_source_uses_own_crs_and_affine(tmp_path):
    from test_dem import LUNAR
    from pyproj import CRS, Transformer
    with ExitStack() as stack:
        loc=location(20,-20)
        crs=LUNAR.replace('+lon_0=0','+lon_0=30')
        x,y=Transformer.from_crs(CRS.from_user_input(crs).geodetic_crs,crs,always_xy=True).transform(loc.longitude_deg_east,loc.latitude_deg)
        p=raster(tmp_path/'rotated_meridian.tif',np.full((10,10),42,dtype='float32'),crs=crs,transform=from_origin(x-25,y+25,5,5))
        dem=stack.enter_context(open_dem(p,reference(p)))
        e=MultiResolutionDem([TerrainSource('SITE01',dem)])
        r=e.sample(TerrainRequest(location=loc,policy=TerrainPolicy(registration='PROTOTYPE')))
        assert r.surface_elevation_m==42
        assert r.selected.x_m==pytest.approx(x)
        assert r.selected.y_m==pytest.approx(y)
