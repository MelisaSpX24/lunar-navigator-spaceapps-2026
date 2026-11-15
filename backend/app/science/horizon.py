"""Exact spherical point geometry on geodesic rays. No continuous-terrain claim."""
import math
import hashlib
import json
from collections import Counter
from pathlib import Path
from app.data.raster import open_local
from app.data.manifest import sha256_file
from pyproj import Geod
from app.data.fusion import TerrainRequest
from app.data.coordinates import validate_coordinates
from app.data.observer import prepare_observer
from app.science.geometry import REFERENCE_RADIUS_M as R
from app.science.horizon_models import HorizonRequest, HorizonRay, HorizonResult, Obstruction

LIMITATIONS=[
 'Point samples do not cover every crossed cell; narrow ridges and azimuth gaps can be missed.',
 'Adaptive step uses the last selected resolution; a boundary or NoData island between samples can be missed.',
 'Complete means all planned samples in the requested range; excludes the unsampled observer-to-start interval and terrain beyond range.',
 'Registration, pixel resolution and source seams remain uncertain; no physical accuracy or visibility guarantee.',
 'Range convergence is not established by a single run. No refraction or sloped ground normal is used.',
]

def elevation_angle_deg(surface_m,device_m,terrain_m,distance_m):
    if not all(math.isfinite(v) for v in (surface_m,device_m,terrain_m,distance_m)) or device_m<0 or not 0<distance_m<math.pi*R or R+surface_m<=0 or R+terrain_m<=0:
        raise ValueError('Invalid physical horizon geometry')
    if not math.isfinite(R+surface_m+device_m): raise ValueError('Observer radius overflow')
    alpha=distance_m/R
    # Exact cosine identity avoids cancellation for short distances.
    up=(terrain_m-surface_m-device_m)-2*(R+terrain_m)*math.sin(alpha/2)**2
    horizontal=(R+terrain_m)*math.sin(alpha)
    if not all(math.isfinite(v) for v in (up,horizontal)): raise ValueError("Nonfinite horizon vector")
    return math.degrees(math.atan2(up,horizontal))

def quality_identity(layer):
    identity={'id':layer.product.id,'sha256':layer.sha256,
              'kind':layer.product.kind,'units':layer.product.units}
    try:
        with open_local(layer.path) as ds:
            identity['auxiliary_hashes']={Path(p).name:sha256_file(Path(p)) for p in ds.files
                if Path(p).resolve()!=layer.path.resolve()}
    except (OSError,ValueError):
        identity['auxiliary_identity_status']='UNAVAILABLE'
    return identity

class HorizonBudgetError(ValueError):
    """Budget failure retaining actual ray terrain-query count, never a horizon."""
    def __init__(self, message, samples=0):
        self.samples = samples
        super().__init__(message)

class TerrainHorizonEngine:
    def __init__(self, terrain):
        self.terrain=terrain
        self.geod=Geod(a=R,b=R)
        self.metadata_provider=None
    def source_metadata(self):
        return {
            role: {
                "reference": s.dem.reference.model_dump(mode="json"),
                "crs_wkt": s.dem.crs.to_wkt(),
                "transform": list(s.dem.ds.transform),
                "resolution_m": list(s.dem.ds.res),
                "auxiliary_hashes": s.dem.auxiliary_file_hashes,
                "quality": [quality_identity(q) for q in s.quality_layers],
            }
            for role, s in self.terrain.sources.items()
        }

    def _query(self,request,location):
        return self.terrain.sample(TerrainRequest(location=location,policy=request.policy,
            preferred_resolution_m=request.preferred_resolution_m,purpose='TERRAIN'))
    def calculate(self,request:HorizonRequest):
        azimuths=request.directions()
        # A lower bound rejects clearly impossible requests before data reads.
        least=math.ceil((request.max_range_m-request.sampling.start_m)/request.sampling.max_step_m)+1
        if least>request.max_samples_per_ray or least*len(azimuths)>request.max_total_samples:
            raise HorizonBudgetError('Horizon sample budget exceeded')
        observer=self._query(request,request.location)
        sources=self.metadata_provider() if self.metadata_provider else self.source_metadata()
        identity=hashlib.sha256(json.dumps({'request':request.model_dump(mode='json'),
            'observer':observer.model_dump(mode='json'),'sources':sources,'algorithm':'spherical-point-rays-v1'},sort_keys=True,allow_nan=False).encode()).hexdigest()
        rays=[];used=0
        if observer.status=='VALID' and observer.selected is not None:
            prepare_observer(observer.selected,request.device_height_m)
            for az in azimuths:
                ray,n=self._ray(request,observer,az,request.max_total_samples-used)
                rays.append(ray);used+=n
        else:
            rays=[HorizonRay(azimuth_deg=a,coverage_status='UNKNOWN',requested_range_m=request.max_range_m,
                warnings=['INVALID_OBSERVER_EVIDENCE']+observer.warnings) for a in azimuths]
        statuses={r.coverage_status for r in rays}
        status='COMPLETE_SAMPLED_RANGE' if statuses=={'COMPLETE_SAMPLED_RANGE'} else 'UNKNOWN' if statuses=={'UNKNOWN'} else 'INCOMPLETE'
        families={s.dem.reference.family for s in self.terrain.sources.values()}
        origin='SYNTHETIC_TEST' if families=={'SYNTHETIC_TEST_FIXTURE'} else 'REAL_NASA_PROTOTYPE' if families<= {'LOLA','LROC_STEREO_DTM'} else 'MIXED_OR_UNVERIFIED'
        return HorizonResult(request=request,observer_surface=observer,identity=identity,sources=sources,
            data_origin=origin,rays=rays,overall_status=status,limitations=LIMITATIONS)
    def _ray(self,req,observer,az,budget):
        s=req.sampling.start_m;valid=missing=outside=conflicts=reported=errors=transitions=0
        sources=Counter();quality=Counter();reasons=Counter();resolutions=set();warnings=set(observer.warnings)
        best=None;previous=None;n=0
        while True:
            if n>=min(req.max_samples_per_ray,budget): raise HorizonBudgetError('Horizon sample budget exceeded during ray', n)
            lon,lat,_=self.geod.fwd(req.location.longitude_deg_east,req.location.latitude_deg,az,s)
            loc=validate_coordinates(lat,lon%360)
            sample=self._query(req,loc);n+=1;warnings.update(sample.warnings)
            for a in sample.attempts: reasons[a.status]+=1
            conflicts+=sample.status=='UNRESOLVED_SOURCE_CONFLICT'
            reported+=any(w.startswith('SOURCE_HEIGHT_CONFLICT') for w in sample.warnings)
            errors+=any(a.status=='SOURCE_READ_ERROR' for a in sample.attempts)
            outside+=bool(sample.attempts) and all(a.status in ('OUTSIDE_RASTER','OUT_OF_RASTER_BOUNDS') for a in sample.attempts)
            step=req.sampling.min_step_m
            if sample.status=='VALID' and sample.selected is not None:
                selected=sample.selected;h=sample.surface_elevation_m
                angle=elevation_angle_deg(observer.surface_elevation_m,req.device_height_m,h,s)
                valid+=1;sources[selected.product_id]+=1;quality[selected.quality.status]+=1
                resolutions.update(selected.resolution_m)
                current=selected.product_id
                if previous is not None and current!=previous: transitions+=1
                previous=current
                if best is None or angle>best.elevation_deg:
                    best=Obstruction(distance_m=s,location=loc,elevation_deg=angle,terrain=sample)
                step=min(req.sampling.max_step_m,max(req.sampling.min_step_m,min(selected.resolution_m)*req.sampling.resolution_factor))
            else:
                missing+=1
                # Unknown segments use conservative requested scale, still point sampling.
                step=min(req.sampling.max_step_m,max(req.sampling.min_step_m,req.preferred_resolution_m*req.sampling.resolution_factor))
            if s>=req.max_range_m: break
            s=min(req.max_range_m,s+step)
        status='UNKNOWN' if not valid else 'INCOMPLETE' if missing else 'COMPLETE_SAMPLED_RANGE'
        return HorizonRay(azimuth_deg=az,coverage_status=status,
            horizon_elevation_deg=best.elevation_deg if status=='COMPLETE_SAMPLED_RANGE' else None,
            partial_max_obstruction_deg=best.elevation_deg if status=='INCOMPLETE' else None,
            obstruction=best,requested_range_m=req.max_range_m,sampled_range_m=s,
            valid_sample_count=valid,missing_sample_count=missing,outside_sample_count=outside,
            conflict_sample_count=conflicts,reported_conflict_count=reported,read_error_count=errors,
            source_transition_count=transitions,source_counts=dict(sources),resolutions_m=sorted(resolutions),
            quality_status_counts=dict(quality),reason_counts=dict(reasons),warnings=sorted(warnings)),n
