# Scientific job API — Command 10

The single scientific worker is explicitly enabled with LUNAR_ENABLE_JOBS=1. Without it, legacy analysis 503 behaviour remains. Health 1.0 is unchanged: science_ready=false. `/capabilities` distinguishes the owned worker, configured file availability, recorded scenarios and bounded prototype execution; file existence is not successful hash validation. Hash/CRS/metadata validation happens when a job opens trusted configured sources.

## HTTP contract

- GET `/api/v1/health`: unchanged HealthResponse 1.0.
- GET `/api/v1/capabilities`: prototype availability and server limits.
- GET `/api/v1/result-schemas`: backend-owned output schemas; new temporal jobs return command-10-temporal-batch-v2.
- POST `/api/v1/analyses`: AnalysisRequest 1.0 body. Query: mode=live|recorded; evaluation_policy=STRICT_EVIDENCE|PROTOTYPE_SAMPLED_ESTIMATE; registration=STRICT|PROTOTYPE; step_s=600..3600. Defaults STRICT. Live returns JobAccepted 202. Recorded is explicit opt-in and returns AnalysisResult 1.0/200 only for exact scientific configuration, coordinate, time/duration, thresholds, heights and sampling matches; otherwise 404. Historical recorded scenarios require options.include_full_horizon=false; live requests can compute the requested bounded 1-degree profile.
- POST `/api/v1/analyses/jobs`: extended AnalysisJobRequest (`analysis`, `evaluation_policy`, `registration`, `step_s`, `disk_samples`, `resources`, optional `resume_from`).
- POST `/api/v1/optimizations/temporal`: TemporalJobRequest (`optimization`: existing TemporalOptimizationRequest; `max_candidate_evaluations`:1..31 including baseline; `resources`; optional `resume_from`).
- POST `/api/v1/optimizations/local`: LocalJobRequest (`optimization`: LocalSiteOptimizationRequest; `resources`; optional `resume_from`).
- GET `/api/v1/jobs/{id}`: typed ScientificJobStatus, 200; absent ID 404.
- GET `/api/v1/jobs/{id}/result`: typed ScientificJobResult envelope, 200 only for persisted terminal evidence; otherwise 409. `result.analysis` is AnalysisResult 1.0 for analysis jobs. Optimizers return their documented backend-local result. Cancelled/failed jobs may have partial evidence; terminal status must be checked before treating it as complete analysis.
- POST `/api/v1/jobs/{id}/cancel`: idempotent typed current status; RUNNING becomes CANCEL_REQUESTED, QUEUED becomes CANCELLED. Terminal jobs stay terminal.

Invalid input 422; request body above 128 KiB 413; bounded active queue/storage admission 429; disabled/missing science resources 503 with explicit codes; unresolved named sites 503. A 202 means durable queued work, never MET. The prototype resolves coordinate requests only; named site coordinates are not guessed. Output result integrity failure is 500. No arbitrary client file/kernel/executable paths are accepted. Optional LROC and 1024-disk requests are rejected by this API configuration; baseline remains 5 m + 80 m, 64/256 samples.

## Persistence, ownership and cancellation

SQLite WAL with synchronous=FULL persists queue, metadata, final JSON and SHA-256-bound checkpoints transactionally. Results are committed atomically as SQLite blobs; no partially written final files are exposed. One nonblocking OS file lock owns one worker per database. Separate Uvicorn workers sharing a database cannot each start science workers. Run with one Uvicorn worker. SPICE sessions are opened/closed inside that serial worker, not HTTP handler threads.

Default maximum four active jobs, 64 stored jobs, 8 MiB result/checkpoint payload, 16 MiB checkpoint aggregate per job. Storage quota refuses admission/writes; archive management is an operator task. Completed results survive restart. RUNNING/CANCEL_REQUESTED from a previous owner become INTERRUPTED; queued work remains queued. There is no claim of execution while the server is down. Cancellation/shutdown is cooperative before expensive candidates and between bounded UTC calls. A call already running may take tens of seconds or more to finish. No unsafe mid-SPICE/raster thread termination is used.

States: QUEUED durably admitted; RUNNING worker-owned; COMPLETED execution/result persisted (not necessarily MET); PARTIAL finite evidence/resource limit; FAILED explicit error class/code; CANCEL_REQUESTED pending safe stop; CANCELLED safely stopped; INTERRUPTED worker/server loss. Percent is null unless completed execution genuinely finished. Candidate counts and stages are measured, not simulated.

## Resume and resource accounting

Resubmit the same job-type endpoint with the same scientific input and `resume_from` set to a terminal job ID. Resources and temporal admission count may be extended. Changed scientific requests are rejected. Source manifests/kernels are rehashed/reopened; checkpoint keys bind exact UTC/scientific request, DEM/quality namespace, kernel hashes and algorithm. Corrupt checkpoint payloads are rejected. Only complete, non-budget-limited single-UTC disk evidence is cached; window segments, censoring, brackets, operation evaluation and hashes are rebuilt, never cropped or relabelled.

Checkpoint ancestry is bounded to eight levels and recovered entries are materialized into the new job. Cumulative charged scientific counters include retained checkpoint costs once; actual new engine work may be smaller. Wall allowance is per execution attempt. `checkpoint_reused` counts lookups, not necessarily distinct UTCs. Static ray LRU remains exact and session-scoped. Resume is explicit rather than automatic. If source identity changes, matching checkpoint keys are unavailable and fresh computation is required; no stale evidence is promoted.

Resources bound wall admission (maximum 3600 s), full visibility calls (256), horizon rays (50000), terrain positions (20000000), cache (4096), candidates and output. Local screening reserves its bounded neighbour-read cost before admission. Wall control is cooperative, not a hard real-time interrupt. Setup/hash time is visible in job timestamps and may precede the scientific loop.

## Deployment boundary

This is a local/single-host prototype, not an internet-ready multi-tenant queue. Bind loopback. Before public deployment add authenticated job ownership, reverse-proxy rate limiting, disk retention/backups, TLS and external process supervision. IDs are random 128-bit values, not authentication. Duplicate submissions create separate jobs and remain quota-bound. CORS is opt-in via LUNAR_ALLOWED_ORIGINS; no wildcard/credential sharing is enabled. A managed external durable worker is not included.

Command 10 closure: Linux/POSIX flock is required (WSL2 supported; native Windows unsupported). Optional temporal outer fields `screening_strategy` (EXACT_ONLY/HORIZON_GRID) and `grid_spacing_deg` (1.0/0.5) are advertised in OpenAPI. Grid preparation is counted and only affects discovery. Candidate origin uses per-candidate call deltas, with mixed/replay resource details. Partial window searches do not become completed AnalysisResult objects; `analysis` may be null while partial evidence remains retrievable. Recorded catalog bytes are integrity-pinned to the reviewed repository artifact; missing/tampered catalogs never return a fabricated recorded success.

Final closure HTTP acceptance covered live temporal completion (31 window executions), diverse local verification (four entries), both optimizer A/B paths, queued cancellation with correct CANCELLED stage, 429 admission at capacity, 404 unknown jobs, 422 invalid bodies and resumed persisted 360-direction analysis. A zero-new-ray live geometry request returned PARTIAL with analysis=null, INCOMPLETE decision and null score. Eight recorded NASA profile/policy requests retained PRECOMPUTED origin and explicit requirements (including min_sun_visible_s=7200). During an active real NASA job, ten health/status queries averaged 0.006084 s, maximum 0.008323 s; these are observations, not latency guarantees.
