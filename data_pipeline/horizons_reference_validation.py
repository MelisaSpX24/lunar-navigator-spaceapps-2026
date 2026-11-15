"""Read user-supplied Horizons tables; compare exact UTCs without equating models.

Raw inputs are never changed or copied into evidence. LT+S diagnostics omit
Horizons gravitational bending and do not establish frame/ephemeris equivalence.
"""

import argparse
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from app.science.geometry import Observer
from app.science.astronomy import calculate
from app.science.kernels import KernelSession

# Six printed decimals contribute at most 0.5 microdegree quantization. This
# predeclared one-microdegree threshold applies ONLY to equivalent configurations.
EQUIVALENT_TOLERANCE_DEG = 0.000001


class InvalidReference(ValueError):
    pass


def utc(value):
    for fmt in ("%Y-%b-%d %H:%M:%S.%f", "%Y-%b-%d %H:%M:%S", "%Y-%b-%d %H:%M"):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    raise InvalidReference("Invalid Horizons calendar UTC")


def angular_difference(backend, reference):
    return (backend - reference + 180) % 360 - 180


def parse_reference(path, target):
    path = Path(path)
    if path.stat().st_size > 8 * 1024 * 1024:
        raise InvalidReference("Reference exceeds 8 MiB input limit")
    raw = path.read_bytes()
    try:
        data = json.loads(
            raw, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x))
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InvalidReference("Invalid finite JSON") from exc
    signature = data.get("signature") if isinstance(data, dict) else None
    if (
        not isinstance(data, dict)
        or not isinstance(signature, dict)
        or data.get("error")
        or signature.get("source") != "NASA/JPL Horizons API"
    ):
        raise InvalidReference("Not a successful Horizons API response")
    text = data.get("result")
    if (
        not isinstance(text, str)
        or text.count("$$SOE") != 1
        or text.count("$$EOE") != 1
    ):
        raise InvalidReference("Missing unique ephemeris boundaries")

    def field(pattern):
        match = re.search(pattern, text, re.M)
        if match is None:
            raise InvalidReference("Required metadata absent: " + pattern)
        return match

    t = field(r"^Target body name:\s*(\w+) \((\d+)\)\s*\{source: (\w+)\}")
    expected = {"sun": ("Sun", "10"), "earth": ("Earth", "399")}[target]
    if t.group(1, 2) != expected:
        raise InvalidReference("Wrong target")
    center = field(r"^Center body name:\s*(\w+) \((\d+)\)")
    if center.group(1, 2) != ("Moon", "301"):
        raise InvalidReference("Wrong observer center")
    site = field(
        r"^Center geodetic\s*:\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\s*\{E-lon\(deg\),Lat\(deg\),Alt\(km\)\}"
    )
    lon, lat, height = map(float, site.group(1, 2, 3))
    if not (0 <= lon < 360 and -90 <= lat <= 90 and math.isfinite(height)):
        raise InvalidReference("Invalid observer coordinates")
    radii = [
        float(x)
        for x in field(
            r"^Center radii\s*:\s*([\d.]+),\s*([\d.]+),\s*([\d.]+) km"
        ).group(1, 2, 3)
    ]
    if height + min(radii) <= 0:
        raise InvalidReference("Observer altitude lies below body center")
    if not all(math.isfinite(x) and x > 0 for x in radii):
        raise InvalidReference("Invalid center reference radii")
    target_pole = re.search(r"^Target pole/equ\s*:\s*(\S+)", text, re.M)
    frame = field(r"^Center pole/equ\s*:\s*(\S+)").group(1)
    start = utc(field(r"^Start time\s*:\s*A.D. (.*?)\s+UT\s*$").group(1))
    end = utc(field(r"^Stop\s+time\s*:\s*A.D. (.*?)\s+UT\s*$").group(1))
    step = int(field(r"^Step-size\s*:\s*(\d+) minutes").group(1)) * 60
    if start.year < 1962 or end < start or step <= 0:
        raise InvalidReference("Unsupported UT/date range")
    if (
        re.search(r"^\s*Date__\(UT\)__HR:MN\s+Azi____\(a-app\)___Elev\s*$", text, re.M)
        is None
        or "Airless apparent azimuth" not in text
        or "Atmos refraction: NO (AIRLESS)" not in text
    ):
        raise InvalidReference("Unsupported quantity or refraction definition")
    rows = []
    table = text.split("$$SOE")[1].split("$$EOE")[0]
    for line in table.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(
            r"\s*(\d{4}-[A-Za-z]{3}-\d{2} \d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)\s+.*?\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*",
            line,
        )
        if match is None:
            raise InvalidReference("Unsupported or unavailable ephemeris row")
        epoch = utc(match[1])
        az, el = float(match[2]), float(match[3])
        if not start <= epoch <= end or not 0 <= az < 360 or not -90 <= el <= 90:
            raise InvalidReference("Row outside range")
        if rows and (
            epoch <= rows[-1]["utc"]
            or (epoch - rows[-1]["utc"]).total_seconds() != step
        ):
            raise InvalidReference("Duplicate, unordered or irregular timestamps")
        rows.append({"utc": epoch, "azimuth_deg": az, "elevation_deg": el})
    if not rows or rows[0]["utc"] != start or rows[-1]["utc"] != end:
        raise InvalidReference("Incomplete date range")
    return {
        "file": path.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_size": len(raw),
        "origin_url": "https://ssd.jpl.nasa.gov/api/horizons.api",
        "origin_evidence": "USER_SUPPLIED_API_RESPONSE_SIGNATURE_NOT_INDEPENDENT_DOWNLOAD_AUTHENTICATION",
        "query_parameters": None,
        "retrieved_at_utc": None,
        "generation_metadata": field(r"^Ephemeris / (.*)$").group(1).strip(),
        "api_signature": data["signature"],
        "target": target,
        "target_id": int(t[2]),
        "ephemeris": t[3],
        "center": "Moon",
        "center_id": 301,
        "coordinate_type": "GEODETIC",
        "longitude_deg_east": lon,
        "latitude_deg": lat,
        "altitude_km": height,
        "altitude_rounding_half_width_m": 0.5
        * 10 ** (-len(site[3].split(".")[-1]))
        * 1000,
        "center_radii_km": radii,
        "center_frame": frame,
        "target_pole_frame": target_pole.group(1) if target_pole else None,
        "time_system": "UTC_FOR_THESE_POST_1962_EPOCHS",
        "start_utc": start,
        "end_utc": end,
        "step_s": step,
        "correction": "AIRLESS_APPARENT_LIGHT_TIME_STELLAR_ABERRATION_GRAVITATIONAL_DEFLECTION",
        "quantity": "TARGET_CENTER_AZIMUTH_ELEVATION",
        "azimuth_convention": "NORTH_0_EAST_90_CLOCKWISE",
        "coordinate_note": "Geodetic and planetocentric latitude coincide on the declared spherical center; mean-Earth frame realization equivalence is separate.",
        "samples": rows,
    }


def configuration_reasons(ref, observer, correction):
    reasons = []
    if (ref["latitude_deg"], ref["longitude_deg_east"]) != (
        observer.latitude_deg,
        observer.longitude_deg_east,
    ):
        reasons.append("OBSERVER_COORDINATE_MISMATCH")
    altitude = observer.surface_elevation_m + observer.device_height_m
    if (
        abs(ref["altitude_km"] * 1000 - altitude)
        > ref["altitude_rounding_half_width_m"]
    ):
        reasons.append("OBSERVER_ALTITUDE_MISMATCH")
    if ref["center_radii_km"] != [observer.reference_radius_m / 1000] * 3:
        reasons.append("REFERENCE_SPHERE_MISMATCH")
    if ref["center_frame"] != observer.frame:
        reasons.append("FRAME_REALIZATION_NOT_EQUIVALENT")
    if ref["ephemeris"] != "DE421":
        reasons.append("EPHEMERIS_MODEL_MISMATCH")
    if correction == "NONE":
        reasons.append("GEOMETRIC_VS_APPARENT_CORRECTION_MISMATCH")
    elif "GRAVITATIONAL_DEFLECTION" in ref["correction"]:
        reasons.append("GRAVITATIONAL_DEFLECTION_NOT_MODELED_BY_LT_S")
    return reasons


def numeric_acceptance(azimuth_error, elevation_error, configuration_errors):
    if configuration_errors:
        return "CONFIGURATION_MISMATCH"
    if azimuth_error is None:
        return "INCONCLUSIVE"
    return (
        "MATCHED_REFERENCE"
        if max(abs(azimuth_error), abs(elevation_error)) <= EQUIVALENT_TOLERANCE_DEG
        else "NUMERIC_TOLERANCE_EXCEEDED"
    )


def statistics(values):
    return (
        {
            "count": len(values),
            "mean_absolute_deg": sum(abs(x) for x in values) / len(values),
            "maximum_absolute_deg": max(abs(x) for x in values),
            "rms_deg": math.sqrt(sum(x * x for x in values) / len(values)),
        }
        if values
        else None
    )


def validate(sun, earth, kernel_dir, kernel_index, observer, metadata=None):
    refs = {}
    errors = {}
    for name, path in [("sun", sun), ("earth", earth)]:
        try:
            refs[name] = parse_reference(path, name)
        except (ValueError, OSError) as exc:
            errors[name] = (
                "SOURCE_FILE_UNAVAILABLE" if isinstance(exc, OSError) else str(exc)
            )
    result = {
        "schema_version": "command-10-horizons-reference-v1",
        "references": refs,
        "errors": errors,
        "numeric_tolerance_deg": EQUIVALENT_TOLERANCE_DEG,
        "tolerance_scope": "Only equivalent models; six-decimal reference quantization, never widened after seeing residuals.",
        "source_metadata": metadata,
        "operational_observer": observer.model_dump(mode="json"),
        "science_ready": False,
        "limitations": [
            "Cross-ephemeris software diagnostic is not observational or absolute DEM registration certification.",
            "LT+S does not include gravitational bending; MEAN_ME is not proven identical to MOON_ME_DE421.",
            "No interpolation or nearest-time matching.",
        ],
    }
    if errors:
        result.update(
            status="INVALID_REFERENCE", comparisons=[], equivalent_matched_samples=0
        )
        return result
    common = sorted(
        set(x["utc"] for x in refs["sun"]["samples"])
        & set(x["utc"] for x in refs["earth"]["samples"])
    )
    if not common:
        result.update(
            status="INCONCLUSIVE",
            comparisons=[],
            equivalent_matched_samples=0,
            reason_codes=["NO_COMMON_EXACT_UTC"],
        )
        return result
    rows = []
    with KernelSession(kernel_dir, kernel_index) as session:
        result["kernel_identities"] = [
            {k: r[k] for k in ("filename", "sha256")} for r in session.records
        ]
        for correction in ("NONE", "LT+S"):
            reasons = {
                name: configuration_reasons(ref, observer, correction)
                for name, ref in refs.items()
            }
            # Separate reference-height control; never alters actual operation inputs.
            aligned = Observer.model_validate(
                observer.model_dump()
                | {
                    "surface_elevation_m": refs["sun"]["altitude_km"] * 1000,
                    "device_height_m": 0,
                }
            )
            if refs["sun"]["altitude_km"] != refs["earth"]["altitude_km"]:
                reasons["earth"].append("SUN_EARTH_REFERENCE_ALTITUDE_DIFFERENCE")
            for mode, obs in [
                ("OPERATIONAL_DEM_OBSERVER_DIAGNOSTIC", observer),
                ("REFERENCE_ALIGNED_DIAGNOSTIC", aligned),
            ]:
                for epoch in common:
                    try:
                        geom = calculate(session, obs, epoch, correction)
                    except Exception as exc:
                        rows.append(
                            {
                                "utc": epoch,
                                "mode": mode,
                                "correction": correction,
                                "status": "REJECTED_BACKEND_EPOCH",
                                "reason": getattr(exc, "code", type(exc).__name__),
                            }
                        )
                        continue
                    row = {
                        "utc": epoch,
                        "mode": mode,
                        "correction": correction,
                        "observer_altitude_m": obs.surface_elevation_m
                        + obs.device_height_m,
                        "frame": obs.frame,
                        "comparison_validity": "REFERENCE_CONFIGURATION_NOT_EQUIVALENT",
                        "bodies": {},
                    }
                    for name, ref in refs.items():
                        sample = next(x for x in ref["samples"] if x["utc"] == epoch)
                        d = getattr(geom, name)
                        row["bodies"][name] = {
                            "reference_azimuth_deg": sample["azimuth_deg"],
                            "backend_azimuth_deg": d.azimuth_deg,
                            "azimuth_difference_deg": (
                                None
                                if d.azimuth_deg is None
                                else angular_difference(
                                    d.azimuth_deg, sample["azimuth_deg"]
                                )
                            ),
                            "reference_elevation_deg": sample["elevation_deg"],
                            "backend_elevation_deg": d.elevation_deg,
                            "elevation_difference_deg": d.elevation_deg
                            - sample["elevation_deg"],
                            "configuration_reasons": configuration_reasons(
                                ref, obs, correction
                            ),
                        }
                    for body in row["bodies"].values():
                        body["numeric_acceptance"] = numeric_acceptance(
                            body["azimuth_difference_deg"],
                            body["elevation_difference_deg"],
                            body["configuration_reasons"],
                        )
                    row["comparison_validity"] = (
                        "MATCHED_REFERENCE"
                        if all(
                            body["numeric_acceptance"] == "MATCHED_REFERENCE"
                            for body in row["bodies"].values()
                        )
                        else "REFERENCE_CONFIGURATION_NOT_EQUIVALENT"
                    )
                    rows.append(row)
    result["comparisons"] = rows
    result["unmatched_reference_samples"] = {
        name: [row["utc"] for row in ref["samples"] if row["utc"] not in common]
        for name, ref in refs.items()
    }
    result["exact_common_utc_count"] = len(common)
    matched = {
        r["utc"] for r in rows if r.get("comparison_validity") == "MATCHED_REFERENCE"
    }
    result["equivalent_matched_samples"] = len(matched)
    result["configuration_rejected_reference_rows"] = 2 * len(common)
    result["status"] = (
        "MATCHED_REFERENCE"
        if len(matched) == len(common)
        else "PARTIAL_REFERENCE_MATCH" if matched else "CONFIGURATION_MISMATCH"
    )
    result["diagnostic_statistics"] = {}
    for mode in ("OPERATIONAL_DEM_OBSERVER_DIAGNOSTIC", "REFERENCE_ALIGNED_DIAGNOSTIC"):
        for correction in ("NONE", "LT+S"):
            result["diagnostic_statistics"][mode + ":" + correction] = {
                name: {
                    angle: statistics(
                        [
                            r["bodies"][name][angle + "_difference_deg"]
                            for r in rows
                            if r.get("bodies")
                            and r["mode"] == mode
                            and r["correction"] == correction
                            and r["bodies"][name][angle + "_difference_deg"] is not None
                        ]
                    )
                    for angle in ("azimuth", "elevation")
                }
                for name in ("sun", "earth")
            }
    requested = [
        "2026-11-20T08:00:00Z",
        "2026-11-23T17:26:15Z",
        "2026-11-23T16:15:00Z",
        "2026-11-23T16:26:15Z",
        "2026-11-27T02:00:00Z",
    ]
    result["requested_utc_alignment"] = {
        x: (
            "EXACT_MATCH"
            if datetime.fromisoformat(x) in common
            else "REJECTED_NO_EXACT_REFERENCE_UTC"
        )
        for x in requested
    }
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sun", required=True, type=Path)
    p.add_argument("--earth", required=True, type=Path)
    p.add_argument("--kernel-dir", default=os.environ.get("NASA_KERNEL_DIR"))
    p.add_argument("--kernel-index", default=os.environ.get("NASA_KERNEL_INDEX"))
    p.add_argument("--observer", type=Path)
    p.add_argument("--source-metadata", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Refusing overwrite")
    if a.observer:
        observer = Observer.model_validate_json(a.observer.read_text())
    else:
        old = json.loads(
            Path(
                "data_pipeline/evidence/command-09-temporal-optimizer.json"
            ).read_text()
        )
        observer = Observer.model_validate(
            old["live_windows"][0]["timeline"][0]["bodies"]["sun"]["observer"]
        )
    r = validate(
        a.sun,
        a.earth,
        a.kernel_dir,
        a.kernel_index,
        observer,
        json.loads(a.source_metadata.read_text()) if a.source_metadata else None,
    )
    r["observer_configuration_origin"] = (
        "USER_SUPPLIED_OBSERVER"
        if a.observer
        else "RECORDED_REAL_DEM_OBSERVER_NOT_NEW_DEM_READ"
    )
    if not a.observer:
        r["observer_record_sha256"] = hashlib.sha256(
            Path(
                "data_pipeline/evidence/command-09-temporal-optimizer.json"
            ).read_bytes()
        ).hexdigest()
    with a.output.open("x") as f:
        json.dump(r, f, default=lambda x: x.isoformat(), indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
