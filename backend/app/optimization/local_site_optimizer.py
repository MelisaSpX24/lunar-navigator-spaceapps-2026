"""Geodesic generation and DEM screening; scientific eligibility uses Command 08."""

import math, time
import numpy as np
from pyproj import Geod
from rasterio.windows import Window
from app.models.analysis import Coordinates, AnalysisRequest
from app.data.fusion import TerrainRequest
from app.jobs.store import digest
from app.optimization.local_site_models import (
    LocalSiteCandidate,
    LocalSiteOptimizationResult,
)

GEOD = Geod(a=1737400, b=1737400)
LIMITATIONS = [
    "Slope threshold is EXAMPLE_OPERATION_ASSUMPTION, not landing safety certification.",
    "Grid-gradient slope at source resolution cannot resolve rocks or subpixel hazards.",
    "Only screened/verified finite candidates are covered; no globally best site claim.",
    "ABSOLUTE_REGISTRATION_UNVERIFIED; no offsets or resampling applied.",
]


def slope_estimate(array, resolution):
    a = np.ma.asarray(array)
    if (
        a.shape != (3, 3)
        or np.ma.getmaskarray(a).any()
        or not np.isfinite(a.data).all()
    ):
        return None
    dx, dy = resolution
    if not dx > 0 or not dy > 0:
        raise ValueError("Invalid pixel scale")
    gx = (float(a[1, 2]) - float(a[1, 0])) / (2 * dx)
    gy = (float(a[2, 1]) - float(a[0, 1])) / (2 * dy)
    return math.degrees(math.atan(math.hypot(gx, gy)))


def locations(request):
    site = request.baseline_analysis.site
    if site.kind != "COORDINATES":
        raise ValueError("Local search requires resolved coordinates")
    pool = []
    rings = math.ceil(request.search_radius_m / request.coarse_step_m)
    for ring in range(1, rings + 1):
        radius = min(request.search_radius_m, ring * request.coarse_step_m)
        n = max(8, math.ceil(2 * math.pi * radius / request.coarse_step_m))
        for j in range(n):
            lon, lat, _ = GEOD.fwd(
                site.longitude_deg_east, site.latitude_deg, 360 * j / n, radius
            )
            if -90 < lat < 90:
                pool.append(Coordinates(latitude_deg=lat, longitude_deg_east=lon % 360))
    slots = max(1, (request.max_generated_candidates - 1) * 3 // 4)
    count = min(slots, len(pool))
    return [pool[(i * (len(pool) - 1)) // max(1, count - 1)] for i in range(count)]


def screen(terrain, location, policy, max_slope):
    t = time.perf_counter()
    sample = terrain.sample(TerrainRequest(location=location, policy=policy))
    result = {
        "status": sample.status,
        "slope_deg": None,
        "slope_method": "UNKNOWN",
        "eligible": False,
        "warnings": sample.warnings,
        "sample_positions": 1,
        "seconds": 0,
    }
    if sample.selected is not None:
        s = sample.selected
        source = next(
            x
            for x in terrain.sources.values()
            if x.dem.reference.product_id == s.product_id
        )
        result.update(
            surface_elevation_m=s.surface_elevation_m,
            product_id=s.product_id,
            sha256=s.raster_sha256,
            resolution_m=s.resolution_m,
            quality=s.quality.model_dump(mode="json"),
            reference=s.reference.model_dump(mode="json"),
            overlap_spread_m=sample.overlap_spread_m,
        )
        try:
            a, _ = source.dem.read_elevation_window(
                Window(s.column_zero_based - 1, s.row_zero_based - 1, 3, 3)
            )
            result["sample_positions"] += 9
            result["slope_deg"] = slope_estimate(a, s.resolution_m)
            result["slope_method"] = "SOURCE_GRID_3X3_CENTRAL_DIFFERENCE_ESTIMATE"
        except (ValueError, OSError):
            result["warnings"].append("SLOPE_NEIGHBOURS_UNAVAILABLE")
        result["eligible"] = (
            sample.status == "VALID"
            and result["slope_deg"] is not None
            and result["slope_deg"] <= max_slope
        )
    result["seconds"] = time.perf_counter() - t
    return result


def improves_baseline(baseline, candidate, equivalent, delta):
    return bool(
        equivalent
        and candidate.stage == "DETAILED_EVALUATED"
        and candidate.terrain.get("eligible")
        and candidate.operation
        and candidate.operation.decision.status == "MET"
        and (
            not baseline.terrain.get("eligible")
            or baseline.operation.decision.status != "MET"
            or delta is not None
            and delta > 0
        )
    )


def select_detailed(candidates, request):
    """Admission heuristic, never a new operation score or visibility claim."""

    def quality(c):
        return (
            {
                "QUALITY_LAYERS_PRESENT": 0,
                "PARTIAL_QUALITY_DATA": 1,
                "QUALITY_NOT_ASSESSED": 2,
            }.get(c.terrain.get("quality", {}).get("status"), 3),
            c.terrain.get("resolution_m", [float("inf")])[0],
            c.terrain["slope_deg"],
            c.distance_m,
            c.candidate_id,
        )

    pool = sorted(
        [c for c in candidates if c.terrain["eligible"]],
        key=(
            quality
            if request.selection_strategy == "TERRAIN_DIVERSE"
            else lambda c: (c.terrain["slope_deg"], c.distance_m, c.candidate_id)
        ),
    )
    slots = request.max_detailed_candidates - 1
    if request.selection_strategy == "SLOPE_ONLY":
        return pool[:slots]
    selected = []
    if pool and slots:
        selected.append(pool.pop(0))
    while pool and len(selected) < slots:

        def rank(c):
            nearest = min(
                GEOD.inv(
                    c.location.longitude_deg_east,
                    c.location.latitude_deg,
                    x.location.longitude_deg_east,
                    x.location.latitude_deg,
                )[2]
                for x in selected
            )
            return (-nearest, quality(c))

        candidate = min(pool, key=rank)
        selected.append(candidate)
        pool.remove(candidate)
    return selected


def optimize_local(request, terrain, evaluate, context):
    start = time.perf_counter()
    site = request.baseline_analysis.site
    if site.kind != "COORDINATES":
        raise ValueError("Local search requires coordinates")

    def make(loc):
        bearing, _, distance = GEOD.inv(
            site.longitude_deg_east,
            site.latitude_deg,
            loc.longitude_deg_east,
            loc.latitude_deg,
        )
        return LocalSiteCandidate(
            candidate_id=digest(loc.model_dump())[:24],
            location=loc,
            distance_m=distance,
            bearing_deg=None if distance < 1e-6 else bearing % 360,
            stage="GENERATED",
        )

    baseline = make(
        Coordinates(**{k: v for k, v in site.model_dump().items() if k != "kind"})
    )
    candidates = []
    seen = {(site.latitude_deg, site.longitude_deg_east)}
    queries = 0

    def inspect(loc):
        nonlocal queries
        context.budget_check(anticipated_samples=10)
        context.update("TERRAIN_SCREENING")
        c = make(loc)
        c.terrain = screen(
            terrain,
            loc,
            request.window_template.visibility.terrain.policy,
            request.max_slope_deg,
        )
        queries += c.terrain["sample_positions"]
        context.terrain_screen_positions = queries
        context.budget_check()
        c.stage = (
            "ELIGIBLE_FOR_DETAIL"
            if c.terrain["eligible"]
            else (
                "SLOPE_UNKNOWN"
                if c.terrain["slope_deg"] is None
                else "SCREENED_OUT_TERRAIN"
            )
        )
        if not c.terrain["eligible"]:
            c.reason_codes = [
                (
                    "SLOPE_UNKNOWN"
                    if c.terrain["slope_deg"] is None
                    else "SLOPE_EXCEEDS_THRESHOLD"
                )
            ]
        return c

    baseline = inspect(baseline.location)
    for loc in locations(request):
        if (loc.latitude_deg, loc.longitude_deg_east) not in seen:
            candidates.append(inspect(loc))
            seen.add((loc.latitude_deg, loc.longitude_deg_east))
    # Reserve a bounded refinement around the best available coarse gradient.
    best = sorted(
        [c for c in candidates if c.terrain["eligible"]],
        key=lambda c: (c.terrain["slope_deg"], c.distance_m, c.candidate_id),
    )[:2]
    for center in best:
        for bearing in range(0, 360, 45):
            if len(candidates) + 1 >= request.max_generated_candidates:
                break
            lon, lat, _ = GEOD.fwd(
                center.location.longitude_deg_east,
                center.location.latitude_deg,
                bearing,
                request.refinement_step_m,
            )
            _, _, distance = GEOD.inv(
                site.longitude_deg_east, site.latitude_deg, lon, lat
            )
            if distance > request.search_radius_m + 1e-7 or not -90 < lat < 90:
                continue
            key = (lat, lon % 360)
            if key not in seen:
                candidates.append(
                    inspect(Coordinates(latitude_deg=lat, longitude_deg_east=lon % 360))
                )
                seen.add(key)
    selected = select_detailed(candidates, request)
    detailed = 0
    for c in [baseline] + selected:
        context.update(
            "COMPUTING_VISIBILITY",
            total_candidates=1 + len(selected),
            completed_candidates=detailed,
        )
        data = request.baseline_analysis.model_dump(exclude_unset=True)
        data["site"] = {"kind": "COORDINATES", **c.location.model_dump()}
        analysis = AnalysisRequest.model_validate(data)
        w = request.window_template.model_dump()
        w["visibility"]["terrain"]["location"] = c.location.model_dump()
        try:
            op, windows = evaluate(
                analysis, type(request.window_template).model_validate(w)
            )
            c.operation = op
            c.metrics = {k: m.model_dump() for k, m in windows.metrics.items()}
            c.evidence_sha256 = op.provenance["window_evidence_sha256"]
            c.stage = (
                "DETAILED_EVALUATED"
                if windows.execution_status == "COMPLETED"
                else "SCIENTIFICALLY_INCOMPLETE"
            )
        except Exception as exc:
            from app.jobs.manager import JobStop

            if isinstance(exc, JobStop):
                raise
            c.stage = "SCIENTIFICALLY_INCOMPLETE"
            c.reason_codes = [getattr(exc, "code", type(exc).__name__)]
        detailed += 1
        context.capture(
            {
                "kind": "LOCAL_PARTIAL",
                "baseline": baseline.model_dump(mode="json"),
                "candidates": [x.model_dump(mode="json") for x in candidates],
            }
        )
    comparisons = []
    recommendations = []
    ranked = sorted(
        selected,
        key=lambda c: (
            {"MET": 0, "NOT_MET": 1, "INCOMPLETE": 2}.get(
                c.operation.decision.status if c.operation else "", 3
            ),
            -(
                c.operation.score.value
                if c.operation and c.operation.score.value is not None
                else -1
            ),
            c.distance_m,
            c.candidate_id,
        ),
    )
    for c in ranked:
        b, a = baseline.operation, c.operation
        equivalent = bool(
            a
            and b
            and a.provenance["sources"] == b.provenance["sources"]
            and a.score.model_version == b.score.model_version
        )
        delta = (
            a.score.value - b.score.value
            if equivalent and a.score.value is not None and b.score.value is not None
            else None
        )
        better = improves_baseline(baseline, c, equivalent, delta)
        comparisons.append(
            {
                "candidate_id": c.candidate_id,
                "comparison_validity": (
                    "SAME_SOURCES" if equivalent else "COMPARISON_NOT_EQUIVALENT"
                ),
                "score_delta": delta,
                "better_modeled_operation": better,
                "distance_m": c.distance_m,
                "bearing_deg": c.bearing_deg,
            }
        )
        if better and len(recommendations) < request.max_recommendations:
            recommendations.append(c)
    for c in candidates:
        if c.stage == "ELIGIBLE_FOR_DETAIL":
            c.stage = "NOT_EVALUATED_RESOURCE_LIMIT"
    return LocalSiteOptimizationResult(
        request=request,
        baseline=baseline,
        candidates=candidates,
        recommendations=recommendations,
        comparisons=comparisons,
        outcome=(
            "BETTER_VERIFIED_CANDIDATES_FOUND"
            if recommendations
            else "NO_BETTER_VERIFIED_SITE_FOUND_IN_EVALUATED_SET"
        ),
        search_status="PARTIAL_FINITE_SEARCH",
        scope={
            "selection_strategy": request.selection_strategy,
            "selection_role": "TERRAIN_QUALITY_AND_GEODESIC_DIVERSITY_NOT_OPERATION_SCORE",
            "generated_including_baseline": 1 + len(candidates),
            "terrain_eligible": sum(
                c.terrain["eligible"] for c in [baseline] + candidates
            ),
            "slopes_known": sum(
                c.terrain["slope_deg"] is not None for c in [baseline] + candidates
            ),
            "detailed_attempts_including_baseline": detailed,
        },
        resource_consumption={
            "seconds": time.perf_counter() - start,
            "terrain_screen_sample_positions": queries,
        },
        limitations=LIMITATIONS,
    )
