# Scientific backend — Command 01

Python **3.12** is supported and tested. This is an infrastructure-only backend:
no NASA data, kernels, scientific calculations or optimizer are included.

## Setup and run

From `backend/`:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-tested.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`requirements-tested.txt` records the versions installed and tested for this
command. For a new resolution use `pip install -e '.[test]'`; run the suite before
updating that snapshot. API documentation is at `/docs`; schema is at `/openapi.json`.

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
```

## Health and readiness

`GET /api/v1/health` returns HTTP 200:

```json
{
  "status": "ok",
  "science_ready": false,
  "dem_ready": false,
  "kernels_ready": false,
  "reason_codes": ["SCIENCE_ENGINE_NOT_READY"]
}
```

Liveness does not imply scientific readiness. Readiness is deliberately false
until real modules and validated data are integrated; file existence alone must
not enable it.

## Analysis contract (backend-local draft, version 1.0)

`POST /api/v1/analyses` accepts this scenario input. CR1 is a research coordinate;
its DEM coverage has **not** been verified. Heights, thresholds and times below
are example user assumptions, not NASA requirements or measured results.

```json
{
  "schema_version": "1.0",
  "site": {
    "kind": "COORDINATES",
    "latitude_deg": -89.468,
    "longitude_deg_east": 222.6,
    "frame": "MOON_ME_DE421",
    "latitude_type": "PLANETOCENTRIC"
  },
  "observer": {
    "surface_elevation_mode": "DEM",
    "solar_height_above_surface_m": 1,
    "earth_height_above_surface_m": 1
  },
  "time": {"start_utc": "2026-11-20T08:00:00Z", "duration_s": 21600},
  "operation": {
    "profile": "CUSTOM_OPERATION",
    "requirements": {"min_earth_continuous_s": 3600}
  }
}
```

Alternatively use `"site": {"kind": "SITE_ID", "site_id": "CR1"}`. Site-ID
syntax is validated, but there is no site registry/resolution yet. Mixing the
two site formats is rejected. Exact poles are rejected pending a validated
azimuth convention. Longitude is east-positive [0, 360); dates require UTC `Z`
or `+00:00`. Positive integer seconds are required for duration. Nonfinite
numbers, unexpected keys, negative heights and inconsistent duration requirements
are rejected. Invalid inputs return HTTP 422 with field locations and messages.

Profiles: `SOLAR_POWERED_EXPERIMENT`, `EARTH_DATA_TRANSMISSION`,
`SHORT_SURFACE_OBSERVATION`, `CUSTOM_OPERATION`. They share one model; defaults
are illustrative and no operational profile evaluation is implemented yet.

Valid requests return **HTTP 503** with a typed `AnalysisResult`, not a scientific
success. Inspect `decision.reason_codes` for `SCIENCE_ENGINE_NOT_READY`:

- `execution_status = NOT_RUN`; `decision.status = INCOMPLETE`.
- `score.value = null`; `resolved_site`, `series`, `horizons` are null.
- Visibility window arrays are null (not calculated), not empty (calculated,
  with no windows). Zero means an actually calculated zero only.
- `data_origin = null` because no dataset was computed. Future result origins:
  `PRECOMPUTED`, `LIVE_COMPUTED`, `TEST_FIXTURE`.
- The UUID identifies this response, not a persisted/retrievable analysis.

`execution_status` and scientific `decision.status` are independent: a completed
calculation may still yield INCOMPLETE due to insufficient data. Result models
include time samples, separate observer horizon profiles, disk fractions [0, 1],
half-open UTC windows [start, end), rule results, score components, quality,
limitations and source/kernel provenance. Missing scientific values stay null.
Static and live analyses will use this same result format. These backend-local
models must be coordinated with the team lead before shared contracts are edited.

## Deferred modules and next step

Only health and analysis validation are implemented. Capabilities, scenarios,
temporal search and spatial search endpoints are reserved for later commands.
No frontend or shared-contract files are changed.

Command 02 adds optional `data` dependencies (NumPy, Rasterio and PyProj), local
bounded raster tools and source manifests. See `../data_pipeline/README.md` for
commands, measured dependency versions and unresolved NASA file access. The
tested requirements snapshot now includes these tools. Command 03 adds optional
SpiceyPy geometry and local kernel inspection; see SCIENCE.md. No real NASA kernel
calculation or raster file has been validated locally;
the API deliberately retains SCIENCE_ENGINE_NOT_READY. Benchmark before choosing
search budgets; do not claim landing, power or radio-link certification.
