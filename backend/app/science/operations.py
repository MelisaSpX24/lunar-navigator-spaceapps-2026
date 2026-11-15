"""Evidence-only operation evaluation. Never opens DEM or SPICE sessions."""

import hashlib, json, math, re
from app.models.analysis import Requirements, Decision, RuleResult, DataQuality
from app.science.operation_models import (
    OperationEvaluationRequest,
    OperationEvaluationResult,
    RuleEvidence,
)
from app.science.window_models import WindowSearchResult
from app.science.scoring import weights_for, compute_planning_score

LIMITATIONS = [
    "Planning Suitability Index weights are EXAMPLE_OPERATION_ASSUMPTION, not NASA technical requirements.",
    "Sampled windows do not certify continuous physical visibility; short events may be missed.",
    "Solar geometry is not electrical power; Earth clearance is not RF success.",
    "Score is a planning index, not probability of success or landing safety certification.",
    "Source identities bind supplied artifacts; no independent observational or file authenticity verification is performed here.",
]


def evidence_identity(windows):
    return hashlib.sha256(
        json.dumps(
            windows.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def effective_requirements(request):
    r = request.analysis.operation.requirements
    values = r.model_dump(exclude_unset=True)
    if request.example_preset:
        name = (
            "min_sun_visible_s"
            if request.example_preset == "SOLAR_1H"
            else "min_earth_continuous_s"
        )
        values.setdefault(name, 3600)
    result = Requirements.model_validate(values)
    for name in (
        "min_sun_visible_s",
        "min_earth_continuous_s",
        "min_joint_continuous_s",
    ):
        if (
            getattr(result, name) is not None
            and getattr(result, name) > request.analysis.time.duration_s
        ):
            raise ValueError("Example preset requirement exceeds operation duration")
    return result


def mismatch(request, windows, requirements):
    a = request.analysis
    w = windows.request
    v = w.visibility
    site = a.site
    if site.kind == "SITE_ID":
        if request.resolved_site is None or request.resolved_site_id != site.site_id:
            return True
        site = request.resolved_site
    return any(
        (
            site.latitude_deg != v.terrain.location.latitude_deg,
            site.longitude_deg_east != v.terrain.location.longitude_deg_east,
            site.frame != v.terrain.location.frame,
            site.latitude_type != v.terrain.location.latitude_type,
            a.time.start_utc != w.start_utc,
            a.time.duration_s != w.duration_s,
            a.observer.solar_height_above_surface_m != v.solar_height_above_surface_m,
            a.observer.earth_height_above_surface_m != v.earth_height_above_surface_m,
            requirements.min_solar_disk_visible_fraction != w.solar_fraction,
            requirements.earth_clearance_margin_deg != w.earth_margin_deg,
            request.correction != v.correction,
            requirements.require_simultaneous and not w.joint,
            evidence_identity(windows) != request.window_evidence_sha256,
        )
    )


def validate_metrics(windows):
    """Reject internally inconsistent duration/segment evidence before normalization."""
    d = windows.request.duration_s
    for family, m in windows.metrics.items():
        values = [
            m.estimated_duration_s,
            m.estimated_longest_continuous_s,
            m.estimated_interruption_s,
            m.estimated_longest_interruption_s,
            m.unknown_duration_s,
        ]
        if any(not math.isfinite(x) or not 0 <= x <= d for x in values):
            return False
        if not math.isclose(values[0] + values[2] + values[4], d, abs_tol=1e-6):
            return False
        if values[1] > values[0] or values[3] > values[2]:
            return False
        parts = windows.segments.get(family, [])
        cursor = windows.request.start_utc
        totals = {"MET": [], "NOT_MET": [], "UNKNOWN": []}
        for s in parts:
            if s.start_utc != cursor or s.end_utc > windows.request.end_utc:
                return False
            totals[s.condition].append((s.end_utc - s.start_utc).total_seconds())
            cursor = s.end_utc
        if cursor != windows.request.end_utc:
            return False
        expected = [
            sum(totals["MET"]),
            max(totals["MET"], default=0),
            sum(totals["NOT_MET"]),
            max(totals["NOT_MET"], default=0),
            sum(totals["UNKNOWN"]),
        ]
        if any(not math.isclose(x, y, abs_tol=1e-6) for x, y in zip(values, expected)):
            return False
        lo, hi = m.duration_lower_bound_s, m.duration_upper_bound_s
        if any(
            x is not None and (not math.isfinite(x) or not 0 <= x <= d)
            for x in (lo, hi)
        ):
            return False
        if lo is not None and hi is not None and lo > hi:
            return False
    return True


def evaluate_rules(request, windows, requirements, invalid_reason=None):
    specs = []
    r = requirements
    for field, code, family, metric, maximum in [
        (
            "min_sun_visible_s",
            "MIN_SUN_VISIBLE_DURATION",
            "sun",
            "estimated_duration_s",
            False,
        ),
        (
            "max_dark_gap_s",
            "MAX_DARK_GAP",
            "sun",
            "estimated_longest_interruption_s",
            True,
        ),
        (
            "min_earth_continuous_s",
            "MIN_EARTH_CONTINUOUS_DURATION",
            "earth",
            "estimated_longest_continuous_s",
            False,
        ),
        (
            "min_joint_continuous_s",
            "MIN_JOINT_CONTINUOUS_DURATION",
            "joint",
            "estimated_longest_continuous_s",
            False,
        ),
    ]:
        if getattr(r, field) is not None:
            specs.append((code, family, metric, getattr(r, field), maximum, "s"))
    if r.require_simultaneous and r.min_joint_continuous_s is None:
        specs.append(
            (
                "REQUIRE_SIMULTANEOUS_VISIBILITY",
                "joint",
                "estimated_longest_continuous_s",
                0,
                False,
                "s (positive required)",
            )
        )
    if "earth_clearance_margin_deg" in r.model_fields_set:
        specs.append(
            (
                "EARTH_CLEARANCE_MARGIN",
                "earth",
                "estimated_longest_continuous_s",
                (
                    r.min_earth_continuous_s
                    if r.min_earth_continuous_s is not None
                    else request.analysis.time.duration_s
                ),
                False,
                f"s at Earth margin {r.earth_clearance_margin_deg} deg",
            )
        )
    if (
        "min_solar_disk_visible_fraction" in r.model_fields_set
        and r.min_sun_visible_s is None
        and r.max_dark_gap_s is None
        and not r.require_simultaneous
    ):
        specs.append(
            (
                "SOLAR_DISK_THRESHOLD",
                "sun",
                "estimated_longest_continuous_s",
                request.analysis.time.duration_s,
                False,
                f"s at solar fraction {r.min_solar_disk_visible_fraction}",
            )
        )
    output = []
    for code, family, metric, threshold, maximum, unit in specs:
        m = windows.metrics.get(family)
        actual = getattr(m, metric) if m else None
        reason = invalid_reason
        status = "INCOMPLETE"
        if not reason and (
            m is None
            or m.unknown_duration_s
            or windows.sampled_windows.get(family) is None
        ):
            reason = "UNKNOWN_TEMPORAL_EVIDENCE"
        if not reason and request.evaluation_policy == "STRICT_EVIDENCE":
            # Only the total-duration bounds apply to total solar duration, not
            # to longest continuous windows or longest interruptions.
            if (
                code == "MIN_SUN_VISIBLE_DURATION"
                and m.duration_lower_bound_s is not None
                and m.duration_lower_bound_s >= threshold
            ):
                status = "MET"
            elif (
                code == "MIN_SUN_VISIBLE_DURATION"
                and m.duration_upper_bound_s is not None
                and m.duration_upper_bound_s < threshold
            ):
                status = "NOT_MET"
            else:
                reason = "PHYSICAL_DURATION_NOT_CERTIFIED"
        elif not reason:
            met = actual <= threshold if maximum else actual >= threshold
            if code == "REQUIRE_SIMULTANEOUS_VISIBILITY":
                met = actual > 0
            status = "MET" if met else "NOT_MET"
        reason = reason or ("MODELED_REQUIREMENT_" + status)
        message = f"{code}: required {threshold} {unit}; sampled actual {actual} {unit}. {status} under {request.evaluation_policy}. Source: {family}.{metric}. Continuous physical visibility is not certified."
        output.append(
            RuleEvidence(
                rule=RuleResult(
                    code=code,
                    status=status,
                    required=threshold,
                    actual=actual,
                    message=message,
                ),
                policy=request.evaluation_policy,
                evidence_status=windows.scientific_evidence_status,
                unit=unit,
                source_metric=f"{family}.{metric}",
                reason_codes=[reason],
            )
        )
    return output


def valid_sources(windows):
    sources = windows.source_evidence
    if windows.data_origin == "SYNTHETIC_TEST":
        return bool(sources.get("dem") and sources.get("kernel_ids"))
    if windows.data_origin != "REAL_NASA_PROTOTYPE":
        return False
    try:
        return (
            bool(sources["dem"] and sources["kernel_ids"])
            and all(
                re.fullmatch(r"[0-9a-f]{64}", s["reference"]["raster_sha256"])
                and s["reference"]["target_spice_frame"] == "MOON_ME_DE421"
                for s in sources["dem"].values()
            )
            and all(
                re.fullmatch(r"[^:]+:[0-9a-f]{64}", k) for k in sources["kernel_ids"]
            )
        )
    except (KeyError, TypeError):
        return False


def evaluate_operation(
    request: OperationEvaluationRequest, windows: WindowSearchResult
):
    r = effective_requirements(request)
    reason = "ANALYSIS_WINDOW_MISMATCH" if mismatch(request, windows, r) else None
    if not reason and not validate_metrics(windows):
        reason = "INVALID_WINDOW_METRICS"
    if not reason and not valid_sources(windows):
        reason = "SOURCE_EVIDENCE_UNAVAILABLE"
    rules = evaluate_rules(request, windows, r, reason)
    statuses = [x.rule.status for x in rules]
    status = (
        "NOT_MET"
        if "NOT_MET" in statuses
        else "INCOMPLETE" if not statuses or "INCOMPLETE" in statuses else "MET"
    )
    reasons = sorted({c for x in rules for c in x.reason_codes})
    if reason:
        reasons.append(reason)
    if not rules:
        reasons.append("NO_ACTIVE_REQUIREMENTS")
    score, details = compute_planning_score(
        windows,
        request.evaluation_policy,
        weights_for(request.analysis.operation.profile, r),
        invalid=bool(reason) or not rules or "INCOMPLETE" in statuses,
    )
    families = {x.source_metric.split(".")[0] for x in rules}
    incomplete = (
        bool(reason)
        or not rules
        or any(
            f not in windows.metrics or windows.metrics[f].unknown_duration_s
            for f in families
        )
    )
    quality = DataQuality(
        status="INSUFFICIENT" if incomplete else "LIMITED",
        coverage_complete=not incomplete,
        limitations=LIMITATIONS + windows.limitations,
    )
    return OperationEvaluationResult(
        request=request,
        effective_requirements=r.model_dump(),
        assumption_labels=(
            ["EXAMPLE_OPERATION_ASSUMPTION"] if request.example_preset else []
        ),
        decision=Decision(
            status=status, rules=[x.rule for x in rules], reason_codes=reasons
        ),
        rule_evidence=rules,
        score=score,
        score_evidence=request.evaluation_policy,
        score_details=details,
        quality=quality,
        provenance={
            "window_evidence_sha256": evidence_identity(windows),
            "sources": windows.source_evidence,
            "window_request": windows.request.model_dump(mode="json"),
        },
        data_origin=windows.data_origin,
        limitations=LIMITATIONS + windows.limitations,
    )
