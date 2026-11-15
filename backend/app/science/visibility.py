"""Session-scoped disk visibility with bounded exact-ray reuse; no API promotion."""
from collections import OrderedDict
from pathlib import Path
from copy import deepcopy
from app.data.raster import open_local
from datetime import timedelta
import hashlib
import math
import json
import time
import resource
import numpy as np
import spiceypy as spice
from app.data.fusion import TerrainRequest
from app.data.observer import prepare_observer
from app.science.astronomy import calculate
from app.science.disk_geometry import angular_radius, disk_samples, sampled_fraction
from app.science.kernels import ScienceError
from app.science.horizon import TerrainHorizonEngine, HorizonBudgetError, quality_identity, LIMITATIONS as TERRAIN_LIMITATIONS
from app.science.horizon_models import HorizonRequest
from app.science.visibility_models import BodyVisibility, VisibilityResult, VisibilitySeries

LIMITATIONS=TERRAIN_LIMITATIONS+[
 'SPHERICAL_BODY_DISK_APPROXIMATION: effective radius is arithmetic mean of PCK axes; Earth flattening is not resolved.',
 'Equal projected-area finite disk samples; bounds apply only to these samples and the sampled terrain model.',
 'No horizon interpolation. Uncomputed rays remain UNKNOWN. No physical FULL/NONE guarantee between samples.',
 'LT+S uses corrected centre distance for radius; differential aberration across the disk is neglected.',
 'INDEPENDENT_ASTRONOMY_VALIDATION_NOT_ESTABLISHED',
 'Solar disk fraction is not electrical power; Earth disk fraction is not RF link availability.',
 'ABSOLUTE_REGISTRATION_NOT_VERIFIED; no atmospheric refraction or source alignment correction.',
]


class VisibilityEngine:
    """Borrow immutable open kernel/DEM sessions. Discard cache when sessions close.

    Cache namespace includes full source references, CRS, auxiliary and quality
    evidence via the existing horizon identity. Requests include device height,
    observer location, policies, sampling, range and resource budgets, not UTC.
    """
    def __init__(self, session, terrain, cache_size=512):
        if type(cache_size) is not int or not 1<=cache_size<=4096: raise ValueError('Invalid cache size')
        self.session,self.terrain=session,terrain
        self.horizon=TerrainHorizonEngine(terrain)
        self.cache=OrderedDict(); self.cache_size=cache_size
        self.hits=self.misses=self.dem_samples=0
        self.completed=self.rejected=self.failed=self.cache_misses=self.evictions=0
        self.sources=None; self.origin=None
        self.namespace=hashlib.sha256(json.dumps({k:{'reference':s.dem.reference.model_dump(mode='json'),
            'crs':s.dem.crs.to_wkt(),'transform':list(s.dem.ds.transform),'auxiliary':s.dem.auxiliary_file_hashes,
            'quality':[quality_identity(q) for q in s.quality_layers]} for k,s in terrain.sources.items()},sort_keys=True).encode()).hexdigest()
        self._quality_paths=set()
        for source in terrain.sources.values():
            for layer in source.quality_layers:
                with open_local(layer.path) as ds:self._quality_paths.update(ds.files)
        self._initial_source_state=self._source_state()
        self._horizon_sources=self.horizon.source_metadata()
        self.horizon.metadata_provider=self._source_metadata


    def _source_metadata(self):
        self._assert_sources_unchanged()
        return deepcopy(self._horizon_sources)


    def _source_state(self):
        metadata = []
        paths = set()
        for role, source in self.terrain.sources.items():
            dem = source.dem
            if dem.ds.closed:
                raise ScienceError("DEM_SOURCE_UNAVAILABLE", "Terrain session closed")
            paths.update(dem.ds.files)
            metadata.append(
                (
                    role,
                    id(dem),
                    dem.reference.model_dump_json(),
                    tuple(dem.ds.transform),
                    dem.crs.to_wkt(),
                    tuple(sorted(dem.auxiliary_file_hashes.items())),
                    tuple(
                        (q.sha256, q.product.model_dump_json())
                        for q in source.quality_layers
                    ),
                )
            )
        paths.update(self._quality_paths)
        optional = {
            str(p) + suffix for p in paths for suffix in (".aux.xml", ".ovr", ".msk")
        }
        try:
            files = []
            for p in sorted(paths | optional):
                path = Path(p)
                if not path.exists() and p in optional and p not in paths:
                    files.append((str(path.resolve()), None))
                    continue
                st = path.stat()
                files.append(
                    (
                        str(path.resolve()),
                        st.st_dev,
                        st.st_ino,
                        st.st_size,
                        st.st_mtime_ns,
                        st.st_ctime_ns,
                    )
                )
            files = tuple(files)
        except OSError as exc:
            raise ScienceError("DEM_SOURCE_UNAVAILABLE", str(exc)) from exc
        return metadata, files


    def _assert_sources_unchanged(self):
        if self._source_state() != self._initial_source_state:
            self.cache.clear()
            raise ScienceError(
                "DEM_SOURCE_CHANGED", "Reopen and revalidate the science session"
            )


    def _cache_keys(self, q):
        exact = self.namespace + ":disk-exact-rays-v1:" + q.model_dump_json()
        values = q.model_dump()
        values.pop("max_total_samples")
        complete = (
            self.namespace
            + ":disk-complete-total-allowance-v1:"
            + json.dumps(values, sort_keys=True, default=str)
        )
        return exact, complete


    def _ray(self, req, az, budget):
        self.last_budget_stage=None
        self._assert_sources_unchanged()
        if az is None: return None,None,'HORIZON_AZIMUTH_NOT_SAMPLED'
        if any(s.dem.ds.closed for s in self.terrain.sources.values()):
            raise ScienceError('DEM_SOURCE_UNAVAILABLE','Terrain session closed')
        q=HorizonRequest.model_validate(req.model_dump() | {'mode':'RAYS','azimuths_deg':[az]})
        exact,complete=self._cache_keys(q)
        key=complete if complete in self.cache else exact
        if key in self.cache:
            self.hits+=1; self.cache.move_to_end(key)
            return self.cache[key]
        self.cache_misses+=1
        if budget[0]<=0 or budget[1]<=0:
            self.last_budget_stage='NEW_RAY_LIMIT' if budget[0]<=0 else 'TOTAL_POINT_LIMIT'
            self.rejected+=1
            return None,None,'COMPUTATION_BUDGET_EXCEEDED'
        least=math.ceil((q.max_range_m-q.sampling.start_m)/q.sampling.max_step_m)+1
        if least>min(q.max_samples_per_ray,budget[1]):
            self.last_budget_stage='MINIMUM_POINT_PREFLIGHT'
            self.rejected+=1
            return None,None,'COMPUTATION_BUDGET_EXCEEDED'
        budget[0]-=1;self.misses+=1
        try: result=self.horizon.calculate(HorizonRequest.model_validate(q.model_dump() | {'max_total_samples':min(q.max_total_samples,budget[1])}))
        except HorizonBudgetError as exc:
            self.last_budget_stage='MINIMUM_POINT_PREFLIGHT' if exc.samples==0 else 'PER_RAY_POINT_LIMIT' if q.max_samples_per_ray<=budget[1] else 'TOTAL_POINT_LIMIT'
            self.failed+=1
            self.dem_samples+=exc.samples
            budget[1]=max(0,budget[1]-exc.samples)
            self.rejected+=1
            return None,None,'COMPUTATION_BUDGET_EXCEEDED'
        self.completed+=1
        self.sources=result.sources;self.origin=result.data_origin
        ray=result.horizon_at_azimuth(az)
        self.dem_samples+=ray.valid_sample_count+ray.missing_sample_count
        budget[1]-=ray.valid_sample_count+ray.missing_sample_count
        code={'COMPLETE_SAMPLED_RANGE':None,'INCOMPLETE':'HORIZON_INCOMPLETE','UNKNOWN':'HORIZON_UNKNOWN'}[ray.coverage_status]
        value=(ray,result.identity,code)
        key=complete if ray.coverage_status=='COMPLETE_SAMPLED_RANGE' else exact
        self.cache[key]=value
        if len(self.cache)>self.cache_size:
            self.cache.popitem(last=False);self.evictions+=1
        return value

    def counters(self):
        return dict(attempted_rays=self.misses,completed_rays=self.completed,
            failed_budget_attempts=self.failed,budget_rejected_rays=self.rejected,
            cache_hits=self.hits,cache_misses=self.cache_misses,dem_samples=self.dem_samples,
            cache_evictions=self.evictions)

    def preflight(self, request):
        """Exact direction/cache inventory; point/time estimates are not guarantees."""
        import math
        surface=self.terrain.sample(TerrainRequest(location=request.terrain.location,policy=request.terrain.policy,preferred_resolution_m=request.terrain.preferred_resolution_m))
        if surface.selected is None:raise ScienceError('INVALID_OBSERVER','No accepted observer')
        self._assert_sources_unchanged()
        keys={}
        for body,height in [('sun',request.solar_height_above_surface_m),('earth',request.earth_height_above_surface_m)]:
            observer=prepare_observer(surface.selected,height).observer
            direction=getattr(calculate(self.session,observer,request.utc,request.correction),body)
            try:
                with self.session.call():radii=np.asarray(spice.bodvrd(body.upper(),'RADII',3)[1],dtype=float)
            except ScienceError as exc:
                raise ScienceError('DISK_RADIUS_UNAVAILABLE',str(exc)) from exc
            if radii.shape!=(3,) or not np.isfinite(radii).all() or (radii<=0).any():
                raise ScienceError('DISK_RADIUS_UNAVAILABLE',body)
            alpha=angular_radius(float(np.mean(radii)),direction.distance_km)
            for az in [direction.azimuth_deg]+[a for a,e,w in disk_samples(direction.azimuth_deg,direction.elevation_deg,alpha,request.disk_samples)]:
                if az is None:continue
                q=HorizonRequest.model_validate(request.terrain.model_dump()|{'device_height_m':height,'mode':'RAYS','azimuths_deg':[az]})
                exact,complete=self._cache_keys(q)
                keys[complete]=exact
        hits=sum(complete in self.cache or exact in self.cache for complete,exact in keys.items());new=len(keys)-hits
        sampling=request.terrain.sampling
        low=math.ceil((request.terrain.max_range_m-sampling.start_m)/sampling.max_step_m)+1
        high=math.ceil((request.terrain.max_range_m-sampling.start_m)/sampling.min_step_m)+1
        average=self.dem_samples/self.completed if self.completed else None
        return dict(unique_ray_keys=len(keys),cached_ray_keys=hits,required_new_rays=new,
            minimum_dem_samples=new*low,maximum_lattice_dem_samples=new*high,
            estimated_dem_samples=None if average is None else math.ceil(new*average),
            ray_budget_sufficient=new<=request.max_new_rays,
            minimum_point_budget_sufficient=new*low<=request.terrain.max_total_samples,
            cache_capacity=self.cache_size,cache_namespace=self.namespace,
            limitation='Initial cache inventory; LRU eviction may require more work. Mean cost is empirical, not a bound.')

    def run(self,request):
        start=time.perf_counter(); accounting_before=self.counters(); plan=self.preflight(request); before=(self.hits,self.misses,self.dem_samples)
        # Observer selection uses the same policy as every ray; no fallback height.
        surface=self.terrain.sample(TerrainRequest(location=request.terrain.location,
            policy=request.terrain.policy,preferred_resolution_m=request.terrain.preferred_resolution_m))
        if surface.selected is None:raise ScienceError('INVALID_OBSERVER','No policy-acceptable DEM observer')
        budget=[request.max_new_rays,request.terrain.max_total_samples];bodies=[];geometries={}
        for body,height in [('SUN',request.solar_height_above_surface_m),('EARTH',request.earth_height_above_surface_m)]:
            t=time.perf_counter(); counters=(self.hits,self.misses,self.dem_samples)
            observer=prepare_observer(surface.selected,height).observer
            ts=time.perf_counter()
            if height not in geometries:geometries[height]=calculate(self.session,observer,request.utc,request.correction)
            geometry=geometries[height];spice_seconds=time.perf_counter()-ts
            direction=geometry.sun if body=='SUN' else geometry.earth
            try:
                with self.session.call():
                    radii=np.asarray(spice.bodvrd(body,'RADII',3)[1],dtype=float)
            except ScienceError as exc:
                raise ScienceError('DISK_RADIUS_UNAVAILABLE',str(exc)) from exc
            if radii.shape!=(3,) or not np.isfinite(radii).all() or (radii<=0).any():
                raise ScienceError('DISK_RADIUS_UNAVAILABLE',body)
            radius=float(np.mean(radii));alpha=angular_radius(radius,direction.distance_km)
            q=HorizonRequest.model_validate(request.terrain.model_dump() | {'device_height_m':height})
            ids=set();reasons=set(); observed={}; stages={}
            body_before=self.counters()
            def lookup(az):
                ray,identity,code=self._ray(q,az,budget)
                observed[az]=(ray,code)
                stages[az]=self.last_budget_stage
                if identity:ids.add(identity)
                if code:reasons.add(code)
                if ray:reasons.update(ray.warnings)
                return ray
            center=lookup(direction.azimuth_deg)
            horizon=center.horizon_elevation_deg if center else None
            samples=tuple(disk_samples(direction.azimuth_deg,direction.elevation_deg,alpha,request.disk_samples))
            values=sampled_fraction(samples,lookup)
            unknown_directions=[]
            for az,el,w in samples:
                ray,code=observed.get(az,(None,'HORIZON_AZIMUTH_NOT_SAMPLED'))
                if ray is None or ray.coverage_status=='UNKNOWN' or (ray.coverage_status=='INCOMPLETE' and el>ray.partial_max_obstruction_deg):
                    unknown_directions.append(dict(azimuth_deg=az,reason=code,budget_stage=stages.get(az),terrain_reasons=ray.reason_counts if ray else {}))
            bodies.append(BodyVisibility(body=body,utc=geometry.time_utc,observer=observer,direction=direction,
                angular_radius_deg=alpha,radii_km=radii.tolist(),effective_radius_km=radius,
                radius_kernel=next(k for k in geometry.kernel_ids if k.startswith('pck00011.tpc:')),
                center_horizon_deg=horizon,center_clearance_deg=None if horizon is None else direction.elevation_deg-horizon,
                **values,horizon_ids=sorted(ids),disk_sample_count=request.disk_samples,reason_codes=sorted(reasons),
                performance=dict(accounting={k:v-body_before[k] for k,v in self.counters().items()},unknown_directions=unknown_directions,seconds=time.perf_counter()-t,spice_seconds=spice_seconds,cache_hits=self.hits-counters[0],new_rays=self.misses-counters[1],dem_samples=self.dem_samples-counters[2])))
        # Evidence even when zero rays were affordable.
        sources=self.sources or {k:{'reference':s.dem.reference.model_dump(mode='json')} for k,s in self.terrain.sources.items()}
        return VisibilityResult(request=request,sun=bodies[0],earth=bodies[1],sources=sources,
            kernel_ids=geometry.kernel_ids,data_origin=self.origin or 'MIXED_OR_UNVERIFIED',limitations=LIMITATIONS,
            performance=dict(preflight=plan,accounting={k:v-accounting_before[k] for k,v in self.counters().items()},remaining_ray_budget=budget[0],remaining_point_budget=budget[1],seconds=time.perf_counter()-start,cache_hits=self.hits-before[0],new_rays=self.misses-before[1],dem_samples=self.dem_samples-before[2],peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))

    def series(self,request,count=3,step_seconds=3600):
        if type(count) is not int or not 1<=count<=12 or type(step_seconds) is not int or not 1<=step_seconds<=86400:
            raise ValueError('Series limited to 1..12 samples and 1..86400 second steps')
        t=time.perf_counter()
        samples=[self.run(type(request).model_validate(request.model_dump() | {'utc':request.utc+timedelta(seconds=i*step_seconds)})) for i in range(count)]
        return VisibilitySeries(samples=samples,step_seconds=step_seconds,
            performance=dict(seconds=time.perf_counter()-t,cache_hits=sum(s.performance['cache_hits'] for s in samples),new_rays=sum(s.performance['new_rays'] for s in samples),unknown_bodies=sum(b.state=='UNKNOWN' for s in samples for b in [s.sun,s.earth])),
            limitations=['Discrete times only; no exact rise/set or transition times.']+LIMITATIONS)
