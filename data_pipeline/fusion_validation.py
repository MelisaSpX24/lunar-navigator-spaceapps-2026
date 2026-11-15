"""Reproducible real-data diagnostic. Environment paths never enter evidence."""
import os
import json
import time
import resource
from pathlib import Path
from contextlib import contextmanager, ExitStack
import numpy as np
from app.data.coordinates import validate_coordinates
from app.data.dem import open_dem
from app.data.fusion import MultiResolutionDem, TerrainSource, TerrainRequest, TerrainPolicy
from app.data.quality import QualityLayer
from data_pipeline.lola_validation import inspected_reference, inspected_product, HASHES
from data_pipeline.lroc import inspect_lroc_label
from app.data.manifest import sha256_file


@contextmanager
def real_engine():
    directory=Path(os.environ['NASA_LOLA_VALIDATION_DIR'])
    with ExitStack() as stack:
        sources=[]
        for role,name in [('SITE01','Site01_final_adj_5mpp_surf.tif'),('PRODUCT90','LDEM_80S_80MPP_ADJ.TIF')]:
            path=directory/name
            dem=stack.enter_context(open_dem(path,inspected_reference(path)))
            layers=tuple(QualityLayer(path=directory/n,product=inspected_product(directory/n),sha256=HASHES[n])
                         for n in HASHES if 'toterr' in n or 'ldec' in n) if role=='SITE01' else ()
            sources.append(TerrainSource(role,dem,layers))
        path,label=Path(os.environ['NASA_LROC_CR1_DEM']),Path(os.environ['NASA_LROC_CR1_LABEL'])
        old=json.loads((Path(__file__).parent/'evidence/command-03-5.json').read_text())
        # Pin against the previously recorded genuine integration identities.
        expected=json.dumps(old)
        if sha256_file(path) not in expected or sha256_file(label) not in expected:
            raise ValueError('LROC identity differs from genuine closure record')
        sources.append(TerrainSource('LROC',stack.enter_context(open_dem(path,inspect_lroc_label(path,label)))))
        yield MultiResolutionDem(sources)


def request(location):
    return TerrainRequest(location=location,policy=TerrainPolicy(registration='PROTOTYPE'))


def coordinate(dem,x,y):
    return validate_coordinates(*dem.grid.xy_to_geographic(float(x),float(y)))


def height(dem,loc):
    s=dem.sample(loc,allow_unverified_registration=True)
    return s.surface_elevation_m


def stats(values):
    a=np.asarray(values,dtype=float)
    return dict(count=len(a),mean_m=float(a.mean()),median_m=float(np.median(a)),
                rmse_m=float(np.sqrt(np.mean(a*a))),min_m=float(a.min()),max_m=float(a.max()),
                p95_absolute_m=float(np.percentile(abs(a),95))) if len(a) else dict(count=0)


def run(engine):
    started=time.perf_counter()
    site=engine.sources['SITE01'].dem
    far=engine.sources['PRODUCT90'].dem
    lroc=engine.sources['LROC'].dem
    cr1=validate_coordinates(-89.468,222.6)
    # Source grid coordinates, evenly spaced interior cells. Each source projects independently.
    pairs=[]
    for row in range(100,2400,150):
        for col in range(100,2400,150):
            x,y=lroc.grid.pixel_center_xy(row,col)
            loc=coordinate(lroc,x,y)
            a,b=height(lroc,loc),height(site,loc)
            if a is None or b is None: continue
            q=site.sample(loc,allow_unverified_registration=True,quality_layers=list(engine.sources['SITE01'].quality_layers))
            neighbors=[height(site,coordinate(site,x+dx,y+dy)) for dx,dy in [(-10,0),(10,0),(0,-10),(0,10)]]
            slope=None if None in neighbors else float(np.degrees(np.arctan(np.hypot((neighbors[1]-neighbors[0])/20,(neighbors[3]-neighbors[2])/20))))
            pairs.append(dict(x_m=x,y_m=y,lroc_m=a,lola_m=b,difference_m=b-a,
                slope_20m_projected_deg=slope,quality={v.kind:v.value for v in q.quality.layers},
                split='train' if col<1250 else 'validation'))
    # Search a declared, bounded grid. Train on western half, validate eastern half.
    # Constant vertical bias fitted on train only; no adjustment applied to any source.
    trials=[]
    for dx in range(-10,11,5):
        for dy in range(-10,11,5):
            train=[];validation=[]
            for p in pairs:
                value=height(site,coordinate(site,p['x_m']+dx,p['y_m']+dy))
                if value is not None:
                    (train if p['split']=='train' else validation).append(value-p['lroc_m'])
            if train and validation:
                bias=float(np.median(train))
                trials.append(dict(dx_m=dx,dy_m=dy,train_bias_m=bias,
                    train_rmse_after_bias_m=stats(np.array(train)-bias)['rmse_m'],
                    validation_rmse_after_train_bias_m=stats(np.array(validation)-bias)['rmse_m'],
                    train_count=len(train),validation_count=len(validation)))
    best=min(trials,key=lambda t:t['train_rmse_after_bias_m'])
    baseline=next(t for t in trials if t['dx_m']==t['dy_m']==0)
    overlap=[]
    for row in range(100,3100,200):
        for col in range(100,3100,200):
            loc=validate_coordinates(*site.grid.pixel_center_geographic(row,col))
            a,b=height(site,loc),height(far,loc)
            if a is not None and b is not None:
                x,y=site.grid.pixel_center_xy(row,col)
                ns=[height(site,coordinate(site,x+dx,y+dy)) for dx,dy in [(-80,0),(80,0),(0,-80),(0,80)]]
                slope=None if None in ns else float(np.degrees(np.arctan(np.hypot((ns[1]-ns[0])/160,(ns[3]-ns[2])/160))))
                overlap.append(dict(difference_m=b-a,slope_160m_projected_deg=slope,location=loc.model_dump()))
    transitions=[]
    bounds=site.ds.bounds
    for x,y,axis in [(bounds.left,-12000,'x'),(bounds.right,-12000,'x'),(-11000,bounds.top,'y'),(-11000,bounds.bottom,'y')]:
        for delta in (-5,5):
            loc=coordinate(site,x+(delta if axis=='x' else 0),y+(delta if axis=='y' else 0))
            r=engine.sample(request(loc))
            transitions.append(dict(location=loc.model_dump(),boundary_axis=axis,delta_m=delta,
                selected_product=r.selected.product_id if r.selected else None,height_m=r.surface_elevation_m,
                status=r.status,overlap_spread_m=r.overlap_spread_m,
                attempts=[dict(role=a.source_role,status=a.status,height_m=a.sample.surface_elevation_m if a.sample else None) for a in r.attempts]))
    remote=engine.sample(request(coordinate(site,50000,-50000)))
    far_started=time.perf_counter()
    far_counts={}
    cx,cy=site.grid.geographic_to_xy(cr1)
    def far_requests():
        for dx in range(-150000,150001,10000):
            for dy in range(-150000,150001,10000):
                r=request(coordinate(site,cx+dx,cy+dy));r.purpose='FAR_TERRAIN'
                yield r
    for result in engine.iter_samples(far_requests()):
        key=result.selected.product_id if result.selected else result.status
        far_counts[key]=far_counts.get(key,0)+1
    far_benchmark=dict(samples=sum(far_counts.values()),source_counts=far_counts,
        seconds=time.perf_counter()-far_started,method='31x31 projected grid over 300 km square; streamed point queries, not full area/horizon proof')
    return dict(schema_version='1',science_ready=False,far_benchmark=far_benchmark,
        sources={s.role:s.dem.reference.model_dump(mode='json') for s in engine.sources.values()},
        cr1=engine.sample(request(cr1)).model_dump(mode='json'),
        lroc_pairs=pairs,lroc_minus_lola_sign='differences are LOLA minus LROC',
        lroc_relative_stats=stats([p['difference_m'] for p in pairs]),
        slope_groups={name:stats([p['difference_m'] for p in pairs if p['slope_20m_projected_deg'] is not None and (p['slope_20m_projected_deg']<10)==low]) for name,low in [('under_10deg',True),('at_least_10deg',False)]},
        shift_search=dict(trials=trials,best_training=best,zero_shift=baseline,
            interpretation='Exploratory containing-cell grid search, 5 m grid precision, +/-10 m bounds; no statistical confidence interval. Spatial holdout is not independent ground truth. Resolution/slope/interpolation errors confound shift. No correction applied.'),
        site01_product90_difference=stats([p['difference_m'] for p in overlap]),
        site01_product90_samples=overlap,
        site01_product90_slope_groups={name:stats([p['difference_m'] for p in overlap if p['slope_160m_projected_deg'] is not None and (p['slope_160m_projected_deg']<10)==low]) for name,low in [('under_10deg',True),('at_least_10deg',False)]},
        source_transitions=transitions,
        transition_jumps_m=[transitions[i+1]['height_m']-transitions[i]['height_m'] for i in range(0,8,2)],
        quality_groups={name:stats([p['difference_m'] for p in pairs if (p['quality']['COUNT']>0)==positive]) for name,positive in [('direct_spot',True),('interpolated',False)]},
        far_sample=remote.model_dump(mode='json'),
        performance=dict(diagnostic_seconds=time.perf_counter()-started,process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        registration='RELATIVE_COREGISTRATION_ASSESSED_ABSOLUTE_UNVERIFIED',
        absolute_registration='LROC_ABSOLUTE_REGISTRATION_NOT_VERIFIED')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args()
    if args.output.exists(): parser.error('Refusing to overwrite evidence')
    with real_engine() as engine: result=run(engine)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['lroc_relative_stats','site01_product90_difference','performance']}))
