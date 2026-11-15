"""Offline projections of recorded NASA evidence; no new scientific execution."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import pytest
from pyproj import Geod
from data_pipeline.demo.export_demo import build, ROOT

DEMO = ROOT / "data_pipeline/demo"


def test_deterministic_export_and_manifest():
    first = build()
    assert first == build()
    manifest = json.loads(first["manifest.json"])
    for name, raw in first.items():
        assert (DEMO / name).read_bytes() == raw
        json.loads(raw, parse_constant=lambda x: pytest.fail(x))
        if name != "manifest.json":
            assert hashlib.sha256(raw).hexdigest() == manifest["files"][name]["sha256"]
    assert sum(len(x) for x in first.values()) < 100000


def test_temporal_configuration_changes_only_start():
    r = json.loads((DEMO / "temporal_demo.json").read_text())
    a, b = r["baseline"], r["alternatives"][0]
    left = copy.deepcopy(a["source_request"])
    right = copy.deepcopy(b["source_request"])
    assert left["time"].pop("start_utc") == "2026-11-20T08:00:00Z"
    assert right["time"].pop("start_utc") == "2026-11-23T16:26:15Z"
    assert left == right and left["time"]["duration_s"] == 21600
    assert [
        (x["decision"]["status"], x["planning_score"]["value"]) for x in (a, b)
    ] == [("NOT_MET", 0), ("MET", 100)]
    assert a["source_identity"] == b["source_identity"]
    assert (
        a["planning_score"]["model_version"]
        == b["planning_score"]["model_version"]
        == "24and28-planning-score-v1"
    )


def test_local_coordinates_requirements_and_three_real_alternatives():
    r = json.loads((DEMO / "local_demo.json").read_text())
    a = r["baseline"]
    assert len(r["alternatives"]) == 3
    g = Geod(a=1737400, b=1737400)
    site = a["source_request"]["site"]
    for c in r["alternatives"]:
        x = copy.deepcopy(a["source_request"])
        y = copy.deepcopy(c["source_request"])
        loc = y.pop("site")
        x.pop("site")
        assert x == y and x["time"]["duration_s"] == 3600
        assert c["explicit_requirement_fields"] == ["min_sun_visible_s"]
        az, _, dist = g.inv(
            site["longitude_deg_east"],
            site["latitude_deg"],
            loc["longitude_deg_east"],
            loc["latitude_deg"],
        )
        assert dist == pytest.approx(c["distance_m"], abs=1e-7)
        assert az % 360 == pytest.approx(c["bearing_deg"], abs=1e-9)
        assert c["terrain"]["slope_deg"] <= 10 and c["decision"]["status"] == "MET"
        assert c["source_identity"] == a["source_identity"]


@pytest.mark.parametrize("name", ["local_demo.json", "temporal_demo.json"])
def test_missing_analysis_panels_are_explicit(name):
    r = json.loads((DEMO / name).read_text())
    for c in [r["baseline"]] + r["alternatives"]:
        assert all(
            c[k] is None
            for k in (
                "analysis_result",
                "horizon_profile",
                "time_series",
                "window_segments",
            )
        )
        assert c["delivery_data_origin"] == "RECORDED_EVIDENCE_EXPORT"
        assert c["scientific_data_origin"] == "REAL_NASA_PROTOTYPE"
        assert c["evaluation_policy"] == "PROTOTYPE_SAMPLED_ESTIMATE"
        assert c["window_evidence_sha256"] and c["limitations"]


def test_export_check_and_overwrite_refusal_without_server(tmp_path):
    cmd = [
        sys.executable,
        "-m",
        "data_pipeline.demo.export_demo",
        "--output-dir",
        str(tmp_path),
    ]
    first = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert (
        subprocess.run(cmd + ["--check"], cwd=ROOT, capture_output=True).returncode == 0
    )
    assert subprocess.run(cmd, cwd=ROOT, capture_output=True).returncode != 0
    p = tmp_path / "local_demo.json"
    p.write_text("{}")
    assert (
        subprocess.run(cmd + ["--check"], cwd=ROOT, capture_output=True).returncode != 0
    )
