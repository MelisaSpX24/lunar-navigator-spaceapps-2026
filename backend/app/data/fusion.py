"""Virtual, bounded source selection. No mosaic, offsets or terrain visibility."""
from dataclasses import dataclass
from itertools import islice
from typing import Literal

from pydantic import Field
from app.models.analysis import Model, Coordinates
from app.data.dem import DemReader
from app.data.dem_models import DemSample
from app.data.quality import QualityLayer


class TerrainPolicy(Model):
    registration: Literal['STRICT', 'PROTOTYPE'] = 'STRICT'
    enable_lroc: bool = False
    conflict: Literal['REPORT', 'REJECT'] = 'REPORT'
    conflict_threshold_m: float = Field(default=10, gt=0)


class TerrainRequest(Model):
    location: Coordinates
    preferred_resolution_m: float = Field(default=5, gt=0)
    purpose: Literal['TERRAIN', 'FAR_TERRAIN', 'REGISTRATION_DIAGNOSTIC'] = 'TERRAIN'
    policy: TerrainPolicy = Field(default_factory=TerrainPolicy)


class SourceAttempt(Model):
    source_role: str
    product_id: str
    sha256: str
    status: str
    sample: DemSample | None = None


class TerrainSample(Model):
    request: TerrainRequest
    status: Literal['VALID', 'UNKNOWN', 'UNRESOLVED_SOURCE_CONFLICT']
    surface_elevation_m: float | None
    selected: DemSample | None
    selection_reason: str
    attempts: list[SourceAttempt]
    overlap_spread_m: float | None
    warnings: list[str]
    science_ready: Literal[False] = False


@dataclass(frozen=True)
class TerrainSource:
    role: Literal['SITE01', 'PRODUCT90', 'LROC']
    dem: DemReader
    quality_layers: tuple[QualityLayer, ...] = ()


class MultiResolutionDem:
    """Borrows open immutable DEM sessions; hashes are checked by open_dem once.

    Source role is a caller declaration, not authentication. Each DemReader has
    already checked its actual CRS/encoding and pinned reference identity.
    """
    def __init__(self, sources: list[TerrainSource], *, max_batch=1024):
        if not sources or len(sources) > 3 or len({s.role for s in sources}) != len(sources):
            raise ValueError('Supply one to three unique source roles')
        if type(max_batch) is not int or not 0 < max_batch <= 4096:
            raise ValueError('Batch budget must be an integer in [1,4096]')
        for source in sources:
            if source.role not in ('SITE01', 'PRODUCT90', 'LROC'):
                raise ValueError('Unknown terrain source role')
            ref = source.dem.reference
            expected = {'SITE01': ('LOLA', 'PGDA Product 78'),
                        'PRODUCT90': ('LOLA', 'PGDA Product 90'),
                        'LROC': ('LROC_STEREO_DTM', 'LRO-L-LROC-5-RDR-V1.0')}[source.role]
            if ref.family != 'SYNTHETIC_TEST_FIXTURE' and (ref.family, ref.source_product_family) != expected:
                raise ValueError('Source role conflicts with its product family')
        self.sources = {s.role: s for s in sources}
        self.max_batch = max_batch

    def sample(self, request: TerrainRequest) -> TerrainSample:
        policy = request.policy
        roles = ['SITE01', 'PRODUCT90']
        if policy.enable_lroc:
            roles = (['LROC'] + roles if request.preferred_resolution_m < 5 else roles + ['LROC'])
        attempts, valid, warnings = [], [], []
        for role in roles:
            source = self.sources.get(role)
            if source is None:
                continue
            ref = source.dem.reference
            status = None
            if ref.frame_status == 'INCOMPATIBLE':
                status = 'INCOMPATIBLE_FRAME'
            elif policy.registration == 'STRICT' and not ref.product_specific_frame_verified:
                status = 'FRAME_NOT_PRODUCT_VERIFIED'
            sample = None
            if status is None:
                try:
                    sample = source.dem.sample(request.location,
                        allow_unverified_registration=policy.registration == 'PROTOTYPE',
                        quality_layers=list(source.quality_layers))
                    status = sample.status
                except (OSError, ValueError) as exc:
                    # Errors are visible evidence; never manufacture a height.
                    status = getattr(exc, 'code', 'SOURCE_READ_ERROR')
                    warnings.append(f'{role}: {status}')
            attempts.append(SourceAttempt(source_role=role, product_id=ref.product_id,
                sha256=ref.raster_sha256, status=status, sample=sample))
            if sample is not None and sample.status == 'VALID':
                valid.append(sample)
        spread = max(s.surface_elevation_m for s in valid)-min(s.surface_elevation_m for s in valid) if len(valid)>1 else None
        selected = valid[0] if valid else None
        status = 'VALID' if selected else 'UNKNOWN'
        reason = 'FIRST_VALID_POLICY_ACCEPTABLE_SOURCE' if selected else 'NO_VALID_POLICY_ACCEPTABLE_SOURCE'
        if spread is not None and spread > policy.conflict_threshold_m:
            warnings.append('SOURCE_HEIGHT_CONFLICT: threshold is a user policy, not an accuracy bound')
            if policy.conflict == 'REJECT':
                status, selected, reason = 'UNRESOLVED_SOURCE_CONFLICT', None, 'POLICY_REJECTED_OVERLAP_SPREAD'
        if selected and max(selected.resolution_m) > request.preferred_resolution_m:
            warnings.append('PREFERRED_RESOLUTION_NOT_MET')
        if any(s.prototype_registration_assumption_used for s in valid):
            warnings.append('ABSOLUTE_REGISTRATION_NOT_VERIFIED')
        warnings.append('Containing cells at different resolutions can differ on slopes; no blending or offsets applied.')
        return TerrainSample(request=request, status=status, selected=selected,
            surface_elevation_m=selected.surface_elevation_m if selected else None,
            selection_reason=reason, attempts=attempts, overlap_spread_m=spread, warnings=warnings)

    def sample_batch(self, requests):
        # Bounded even for generators; no global DEM arrays or unbounded cache.
        items = list(islice(iter(requests), self.max_batch+1))
        if len(items)>self.max_batch:
            raise ValueError('Terrain query batch exceeds budget')
        return [self.sample(item) for item in items]

    def iter_samples(self, requests):
        """Far-terrain streaming interface; caller retains only needed results."""
        for request in requests:
            yield self.sample(request)
