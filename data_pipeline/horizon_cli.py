"""Read-only genuine terrain CLI. Explicit prototype opt-in, no source downloads."""
import argparse,json,os,time,resource
from pathlib import Path
from contextlib import ExitStack,contextmanager
from app.data.dem import open_dem
from app.data.fusion import MultiResolutionDem,TerrainSource
from app.data.quality import QualityLayer
from app.science.horizon import TerrainHorizonEngine
from app.science.horizon_models import HorizonRequest
from data_pipeline.lola_validation import inspected_reference,inspected_product,HASHES
from data_pipeline.lroc import inspect_lroc_label

@contextmanager
def terrain_session(enable_lroc=False):
    directory=Path(os.environ['NASA_LOLA_VALIDATION_DIR'])
    with ExitStack() as stack:
        sources=[]
        for role,name in [('SITE01','Site01_final_adj_5mpp_surf.tif'),('PRODUCT90','LDEM_80S_80MPP_ADJ.TIF')]:
            path=directory/name
            dem=stack.enter_context(open_dem(path,inspected_reference(path)))
            layers=tuple(QualityLayer(path=directory/n,product=inspected_product(directory/n),sha256=HASHES[n]) for n in HASHES if 'toterr' in n or 'ldec' in n) if role=='SITE01' else ()
            sources.append(TerrainSource(role,dem,layers))
        if enable_lroc:
            path,label=Path(os.environ['NASA_LROC_CR1_DEM']),Path(os.environ['NASA_LROC_CR1_LABEL'])
            sources.append(TerrainSource('LROC',stack.enter_context(open_dem(path,inspect_lroc_label(path,label)))))
        yield MultiResolutionDem(sources)


def measured(engine,request):
    start=time.perf_counter();result=engine.calculate(request)
    return result,dict(seconds=time.perf_counter()-start,process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        azimuth_count=len(result.rays),samples=sum(r.valid_sample_count+r.missing_sample_count for r in result.rays),
        identity=result.identity,sampling=request.sampling.model_dump(),max_range_m=request.max_range_m,
        source_hashes={k:v['reference']['raster_sha256'] for k,v in result.sources.items()})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if a.request.stat().st_size>65536:p.error('Request exceeds 64 KiB')
    request=HorizonRequest.model_validate_json(a.request.read_text())
    if a.output.exists():p.error('Refusing to overwrite output')
    with terrain_session(request.policy.enable_lroc) as terrain:
        result,performance=measured(TerrainHorizonEngine(terrain),request)
    with a.output.open('x') as f:json.dump({'result':result.model_dump(mode='json'),'performance':performance},f,indent=2,allow_nan=False)
