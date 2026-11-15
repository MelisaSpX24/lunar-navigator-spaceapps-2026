"""Actual CR1 validation and sensitivity measurements, never synthetic substitution."""
import argparse,json,resource
from pathlib import Path
import numpy as np
from app.data.coordinates import validate_coordinates
from app.data.fusion import MultiResolutionDem,TerrainPolicy
from app.science.horizon import TerrainHorizonEngine,elevation_angle_deg
from app.science.horizon_models import HorizonRequest,Sampling
from data_pipeline.horizon_cli import terrain_session,measured

def request(**kw):
    d=dict(location=validate_coordinates(-89.468,222.6),mode='RAYS',azimuths_deg=[0,90,180,270],
           policy=TerrainPolicy(registration='PROTOTYPE'),sampling=Sampling(resolution_factor=4))
    d.update(kw);return HorizonRequest(**d)

def compact(result,perf):
    return dict(performance=perf,request=result.request.model_dump(mode='json'),identity=result.identity,
        observer_height_m=result.observer_surface.surface_elevation_m,overall_status=result.overall_status,
        rays=[dict(azimuth_deg=r.azimuth_deg,status=r.coverage_status,angle_deg=r.horizon_elevation_deg,
            partial_deg=r.partial_max_obstruction_deg,distance_m=r.obstruction.distance_m if r.obstruction else None,
            obstruction_source=r.obstruction.terrain.selected.product_id if r.obstruction else None,
            valid=r.valid_sample_count,missing=r.missing_sample_count,transitions=r.source_transition_count,
            source_counts=r.source_counts,reported_conflicts=r.reported_conflict_count) for r in result.rays])

def differences(first,second):
    a={r['azimuth_deg']:r for r in first['rays']};b={r['azimuth_deg']:r for r in second['rays']}
    pairs=[(az,b[az]['angle_deg']-a[az]['angle_deg']) for az in sorted(a.keys()&b.keys()) if a[az]['angle_deg'] is not None and b[az]['angle_deg'] is not None]
    if not pairs:return {'count':0}
    values=np.array([v for _,v in pairs]);idx=int(np.argmax(abs(values)))
    return dict(count=len(pairs),max_absolute_deg=float(abs(values).max()),median_absolute_deg=float(np.median(abs(values))),rms_deg=float(np.sqrt(np.mean(values**2))),largest_change_azimuth=pairs[idx][0],signed_differences=pairs,
        obstruction_distance_changes_m={str(az):b[az]['distance_m']-a[az]['distance_m'] for az,_ in pairs})

def run(output):
    if output.exists():raise ValueError('Refusing to overwrite evidence')
    runs={}
    with terrain_session() as terrain:
        engine=TerrainHorizonEngine(terrain)
        def execute(name,req,eng=engine):
            result,perf=measured(eng,req);runs[name]=compact(result,perf)
            print(name,perf['seconds'],perf['samples'],flush=True)
            return result
        full=execute('full_5deg',request(mode='FULL_HORIZON',azimuth_step_deg=5,sampling=Sampling(resolution_factor=8,max_step_m=640)))
        for end in (50000,100000,150000):execute(f'range_{end}',request(max_range_m=end))
        for factor in (2,1):execute(f'step_factor_{factor}',request(sampling=Sampling(resolution_factor=factor)))
        for step in (5,2,1):execute(f'sector_{step}deg',request(mode='SECTOR_HORIZON',sector_start_deg=0,sector_end_deg=30,azimuth_step_deg=step,sampling=Sampling(resolution_factor=4)))
        for device in (0,2,10):execute(f'device_{device}',request(device_height_m=device))
        single=execute('single',request(azimuths_deg=[0]));again=execute('single_repeat',request(azimuths_deg=[0]))
        assert single.identity==again.identity and single.rays==again.rays
        # Reproduce the 10 m crossing at Site01 northern boundary; observer 200 m inside.
        site=terrain.sources['SITE01'].dem
        lonlat=site.grid.xy_to_geographic(-11000,-4200)
        obs=validate_coordinates(*lonlat)
        end=validate_coordinates(*site.grid.xy_to_geographic(-11000,-3500))
        az,_,_=engine.geod.inv(obs.longitude_deg_east,obs.latitude_deg,end.longitude_deg_east,end.latitude_deg)
        boundary=request(location=obs,azimuths_deg=[az%360],max_range_m=600,sampling=Sampling(start_m=5,min_step_m=5,max_step_m=5))
        execute('boundary_fusion',boundary)
        fixed_observer=engine._query(boundary,boundary.location)
        class FixedObserverEngine(TerrainHorizonEngine):
            # Diagnostic only: same actual Site01 observer for every source comparison.
            def _query(self,req,loc):
                if loc==req.location: return fixed_observer
                return super()._query(req,loc)
        for role in ('SITE01','PRODUCT90'):
            execute('boundary_'+role,boundary,FixedObserverEngine(MultiResolutionDem([terrain.sources[role]])))
        boundary_trace=[]
        for distance in (195,200,205):
            lon,lat,_=engine.geod.fwd(obs.longitude_deg_east,obs.latitude_deg,az%360,distance)
            sample=engine._query(boundary,validate_coordinates(lat,lon%360))
            boundary_trace.append(dict(distance_m=distance,location=sample.request.location.model_dump(),
                height_m=sample.surface_elevation_m,source=sample.selected.product_id if sample.selected else None,
                angle_deg=elevation_angle_deg(fixed_observer.surface_elevation_m,1,sample.surface_elevation_m,distance) if sample.selected else None))
        comparisons={f'range_{a}_{b}':differences(runs[f'range_{a}'],runs[f'range_{b}']) for a,b in [(50000,100000),(100000,150000)]}
        comparisons.update(step_coarse_medium=differences(runs['range_150000'],runs['step_factor_2']),step_medium_fine=differences(runs['step_factor_2'],runs['step_factor_1']))
        # Interpolation is a diagnostic only, never used by horizon_at_azimuth.
        fine=runs['sector_1deg']['rays']
        az_sensitivity={}
        for step in (5,2):
            coarse=runs[f'sector_{step}deg']['rays']
            predicted=np.interp([r['azimuth_deg'] for r in fine],[r['azimuth_deg'] for r in coarse],[r['angle_deg'] for r in coarse])
            error=predicted-np.array([r['angle_deg'] for r in fine])
            az_sensitivity[str(step)]=dict(max_absolute_deg=float(abs(error).max()),rms_deg=float(np.sqrt(np.mean(error**2))),median_absolute_deg=float(np.median(abs(error))),largest_change_azimuth=fine[int(np.argmax(abs(error)))]['azimuth_deg'],method='Diagnostic linear interpolation error against measured 1 degree sector; no continuous-terrain accuracy claim')
        evidence=dict(data_origin='REAL_NASA_PROTOTYPE',science_ready=False,full_profile=full.model_dump(mode='json'),runs=runs,comparisons=comparisons,azimuth_sensitivity=az_sensitivity,boundary_trace=boundary_trace,
            limitations=['All actual DEM source hashes and registration evidence retained in full_profile.','Point sampling is not full cell traversal. No statistical accuracy or beyond-range bound.','Source-only boundary runs retain the exact actual Site01 observer; only ray terrain sources differ.','Site01-only partial angle is a known-terrain maximum, not a complete horizon.','Existing source-only differences must not be relabeled independent absolute registration.'])
        output.write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();run(a.output)
