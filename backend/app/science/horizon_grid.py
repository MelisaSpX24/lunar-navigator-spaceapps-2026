"""Time-independent grid for screening; interpolation never proves visibility."""

import math, time
from pydantic import Field
from app.models.analysis import Model
from app.science.horizon_models import HorizonRequest
from app.jobs.store import digest
from app.data.fusion import TerrainRequest


class HorizonGrid(Model):
    schema_version: str = "command-10-screening-grid-v1"
    identity: str
    source_signature: str
    request: HorizonRequest
    spacing_deg: float
    observer_surface_elevation_m: float | None
    elevations: dict[str, float | None]
    coverage: dict[str, str]
    complete_scheduled_grid: bool
    performance: dict
    limitations: list[str]

    def lookup(self, azimuth):
        if not math.isfinite(azimuth):
            raise ValueError("Nonfinite azimuth")
        az = azimuth % 360
        key = str(float(az))
        if key in self.elevations:
            value = self.elevations[key]
            return {
                "kind": "EXACT_GRID" if value is not None else "UNKNOWN",
                "elevation_deg": value,
                "strict_visibility_evidence": False,
            }
        left = math.floor(az / self.spacing_deg) * self.spacing_deg
        right = (left + self.spacing_deg) % 360
        a, b = self.elevations.get(str(float(left))), self.elevations.get(
            str(float(right))
        )
        if a is None or b is None:
            return {
                "kind": "UNKNOWN",
                "elevation_deg": None,
                "strict_visibility_evidence": False,
            }
        weight = (az - left) / self.spacing_deg
        return {
            "kind": "APPROXIMATE_INTERPOLATION",
            "elevation_deg": a + (b - a) * weight,
            "strict_visibility_evidence": False,
        }


def build_grid(
    engine,
    request,
    spacing_deg=1.0,
    max_new_rays=720,
    max_samples=1000000,
    checkpoint=None,
):
    if spacing_deg not in (1.0, 0.5):
        raise ValueError("Supported grid spacings: 1 or 0.5 degrees")
    if not 0 <= max_new_rays <= 720 or not 0 < max_samples <= 5000000:
        raise ValueError("Grid budget invalid")
    engine._assert_sources_unchanged()
    t = time.perf_counter()
    before = engine.counters()
    budget = [max_new_rays, max_samples]
    values = {}
    coverage = {}
    surface = engine.terrain.sample(
        TerrainRequest(
            location=request.location,
            policy=request.policy,
            preferred_resolution_m=request.preferred_resolution_m,
        )
    )
    for i in range(int(360 / spacing_deg)):
        if checkpoint:
            checkpoint()
        az = float(i * spacing_deg)
        ray, identity, code = engine._ray(request, az, budget)
        values[str(az)] = (
            ray.horizon_elevation_deg
            if ray and ray.coverage_status == "COMPLETE_SAMPLED_RANGE"
            else None
        )
        coverage[str(az)] = ray.coverage_status if ray else code or "UNKNOWN"
    metadata = {
        "request": request.model_dump(mode="json"),
        "source_signature": engine.namespace,
        "spacing_deg": spacing_deg,
        "surface_elevation_m": surface.surface_elevation_m,
        "algorithm": "command-10-screening-grid-v1",
    }
    return HorizonGrid(
        identity=digest(metadata),
        source_signature=engine.namespace,
        request=request,
        spacing_deg=spacing_deg,
        observer_surface_elevation_m=surface.surface_elevation_m,
        elevations=values,
        coverage=coverage,
        complete_scheduled_grid=all(v is not None for v in values.values()),
        performance={
            "seconds": time.perf_counter() - t,
            **{k: v - before[k] for k, v in engine.counters().items()},
        },
        limitations=[
            "Complete scheduled grid is not continuous azimuth coverage.",
            "Interpolated elevations can miss narrow ridges; use only candidate screening.",
            "Exact disk directions must be verified through the existing ray engine.",
        ],
    )
