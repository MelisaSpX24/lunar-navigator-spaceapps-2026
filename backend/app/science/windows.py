"""Three-valued, finite-sample temporal estimates and bracket refinement."""

from datetime import timedelta
import hashlib, json, time, resource, math
from app.science.window_models import (
    WindowSearchRequest,
    TemporalConditionSample,
    TemporalSegment,
    EventBracket,
    WindowMetrics,
    WindowSearchResult,
)
from app.science.kernels import ScienceError
from app.science.visibility_models import VisibilityRequest

LIMITATIONS = [
    "Equal endpoint conditions do not certify continuous visibility; short events between samples can be missed.",
    "Durations and windows are sampled estimates, not physical lower/upper bounds; certified duration bounds remain null.",
    "Refined brackets concern finite disk/raster samples and may contain multiple crossings; no unique event UTC is claimed.",
    "Sun fraction is not electrical power; Earth centre clearance is not RF communication success.",
    "INDEPENDENT_ASTRONOMY_VALIDATION_NOT_ESTABLISHED; absolute terrain registration remains unverified.",
    "UTC civil-grid durations do not model leap-second labels; each actual epoch is separately converted by the existing SPICE LSK path.",
]


def solar_condition(lower, upper, threshold):
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Invalid threshold")
    if lower is None or upper is None:
        return "UNKNOWN"
    if not 0 <= lower <= upper <= 1:
        raise ValueError("Invalid sampled-model bounds")
    return (
        "MET" if lower >= threshold else "NOT_MET" if upper < threshold else "UNKNOWN"
    )


def earth_condition(clearance, margin):
    if not math.isfinite(margin) or (
        clearance is not None and not math.isfinite(clearance)
    ):
        raise ValueError("Nonfinite clearance or margin")
    return (
        "UNKNOWN" if clearance is None else "MET" if clearance >= margin else "NOT_MET"
    )


def joint_condition(a, b):
    return "NOT_MET" if "NOT_MET" in (a, b) else "MET" if a == b == "MET" else "UNKNOWN"


def definition_id(request, family, source_identity):
    payload = {
        "family": family,
        "solar_fraction": request.solar_fraction,
        "earth_margin_deg": request.earth_margin_deg,
        "visibility": request.visibility.model_dump(mode="json"),
        "source_identity": source_identity,
    }
    payload["visibility"].pop("utc")
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


class VisibilityEvaluator:
    """One existing open visibility engine; global ray/point budgets per search."""

    def __init__(self, engine, request):
        self.engine, self.request = engine, request
        self.before = engine.counters()
        self.sources = {}
        self.calls = 0

    @property
    def identity(self):
        return self.engine.namespace

    def __call__(self, utc):
        r = self.request
        used = self.engine.counters()
        rays = r.max_new_rays - (used["attempted_rays"] - self.before["attempted_rays"])
        points = r.max_terrain_samples - (
            used["dem_samples"] - self.before["dem_samples"]
        )
        if self.calls >= r.max_visibility_evaluations:
            raise ScienceError(
                "WINDOW_SEARCH_INCOMPLETE_RESOURCE_LIMIT",
                "Global window budget exhausted",
            )
        values = r.visibility.model_dump()
        cache_only = rays <= 0 or points <= 0 or r.visibility.max_new_rays == 0
        values.update(
            utc=utc,
            max_new_rays=0 if cache_only else min(rays, r.visibility.max_new_rays),
        )
        # Terrain request participates in exact cache identity and requires a
        # positive point limit. Preserve it for cache-only runs; zero new rays
        # prevents every cache miss from doing terrain work, even with no points.
        if not cache_only:
            values["terrain"]["max_total_samples"] = min(
                points, r.visibility.terrain.max_total_samples
            )
        self.calls += 1
        t = time.perf_counter()
        result = self.engine.run(VisibilityRequest.model_validate(values))
        self.sources = {
            "dem": result.sources,
            "kernel_ids": result.kernel_ids,
            "data_origin": result.data_origin,
        }
        sun = solar_condition(
            result.sun.visible_fraction_lower_bound,
            result.sun.visible_fraction_upper_bound,
            r.solar_fraction,
        )
        earth = earth_condition(result.earth.center_clearance_deg, r.earth_margin_deg)
        bodies = {}
        for name, b in [("sun", result.sun), ("earth", result.earth)]:
            bodies[name] = {
                "direction": b.direction.model_dump(),
                "angular_radius_deg": b.angular_radius_deg,
                "disk_state": b.state,
                "visible_fraction": b.visible_fraction,
                "lower_bound": b.visible_fraction_lower_bound,
                "upper_bound": b.visible_fraction_upper_bound,
                "center_clearance_deg": b.center_clearance_deg,
                "observer": b.observer.model_dump(),
                "performance": b.performance,
                "reason_codes": b.reason_codes,
            }
            # Full per-disk direction lists are unnecessary for timeline outputs.
            bodies[name]["performance"] = dict(b.performance)
            bodies[name]["performance"].pop("unknown_directions", None)
        return TemporalConditionSample(
            time_utc=utc,
            sun=sun,
            earth=earth,
            joint=joint_condition(sun, earth) if r.joint else None,
            bodies=bodies,
            source_identity=self.identity,
            evaluation_seconds=time.perf_counter() - t,
            reason_codes=sorted(
                set(result.sun.reason_codes + result.earth.reason_codes)
            ),
        )


def search(
    request: WindowSearchRequest,
    evaluate,
    *,
    source_identity="SYNTHETIC_TEST",
    source_evidence=None,
    fallback_data_origin=None,
):
    """Evaluator must return evidence, never interpolate observations. End is a boundary probe."""
    started = time.perf_counter()
    samples = {}
    missing_times = set()
    evaluations = 0
    refinements = 0
    events = []
    resource_limited = False
    families = ["sun", "earth"] + (["joint"] if request.joint else [])
    ids = {f: definition_id(request, f, source_identity) for f in families}

    def at(t):
        nonlocal evaluations, resource_limited
        if t in samples:
            return samples[t]
        if (
            len(samples) >= request.max_temporal_samples
            or evaluations >= request.max_visibility_evaluations
        ):
            resource_limited = True
            s = TemporalConditionSample(
                time_utc=t, reason_codes=["WINDOW_SEARCH_INCOMPLETE_RESOURCE_LIMIT"]
            )
            if len(samples) < request.max_temporal_samples:
                samples[t] = s
            else:
                missing_times.add(t)
            return s
        evaluations += 1
        try:
            s = evaluate(t)
        except ScienceError as exc:
            if exc.code in ("KERNEL_HASH_MISMATCH", "KERNEL_MISSING"):
                raise
            s = TemporalConditionSample(time_utc=t, reason_codes=[exc.code])
        if s.time_utc != t:
            raise ValueError("Evaluator timestamp mismatch")
        resource_limited |= any(
            "BUDGET" in x or "RESOURCE_LIMIT" in x for x in s.reason_codes
        )
        samples[t] = s
        return s

    start, end = request.start_utc, request.end_utc
    grid = [start]
    t = start
    while t < end:
        t = min(end, t + timedelta(seconds=request.step_s))
        grid.append(t)
    # Boundary-first scheduling preserves useful confinement evidence under interruption.
    at(start)
    at(end)
    for t in grid[1:-1]:
        at(t)
    # Insert UNKNOWN sentinels for grid times not evaluated; no bridging gaps.
    for t in grid:
        if t not in samples:
            samples[t] = TemporalConditionSample(
                time_utc=t, reason_codes=["WINDOW_SEARCH_INCOMPLETE_RESOURCE_LIMIT"]
            )
    for _ in range(request.midpoint_depth):
        times = sorted(samples)
        for left, right in zip(times, times[1:]):
            at(left + (right - left) / 2)
    for family in families:
        times = sorted(samples)
        for left, right in zip(times, times[1:]):
            a, b = getattr(samples[left], family), getattr(samples[right], family)
            if "UNKNOWN" in (a, b) or a == b:
                continue
            count = 0
            while (
                right - left
            ).total_seconds() > request.event_resolution_s and refinements < request.max_refinements:
                mid = left + (right - left) / 2
                if mid in (left, right):
                    break
                s = at(mid)
                refinements += 1
                count += 1
                c = getattr(s, family)
                if c == "UNKNOWN":
                    break
                if c == a:
                    left = mid
                else:
                    right = mid
            width = (right - left).total_seconds()
            events.append(
                EventBracket(
                    definition_id=ids[family],
                    family=family,
                    event_type="START" if a == "NOT_MET" else "LOSS",
                    left_utc=left,
                    right_utc=right,
                    left_condition=a,
                    right_condition=b,
                    width_s=width,
                    evaluation_count=count,
                    status=(
                        "EVENT_BRACKETED"
                        if width <= request.event_resolution_s
                        else "EVENT_BRACKET_NOT_REFINED"
                    ),
                )
            )
    timeline = [samples[t] for t in sorted(samples)]
    segments = {}
    windows = {}
    metrics = {}
    next_events = {}
    for family in families:
        parts = []
        for a, b in zip(timeline, timeline[1:]):
            x, y = getattr(a, family), getattr(b, family)
            condition = (
                x
                if x == y
                and x != "UNKNOWN"
                and not any(a.time_utc < t < b.time_utc for t in missing_times)
                else "UNKNOWN"
            )
            reasons = (
                []
                if condition != "UNKNOWN"
                else sorted(
                    set(
                        a.reason_codes
                        + b.reason_codes
                        + ["TEMPORAL_INTERVAL_UNRESOLVED"]
                    )
                )
            )
            part = TemporalSegment(
                start_utc=a.time_utc,
                end_utc=b.time_utc,
                condition=condition,
                definition_id=ids[family],
                evidence_status=(
                    "SAMPLED_ESTIMATE"
                    if condition != "UNKNOWN"
                    else "TEMPORAL_INTERVAL_UNRESOLVED"
                ),
                temporal_resolution_s=(b.time_utc - a.time_utc).total_seconds(),
                reason_codes=reasons,
                start_censored=a.time_utc == start and condition == "MET",
                end_censored=b.time_utc == end and condition == "MET",
            )
            if (
                parts
                and parts[-1].condition == part.condition
                and parts[-1].end_utc == part.start_utc
            ):
                prev = parts[-1]
                prev.end_utc = part.end_utc
                prev.end_censored = part.end_censored
                prev.temporal_resolution_s = max(
                    prev.temporal_resolution_s, part.temporal_resolution_s
                )
                prev.reason_codes = sorted(set(prev.reason_codes + part.reason_codes))
            else:
                parts.append(part)
        segments[family] = parts
        unknown = any(p.condition == "UNKNOWN" for p in parts)
        windows[family] = (
            None if unknown else [p for p in parts if p.condition == "MET"]
        )
        durations = {
            s: [
                (p.end_utc - p.start_utc).total_seconds()
                for p in parts
                if p.condition == s
            ]
            for s in ["MET", "NOT_MET", "UNKNOWN"]
        }
        brackets = [e for e in events if e.family == family]
        metrics[family] = WindowMetrics(
            estimated_duration_s=sum(durations["MET"]),
            estimated_longest_continuous_s=max(durations["MET"], default=0),
            estimated_interruption_s=sum(durations["NOT_MET"]),
            estimated_longest_interruption_s=max(durations["NOT_MET"], default=0),
            unknown_duration_s=sum(durations["UNKNOWN"]),
            number_of_windows=len(durations["MET"]),
            number_of_brackets=len(brackets),
            temporal_resolution_s=max(
                (p.temporal_resolution_s for p in parts), default=0
            ),
        )
        for kind in ["START", "LOSS"]:
            candidates = sorted(
                [e for e in brackets if e.event_type == kind], key=lambda e: e.left_utc
            )
            coverage = any(
                "COVERAGE" in code for s in timeline for code in s.reason_codes
            )
            status = (
                "OUT_OF_KERNEL_COVERAGE"
                if coverage
                else (
                    "EVENT_SEARCH_INCOMPLETE"
                    if resource_limited
                    or any(getattr(s, family) == "UNKNOWN" for s in timeline)
                    else (
                        "EVENT_TIME_UNRESOLVED"
                        if candidates and candidates[0].status != "EVENT_BRACKETED"
                        else (
                            "EVENT_BRACKETED"
                            if candidates
                            else "NO_EVENT_OBSERVED_WITHIN_SEARCH"
                        )
                    )
                )
            )
            next_events[family + "_" + kind.lower()] = {
                "status": status,
                "first_observed_bracket": (
                    candidates[0].model_dump(mode="json") if candidates else None
                ),
                "event_utc": None,
            }
    evidence = source_evidence() if callable(source_evidence) else source_evidence or {}
    return WindowSearchResult(
        request=request,
        timeline=timeline,
        segments=segments,
        sampled_windows=windows,
        brackets=events,
        metrics=metrics,
        next_events=next_events,
        source_evidence=evidence,
        data_origin=evidence.get("data_origin")
        or fallback_data_origin
        or (
            "SYNTHETIC_TEST"
            if source_identity == "SYNTHETIC_TEST"
            else "MIXED_OR_UNVERIFIED"
        ),
        execution_status=(
            "PARTIAL"
            if resource_limited or any("UNKNOWN" in [s.sun, s.earth] for s in timeline)
            else "COMPLETED"
        ),
        performance={
            "seconds": time.perf_counter() - started,
            "evaluations": evaluations,
            "refinements": refinements,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        limitations=LIMITATIONS,
    )


def run_windows(engine, request):
    from app.science.astronomy import utc_to_et

    span = utc_to_et(engine.session, request.end_utc) - utc_to_et(
        engine.session, request.start_utc
    )
    if abs(span - request.duration_s) > 0.1:
        raise ValueError("UTC interval crosses an unsupported leap-second boundary")
    evaluator = VisibilityEvaluator(engine, request)
    before = engine.counters()
    result = search(
        request,
        evaluator,
        source_identity=engine.namespace,
        source_evidence=lambda: evaluator.sources,
        fallback_data_origin="MIXED_OR_UNVERIFIED",
    )
    result.performance["visibility_accounting"] = {
        k: v - before[k] for k, v in engine.counters().items()
    }
    result.performance["visibility_evaluations"] = evaluator.calls
    return result
