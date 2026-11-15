"""Reproducible genuine NASA validation and controlled 20/80 m experiments."""
import argparse,json,os,time
from pathlib import Path
import numpy as np
from app.science.kernels import KernelSession
from app.science.visibility import VisibilityEngine
from app.science.visibility_models import VisibilityRequest
from app.science.horizon_models import HorizonRequest,Sampling
from data_pipeline.visibility_cli import visibility_terrain
from data_pipeline.horizon_cli import measured
from data_pipeline.horizon_validation import compact,differences
from app.science.disk_geometry import disk_samples,sampled_fraction
from types import SimpleNamespace


def pilot():
    return VisibilityRequest(terrain=HorizonRequest(location={'latitude_deg':-89.468,'longitude_deg_east':222.6},
        policy={'registration':'PROTOTYPE','conflict':'REPORT'},sampling=Sampling(resolution_factor=8,max_step_m=640)),utc='2026-11-20T08:00:00Z')


def run(output):
    if output.exists():raise ValueError('Refusing overwrite')
    report={'science_ready':False,'data_origin':'REAL_NASA_PROTOTYPE','runs':{},'comparisons':{}}
    req=pilot()
    with KernelSession(os.environ['NASA_KERNEL_DIR'],os.environ['NASA_KERNEL_INDEX']) as session:
        for label,twenty in [('baseline80',False),('experiment20',True)]:
            if twenty and not Path(os.environ.get('NASA_PRODUCT90_DEM','/nonexistent')).is_file():
                report['comparison_status']='LOLA20_COMPARISON_NOT_RUN_DATA_UNAVAILABLE';continue
            setup=time.perf_counter()
            with visibility_terrain(twenty) as terrain:
                engine=VisibilityEngine(session,terrain)
                run={'setup_seconds':time.perf_counter()-setup}
                result=engine.run(req);run['pilot']=result.model_dump(mode='json')
                print(label,'pilot',result.performance,flush=True)
                run['repeat']=engine.run(req).performance
                directions=sorted(set([0.,90.,180.,270.,result.sun.direction.azimuth_deg,result.earth.direction.azimuth_deg]))
                for name,sampling in [('adaptive',req.terrain.sampling),('common100m',Sampling(start_m=5,min_step_m=100,max_step_m=100))]:
                    q=HorizonRequest.model_validate(req.terrain.model_dump() | {'mode':'RAYS','azimuths_deg':directions,'sampling':sampling.model_dump()})
                    h,p=measured(engine.horizon,q);run[name]=compact(h,p)
                # Command05 seam diagnostic, same Site01 cell and fixed distance grid in both sessions.
                lat,lon=terrain.sources['SITE01'].dem.grid.xy_to_geographic(-11000,-4200)
                boundary=HorizonRequest.model_validate(req.terrain.model_dump() | {'location':{'latitude_deg':lat,'longitude_deg_east':lon},'mode':'RAYS','azimuths_deg':[0.], 'max_range_m':600,'sampling':{'start_m':5,'min_step_m':5,'max_step_m':5}})
                h,p=measured(engine.horizon,boundary);run['boundary']=compact(h,p)
                if not twenty:
                    limited=VisibilityRequest.model_validate(req.model_dump() | {'max_new_rays':8})
                    run['series']=engine.series(limited,3,3600).model_dump(mode='json')
                    run['disk_benchmarks']={}
                    for n in (64,256,1024):
                        r=engine.run(VisibilityRequest.model_validate(req.model_dump() | {'disk_samples':n,'max_new_rays':0}))
                        run['disk_benchmarks'][str(n)]={'performance':r.performance,'sun_unknown':r.sun.unknown_fraction,'earth_unknown':r.earth.unknown_fraction}
                report['runs'][label]=run
        if 'experiment20' in report['runs']:
            a,b=[report['runs'][k] for k in ['baseline80','experiment20']]
            for key in ['adaptive','common100m','boundary']:
                report['comparisons'][key]=differences(a[key],b[key])
                v=[v for az,v in report['comparisons'][key].get('signed_differences',[])]
                if v:report['comparisons'][key]['mean_signed_deg']=float(np.mean(v))
            assert a['pilot']['sun']['observer']==b['pilot']['sun']['observer']
            report['comparisons']['disks']={}
            for body in ['sun','earth']:
                x,y=a['pilot'][body],b['pilot'][body]
                report['comparisons']['disks'][body]={'center_clearance_delta_deg':None if x['center_clearance_deg'] is None or y['center_clearance_deg'] is None else y['center_clearance_deg']-x['center_clearance_deg'],
                    'fraction_delta':None if x['visible_fraction'] is None or y['visible_fraction'] is None else y['visible_fraction']-x['visible_fraction'],
                    'states':[x['state'],y['state']],'unknown_delta':y['unknown_fraction']-x['unknown_fraction']}
            report['comparison_status']='DISK_COMPARISON_INCOMPLETE' if any(report['comparisons']['disks'][b]['fraction_delta'] is None for b in ['sun','earth']) else 'COMPLETED_SAMPLED_MODEL_COMPARISON'
    report['analytic_convergence']={}
    for n in (64,256,1024):
        t=time.perf_counter();errors=[]
        for ratio in np.linspace(-1,1,101):
            f=sampled_fraction(disk_samples(0,float(ratio*.27),.27,n),lambda a:SimpleNamespace(coverage_status='COMPLETE_SAMPLED_RANGE',horizon_elevation_deg=0))['visible_fraction']
            exact=(np.arccos(-ratio)+ratio*np.sqrt(1-ratio*ratio))/np.pi
            errors.append(float(f-exact))
        report['analytic_convergence'][str(n)]={'max_absolute_fraction_error':max(map(abs,errors)),'rms_fraction_error':float(np.sqrt(np.mean(np.array(errors)**2))),'seconds':time.perf_counter()-t}
    with output.open('x') as f:json.dump(report,f,indent=2,allow_nan=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);run(p.parse_args().output)
