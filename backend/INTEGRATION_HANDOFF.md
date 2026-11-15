# Frontend integration handoff — Command 10

## Start the backend

Use Python 3.12 with backend data/science dependencies installed. From the repository root:

```
export PYTHONPATH=backend:.
export NASA_KERNEL_DIR=/configured/trusted/kernel-directory
export NASA_KERNEL_INDEX=/configured/trusted/kernel-index.json
export NASA_LOLA_VALIDATION_DIR=/configured/trusted/lola-directory
export LUNAR_ENABLE_JOBS=1
export LUNAR_JOB_DB=/persistent/private/lunar-jobs/jobs.sqlite
export LUNAR_ALLOWED_ORIGINS=http://localhost:5173
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --workers 1
```

Paths above are operator configuration placeholders, not files supplied by the client. The kernel index must pin de421.bsp, moon_pa_de421_1900-2050.bpc, moon_080317.tf, naif0012.tls and pck00011.tpc. The trusted LOLA directory must contain the inspected Site01 surface/ldec/toterr and Product90 80 m files expected by data_pipeline.horizon_cli. Existing checked references and quality hashes are used. Optional 20 m remains separate and inactive. See SCIENTIFIC_JOB_API.md for resource/storage and deployment limits.

## Availability is not scientific certification

GET `/api/v1/health` still returns science_ready=false and SCIENCE_ENGINE_NOT_READY. Do not use that alone to disable every prototype request. GET `/api/v1/capabilities` separately reports `scientific_job_runner_available`, `configured_science_files_available` and `bounded_live_prototype_supported`. Those mean the bounded job service can attempt prototype computation; they do not certify all coordinates/epochs or absolute registration. No frontend safeguard is changed by this backend PR.

## Analysis request and loading flow

POST `/api/v1/analyses?registration=PROTOTYPE&evaluation_policy=PROTOTYPE_SAMPLED_ESTIMATE` with:

```json
{"schema_version":"1.0","site":{"kind":"COORDINATES","latitude_deg":-89.468,"longitude_deg_east":222.6},"time":{"start_utc":"2026-11-20T08:00:00Z","duration_s":3600},"operation":{"profile":"SOLAR_POWERED_EXPERIMENT","requirements":{"min_sun_visible_s":600}}}
```

Thresholds in examples are EXAMPLE_OPERATION_ASSUMPTION. Requirements explicitly supplied by the user are preserved; serialize requirements with exclude-unset semantics rather than adding unintended default rules. STRICT_EVIDENCE and STRICT terrain registration remain defaults; prototype assumptions require explicit selection. Coordinate inputs are supported; unresolved site IDs produce an explicit unavailable response.

A long analysis returns HTTP 202 with job_id, job_type, status, submitted_at_utc, request_identity, status_url, result_url, cancellation_url, scientific_mode and resource_policy. Store the returned job ID and exact client request identity. Poll status_url every 1–2 seconds with backoff; each polling HTTP call should use an ordinary short network timeout, not the several-minute science duration. Do not keep the submission connection open.

Show loading for QUEUED/RUNNING; show cancellation pending for CANCEL_REQUESTED. Render only trustworthy stage/count information. progress_percent may be null. Never invent progress from elapsed time. On network loss show disconnected/unknown execution state and retry polling; do not mark the job failed or resubmit automatically, because accepted work may still be running.

On terminal status fetch result_url if result_available. The result envelope is `{job_id,job_type,status,result}`. Analysis jobs put the public AnalysisResult 1.0 at `result.analysis`, plus backend-local `window_evidence`, `operation_evidence`, resource counters and checkpoint reuse information. Validate envelope status before rendering complete analysis. PARTIAL/CANCELLED/FAILED may contain partial scientific evidence, not a complete AnalysisResult. Operation MET/NOT_MET/INCOMPLETE and execution status are independent.

AnalysisResult.request matches the validated request, with normal Pydantic defaults expanded. Compare normalized requests, retaining explicit requirement activation semantics. series may include an end-boundary probe. Windows are [start,end). Missing/unknown windows are null; a completed sampled estimate with no matching window is []. Live requests with include_full_horizon=true build a budgeted 1-degree exact sampled grid (separate profiles for different heights). horizons=null means the full azimuth profile was not calculated, for example in historical recorded windows; no 360-degree profile is fabricated. coverage_complete refers to scheduled grid directions, not continuous/interpolated accuracy. Individual angles/fractions/clearances can be null. Source version strings may explicitly say UNSPECIFIED_HASH_PINNED rather than invent a publisher version.

## Recorded examples

Use `mode=recorded` explicitly with registration=PROTOTYPE and matching sampling/policy. Set options.include_full_horizon=false for historical recorded examples; they do not contain a full horizon profile and requests requiring it return 404. Exact six-hour CR1 records exist at 2026-11-20T08:00:00Z and 2026-11-23T17:26:15Z. A matching record returns HTTP 200, AnalysisResult.data_origin=PRECOMPUTED. Different time, duration, coordinate, threshold, height or scientific configuration must not receive that record; 404 is expected. Default mode is live, never silent fallback to a different recorded scenario. Live source-backed results use LIVE_COMPUTED; unverified/missing-source analysis origin remains null. TEST_FIXTURE is reserved for tests. Optimizer candidate evidence modes distinguish live/replayed records.

## Optimizers

Use the completed analysis job’s `result.window_evidence.request` as window_template for both optimizers; the frontend copies backend-generated configuration and does not derive astronomy or terrain settings. Keep baseline_analysis equal to the analyzed request.

POST `/api/v1/optimizations/temporal` with `optimization` matching TemporalOptimizationRequest (baseline_analysis, window_template, evaluation_policy, confinement and discovery budgets), outer `max_candidate_evaluations` and `resources`. The batch ledger preserves every discovered UTC. Baseline is included in admission count. Returned candidates distinguish complete, partial, invalid and uncomputed. Recommendations are decision-first and never padded. The canonical seven-day request produces 30 alternatives; resource-limited jobs need not complete all 30. See TEMPORAL_SEARCH_VALIDATION.md.

POST `/api/v1/optimizations/local` with `optimization` matching LocalSiteOptimizationRequest. Required fields: baseline_analysis and window_template; optional radius (maximum 5000 m), coarse/refinement steps, max generated/detailed counts, recommendations and slope threshold. The template must match the baseline scientific request. Only coordinates and their DEM heights change; UTC/duration/profile/requirements/heights/correction/policy remain fixed. GET `/openapi.json` exposes exact backend-owned models; use them rather than guessing keys.

Local results contain baseline, candidates, recommendations, comparisons, scope and resource consumption. A recommended location is in `result.recommendations[i].location`; distance_m and bearing_deg are geodesic from baseline, 0 north/90 east. Surface elevation/slope/source resolution/quality are in terrain. Slope is an approximate source-grid gradient and not landing safety. A real measured example at -89.43734917039663, 222.8374650555442 east is about 931.976 m along 4.351 degrees from CR1; its one-hour pilot must not be relabelled as a six-hour result. A recommendation or no-better-site result applies only to the evaluated finite set.

## Cancel, resume and restart

POST cancellation_url. QUEUED can cancel immediately; RUNNING returns CANCEL_REQUESTED until the current bounded calculation reaches a safe checkpoint. Keep polling. CANCELLED is a separate terminal state. Fetch available partial evidence only with clear incomplete labels. Never interpret cancellation request acceptance as completed cancellation.

Completed SQLite jobs/results survive restart. Running jobs left by a lost worker become INTERRUPTED. Queued jobs are durably retained. Explicitly resubmit the same typed job request with resume_from set to the terminal job ID; `/analyses/jobs` supports extended analysis settings/resources. Source signatures are revalidated before checkpoint reuse. Resources may be extended, but scientific settings cannot silently change. The server is not computing while shut down.

## Errors and limitations

422 invalid/missing parameters; 413 body limit; 429 queue/storage quota; 503 disabled or unavailable sources; 404 unknown job or unavailable recorded match; 409 unfinished/no result. FAILED carries sanitized error class/code. Do not turn any of these into a successful site or zero score.

Planning Suitability Index is a versioned normalized prototype metric, not probability of success. High score cannot override mandatory NOT_MET. STRICT estimates can remain INCOMPLETE/null. Geometric sunlight is not electricity; Earth clearance is not RF success. Absolute DEM registration and independent Horizons/observational validation remain unverified; source metadata/projections alone do not prove them. CORS/authentication/rate limiting and public deployment require explicit operator setup; this server is not a public production service.

All required API paths and backend-local schemas are available for Command 11. Begin with capabilities, 202 submission, polling, envelope/result validation and uncertainty rendering. The frontend files and their existing safeguards were not changed.

GET `/api/v1/result-schemas` returns the backend-owned JSON schemas for AnalysisResult 1.0, LocalSiteOptimizationResult and TemporalBatchResult. New temporal jobs use `command-10-temporal-batch-v2`: `limitations` is a string list and `scientific_window_template` is separate. Historical v1 experimental artifacts are retained as recorded evidence; clients should validate new responses against the advertised v2 schema. A real checkpoint-only HTTP replay was validated against this model without new visibility computations.

## Command 10 closure additions

Deployment requires Linux, WSL2 or a POSIX server supporting `fcntl.flock`; native Windows deployment is not supported by this worker-ownership implementation. Use one Uvicorn worker and the configured private SQLite directory.

Temporal submissions optionally accept outer `screening_strategy="HORIZON_GRID"` and `grid_spacing_deg=1.0` (or 0.5). Default EXACT_ONLY remains unchanged. The grid affects coarse candidate priority only; final decisions still use exact windows. `screening` reports preparation and query costs, while `pipeline_seconds` includes grid preparation and detailed verification. A grid build is not a free speedup. Candidate `resource_consumption` now distinguishes new visibility evaluations, checkpoint lookups and mixed origin. A job can be LIVE_COMPUTED because it built a new grid even if its final candidate windows were entirely replayed.

Local submissions optionally accept `optimization.selection_strategy="TERRAIN_DIVERSE"`; terrain-eligible candidates are admitted using source resolution, slope and geodesic separation, not a new suitability score. SLOPE_ONLY remains the compatible default. Time, duration, requirements and final operation/score definitions do not change.

Historical CR1 hints are admitted only inside the pinned recorded scenario and exact source configuration. Other requests use normal deterministic discovery. Missing/corrupt historical catalogs do not authorize a hint.

A PARTIAL analysis job may have `result.analysis=null` and retains `window_evidence`, `operation_evidence` or partial single-UTC evidence. AnalysisResult 1.0 has no PARTIAL execution enum: the service does not label an unfinished window search COMPLETED to fit that schema. Always inspect the job status and result availability before rendering.

Resource reporting distinguishes `resources` (charged retained-plus-new work), `new_resources` (this execution's actual horizon/visibility work) and `checkpoint_resources` (retained evidence costs). Local results use the analogous scientific_resources/new_scientific_resources/checkpoint_scientific_resources fields. Cache lookups are not distinct new epochs. In the server batch API, outer resources and max_candidate_evaluations govern job-wide admission; the nested window limits still bound each candidate. Nested optimizer detailed count also controls the discovery prefix, not the explicitly extended outer 31-entry batch admission.

The final canonical temporal closure evaluated all 30 alternatives plus baseline. Scientific INCOMPLETE remains possible even when every scheduled calculation finished. See TEMPORAL_SEARCH_VALIDATION.md and the closure evidence; do not convert job COMPLETED into operation MET.

Final acceptance examples and exact requests are in data_pipeline/evidence/command-10-closure.json. All canonical 30 temporal alternatives were evaluated, but two scientific decisions remain INCOMPLETE. The diverse local one-hour experiment now has three genuinely verified prototype recommendations. Grid-assisted prioritization was slower in the measured one-hour A/B, so clients should retain EXACT_ONLY unless explicitly experimenting. Uploaded Horizons references support numerical diagnostics at 17 exact UTCs but do not prove equivalent DE421/frame/correction configuration. None of these scientific limitations prevents use of the bounded job protocol for Command 11.
