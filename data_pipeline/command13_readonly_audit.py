"""Read-only Command 13 checks. Never submits jobs or computes NASA visibility.

Requires the retained private job database, configured source environment and an
already running loopback API. Output excludes private source/database paths.
Run from repository root with PYTHONPATH=backend:.
"""

import os, json, hashlib, sqlite3, urllib.request
from pathlib import Path
from datetime import datetime
import rasterio
import numpy as np
from pyproj import Transformer, CRS
from app.jobs.store import digest
from app.models.analysis import AnalysisResult
from app.services.models import TemporalBatchResult
from app.optimization.local_site_models import LocalSiteOptimizationResult
from app.science.window_models import WindowSearchResult
from app.science.operations import evidence_identity
from app.science.kernels import read_index
from data_pipeline.lola_validation import HASHES
import argparse
from urllib.parse import urlparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--job-db", type=Path, required=True)
parser.add_argument("--api-url", default="http://127.0.0.1:8010")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
if not __debug__:
    parser.error("Audit assertions must be enabled; do not use Python -O")
if args.output.exists():
    parser.error("Refusing to overwrite audit evidence")
if urlparse(args.api_url).hostname not in ("localhost", "127.0.0.1", "::1"):
    parser.error("Read-only HTTP audit is limited to a loopback server")
root = Path(__file__).resolve().parents[1]
e = json.loads(
    (
        root / "data_pipeline/evidence/nasa-live-optimizer-demo-readiness.json"
    ).read_text()
)
out = {
    "schema_version": "command-13-read-only-audit-v1",
    "base_sha": "ca26fba597b7622e2c1aba01fb6cfb280bad3d91",
    "new_nasa_calculations": 0,
    "source_files": [],
    "persisted_jobs": [],
    "http_get_checks": [],
}


def sha(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


records = read_index(
    Path(os.environ["NASA_KERNEL_DIR"]), Path(os.environ["NASA_KERNEL_INDEX"])
)
assert {r["filename"] + ":" + r["sha256"] for r in records} == set(
    e["source_identity"]["kernel_ids"]
)
for r in records:
    out["source_files"].append(
        {k: r[k] for k in ("filename", "sha256", "architecture", "kind")}
    )
for name, expected in HASHES.items():
    p = Path(os.environ["NASA_LOLA_VALIDATION_DIR"]) / name
    actual = sha(p)
    assert actual == expected
    with rasterio.open(p) as ds:
        crs = ds.crs.to_wkt()
        tr = Transformer.from_crs(CRS.from_wkt(crs).geodetic_crs, crs, always_xy=True)
        x, y = tr.transform(222.6, -89.468)
        row, col = ds.index(x, y)
        value = ds.read(1, window=rasterio.windows.Window(col, row, 1, 1), masked=True)[
            0, 0
        ]
        out["source_files"].append(
            {
                "filename": name,
                "sha256": actual,
                "bytes": p.stat().st_size,
                "resolution_m": list(ds.res),
                "dimensions": [ds.width, ds.height],
                "bounds": list(ds.bounds),
                "nodata": str(ds.nodata),
                "crs_wkt": crs,
                "cr1_pixel_valid": not bool(np.ma.is_masked(value)),
                "cr1_value": (None if np.ma.is_masked(value) else float(value)),
            }
        )
man = json.loads((root / "data_pipeline/demo/manifest.json").read_text())
for name, info in man["files"].items():
    p = root / "data_pipeline/demo" / name
    assert sha(p) == info["sha256"] and p.stat().st_size == info["bytes"]
for info in man["sources"]:
    assert sha(root / info["file"]) == info["sha256"]
out["demo_manifest"] = "PASS"
uri = args.job_db.resolve().as_uri() + "?mode=ro"
db = sqlite3.connect(uri, uri=True)
db.row_factory = sqlite3.Row
assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
assert (
    db.execute(
        "select count(*) from jobs where status in ('QUEUED','RUNNING','CANCEL_REQUESTED')"
    ).fetchone()[0]
    == 0
)
runs = [
    {"job_id": e["original_analysis_job_id"]},
    e["analysis_checkpoint_replay"],
    *e["optimizer_runs"],
]
for run in runs:
    r = dict(db.execute("select * from jobs where id=?", (run["job_id"],)).fetchone())
    v = json.loads(r["result"])
    payload = json.loads(r["payload"])
    origin = (
        v["analysis"]["data_origin"] if r["kind"] == "ANALYSIS" else v["data_origin"]
    )
    if "data_origin" in run:
        assert origin == run["data_origin"]
    if "request_identity" in run:
        assert r["identity"] == run["request_identity"]
    assert digest(v) == r["result_hash"]
    assert digest({"kind": r["kind"], "payload": payload}) == r["identity"]
    duration = (
        datetime.fromisoformat(r["finished"]) - datetime.fromisoformat(r["started"])
    ).total_seconds()
    if "wall_time_s" in run:
        assert abs(duration - run["wall_time_s"]) < 1e-6
    if r["kind"] == "ANALYSIS":
        a = AnalysisResult.model_validate(v["analysis"])
        assert (
            a.request.time.duration_s == 3600
            and a.request.operation.requirements.min_sun_visible_s == 600
        )
        w = WindowSearchResult.model_validate(v["window_evidence"])
        assert (
            evidence_identity(w)
            == v["operation_evidence"]["request"]["window_evidence_sha256"]
        )
    else:
        (
            TemporalBatchResult
            if r["kind"] == "TEMPORAL"
            else LocalSiteOptimizationResult
        ).model_validate(v)
        baseline = v["request"]["baseline_analysis"]
        assert (
            baseline["time"]["duration_s"] == 3600
            and baseline["operation"]["requirements"]["min_sun_visible_s"] == 600
        )
        allc = {c["candidate_id"]: c for c in [v["baseline"], *v["candidates"]]}
        completed = [
            c
            for c in allc.values()
            if c.get("stage", c.get("evaluation_status")) == "DETAILED_EVALUATED"
        ]
        assert len(completed) == sum(run["decisions_including_baseline"].values())
        for c in allc.values():
            if (
                c.get("stage", c.get("evaluation_status"))
                == "NOT_EVALUATED_RESOURCE_LIMIT"
            ):
                assert c["operation"] is None and not c["metrics"]
        for c in completed:
            op = c["operation"]
            a = op["request"]["analysis"]
            expected = json.loads(json.dumps(baseline))
            if r["kind"] == "LOCAL":
                expected["site"] = {"kind": "COORDINATES", **c["location"]}
            else:
                expected["time"]["start_utc"] = c["start_utc"]
                assert (
                    datetime.fromisoformat(c["end_utc"].replace("Z", "+00:00"))
                    - datetime.fromisoformat(c["start_utc"].replace("Z", "+00:00"))
                ).total_seconds() == 3600
            assert a == expected
            assert c["evidence_sha256"] == op["request"]["window_evidence_sha256"]
            assert op["score"]["model_version"] == "24and28-planning-score-v1"
            assert (
                op["provenance"]["sources"]
                == v["baseline"]["operation"]["provenance"]["sources"]
            )
        for c in v["recommendations"]:
            assert (
                c["operation"]["decision"]["status"] == "MET"
                and c.get("stage", c.get("evaluation_status")) == "DETAILED_EVALUATED"
            )
        for c in run["evaluated"]:
            actual = allc[c["candidate_id"]]
            assert (
                actual["operation"]["decision"]["status"] == c["decision"]
                and actual["metrics"] == c["metrics"]
                and actual["operation"]["score"] == c["score"]
            )
    checkpoints = list(
        db.execute(
            "select key,payload,hash from checkpoints where job_id=?", (r["id"],)
        )
    )
    counts = {}
    for cp in checkpoints:
        value = json.loads(cp["payload"])
        assert digest(value) == cp["hash"]
        kind = cp["key"].split(":")[0]
        counts[kind] = counts.get(kind, 0) + 1
        if kind == "candidate":
            w = WindowSearchResult.model_validate(value["window"])
            ident = evidence_identity(w)
            assert (
                cp["key"] == "candidate:" + ident
                and value["operation"]["request"]["window_evidence_sha256"] == ident
            )
            assert set(w.source_evidence["kernel_ids"]) == set(
                e["source_identity"]["kernel_ids"]
            )
            for quality in w.source_evidence["dem"]["SITE01"]["quality"]:
                assert HASHES[quality["id"]] == quality["sha256"]
            assert {q["id"] for q in w.source_evidence["dem"]["SITE01"]["quality"]} == {
                n for n in HASHES if "toterr" in n or "ldec" in n
            }
            for role, identity in e["source_identity"]["dem"].items():
                assert (
                    w.source_evidence["dem"][role]["reference"]["raster_sha256"]
                    == identity["sha256"]
                )
    out["persisted_jobs"].append(
        {
            "job_id": r["id"],
            "job_type": r["kind"],
            "status": r["status"],
            "data_origin": origin,
            "request_identity": r["identity"],
            "result_sha256": r["result_hash"],
            "historical_wall_time_s": duration,
            "validated_checkpoints": counts,
        }
    )
# Strictly GET-only; never submit/resume/cancel a science job in this audit.
for suffix in ["health", "capabilities", "result-schemas"] + [
    f"jobs/{r['job_id']}{end}" for r in runs for end in ("", "/result")
]:
    with urllib.request.urlopen(
        args.api_url.rstrip("/") + "/api/v1/" + suffix, timeout=10
    ) as response:
        value = json.load(response)
        assert response.status == 200
        if suffix == "health":
            assert value["science_ready"] is False
        if suffix == "capabilities":
            out["capabilities"] = value
        if suffix.endswith("/result"):
            job = suffix.split("/")[1]
            stored = json.loads(
                db.execute("select result from jobs where id=?", (job,)).fetchone()[0]
            )
            assert value["result"] == stored
        out["http_get_checks"].append({"endpoint": "/api/v1/" + suffix, "status": 200})
expected_totals = {
    k: sum(r["counts"]["new_resources"][k] for r in e["optimizer_runs"])
    for k in e["new_scientific_work_totals"]
}
assert expected_totals == e["new_scientific_work_totals"]
assert (
    sum(r["checkpoint_reused_utc_lookups"] for r in e["optimizer_runs"])
    + e["analysis_checkpoint_replay"]["checkpoint_reused_utc_lookups"]
    == 14
)
out["historical_resource_totals"] = expected_totals
out["historical_checkpoint_lookups"] = 14
out["input_evidence_sha256"] = sha(
    root / "data_pipeline/evidence/nasa-live-optimizer-demo-readiness.json"
)
with args.output.open("x") as output:
    json.dump(out, output, indent=2, allow_nan=False)
    output.write("\n")
print(
    json.dumps(
        {
            "sources": len(out["source_files"]),
            "jobs": len(out["persisted_jobs"]),
            "http_gets": len(out["http_get_checks"]),
            "totals": expected_totals,
        }
    )
)
