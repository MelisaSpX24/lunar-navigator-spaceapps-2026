"""Synthetic text fixtures test parsing; uploaded JPL observations stay private."""

import json
from pathlib import Path
import pytest
from app.science.geometry import Observer
from data_pipeline.horizons_reference_validation import (
    parse_reference,
    InvalidReference,
    configuration_reasons,
    angular_difference,
    statistics,
    EQUIVALENT_TOLERANCE_DEG,
    validate,
    numeric_acceptance,
)

TEXT = """Ephemeris / SYNTHETIC_TEST_NOT_NASA_DOWNLOAD
Target body name: Sun (10) {source: DE441}
Center body name: Moon (301)
Start time : A.D. 2026-Nov-20 08:00:00.0000 UT
Stop  time : A.D. 2026-Nov-20 14:00:00.0000 UT
Step-size : 360 minutes
Center geodetic : 222.6, -89.468, 1.94414 {E-lon(deg),Lat(deg),Alt(km)}
Center radii : 1737.4, 1737.4, 1737.4 km
Center pole/equ : MEAN_ME
Atmos refraction: NO (AIRLESS)
Date__(UT)__HR:MN     Azi____(a-app)___Elev
Airless apparent azimuth
$$SOE
 2026-Nov-20 08:00 *i 186.945856 1.015383
 2026-Nov-20 14:00 *i 183.909765 1.011762
$$EOE
"""


def write(tmp_path, text=TEXT, extra=None):
    p = tmp_path / "reference.json"
    p.write_text(
        json.dumps(
            {
                "signature": {"source": "NASA/JPL Horizons API", "version": "1.2"},
                "result": text,
            }
            | (extra or {})
        )
    )
    return p


def test_valid_api_text_and_exact_timestamps(tmp_path):
    p = write(tmp_path)
    before = p.read_bytes()
    r = parse_reference(p, "sun")
    assert len(r["samples"]) == 2 and r["altitude_km"] == 1.94414
    assert r["samples"][0]["utc"].isoformat() == "2026-11-20T08:00:00+00:00"
    assert r["query_parameters"] is None and r["byte_size"] == len(before)
    assert p.read_bytes() == before


@pytest.mark.parametrize(
    "mutation",
    [
        "json",
        "error",
        "signature",
        "no_table",
        "duplicate_soe",
        "target",
        "center",
        "quantity",
        "refraction",
        "date",
        "range",
        "duplicate_time",
        "step",
        "nodata",
        "longitude",
        "metadata",
    ],
)
def test_invalid_references(tmp_path, mutation):
    changes = {
        "no_table": ("$$SOE", "NO_TABLE"),
        "duplicate_soe": ("$$SOE", "$$SOE\n$$SOE"),
        "target": ("Sun (10)", "Earth (399)"),
        "center": ("Moon (301)", "Earth (399)"),
        "quantity": ("Azi____(a-app)___Elev", "RA DEC"),
        "refraction": ("NO (AIRLESS)", "YES"),
        "date": ("2026-Nov-20 08:00:00.0000", "2026-Feb-30 08:00:00.0000"),
        "range": ("2026-Nov-20 14:00:00.0000", "2026-Nov-20 20:00:00.0000"),
        "duplicate_time": ("2026-Nov-20 14:00 *i", "2026-Nov-20 08:00 *i"),
        "step": ("360 minutes", "60 minutes"),
        "nodata": ("186.945856", "n.a."),
        "longitude": ("222.6, -89.468", "-137.4, -89.468"),
        "metadata": ("Center pole/equ", "Unknown pole/equ"),
    }
    text = TEXT
    if mutation in changes:
        text = text.replace(*changes[mutation])
    p = write(
        tmp_path,
        text,
        (
            {"error": "No ephemeris"}
            if mutation == "error"
            else {"signature": {}} if mutation == "signature" else None
        ),
    )
    if mutation == "json":
        p.write_text("{not json")
    with pytest.raises(InvalidReference):
        parse_reference(p, "sun")


@pytest.mark.parametrize(
    "change,code",
    [
        ("height", "OBSERVER_ALTITUDE_MISMATCH"),
        ("location", "OBSERVER_COORDINATE_MISMATCH"),
        ("radius", "REFERENCE_SPHERE_MISMATCH"),
        ("frame", "FRAME_REALIZATION_NOT_EQUIVALENT"),
        ("model", "EPHEMERIS_MODEL_MISMATCH"),
        ("correction", "GEOMETRIC_VS_APPARENT_CORRECTION_MISMATCH"),
    ],
)
def test_configuration_not_equated(tmp_path, change, code):
    r = parse_reference(write(tmp_path), "sun")
    observer = Observer(
        latitude_deg=-89.468, longitude_deg_east=222.6, surface_elevation_m=1944.14
    )
    if change == "height":
        observer.surface_elevation_m = 0
    if change == "location":
        observer.latitude_deg = -89
    if change == "radius":
        r["center_radii_km"] = [1738] * 3
    assert code in configuration_reasons(r, observer, "NONE")
    assert "GRAVITATIONAL_DEFLECTION_NOT_MODELED_BY_LT_S" in configuration_reasons(
        r, observer, "LT+S"
    )


def test_signed_wrap_statistics_and_predeclared_tolerance():
    assert angular_difference(0.1, 359.9) == pytest.approx(0.2)
    assert angular_difference(359.9, 0.1) == pytest.approx(-0.2)
    assert statistics([-1, 1]) == {
        "count": 2,
        "mean_absolute_deg": 1,
        "maximum_absolute_deg": 1,
        "rms_deg": 1,
    }
    assert statistics([]) is None and EQUIVALENT_TOLERANCE_DEG == 1e-6


def test_invalid_pair_produces_explicit_evidence_without_kernel_execution(tmp_path):
    p = write(tmp_path, extra={"error": "no data"})
    observer = Observer(
        latitude_deg=-89.468, longitude_deg_east=222.6, surface_elevation_m=1944.14
    )
    r = validate(p, p, "missing", "missing", observer)
    assert r["status"] == "INVALID_REFERENCE" and not r["comparisons"]


@pytest.mark.parametrize(
    "residual,errors,expected",
    [
        (0.5e-6, [], "MATCHED_REFERENCE"),
        (1e-6, [], "MATCHED_REFERENCE"),
        (1.1e-6, [], "NUMERIC_TOLERANCE_EXCEEDED"),
        (0, ["EPHEMERIS_MODEL_MISMATCH"], "CONFIGURATION_MISMATCH"),
    ],
)
def test_numeric_tolerance_never_overrides_model_mismatch(residual, errors, expected):
    assert numeric_acceptance(residual, 0, errors) == expected


def test_missing_reference_does_not_leak_local_path(tmp_path):
    observer = Observer(
        latitude_deg=-89.468, longitude_deg_east=222.6, surface_elevation_m=1944.14
    )
    path = tmp_path / "private-missing.json"
    result = validate(path, path, "missing", "missing", observer)
    assert result["status"] == "INVALID_REFERENCE"
    assert result["errors"] == {
        "sun": "SOURCE_FILE_UNAVAILABLE",
        "earth": "SOURCE_FILE_UNAVAILABLE",
    }
    assert str(tmp_path) not in json.dumps(result)


@pytest.mark.parametrize(
    "longitude,latitude,height_m",
    [(222.6, -89.468, 1944.14), (359.99, -89.9, 0), (0, -45, -100)],
)
def test_spherical_geodetic_and_planetocentric_positions_coincide(
    longitude, latitude, height_m
):
    import math
    import numpy as np
    import spiceypy as spice
    from app.science.geometry import observer_position_km

    observer = Observer(
        latitude_deg=latitude,
        longitude_deg_east=longitude,
        surface_elevation_m=height_m,
    )
    geodetic = spice.georec(
        math.radians(longitude), math.radians(latitude), height_m / 1000, 1737.4, 0.0
    )
    assert np.allclose(geodetic, observer_position_km(observer), rtol=0, atol=1e-12)


def test_disjoint_exact_utc_tables_are_inconclusive_without_interpolation(tmp_path):
    sun = write(tmp_path)
    earth = tmp_path / "earth.json"
    text = TEXT.replace("Sun (10)", "Earth (399)").replace("2026-Nov-20", "2026-Nov-19")
    earth.write_text(
        json.dumps(
            {
                "signature": {"source": "NASA/JPL Horizons API", "version": "1.2"},
                "result": text,
            }
        )
    )
    observer = Observer(
        latitude_deg=-89.468, longitude_deg_east=222.6, surface_elevation_m=1944.14
    )
    result = validate(sun, earth, "not-used", "not-used", observer)
    assert result["status"] == "INCONCLUSIVE" and result["reason_codes"] == [
        "NO_COMMON_EXACT_UTC"
    ]


@pytest.mark.parametrize("signature", [None, [], 42])
def test_invalid_signature_shape_is_a_reference_error(tmp_path, signature):
    with pytest.raises(InvalidReference):
        parse_reference(write(tmp_path, extra={"signature": signature}), "sun")


def test_reference_input_size_is_bounded(tmp_path):
    p = tmp_path / "oversized.json"
    with p.open("wb") as f:
        f.truncate(8 * 1024 * 1024 + 1)
    with pytest.raises(InvalidReference, match="input limit"):
        parse_reference(p, "sun")
