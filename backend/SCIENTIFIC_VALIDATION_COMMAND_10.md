# Command 10 scientific and integration validation

This is a bounded NASA-derived prototype, not a landing-safety certification system. General science_ready remains false. Prototype HTTP/job availability is independently exposed. Main base d7a30a769458feb9a68ae53dcd3e095b09cfe70f includes PR #26/#27. The baseline suite was freshly run: 570 passed, zero failed/skipped.

## Sources and independent validation

Default science uses Site01 5 m and Product90 80 m with the five pinned DE421 kernels, MOON_ME_DE421, planetocentric/east-positive coordinates, lunar radius 1737400 m and explicit reference-sphere height evidence. The existing relative overlap/seam diagnostics are preserved; no offsets or blending are added. Containing-cell heights differ across source resolutions and REPORT policy does not certify absolute alignment. Independent product control points and horizontal/vertical absolute accuracy were not obtained. DEM_ABSOLUTE_REGISTRATION remains UNVERIFIED.

The supposedly absent Product90 20 m file is actually present in this workspace. Rechecked size 2696082051 bytes; SHA-256 09b7ca80f9e6a146f970225d18af72fc02787669b3ef51b888e347d2b6845649; 30400×30400, 20 m Float32, south-polar stereographic lunar sphere, NaN NoData, valid CR1 height 1942.38525390625 m. This matches the user transfer manifest, not an independently published NASA checksum. It remains optional and inactive. Thus no candidate is affected by a missing 20 m file; far-terrain 80 m resolution limits still apply because the default was intentionally retained.

HEAD requests to PGDA Product 78/90, the 20 m download URL and official JPL Horizons pages were blocked by proxy tunnel HTTP 403. No repeated multi-GB download was attempted. No equivalent Horizons numerical query/configuration could be established. Target epochs include Nov 20 08:00, Nov 23 17:26:15, the recorded bracket and another epoch; numerical Sun/Earth reference differences remain NOT_MEASURED. HORIZONS_REFERENCE is INCONCLUSIVE; SPICE self-consistency is not independent observational validation.

## Real HTTP/job evidence

A real loopback Uvicorn service accepted an AnalysisRequest with HTTP 202 and random job ID, executed a one-hour CR1 NASA analysis in about 62.5 s, persisted AnalysisResult 1.0, and returned it by polling/result HTTP 200 with LIVE_COMPUTED origin. The server was restarted; the completed result survived. An explicit resumed analysis reused both validated UTC checkpoints with PRECOMPUTED origin. Another actual six-hour analysis was cancelled during a bounded visibility call and reached CANCELLED with partial evidence. No active thread was force-terminated.

A real 5 km local search screened 16 source-backed points, found eight with slope estimates within 10 degrees and verified baseline plus one alternative. See LOCAL_SITE_OPTIMIZER_VALIDATION.md. A canonical temporal API batch plus resume completed four entries including baseline, leaving 27 alternatives without complete decisions. See TEMPORAL_SEARCH_VALIDATION.md. A further restart/chained replay validated the resume materialization/counter path without new full visibility calculations. HTTP recorded and live modes are explicit and source labels differ.

## Sampling and disk validation

A controlled one-hour real CR1 window was evaluated at 60, 30 and 15 minute spacing in one shared scientific session. There were 2/3/5 timeline samples. Exact-UTC checkpoints reused repeated epochs; only five unique visibility calls/650 rays/293469 terrain positions were computed. All three sampled models gave Solar total 0, Earth total/longest 3600, Joint 0, zero sampled unknown duration, NOT_MET/0 for the example solar requirement. Elapsed times 61.217/32.260/60.030 s include different reuse amounts and are not an equal-work speedup comparison. Ten-minute sampling was not run. No six-hour continuity certification follows from this one-hour sensitivity experiment.

Existing analytical full/none/partial/grazing/narrow-obstruction/unknown and 64/256/1024 disk tests are preserved. New real disk/grid checks use 64 samples; no new 1024-ray live workload was started. STRICT evidence still refuses uncertified continuous duration, and prototype scores retain their version and limitations.

## Gate matrix

| Gate | Result | Scope |
|---|---|---|
| LOCAL_SITE_OPTIMIZER | PASS | Bounded coarse/refinement and exact verification |
| SPATIAL_COORDINATE_GEOMETRY | PASS | Geodesic/polar/wrap/radius tests |
| DEM_SCREENING | PASS | Real source/quality/NoData evidence |
| SLOPE_VALIDATION | PASS | Analytic gradient tests; real slopes are estimates |
| SPATIAL_LIVE_EVALUATION | PASS | Baseline plus one complete one-hour candidate |
| TEMPORAL_30_CANDIDATE_SEARCH | PARTIAL | Four entries including baseline; not 30/30 |
| HORIZON_GRID_VALIDATION | PASS | 360/720 scheduled exact directions, unknown/wrap safety |
| EXACT_RAY_EQUIVALENCE | INCONCLUSIVE | Tested nodes match; arbitrary interpolation is not equivalent |
| NASA_20MPP | AVAILABLE | User-manifest hash verified; optional/inactive |
| DEM_ABSOLUTE_REGISTRATION | UNVERIFIED | No independent control-point proof |
| HORIZONS_REFERENCE | INCONCLUSIVE | Proxy 403; no numeric comparison |
| STRICT_PROTOTYPE_SEPARATION | PASS | Existing/new regressions |
| OPERATION_SCORE_REGRESSION | PASS | Existing v1 unchanged |
| ANALYSIS_API | PASS | Real 202 → science → persisted result |
| TEMPORAL_API | PASS | Live batch plus checkpoint resume |
| LOCAL_API | PASS | Live 5 km search |
| LONG_RUNNING_JOB_MANAGER | PASS | Single owner, bounded durable queue |
| JOB_POLLING_AND_RESULT | PASS | Typed actual HTTP results |
| JOB_PERSISTENCE_AND_CANCEL | PASS | Restart, chained resume, cooperative cancellation |
| REAL_SCIENTIFIC_HTTP_EXECUTION | PASS | New NASA calculations, not recorded-only demo |
| FRONTEND_HANDOFF | PASS | INTEGRATION_HANDOFF.md and OpenAPI |
| FULL_BACKEND_TESTS | PASS | 603 passed / 0 failed / 0 skipped |

Command 11 can integrate the bounded prototype service while preserving scientific uncertainty. Authentication/rate limiting, multi-host workers, public deployment, exhaustive spatial search, all 30 temporal alternatives and independent observational/registration certification remain outside the validated deployment/scientific scope. No frontend/shared contract/root configuration was edited.

Final regression: 603 PASSED / 0 FAILED / 0 SKIPPED in 90.01 s, including 33 new cases (26 infrastructure/synthetic and seven actual HTTP/CLI NASA artifact assertions). Existing genuine-file integrations and recorded regressions ran with configured source paths. pip check and diff check passed. GitHub CI was not executed by this task. Requested live analysis horizon export is also verified: one persisted 360-direction profile with matching body horizon IDs and LIVE_COMPUTED origin.

Recorded temporal CLI replay also produced finite JSON and refused an existing output path (0.533084 s including process startup); this is not a new live NASA benchmark.

## Final Command 10 closure acceptance

The earlier delivery snapshot is historical. The final closure evaluates all 30 canonical alternatives plus baseline, adds per-candidate provenance/hint isolation, integrates optional grid prioritization, verifies four local entries, and compares uploaded Horizons tables numerically. Detailed evidence is in command-10-closure.json and its linked JPL/source-comparison supplements. Raw private attachments remain outside Git.

| Gate | Final result |
|---|---|
| EXISTING_PR_28_PRESERVED | PASS |
| LIVE_SCIENTIFIC_API | PASS |
| LONG_RUNNING_JOB_MANAGER | PASS |
| JOB_POLLING_RESULT | PASS |
| CANCELLATION_PERSISTENCE | PASS |
| ANALYSISRESULT_1_0 | PASS |
| LOCAL_SITE_OPTIMIZER | PASS |
| SPATIAL_CANDIDATE_EVALUATION | PARTIAL |
| TEMPORAL_30_CANDIDATE_EVALUATION | PASS |
| TEMPORAL_RESUME | PASS |
| CANDIDATE_ORIGIN_CORRECTNESS | PASS |
| HISTORICAL_HINT_ISOLATION | PASS |
| HORIZON_GRID_INTEGRATION | PASS |
| TOTAL_OPTIMIZER_PERFORMANCE | MEASURED |
| NASA_20MPP | AVAILABLE |
| DEM_ABSOLUTE_REGISTRATION | UNVERIFIED |
| JPL_HORIZONS_COMPARISON | PARTIAL |
| STRICT_PROTOTYPE_SEPARATION | PASS |
| FOUR_MISSION_PROFILES | PASS |
| FULL_BACKEND_TESTS | PASS |
| FRONTEND_HANDOFF | PASS |
| PR_28_UPDATED | PASS |

Final full regression: **674 passed / 0 failed / 0 skipped, 94.01 s**. Seventy-one new cases include 66 infrastructure/synthetic/analytical and five derived real-data assertions; live experiments are separately identified. pip check, diff check, finite JSON and overwrite refusal passed. The cancellation test now observes its pending state using explicit synchronization; no scientific test/tolerance was weakened. GitHub CI is not claimed as passed.

Worker window artifacts recorded a shared-process high-water RSS of 233440 KiB for the canonical batch; this is not isolated per-arm allocation. Temporal closure added 161 actual visibility evaluations/20930 rays/8968176 terrain positions, with retained evidence reported separately. The cold-cache one-hour A/B showed no speedup, so EXACT_ONLY remains default. The local result is still a finite one-hour search, not a six-hour/global optimum.

**COMMAND_10_INTEGRATION_READY_WITH_OPEN_VALIDATION_GATES**: the real HTTP/job chain is ready for bounded prototype integration. Horizons equivalence, absolute registration, physical continuity and exhaustive spatial coverage remain open.
