"""Command 06.1 actual-data, checkpointed budget experiment. No source switching."""
import argparse,json,os,time,resource
from pathlib import Path
from app.science.kernels import KernelSession
from app.science.visibility import VisibilityEngine
from app.science.visibility_models import VisibilityRequest
from data_pipeline.visibility_cli import visibility_terrain
from data_pipeline.visibility_validation import pilot


def compact(r):
    value=r.model_dump(mode='json')
    for b in ('sun','earth'):
        value[b].pop('horizon_ids')  # cache namespace, source hashes and request retain reproducibility
    value.pop('sources');value.pop('limitations')
    return value


def analytic_measurements():
    import math
    from types import SimpleNamespace
    from app.science.disk_geometry import disk_samples,sampled_fraction
    result={}
    for n in (64,256,1024):
        start=time.perf_counter();errors=[]
        for i in range(101):
            ratio=-1+i/50
            f=sampled_fraction(disk_samples(0,ratio*.27,.27,n),lambda az:SimpleNamespace(coverage_status='COMPLETE_SAMPLED_RANGE',horizon_elevation_deg=0))['visible_fraction']
            exact=(math.acos(-ratio)+ratio*math.sqrt(max(0,1-ratio*ratio)))/math.pi
            errors.append(f-exact)
        result[str(n)]={'seconds':time.perf_counter()-start,'max_absolute_fraction_error':max(map(abs,errors)),'rms_fraction_error':math.sqrt(sum(x*x for x in errors)/len(errors))}
    return result


def run(output,run1024=True):
    if output.exists() or output.with_suffix('.partial.json').exists():raise ValueError('Refusing overwrite')
    report={'status':'RUNNING','science_ready':False,'runs':{},'old_diagnostic':'INTENTIONALLY_RESOURCE_LIMITED_DIAGNOSTIC'}
    def save():
        temp=output.with_suffix('.partial.json');temp.write_text(json.dumps(report,indent=2,allow_nan=False))
    with KernelSession(os.environ['NASA_KERNEL_DIR'],os.environ['NASA_KERNEL_INDEX']) as s,visibility_terrain() as terrain:
        e=VisibilityEngine(s,terrain,cache_size=4096);q=pilot()
        def single(name,request):
            plan=e.preflight(request);print(name,'plan',plan,flush=True)
            r=e.run(request);report['runs'][name]=compact(r);save()
            print(name,r.performance,flush=True);return r
        first=single('first64',q);report['sources']=first.sources;report['limitations']=first.limitations
        single('repeat64',q)
        low=VisibilityRequest.model_validate(q.model_dump()|{'max_new_rays':8})
        for name,request in [('low_series',low),('complete_series',q)]:
            r=e.series(request,3,3600)
            report['runs'][name]={'samples':[compact(x) for x in r.samples],'performance':r.performance}
            save();print(name,r.performance,flush=True)
        q256=VisibilityRequest.model_validate(q.model_dump()|{'disk_samples':256,'max_new_rays':514})
        large=single('real256',q256)
        q1024=VisibilityRequest.model_validate(q.model_dump()|{'disk_samples':1024,'max_new_rays':2050})
        plan=e.preflight(q1024)
        cost=large.performance['seconds']/max(1,large.performance['accounting']['completed_rays'])
        plan.update(estimated_seconds=cost*plan['required_new_rays'],time_admission_limit_seconds=900,peak_rss_admission_limit_kib=1048576)
        report['plan1024']=plan;save()
        if run1024 and plan['estimated_seconds']<=900 and plan['estimated_dem_samples']<=q1024.terrain.max_total_samples and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<1048576:
            r1024=single('real1024',q1024)
            report['real1024_status']='COMPLETED' if not any('COMPUTATION_BUDGET_EXCEEDED' in b.reason_codes for b in (r1024.sun,r1024.earth)) else 'REAL_NASA_1024_NOT_COMPLETED_RESOURCE_LIMIT'
        else:report['real1024_status']='REAL_NASA_1024_NOT_COMPLETED_RESOURCE_LIMIT'
        # Small capacity on exactly the same actual terrain: measure eviction without re-running thousands of rays.
        small=VisibilityEngine(s,terrain,cache_size=2)
        start=time.perf_counter()
        for az in [0.,90.,180.,0.]:small._ray(q.terrain,az,[1,2000000])
        report['cache_capacity_diagnostic']={'capacity':2,'directions':[0,90,180,0],'seconds':time.perf_counter()-start,'accounting':small.counters()}
        report['aggregate_accounting']=e.counters();report['cache_capacity']=e.cache_size
        report['status']='COMMAND_06_1_PARTIAL' if any('COMPUTATION_BUDGET_EXCEEDED' in sample[b]['reason_codes'] for sample in report['runs']['complete_series']['samples']+[report['runs']['real256']] for b in ('sun','earth')) else 'COMMAND_06_1_COMPLETE_WITH_LIMITATIONS'
        save()
    report['analytic_measurements']=analytic_measurements()
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--no-1024',action='store_true');a=p.parse_args();run(a.output,not a.no_1024)
