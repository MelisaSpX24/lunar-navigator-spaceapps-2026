"""Read-only disk visibility CLI; default terrain remains Site01 + 80MPP."""
import argparse,json,os,time
from contextlib import contextmanager
from pathlib import Path
from app.data.dem import open_dem
from app.data.fusion import MultiResolutionDem,TerrainSource
from app.data.lola import lola_reference
from app.data.manifest import Manifest,sha256_file
from app.science.kernels import KernelSession,ScienceError
from app.science.visibility import VisibilityEngine
from app.science.visibility_models import VisibilityRequest
from data_pipeline.horizon_cli import terrain_session
from data_pipeline.lola_validation import VERTICAL_EVIDENCE,VERSION_EVIDENCE

LOLA20_HASH='09b7ca80f9e6a146f970225d18af72fc02787669b3ef51b888e347d2b6845649'

@contextmanager
def visibility_terrain(use_20m=False):
    with terrain_session() as baseline:
        if not use_20m:
            yield baseline
            return
        p=Path(os.environ.get('NASA_PRODUCT90_DEM','/nonexistent'))
        if not p.is_file():raise ScienceError('LOLA20_SOURCE_UNAVAILABLE','Set NASA_PRODUCT90_DEM')
        if sha256_file(p)!=LOLA20_HASH:raise ScienceError('LOLA20_HASH_MISMATCH','Unexpected uploaded file identity')
        manifest=Manifest.model_validate_json((Path(__file__).parent/'manifests/lola.json').read_text())
        product=next(x for x in manifest.products if x.id=='LDEM_80S_20MPP_ADJ.TIF')
        product=type(product).model_validate(product.model_dump() | {'height_datum':'HEIGHT_ABOVE_REFERENCE_SPHERE','sha256':LOLA20_HASH,'local_path':str(p),'status':'FILE_INSPECTED'})
        ref=lola_reference(p,product,vertical_evidence=VERTICAL_EVIDENCE,version_evidence=VERSION_EVIDENCE)
        with open_dem(p,ref) as dem:
            if dem.ds.res!=(20.,20.):raise ValueError('Expected 20 m grid')
            yield MultiResolutionDem([baseline.sources['SITE01'],TerrainSource('PRODUCT90',dem)])


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--request',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--use-20m',action='store_true');p.add_argument('--count',type=int,default=1)
    p.add_argument('--step-seconds',type=int,default=3600)
    p.add_argument('--cache-size',type=int,default=512)
    a=p.parse_args()
    if a.output.exists():p.error('Refusing to overwrite output')
    if a.request.stat().st_size>65536:p.error('Request exceeds 64 KiB')
    request=VisibilityRequest.model_validate_json(a.request.read_text())
    t=time.perf_counter()
    try:
        with KernelSession(os.environ['NASA_KERNEL_DIR'],os.environ['NASA_KERNEL_INDEX']) as session, visibility_terrain(a.use_20m) as terrain:
            setup=time.perf_counter()-t
            engine=VisibilityEngine(session,terrain,cache_size=a.cache_size)
            result=engine.run(request) if a.count==1 else engine.series(request,a.count,a.step_seconds)
            payload={'result':result.model_dump(mode='json'),'setup_seconds':setup}
    except ScienceError as exc:
        payload={'execution_status':'FAILED','error_code':exc.code,'message':str(exc),'science_ready':False}
        with a.output.open('x') as f:json.dump(payload,f,indent=2,allow_nan=False)
        raise SystemExit(1)
    with a.output.open('x') as f:json.dump(payload,f,indent=2,allow_nan=False)

if __name__=='__main__':main()
