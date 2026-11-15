"""Explicit opt-in recorded mode; full scientific configuration must match."""

import json
import hashlib
from pathlib import Path
from app.science.window_models import WindowSearchResult
from app.services.scientific_runner import template, operation, adapt_analysis

CATALOG = (
    Path(__file__).resolve().parents[3]
    / "data_pipeline/evidence/command-09-temporal-optimizer.json"
)
CATALOG_SHA256 = "76d063c328b58cf2b8ddd0a0c2fc6c44173cc62446b88ca67d377e3e2aa4c848"
# Repository artifact integrity pin, not independent NASA publisher authenticity.


def find_recorded(request):
    if request.analysis.options.include_full_horizon:
        return (
            None  # Historical window artifacts do not contain a full requested horizon.
        )
    try:
        raw = CATALOG.read_bytes()
    except OSError:
        return None
    if hashlib.sha256(raw).hexdigest() != CATALOG_SHA256:
        return None
    value = json.loads(raw)
    wanted = template(
        request.analysis, request.registration, request.step_s, request.disk_samples
    )
    for data in value["live_windows"]:
        w = WindowSearchResult.model_validate(data)
        if w.execution_status != "COMPLETED" or w.data_origin != "REAL_NASA_PROTOTYPE":
            continue
        # Scientific request comparison ignores resource admission allowances only.
        from app.science.temporal_optimizer import science_configuration
        from types import SimpleNamespace

        if w.request.start_utc != wanted.start_utc or science_configuration(
            w
        ) != science_configuration(SimpleNamespace(request=wanted)):
            continue
        op = operation(request.analysis, w, request.evaluation_policy)
        if "ANALYSIS_WINDOW_MISMATCH" in op.decision.reason_codes:
            continue
        return adapt_analysis(
            request.analysis,
            w,
            op,
            "PRECOMPUTED",
            "recorded-" + op.provenance["window_evidence_sha256"][:24],
        )
    return None
