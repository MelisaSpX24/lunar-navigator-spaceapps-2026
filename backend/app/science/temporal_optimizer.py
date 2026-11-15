"""Same-site UTC discovery, bounded verification and decision-first comparisons."""

from datetime import timedelta
import hashlib, json, time, resource
from app.models.analysis import AnalysisRequest
from app.science.operation_models import OperationEvaluationRequest
from app.science.operations import (
    evaluate_operation,
    evidence_identity,
    effective_requirements,
)
from app.science.scoring import weights_for
from app.science.window_models import WindowSearchRequest
from app.science.windows import run_windows
from app.science.kernels import ScienceError
from app.science.temporal_optimizer_models import (
    TemporalCandidate,
    TemporalCandidateComparison,
    TemporalOptimizationResult,
)

LIMITATIONS = [
    "Only the bounded generated/evaluated start times were searched; no global optimum or absence of other feasible times is proved.",
    "Coarse geometry and event brackets prioritize candidates, not mission eligibility; short temporal events can be missed.",
    "Recommendations inherit sampled-model policy, terrain registration and astronomy limitations; no safety, power or RF guarantee.",
    "Wall-time admission is cooperative between atomic visibility calls; one bounded call may finish after the deadline.",
]


class RecordedProvider:
    mode = "RECORDED"

    def __init__(self, windows):
        self.windows = {}
        for w in windows:
            if w.request.start_utc in self.windows:
                raise ValueError("Duplicate recorded UTC evidence")
            self.windows[w.request.start_utc] = w

    def get(self, request):
        return self.windows.get(request.start_utc)

    def counters(self):
        return {}


class LiveProvider:
    mode = "LIVE"

    def __init__(self, engine, request):
        if engine.cache_size > request.max_cache_entries:
            raise ValueError("Engine cache exceeds optimizer limit")
        self.engine = engine
        self.request = request
        self.before = engine.counters()
        self.calls = 0
        self.started = None

    def counters(self):
        return {
            **{k: v - self.before[k] for k, v in self.engine.counters().items()},
            "visibility_evaluations": self.calls,
        }

    def get(self, request):
        if self.started is None:
            self.started = time.perf_counter()
        provider = self

        class GuardedEngine:
            def __getattr__(self, name):
                return getattr(provider.engine, name)

            def run(self, q):
                used = provider.counters()
                limits = provider.request
                if (
                    provider.calls >= limits.max_window_evaluations
                    or time.perf_counter() - provider.started >= limits.max_wall_time_s
                ):
                    raise ScienceError(
                        "WINDOW_SEARCH_INCOMPLETE_RESOURCE_LIMIT",
                        "Optimizer visibility/time budget exhausted",
                    )
                rays = max(0, limits.max_new_horizon_rays - used["attempted_rays"])
                points = max(0, limits.max_terrain_samples - used["dem_samples"])
                values = q.model_dump()
                values["max_new_rays"] = min(q.max_new_rays, rays) if points else 0
                if points:
                    values["terrain"]["max_total_samples"] = min(
                        points, q.terrain.max_total_samples
                    )
                provider.calls += 1
                return provider.engine.run(type(q).model_validate(values))

        return run_windows(GuardedEngine(), request)


def shifted_requests(request, utc):
    # exclude_unset preserves which Requirements fields actually activate rules.
    a = request.baseline_analysis.model_dump(exclude_unset=True)
    a["time"] = {
        "start_utc": utc,
        "duration_s": request.baseline_analysis.time.duration_s,
    }
    analysis = AnalysisRequest.model_validate(a)
    w = request.window_template.model_dump()
    w["start_utc"] = utc
    w["visibility"]["utc"] = utc
    return analysis, WindowSearchRequest.model_validate(w)


def science_configuration(w):
    v = w.request.model_dump(mode="json")
    v.pop("start_utc")
    v["visibility"].pop("utc")
    # Resource allowances may differ; the scientific sampling method must match.
    for k in (
        "max_new_rays",
        "max_terrain_samples",
        "max_visibility_evaluations",
        "max_temporal_samples",
        "max_refinements",
    ):
        v.pop(k, None)
    v["visibility"].pop("max_new_rays")
    v["visibility"]["terrain"].pop("max_total_samples")
    return v


def discover(request, hints=(), geometry_priority=None):
    if request.selection_strategy == "COVERAGE_AWARE":
        return discover_coverage(request, hints, geometry_priority)
    started = time.perf_counter()
    times = {}
    overflow = False
    duration = timedelta(seconds=request.baseline_analysis.time.duration_s)

    def add(t, source):
        nonlocal overflow
        if not request.search_start_utc <= t or t + duration > request.search_end_utc:
            return
        if t not in times and len(times) >= request.max_coarse_candidates:
            overflow = True
            return
        times.setdefault(t, set()).add(source)

    # Evidence hints are confined to bounded caller-supplied records, not arbitrary files.
    for w in hints[:32]:
        for bracket in w.brackets[:64]:
            for t in (
                bracket.left_utc,
                bracket.right_utc,
                bracket.right_utc + timedelta(seconds=request.refinement_step_s),
            ):
                add(
                    t,
                    (
                        "EVENT_BRACKET_POST_REFINEMENT"
                        if t > bracket.right_utc
                        else "EVENT_BRACKET_CANDIDATE"
                    ),
                )
        for family in w.sampled_windows.values():
            for segment in (family or [])[:64]:
                add(segment.start_utc, "RECORDED_WINDOW_START")
    t = request.search_start_utc
    while t + duration <= request.search_end_utc:
        add(t, "COARSE_GRID")
        t += timedelta(seconds=request.coarse_start_step_s)
        if (
            len(times) >= request.max_coarse_candidates
            and t + duration <= request.search_end_utc
        ):
            overflow = True
            break
    baseline = request.baseline_analysis.time.start_utc
    rows = [(t, sorted(sources)) for t, sources in times.items() if t != baseline]
    # Optional SPICE geometry changes discovery priority only, never decisions.
    priority = {}
    geometry_seconds = 0
    if geometry_priority:
        ts = time.perf_counter()
        for t, _ in rows:
            priority[t] = geometry_priority(t)
        geometry_seconds = time.perf_counter() - ts
    rows.sort(
        key=lambda x: (
            (
                0
                if "EVENT_BRACKET_POST_REFINEMENT" in x[1]
                else 1 if "EVENT_BRACKET_CANDIDATE" in x[1] else 2
            ),
            -priority.get(x[0], 0),
            x[0],
        )
    )
    return rows, {
        "seconds": time.perf_counter() - started,
        "geometry_seconds": geometry_seconds,
        "coarse_screened_candidates": len(rows) if geometry_priority else 0,
        "truncated": overflow,
    }


def discover_coverage(request, hints=(), geometry_priority=None):
    """Bounded grid stratification plus a diverse detailed prefix; no eligibility."""
    started = time.perf_counter()
    start = request.search_start_utc
    last = request.search_end_utc - timedelta(
        seconds=request.baseline_analysis.time.duration_s
    )
    baseline = request.baseline_analysis.time.start_utc
    events = {}
    times = {}

    def insert(target, t, source):
        if start <= t <= last and t != baseline:
            target.setdefault(t, set()).add(source)

    for w in hints[:32]:
        for b in w.brackets[:64]:
            for t in (
                b.left_utc,
                b.right_utc,
                b.right_utc + timedelta(seconds=request.refinement_step_s),
            ):
                insert(
                    events,
                    t,
                    (
                        "EVENT_BRACKET_POST_REFINEMENT"
                        if t > b.right_utc
                        else "EVENT_BRACKET_CANDIDATE"
                    ),
                )
        for family in w.sampled_windows.values():
            for segment in (family or [])[:64]:
                insert(events, segment.start_utc, "RECORDED_WINDOW_START")
    cap = request.max_coarse_candidates
    # Reserve at least half of a multi-slot pool for the full UTC confinement.
    event_cap = min(len(events), cap // 2 if cap > 1 else 1)
    ranked_events = sorted(
        events, key=lambda t: ("EVENT_BRACKET_POST_REFINEMENT" not in events[t], t)
    )
    for t in ranked_events[:event_cap]:
        times[t] = events[t]
    n = int((last - start).total_seconds() // request.coarse_start_step_s) + 1
    slots = cap - len(times)
    # One extra grid index accommodates exclusion of a baseline grid point.
    count = min(n, slots + 1)
    indices = sorted(
        {
            (i * (n - 1)) // (count - 1) if count > 1 else (n - 1) // 2
            for i in range(count)
        }
    )
    # Keep the far end even when the first point is the separate baseline.
    for i in list(
        dict.fromkeys(([indices[0], indices[-1]] + indices[1:-1]) if indices else [])
    ):
        if len(times) >= cap:
            break
        insert(
            times,
            start + timedelta(seconds=i * request.coarse_start_step_s),
            "COARSE_GRID",
        )
    geometry_seconds = 0
    priority = {}
    if geometry_priority:
        t0 = time.perf_counter()
        for t in sorted(times):
            priority[t] = geometry_priority(t)
        geometry_seconds = time.perf_counter() - t0

    def rank(t):
        return (
            "EVENT_BRACKET_POST_REFINEMENT" not in times[t],
            "EVENT_BRACKET_CANDIDATE" not in times[t],
            -priority.get(t, 0),
            t,
        )

    remaining = sorted(times, key=rank)
    chosen = []
    budget = max(0, request.max_detailed_candidates - 1)
    if remaining and budget:
        chosen.append(remaining.pop(0))
    while remaining and len(chosen) < budget:
        t = min(
            remaining,
            key=lambda t: (-min(abs((t - x).total_seconds()) for x in chosen), rank(t)),
        )
        chosen.append(t)
        remaining.remove(t)
    ordered = chosen + remaining
    return [(t, sorted(times[t])) for t in ordered], {
        "seconds": time.perf_counter() - started,
        "geometry_seconds": geometry_seconds,
        "coarse_screened_candidates": len(times) if geometry_priority else 0,
        "truncated": (
            n
            - int(
                start <= baseline <= last
                and (baseline - start) % timedelta(seconds=request.coarse_start_step_s)
                == timedelta(0)
            )
            + sum(
                (t - start) % timedelta(seconds=request.coarse_start_step_s)
                != timedelta(0)
                for t in events
            )
        )
        > len(times),
        "selection_strategy": "COVERAGE_AWARE",
        "selected_alternative_starts": [t.isoformat() for t in chosen],
        "generated_span_s": (max(times) - min(times)).total_seconds() if times else 0,
        "selected_span_s": (max(chosen) - min(chosen)).total_seconds() if chosen else 0,
        "limitation": "Diversity is discovery coverage, not additional scientific verification.",
    }


def candidate_rank(candidate):
    op = candidate.operation
    status = op.decision.status if op else "INCOMPLETE"
    score = op.score.value if op else None
    return (
        {"MET": 0, "NOT_MET": 1, "INCOMPLETE": 2}[status],
        -(score if score is not None else -1),
        candidate.start_utc,
        candidate.candidate_id,
    )


def scoring_signature(operation):
    expected = weights_for(
        operation.request.analysis.operation.profile,
        effective_requirements(operation.request),
    )
    if (
        operation.score.components is not None
        and {c.name: c.weight for c in operation.score.components} != expected
    ):
        return None
    return expected


def compare(baseline, alternative, baseline_window, window):
    a, b = baseline.operation, alternative.operation
    valid = bool(
        a
        and b
        and baseline_window
        and window
        and science_configuration(baseline_window) == science_configuration(window)
        and baseline_window.source_evidence == window.source_evidence
        and a.request.evaluation_policy == b.request.evaluation_policy
        and a.request.analysis.operation.model_dump(exclude_unset=True)
        == b.request.analysis.operation.model_dump(exclude_unset=True)
        and a.score.model_version == b.score.model_version
        and scoring_signature(a) is not None
        and scoring_signature(a) == scoring_signature(b)
    )

    # Actual DEM observer heights must agree when present; missing/incomplete evidence cannot recommend.
    def observers(w):
        return {
            name: sample.bodies[name].get("observer")
            for sample in w.timeline
            for name in ("sun", "earth")
            if name in sample.bodies
        }

    if valid:
        valid = observers(baseline_window) == observers(window)
    classification = "COMPARISON_NOT_EQUIVALENT"
    score_delta = None
    deltas = {}
    unknown = {}
    if valid:
        if a.score.value is not None and b.score.value is not None:
            score_delta = b.score.value - a.score.value
        for family in ("sun", "earth", "joint"):
            x, y = baseline.metrics.get(family), alternative.metrics.get(family)
            if x and y and not x["unknown_duration_s"] and not y["unknown_duration_s"]:
                deltas[family] = {
                    field: y[field] - x[field]
                    for field in (
                        "estimated_duration_s",
                        "estimated_longest_continuous_s",
                        "estimated_longest_interruption_s",
                    )
                }
            else:
                deltas[family] = None
            unknown[family] = (
                y["unknown_duration_s"] - x["unknown_duration_s"] if x and y else None
            )
        if (
            b.decision.status == "MET"
            and alternative.evaluation_status == "DETAILED_EVALUATED"
        ):
            classification = (
                "IMPROVED_ALTERNATIVE"
                if a.decision.status != "MET"
                or (score_delta is not None and score_delta > 0)
                else (
                    "EQUIVALENT_ALTERNATIVE"
                    if score_delta == 0
                    else "NO_MEANINGFUL_IMPROVEMENT_FOUND"
                )
            )
        else:
            classification = "NOT_ELIGIBLE"
    return TemporalCandidateComparison(
        baseline_id=baseline.candidate_id,
        candidate_id=alternative.candidate_id,
        validity="EQUIVALENT_METHOD" if valid else "COMPARISON_NOT_EQUIVALENT",
        classification=classification,
        decision_change=[a.decision.status, b.decision.status] if a and b else None,
        score_delta=score_delta,
        duration_deltas_s=deltas,
        unknown_deltas_s=unknown,
        explanation=f'{classification}: only start UTC changes. Decisions use the existing operation evaluator under {b.request.evaluation_policy if b else "unavailable evidence"}. Deltas are null when evidence is not comparable. No continuous physical visibility is certified.',
    )


def optimize(request, provider, *, hints=(), geometry_priority=None):
    started = time.perf_counter()
    windows = {}
    evaluated = 0
    partial = False
    if isinstance(provider, LiveProvider):
        provider.started = started

    def make(utc, sources):
        key = hashlib.sha256(utc.isoformat().encode()).hexdigest()[:16]
        return TemporalCandidate(
            candidate_id=key,
            start_utc=utc,
            end_utc=utc + timedelta(seconds=request.baseline_analysis.time.duration_s),
            discovery_sources=sources,
        )

    def detail(candidate):
        nonlocal evaluated, partial
        if (
            evaluated >= request.max_detailed_candidates
            or time.perf_counter() - started >= request.max_wall_time_s
        ):
            candidate.evaluation_status = "NOT_EVALUATED_RESOURCE_LIMIT"
            candidate.reason_codes = ["SEARCH_PARTIAL_RESOURCE_LIMIT"]
            partial = True
            return
        a, wreq = shifted_requests(request, candidate.start_utc)
        ts = time.perf_counter()
        evaluated += 1
        try:
            w = provider.get(wreq)
        except ScienceError as exc:
            candidate.evaluation_status = "PARTIAL"
            candidate.reason_codes = [exc.code]
            partial = True
            return
        if w is None:
            candidate.evaluation_status = "PARTIAL"
            candidate.reason_codes = ["RECORDED_EVIDENCE_UNAVAILABLE"]
            partial = True
            return
        windows[candidate.candidate_id] = w
        q = OperationEvaluationRequest(
            analysis=a,
            evaluation_policy=request.evaluation_policy,
            window_evidence_sha256=evidence_identity(w),
            correction=request.window_template.visibility.correction,
            resolved_site=request.resolved_site,
            resolved_site_id=request.resolved_site_id,
        )
        op = evaluate_operation(q, w)
        candidate.operation = op
        candidate.metrics = {k: v.model_dump() for k, v in w.metrics.items()}
        candidate.evidence_sha256 = evidence_identity(w)
        candidate.evidence_mode = provider.mode
        candidate.seconds = time.perf_counter() - ts
        # An exact recorded UTC/configuration is required; never crop/relabel old data.
        if science_configuration(w) != science_configuration(
            request_template_window(request, wreq)
        ):
            candidate.evaluation_status = "INVALID"
            candidate.reason_codes = ["ANALYSIS_WINDOW_MISMATCH"]
            partial = True
            return
        candidate.evaluation_status = (
            "DETAILED_EVALUATED"
            if w.execution_status == "COMPLETED"
            and "ANALYSIS_WINDOW_MISMATCH" not in op.decision.reason_codes
            else "PARTIAL"
        )
        candidate.reason_codes = op.decision.reason_codes
        if candidate.evaluation_status == "PARTIAL":
            partial = True

    baseline = make(request.baseline_analysis.time.start_utc, ["BASELINE"])
    detail(baseline)
    rows, discovery = discover(request, hints, geometry_priority)
    partial |= discovery["truncated"]
    candidates = []
    for index, (t, sources) in enumerate(rows):
        candidate = make(t, sources)
        if request.selection_strategy == "COVERAGE_AWARE" and index >= max(
            0, request.max_detailed_candidates - 1
        ):
            candidate.evaluation_status = "NOT_SELECTED_FOR_DETAILED_EVALUATION"
            candidate.reason_codes = ["CANDIDATE_STRATEGY_NOT_SELECTED"]
            partial = True
        else:
            detail(candidate)
        candidates.append(candidate)
    ranked = sorted([c for c in candidates if c.operation], key=candidate_rank)
    comparisons = []
    recommendations = []
    for candidate in ranked:
        comp = compare(
            baseline,
            candidate,
            windows.get(baseline.candidate_id),
            windows.get(candidate.candidate_id),
        )
        comparisons.append(comp)
        candidate.comparison_validity = comp.validity
        if (
            comp.classification == "IMPROVED_ALTERNATIVE"
            and len(recommendations) < request.max_recommendations
        ):
            recommendations.append(candidate)
    if recommendations:
        outcome = "CANDIDATES_FOUND"
    elif baseline.operation and baseline.operation.decision.status == "MET":
        outcome = "KEEP_CURRENT_PLAN"
    elif not ranked or all(c.operation.decision.status == "INCOMPLETE" for c in ranked):
        outcome = "ONLY_INCOMPLETE_CANDIDATES"
    else:
        outcome = "NO_ELIGIBLE_CANDIDATE_IN_EVALUATED_SET"
    return TemporalOptimizationResult(
        request=request,
        baseline=baseline,
        candidates=candidates,
        recommendations=recommendations,
        ranked_suggestions=[c.candidate_id for c in ranked],
        comparisons=comparisons,
        search_status=(
            (
                "SEARCH_PARTIAL_RESOURCE_LIMIT"
                if (discovery["truncated"] and request.selection_strategy == "LEGACY")
                or any(
                    c.evaluation_status == "NOT_EVALUATED_RESOURCE_LIMIT"
                    or any(
                        "RESOURCE_LIMIT" in code or "BUDGET" in code
                        for code in c.reason_codes
                    )
                    for c in [baseline] + candidates
                )
                else (
                    "SEARCH_PARTIAL_SELECTION_LIMIT"
                    if (
                        discovery["truncated"]
                        and request.selection_strategy == "COVERAGE_AWARE"
                    )
                    or any(
                        c.evaluation_status == "NOT_SELECTED_FOR_DETAILED_EVALUATION"
                        for c in candidates
                    )
                    else "SEARCH_PARTIAL_EVIDENCE_UNAVAILABLE"
                )
            )
            if partial
            else "SEARCH_COMPLETED_EVALUATED_SET"
        ),
        outcome=outcome,
        search_scope={
            "start_utc": request.search_start_utc,
            "end_utc": request.search_end_utc,
            "generated_alternatives": len(rows),
            "detailed_attempts_including_baseline": evaluated,
            "not_evaluated_resource_limit": sum(
                c.evaluation_status == "NOT_EVALUATED_RESOURCE_LIMIT"
                for c in candidates
            ),
            "discovery": discovery,
            "selected_for_detailed_including_baseline": 1
            + min(len(rows), max(0, request.max_detailed_candidates - 1)),
            "detailed_completed_including_baseline": sum(
                c.evaluation_status == "DETAILED_EVALUATED"
                for c in [baseline] + candidates
            ),
            "not_selected": sum(
                c.evaluation_status == "NOT_SELECTED_FOR_DETAILED_EVALUATION"
                for c in candidates
            ),
            "evidence_unavailable": sum(
                "RECORDED_EVIDENCE_UNAVAILABLE" in c.reason_codes
                for c in [baseline] + candidates
            ),
            "invalid": sum(
                c.evaluation_status == "INVALID" for c in [baseline] + candidates
            ),
            "scientifically_incomplete": sum(
                c.operation is not None and c.operation.decision.status == "INCOMPLETE"
                for c in [baseline] + candidates
            ),
        },
        resource_consumption={
            "seconds": time.perf_counter() - started,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "remaining_budgets": {
                "detailed_candidates": max(
                    0, request.max_detailed_candidates - evaluated
                ),
                "visibility_evaluations": max(
                    0,
                    request.max_window_evaluations
                    - provider.counters().get("visibility_evaluations", 0),
                ),
                "new_rays": max(
                    0,
                    request.max_new_horizon_rays
                    - provider.counters().get("attempted_rays", 0),
                ),
                "terrain_samples": max(
                    0,
                    request.max_terrain_samples
                    - provider.counters().get("dem_samples", 0),
                ),
                "wall_time_s": max(
                    0, request.max_wall_time_s - (time.perf_counter() - started)
                ),
            },
            **provider.counters(),
        },
        limitations=LIMITATIONS,
    )


def request_template_window(request, wreq):
    """Small configuration view only; never used as scientific evidence."""
    from types import SimpleNamespace

    return SimpleNamespace(request=wreq)
