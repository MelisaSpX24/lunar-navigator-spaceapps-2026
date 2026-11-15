"""Versioned prototype planning index, independent of mandatory decisions."""

import math
from app.models.analysis import Score, ScoreComponent

VERSION = "24and28-planning-score-v1"
METRICS = {
    "solar_duration": ("sun", "estimated_duration_s", False),
    "solar_continuity": ("sun", "estimated_longest_continuous_s", False),
    "darkness_resilience": ("sun", "estimated_longest_interruption_s", True),
    "earth_availability": ("earth", "estimated_duration_s", False),
    "earth_continuity": ("earth", "estimated_longest_continuous_s", False),
    "joint_availability": ("joint", "estimated_duration_s", False),
}


def weights_for(profile, requirements):
    solar = (
        requirements.min_sun_visible_s is not None
        or requirements.max_dark_gap_s is not None
        or "min_solar_disk_visible_fraction" in requirements.model_fields_set
    )
    earth = (
        requirements.min_earth_continuous_s is not None
        or "earth_clearance_margin_deg" in requirements.model_fields_set
    )
    joint = requirements.require_simultaneous
    if profile == "SOLAR_POWERED_EXPERIMENT" and solar:
        return {
            "solar_duration": 0.45,
            "solar_continuity": 0.35,
            "darkness_resilience": 0.20,
        }
    if profile == "EARTH_DATA_TRANSMISSION" and earth:
        return {"earth_continuity": 0.65, "earth_availability": 0.35}
    names = []
    if requirements.min_sun_visible_s is not None:
        names.append("solar_duration")
    if requirements.max_dark_gap_s is not None:
        names.append("darkness_resilience")
    if "min_solar_disk_visible_fraction" in requirements.model_fields_set and not names:
        names.append("solar_duration")
    if earth:
        names.extend(["earth_continuity", "earth_availability"])
    if joint:
        names.append("joint_availability")
    return {n: 1 / len(names) for n in names}


def compute_planning_score(windows, policy, weights, invalid=False):
    if weights and (
        any(
            name not in METRICS or not math.isfinite(weight) or weight < 0
            for name, weight in weights.items()
        )
        or not math.isclose(sum(weights.values()), 1, abs_tol=1e-12)
    ):
        raise ValueError("Invalid score weights")
    # Physical continuity bounds are unavailable in the current window schema.
    if invalid or not weights or policy == "STRICT_EVIDENCE":
        return Score(model_version=VERSION), []
    duration = windows.request.duration_s
    components = []
    details = []
    for name, weight in weights.items():
        family, field, invert = METRICS[name]
        m = windows.metrics.get(family)
        if (
            m is None
            or m.unknown_duration_s
            or windows.sampled_windows.get(family) is None
        ):
            return Score(model_version=VERSION), []
        raw = getattr(m, field)
        normal = raw / duration
        if invert:
            normal = 1 - normal
        components.append(
            ScoreComponent(
                name=name, raw_value=raw, normalized_value=normal, weight=weight
            )
        )
        details.append(
            {
                "name": name,
                "unit": "s",
                "source_metric": f"{family}.{field}",
                "evidence": "PROTOTYPE_SAMPLED_ESTIMATE",
                "contribution_points": 100 * normal * weight,
            }
        )
    return (
        Score(
            value=sum(d["contribution_points"] for d in details),
            model_version=VERSION,
            components=components,
        ),
        details,
    )
