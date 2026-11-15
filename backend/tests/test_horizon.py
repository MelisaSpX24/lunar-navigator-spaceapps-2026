"""Analytic/synthetic terrain only; not real NASA validation."""
from contextlib import contextmanager
import math
import numpy as np
import pytest
from app.data.dem import open_dem
from app.data.fusion import MultiResolutionDem,TerrainSource,TerrainRequest,TerrainPolicy
from app.science.geometry import Observer,local_axes,observer_position_km,direction_angles,REFERENCE_RADIUS_M as R
from app.science.horizon import TerrainHorizonEngine,elevation_angle_deg
from app.science.horizon_models import HorizonRequest,Sampling,HorizonRay
from test_dem import raster,reference,location

@contextmanager
def synthetic(tmp_path,terrain=lambda d,a:0, missing=lambda d:False):
    path=raster(tmp_path/'surface.tif')
    with open_dem(path,reference(path)) as dem:
        fusion=MultiResolutionDem([TerrainSource('SITE01',dem)])
        base=fusion.sample(TerrainRequest(location=location(),policy=TerrainPolicy(registration='PROTOTYPE')))
        class Analytic(TerrainHorizonEngine):
            def _query(self,req,loc):
                az,_,dist=self.geod.inv(req.location.longitude_deg_east,req.location.latitude_deg,loc.longitude_deg_east,loc.latitude_deg)
                result=base.model_copy(deep=True)
                result.request.location=loc
                if req.policy.registration=='STRICT' or (dist>0.01 and missing(dist)):
                    result.status='UNKNOWN';result.selected=None;result.surface_elevation_m=None
                    return result
                h=0 if dist<0.01 else terrain(dist,az%360)
                result.surface_elevation_m=h;result.selected.surface_elevation_m=h
                result.selected.location=loc
                return result
        yield Analytic(fusion)

def req(**kw):
    defaults=dict(location=location(),mode='RAYS',azimuths_deg=[0],max_range_m=1000,
        policy=TerrainPolicy(registration='PROTOTYPE'),sampling=Sampling(start_m=10,min_step_m=10,max_step_m=10))
    defaults.update(kw);return HorizonRequest(**defaults)

@pytest.mark.parametrize('az',[0,90,180,270,359])
@pytest.mark.parametrize('device',[0,1,2,10])
def test_exact_sphere_matches_existing_enu(az,device):
    from pyproj import Geod
    obs=Observer(latitude_deg=-89.468,longitude_deg_east=222.6,surface_elevation_m=1942,device_height_m=device)
    for distance in (5,1000,100000,150000):
        lon,lat,_=Geod(a=R,b=R).fwd(obs.longitude_deg_east,obs.latitude_deg,az,distance)
        target=Observer(latitude_deg=lat,longitude_deg_east=lon%360,surface_elevation_m=2000)
        vector=observer_position_km(target)-observer_position_km(obs)
        gotaz,angle,_=direction_angles(vector,obs)
        assert ((gotaz-az+180)%360)-180==pytest.approx(0,abs=1e-7)
        assert elevation_angle_deg(1942,device,2000,distance)==pytest.approx(angle,abs=1e-7)


def test_negative_spherical_horizon_and_device_monotonic(tmp_path):
    with synthetic(tmp_path) as engine:
        angles=[]
        for device in [0,1,2,10]:
            r=engine.calculate(req(device_height_m=device)).rays[0]
            assert r.coverage_status=='COMPLETE_SAMPLED_RANGE' and r.horizon_elevation_deg<0
            expected=max(math.degrees(math.atan2(R*math.cos(s/R)-(R+device),R*math.sin(s/R))) for s in range(10,1001,10))
            assert r.horizon_elevation_deg==pytest.approx(expected,abs=1e-7)
            angles.append(r.horizon_elevation_deg)
        assert angles==sorted(angles,reverse=True)
    assert elevation_angle_deg(0,0,0,150000)==pytest.approx(-math.degrees(150000/R)/2)
    assert elevation_angle_deg(0,0,0,150000)<-2


def test_two_hills_choose_angle_not_absolute_height(tmp_path):
    with synthetic(tmp_path,lambda d,a:100 if abs(d-100)<1 else 200 if abs(d-500)<1 else 0) as e:
        r=e.calculate(req()).rays[0]
        assert r.obstruction.distance_m==100
        assert r.horizon_elevation_deg==pytest.approx(elevation_angle_deg(0,1,100,100))

@pytest.mark.parametrize('all_missing',[False,True])
def test_unknown_and_partial(tmp_path,all_missing):
    with synthetic(tmp_path,missing=lambda d:all_missing or 95<d<105) as e:
        r=e.calculate(req()).rays[0]
        assert r.horizon_elevation_deg is None
        assert r.coverage_status==('UNKNOWN' if all_missing else 'INCOMPLETE')
        assert (r.partial_max_obstruction_deg is None)==all_missing
        assert r.unknown_fraction>0


def test_narrow_ridge_phase_and_range(tmp_path):
    with synthetic(tmp_path,lambda d,a:100 if 44<d<46 else 0) as e:
        coarse=e.calculate(req()).rays[0]
        fine=e.calculate(req(sampling=Sampling(start_m=5,min_step_m=5,max_step_m=5))).rays[0]
        assert fine.obstruction.distance_m==45 and fine.horizon_elevation_deg>coarse.horizon_elevation_deg+50
    with synthetic(tmp_path,lambda d,a:20000 if abs(d-120000)<1 else 0) as e:
        rays=[e.calculate(req(max_range_m=end,sampling=Sampling(start_m=1000,min_step_m=100,max_step_m=100,resolution_factor=16))).rays[0] for end in (50000,100000,150000)]
        assert rays[2].horizon_elevation_deg>rays[0].horizon_elevation_deg
        assert rays[2].range_convergence_status=='RANGE_CONVERGENCE_NOT_ESTABLISHED'


def test_sector_full_exact_lookup_identity_and_strict(tmp_path):
    with synthetic(tmp_path) as e:
        full=e.calculate(req(mode='FULL_HORIZON',azimuth_step_deg=5))
        sector=e.calculate(req(mode='SECTOR_HORIZON',sector_start_deg=350,sector_end_deg=15,azimuth_step_deg=5))
        assert len(full.rays)==72 and len(sector.rays)==6
        for r in sector.rays: assert r==full.horizon_at_azimuth(r.azimuth_deg)
        assert full.horizon_at_azimuth(360)==full.horizon_at_azimuth(0)
        assert full.horizon_at_azimuth(2) is None
        assert e.calculate(req()).identity==e.calculate(req()).identity
        assert e.calculate(req()).identity!=e.calculate(req(device_height_m=2)).identity
        assert e.calculate(req(policy=TerrainPolicy())).overall_status=='UNKNOWN'

@pytest.mark.parametrize('changes',[{'device_height_m':-1},{'max_range_m':0},{'azimuths_deg':[360]}, {'azimuths_deg':[float('nan')]},{'max_range_m':float('inf')},{'sampling':{'min_step_m':0.001}},{'sampling':{'max_step_m':10000}}])
def test_invalid_requests(changes):
    with pytest.raises(ValueError):req(**changes)

@pytest.mark.parametrize('args',[(0,-1,0,10),(-R,0,0,10),(0,0,-R,10),(0,0,0,0),(0,0,float('nan'),10)])
def test_invalid_geometry(args):
    with pytest.raises(ValueError):elevation_angle_deg(*args)


def test_budget_and_result_invariants(tmp_path):
    with synthetic(tmp_path) as e:
        with pytest.raises(ValueError,match='budget'): e.calculate(req(max_total_samples=1))
    with pytest.raises(ValueError): HorizonRay(azimuth_deg=0,coverage_status='INCOMPLETE',requested_range_m=10,horizon_elevation_deg=0)


def test_real_raster_source_transition_conflict_and_read_error(tmp_path):
    from contextlib import ExitStack
    from test_fusion import engine
    from app.data.raster import Limits
    with ExitStack() as stack:
        fusion=engine(tmp_path,stack,near=10,far=40)
        e=TerrainHorizonEngine(fusion)
        # Outward direction from the south-polar origin crosses both grids.
        report=e.calculate(req(azimuths_deg=[0],max_range_m=1000)).rays[0]
        assert report.source_transition_count==1
        assert set(report.source_counts)=={'SITE01','PRODUCT90'}
        assert report.reported_conflict_count>0
        assert report.obstruction.terrain.selected.product_id in report.source_counts
        reject=e.calculate(req(policy=TerrainPolicy(registration='PROTOTYPE',conflict='REJECT')))
        assert reject.overall_status=='UNKNOWN' # rejected observer itself
        fusion.sources['SITE01'].dem.limits=Limits(max_working_bytes=1)
        fallback=e.calculate(req()).rays[0]
        assert fallback.read_error_count>0
        assert 'SITE01' not in fallback.source_counts


def test_conflict_rejection_along_ray_keeps_partial_angle(tmp_path):
    with synthetic(tmp_path) as e:
        original=e._query
        def query(request,loc):
            result=original(request,loc)
            _,_,d=e.geod.inv(request.location.longitude_deg_east,request.location.latitude_deg,loc.longitude_deg_east,loc.latitude_deg)
            if 95<d<105:
                result.status='UNRESOLVED_SOURCE_CONFLICT';result.selected=None;result.surface_elevation_m=None
            return result
        e._query=query
        result=e.calculate(req()).rays[0]
        assert result.coverage_status=='INCOMPLETE' and result.conflict_sample_count==1
        assert result.horizon_elevation_deg is None and result.partial_max_obstruction_deg is not None


def test_nonfinite_terrain_and_runtime_budget_rejected(tmp_path):
    with synthetic(tmp_path,lambda d,a:float('nan')) as e:
        with pytest.raises(ValueError):e.calculate(req())
    with synthetic(tmp_path) as e:
        with pytest.raises(ValueError,match='budget'):
            e.calculate(req(max_samples_per_ray=10,sampling=Sampling(max_step_m=1000,resolution_factor=1)))


def test_result_identity_includes_external_quality_mask(tmp_path):
    import rasterio
    from app.data.quality import QualityLayer
    from app.data.manifest import sha256_file
    from test_dem_quality import quality, elevation
    path,ref=elevation(tmp_path)
    layer=quality(tmp_path)
    mask=np.full((10,10),255,dtype='uint8')
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(layer.path,'r+') as ds:ds.write_mask(mask)
    layer=layer.model_copy(update={'sha256':sha256_file(layer.path)})
    def result():
        with open_dem(path,ref) as dem:
            fusion=MultiResolutionDem([TerrainSource('SITE01',dem,(layer,))])
            return TerrainHorizonEngine(fusion).calculate(req(max_range_m=20))
    first=result()
    mask[0,0]=0 # unrelated to observer and these short ray cells
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(layer.path,'r+') as ds:ds.write_mask(mask)
    assert sha256_file(layer.path)==layer.sha256
    second=result()
    assert first.observer_surface==second.observer_surface and first.rays==second.rays
    assert first.identity!=second.identity


def test_quality_outside_status_counts_as_missing_outside(tmp_path):
    from test_dem_quality import elevation,quality
    path,ref=elevation(tmp_path);layer=quality(tmp_path)
    with open_dem(path,ref) as dem:
        engine=TerrainHorizonEngine(MultiResolutionDem([TerrainSource('SITE01',dem,(layer,))]))
        ray=engine.calculate(req(azimuths_deg=[0])).rays[0]
        assert ray.coverage_status=='INCOMPLETE'
        assert ray.outside_sample_count==ray.missing_sample_count>0
