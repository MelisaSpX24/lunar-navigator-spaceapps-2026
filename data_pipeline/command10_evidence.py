"""Assemble measured evidence; redact ephemeral job identifiers and local paths."""

import argparse, json, re, time, hashlib, subprocess
from pathlib import Path
from datetime import datetime
import httpx
from app.models.analysis import AnalysisResult
from app.jobs.models import ScientificJobResult


def run(output):
    output = Path(output)
    if output.exists():
        raise ValueError("Refusing overwrite")
    http = json.loads(Path("/tmp/10-http-full.json").read_text())
    first = json.loads(Path("/tmp/10-http-analysis-result.json").read_text())
    resumed = json.loads(Path("/tmp/10-temporal-resume-result.json").read_text())
    chain = json.loads(Path("/tmp/10-resume-chain-http.json").read_text())
    grid = json.loads(Path("/tmp/10-grid-real.json").read_text())
    sampling = json.loads(Path("/tmp/10-sampling.json").read_text())
    network = json.loads(Path("/tmp/10-network.json").read_text())
    dem = json.loads(Path("/tmp/10-lola20.json").read_text())
    AnalysisResult.model_validate(first["result"]["analysis"])
    ScientificJobResult.model_validate(first)
    c = httpx.Client(base_url="http://127.0.0.1:8010", timeout=10)
    job = first["job_id"]
    t = time.perf_counter()
    reply = c.get("/api/v1/jobs/" + job + "/result")
    reply.raise_for_status()
    get_seconds = time.perf_counter() - t
    t = time.perf_counter()
    for _ in range(20):
        json.dumps(first, allow_nan=False)
    serial_seconds = (time.perf_counter() - t) / 20
    jobs = []
    for name, v in http["runs"].items():
        if "status" in v:
            s = v["status"]
            start = s.get("started_at_utc")
            finish = s.get("finished_at_utc")
            jobs.append(
                {
                    "name": name,
                    "status": s["status"],
                    "queue_wait_s": (
                        (
                            datetime.fromisoformat(start)
                            - datetime.fromisoformat(s["created_at_utc"])
                        ).total_seconds()
                        if start
                        else None
                    ),
                    "processing_s": (
                        (
                            datetime.fromisoformat(finish)
                            - datetime.fromisoformat(start)
                        ).total_seconds()
                        if start and finish
                        else None
                    ),
                }
            )
    r = {
        "status": "COMMAND_10_COMPLETE_INTEGRATION_READY_WITH_SCIENTIFIC_LIMITATIONS",
        "base_sha": "d7a30a769458feb9a68ae53dcd3e095b09cfe70f",
        "execution_origin": "REAL_NASA_HTTP_AND_CONTROLLED_CLI_VALIDATION",
        "public_identifiers_redacted": True,
        "initial_live_http_analysis": first,
        "live_horizon_analysis": json.loads(
            Path("/tmp/10-profile-http-result.json").read_text()
        ),
        "api_profile_regression": json.loads(
            Path("/tmp/10-api-profiles.json").read_text()
        ),
        "release_http_checks": json.loads(
            Path("/tmp/10-release-http-check.json").read_text()
        ),
        "typed_temporal_http": json.loads(
            Path("/tmp/10-typed-temporal-http.json").read_text()
        ),
        "http_lifecycle": http,
        "temporal_resume": resumed,
        "restart_chained_replay": chain,
        "horizon_grid": grid,
        "temporal_sampling": sampling,
        "lola20": dem,
        "external_reference_access": network,
        "job_timings": jobs,
        "measured_http_result_get_s": get_seconds,
        "measured_result_json_serialization_s": serial_seconds,
        "source_validation_time": "NOT_MEASURED_SEPARATELY",
        "notes": [
            "Source setup is included in job processing timestamps.",
            "Temporal batch completed four entries including baseline; remaining alternatives are not operation failures.",
            "Local result is a one-hour 5 km bounded experiment.",
            "No independent Horizons numerical comparison or absolute registration certification.",
        ],
    }
    ids = {}

    def redact(value):
        if isinstance(value, dict):
            return {k: redact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [redact(v) for v in value]
        if isinstance(value, str):
            if re.fullmatch("[a-f0-9]{32}", value):
                ids.setdefault(value, f"{len(ids)+1:032x}")
                return ids[value]
            value = re.sub(
                r"/api/v1/jobs/([a-f0-9]{32})",
                lambda m: "/api/v1/jobs/" + redact(m[1]),
                value,
            )
            if value.startswith("/workspace/") or value.startswith("/tmp/"):
                return "[LOCAL_PATH_REDACTED]"
        return value

    r = redact(r)
    with output.open("x") as f:
        json.dump(r, f, indent=2, allow_nan=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    a = p.parse_args()
    run(a.output)
