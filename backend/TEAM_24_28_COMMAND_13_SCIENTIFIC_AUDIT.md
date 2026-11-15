# Team 24&28 — Command 13 scientific audit

## 1. Executive Summary

**COMMAND_13_COMPLETE_WITH_LIMITATIONS.** The reviewed prototype preserves scientific uncertainty, bounded execution and recorded/live distinctions. No new critical defect was reproduced. No production scientific algorithm, optimizer, score, frontend feature or API contract was changed. This is software/evidence validation, **not scientific certification**.

This audit performed **zero new NASA visibility/optimizer computations**, submitted no real jobs, downloaded no NASA files and did not restart the existing scientific server. It rehashed nine existing scientific files, inspected raster metadata and the CR1 containing cells, validated five persisted real jobs and their checkpoints, performed 13 distinct GET-only HTTP checks per audit pass, and ran 231 backend plus 176 frontend targeted tests. Two live astronomy tests were deliberately deselected; the additional temporal-ranking selection deselected 27 unrelated tests. No test was silently skipped.

| Finding | Status | Evidence boundary |
|---|---|---|
| NASA file identity and recorded source continuity | PASS | Local bytes match pinned identities; publisher authenticity not certified |
| Coordinates, units, UTC and fixed operation inputs | PASS | Static inspection, analytical tests and actual persisted inputs |
| Local and temporal finite-set results | PASS_WITH_LIMITATIONS | Prior real results revalidated; no new live optimization |
| Frontend contracts and incomplete-candidate handling | PASS | Current-main adapter/component regressions |
| Durable job/checkpoint integrity and HTTP retrieval | PASS | Actual stored jobs plus isolated lifecycle tests |
| Performance accounting | PASS_WITH_LIMITATIONS | Historical measured work reconciled; no new speedup benchmark |
| Independent astronomy / absolute DEM registration | PASS_WITH_LIMITATIONS | Open scientific gates retained, not relabelled PASS |
| Fresh real NASA POST-to-completion run | NOT_RETESTED | Earlier E2E evidence retained intentionally |
| Fresh rendered WebGL / server-down browser demonstration | NOT_RETESTED | Prior headless Chromium evidence reviewed; current targeted tests only |

## 2. Repository / Commit Identity

- Audit base: `ca26fba597b7622e2c1aba01fb6cfb280bad3d91`, fetched from `origin/main`.
- Main contains PR #32 through `64421cba669c7573b8a9877b3f87cbeed1d04a97` and PR #33 through the audit base. Git merge history was checked.
- Audit branch: `audit/command-13-scientific-validation`; initial worktree clean.
- Inputs: `SCIENTIFIC_JOB_API.md`, `INTEGRATION_HANDOFF.md`, `LOCAL_JURY_DEMO.md`, `SCIENTIFIC_VALIDATION_COMMAND_10.md`, `LOCAL_SITE_OPTIMIZER_VALIDATION.md`, `TEMPORAL_SEARCH_VALIDATION.md`, current backend models/runner/store and frontend Scientific Backend/Alternative Explorer adapters/tests.
- Principal historical input: [`nasa-live-optimizer-demo-readiness.json`](../data_pipeline/evidence/nasa-live-optimizer-demo-readiness.json). Its checksum is recorded in the new audit evidence.
- New read-only measurements: [`command-13-readonly-audit.json`](../data_pipeline/evidence/command-13-readonly-audit.json).
- No frontend, backend production code, shared contract or root configuration edits. The audit report lives under backend-owned documentation.

## 3. NASA Source Integrity

**PASS_WITH_LIMITATIONS.** `read_index()` freshly verified all five expected filenames, SHA-256 values and SPICE architecture/type headers against the configured index. Their identities also matched the historical optimizer evidence:

| File | SHA-256 |
|---|---|
| de421.bsp | `08b20db2ae22488650641c5a9033e5bfda4b1c4b440cfeaf20f621cfa18ecdb3` |
| moon_pa_de421_1900-2050.bpc | `656f90616403d75a75f0cd6c8830fc5b44f8cb4facb5ccb8915e752b397520cf` |
| moon_080317.tf | `78732477b96f9863e7b0d65bcee3c22b8707ca5ed0db56d1173319cb2e8c7993` |
| naif0012.tls | `678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b` |
| pck00011.tpc | `3dff7b1dbeceaa01f25467767d3fa25816051c85d162d1edf04acb310ee28bb1` |

The actual default loader, `data_pipeline.horizon_cli.terrain_session`, selects Site01 surface plus Product90 **80 m** from `NASA_LOLA_VALIDATION_DIR`, with Site01 `toterr` and `ldec`. It does not substitute an optional 20 m asset based on a similarly named environment variable. All four pinned raster hashes were rechecked; full identities, sizes, WKT and bounds are in the audit JSON.

| Raster | Dimensions | Resolution | NoData | CR1 containing-cell value |
|---|---:|---:|---|---:|
| Site01 surface | 3200 × 3200 | 5 m | NaN | 1942.1014404296875 m |
| Site01 toterr | 3200 × 3200 | 5 m | NaN | 0.22997184097766876 m |
| Site01 ldec | 3200 × 3200 | 5 m | NaN | 0 count |
| Product90 elevation | 7600 × 7600 | 80 m | NaN | 1942.8433837890625 m |

All four sampled cells are valid. A valid zero count is not NoData and is not an accuracy certificate. Both elevation rasters use south polar stereographic coordinates on the 1737400 m sphere. This audit checked metadata/bounds and CR1 cells, **not every pixel's validity**. Earlier coverage/overlap diagnostics remain recorded evidence. No new 20 m inspection or substitution was performed.

Hashes prove byte identity relative to the pinned/user-supplied manifests, not independently published NASA checksums, absolute geodetic accuracy or a product release version. Source versions remain explicitly unspecified where unavailable. Quality-layer hashes survive in each candidate window's source provenance; no missing quality product is inferred from a manifest name alone.

## 4. Geometry / Coordinate / Time Validation

**PASS_WITH_LIMITATIONS.** `geometry.py`, `astronomy.py`, `data/observer.py`, window requests and retained candidate records agree on planetocentric latitude, east-positive longitude, `MOON_ME_DE421`, radial local Up and a 1737400 m lunar reference sphere. Backend azimuth is clockwise from north. `observer_position_km()` adds DEM surface elevation and device height in metres before conversion to kilometres; device heights remain 1 m in the audited jobs. No offset was introduced to make reference comparisons agree.

The audited windows retain `correction=NONE`, 64 disk samples, hourly temporal sampling, explicit PROTOTYPE terrain registration and `PROTOTYPE_SAMPLED_ESTIMATE`. Geometric NONE is not apparent Horizons geometry. UTC alternatives retain exact start/end timestamps and 3600-second duration. Analytical tests cover metres/kilometres, axis orientation, azimuth wrap, invalid heights/coordinates and synthetic time conversion. Fresh NASA position calculation and kernel coverage propagation were NOT_RETESTED.

**Independent validation remains open.** The existing `command-10-horizons-reference.json` has 17 exact common timestamps, **zero equivalent matched samples**, and `CONFIGURATION_MISMATCH`. The altitude-aligned LT+S diagnostic has the following historical residuals; these are not a newly passed reference tolerance:

| Diagnostic angle | Maximum absolute residual, degrees | RMS, degrees |
|---|---:|---:|
| Sun azimuth | 0.000003284645 | 0.000002871540 |
| Sun elevation | 0.000010926081 | 0.000007135269 |
| Earth azimuth | 0.000004122761 | 0.000003497776 |
| Earth elevation | 0.000011139784 | 0.000010016780 |

Reference-aligned altitude is diagnostic only; apparent correction/deflection equivalence remains unresolved. The Nov 23 17:26:15 and Nov 27 02:00 reference timestamps were absent and rejected, not rounded to neighbours. Rechecked derived-artifact tests preserve these distinctions. This is not independent observational or DEM absolute-registration proof. **DEM_ABSOLUTE_REGISTRATION: UNVERIFIED.**

## 5. Local Optimizer Scientific Audit

**PASS_WITH_LIMITATIONS.** The actual persisted one-hour CR1 Local8 result validates as `LocalSiteOptimizationResult`. Its input is radius 1000 m, min_sun_visible_s=600, Solar profile, fixed 2026-11-20 08:00 UTC and unchanged heights/requirements/policy. It contains 32 generated positions including baseline, 21 terrain-eligible, 32 known slopes, eight detailed entries: six MET and two NOT_MET. Eleven candidates were screened out and 13 remained resource-limited/uncomputed. Job status remains PARTIAL; this is not a global optimum claim.

For every completed candidate, exact input preservation, operation evidence SHA, source equality, score version and recorded metrics were checked. Every resource-limited candidate has no operation and no fabricated metrics. Recommendations are completed MET candidates; a high NOT_MET score cannot override mandatory rules.

The preserved nearby candidate is **−89.43734917039663°, 222.8374650555442° E**, distance **931.9756666408481 m**, bearing **4.351316121645229°**, slope **1.207912395153901°**, prototype **MET / 100**. Its baseline remains NOT_MET / 0. The result is one-hour evidence, not six-hour evidence.

`SLOPE_UNKNOWN`, `SCIENTIFICALLY_INCOMPLETE` and `ELIGIBLE_FOR_DETAIL` are accepted local statuses after PR #33. Unknown slope remains null. Operation diagnostics attached to a non-detailed local candidate stay in raw evidence but do not project a score, decision, metrics or A/B eligibility. A detailed operation still must be COMPLETED. Existing targeted tests cover stale MET/100 diagnostics and invalid recommendation rejection. Actual Local8 did not encounter unknown slopes; those branches were tested with explicit fixtures, not claimed as observed NASA events.

Radar uses supplied distance/bearing; globe uses the same candidate latitude and east-longitude-to-visual conversion; selection and A/B share candidate IDs. Coordinate/wrap, component selection and comparison tests passed. Fresh browser rendering was NOT_RETESTED; the earlier real radar/globe/A-B PASS remains historical evidence.

## 6. Temporal Optimizer Scientific Audit

**PASS_WITH_LIMITATIONS.** The actual one-hour result validates as `TemporalBatchResult` v2: 27 alternatives discovered, baseline plus three alternatives detailed, two MET and two NOT_MET, 24 alternatives uncomputed. The job remains PARTIAL. The two MET / 100 timestamps are **2026-11-23T20:00:00Z** and **2026-11-27T02:00:00Z**, with end times exactly one hour later.

All completed candidate requests match baseline except start UTC; coordinates, duration, explicitly supplied min_sun_visible_s=600, source provenance, correction, model version and policy remain fixed. Window hashes were recomputed from persisted window objects without recomputing science. Unevaluated entries have null operation and empty metrics, not NOT_MET/0.

Comparison guards bind scenario, search dimension, explicit requirement fields, scientific configuration and source/score identity. The one-hour live scenario cannot be compared to the six-hour recorded export. The old canonical six-hour run completed 30 alternatives plus baseline in Command 10; that is a different experiment, not evidence that this live one-hour search is complete. Neither was rerun.

## 7. Frontend–Backend Contract Audit

**PASS.** Current main preserves the PR #32 resume controls and PR #33 local-stage fix. Reviewed paths include `alternative-explorer/live.ts`, `requests.ts`, `evidence.ts`, `Comparison.tsx`, `Radar.tsx`, `EvidenceWorkspace.tsx`, `scientific-jobs/useScientificJob.ts`, `services/api/jobs.ts`, and `analysis-results/resultContext.ts`.

- Live optimizer inputs require a completed matching analysis and backend-produced `window_evidence.request`; no frontend reconstruction of astronomy.
- AnalysisResult 1.0, temporal v2 and local v1 are distinct schemas. Persisted results passed their actual Pydantic models; advertised `/result-schemas` was retrievable.
- Completed prototype analysis uses a separate trust path from fully ready science. `science_ready=false` is retained.
- Nulls, missing horizons/series, incomplete terrain, partial execution and null scores remain explicit. Historical optimizer summaries do not manufacture AnalysisResult or full horizons.
- A/B requires compatible scenario, dimension, source, scientific settings, explicit requirements and score version. One-hour and six-hour scenarios remain separate.
- Resume Saved Analysis / Optimizer preserves request identity; retry reconnects to the same job, not a fresh POST. Network failure reports disconnected/unknown execution, never simulated progress.
- The Recorded Evidence package is checksum-valid and separately served by the frontend; it needs no NASA binary or backend. The stopped-backend browser PASS is historical; current evidence/component tests passed. The Scientific Backend recorded HTTP mode still needs a backend and is a different feature.

No new request/response incompatibility was reproduced in the audited paths. General arbitrary-payload fuzzing and an exhaustive browser/platform matrix were not performed.

## 8. Checkpoint and Job Integrity

**PASS_WITH_LIMITATIONS.** The private SQLite database was opened in read-only mode; integrity_check returned `ok`. It contained no queued/running/cancel-requested jobs during inspection. For the original live analysis, its checkpoint replay, Local4, Local8 and Temporal4, request identity and stored result SHA were recomputed and matched. All checkpoint payload hashes for those jobs matched, including candidate-specific window SHA values. Candidate sources matched freshly checked kernels/DEM; checkpoints were inspected, not replayed into new jobs.

| Persisted job role | State | Candidate / UTC / grid checkpoints validated |
|---|---|---|
| Original analysis | COMPLETED | 1 / 2 / 1 |
| Checkpoint analysis replay | COMPLETED | 1 / 2 / 1 |
| Local4 | PARTIAL | 4 / 8 / 0 |
| Local8 | PARTIAL | 8 / 16 / 0 |
| Temporal4 | PARTIAL | 4 / 8 / 0 |

The running loopback API returned HTTP 200 for health, capabilities, result schemas and status/result for each of the five jobs: **13 GET checks**. Each HTTP result equalled the persisted JSON. Capability reported one worker and bounded live prototype support; readiness remained false. No acceptance/POST was fabricated.

Isolated actual-FastAPI tests use explicitly synthetic runners and temporary databases to test 202 admission, polling/results, missing jobs, queue limits, resume mismatch, cancellation and errors. JobStore/Manager tests exercise atomic result/checkpoint hashes, corruption, storage bounds, ownership, interruption/restart and safe cancellation. These are infrastructure tests, not fresh NASA lifecycle experiments.

Resume detail matters: missing checkpoint ID gives 404; wrong type/nonterminal state or changed scientific request gives 409. A valid resume may extend allowed admission/resources. **If source signatures change or a UTC checkpoint is missing, the old key cannot match and an accepted job can perform fresh bounded computation.** The service does not promise replay-only resume. A request mismatch is rejected rather than silently resubmitted. Source validation failure does not become old-source success. Retained cost is charged once per recovered key; lookup count can exceed unique UTC count.

POSIX `fcntl.flock` owns one worker per database; SQLite WAL/FULL commits results durably. Completed evidence survives restart; lost RUNNING/CANCEL_REQUESTED becomes INTERRUPTED; QUEUED remains durable. CANCELLED, FAILED, PARTIAL and INTERRUPTED are distinct. This audit did not disrupt the running real server to repeat historical restart/cancel tests.

## 9. Performance and Resource Accounting

**PASS_WITH_LIMITATIONS.** Times below were recomputed from persisted started/finished timestamps and agree with the historical report. They are **historical job wall times**, not new Command 13 benchmarks and not interchangeable with internal pipeline timing.

| Workload | Historical wall seconds | New visibility evaluations | New completed rays | UTC checkpoint lookups |
|---|---:|---:|---:|---:|
| Original live CR1 analysis | 157.535888 | Original separate run | Original separate run | Original separate run |
| Analysis checkpoint replay | 1.677330 | 0 | 0 | 2 |
| Local4 | 124.380617 | 4 | 520 | 4 |
| Local8 extension | 253.237059 | 8 | 1040 | 8 |
| Temporal4 | 243.982708 | 8 | 1040 | 0 |
| Extension/replay totals | Not a single benchmark | **20** | **2600** | **14** |

Historical new terrain positions sum to **1,157,760**, cache hits **0**, misses **2600**. The original analysis/local run is not charged again into the new-work totals. Checkpoint lookup is not unique UTC or new astronomical evaluation; grid reuse is a separate artifact. Zero exact-ray hits is compatible with different exact azimuths and does not prove cache failure. Cheap checkpoint replay cannot be advertised as a same-work scientific-computation speedup.

Local and Temporal process different coordinate/time sets and retained evidence; their wall times are not a controlled A/B performance comparison. No new RSS, source-validation speed, whole-grid speedup or maximum-load benchmark was measured. Historical peak-RSS measurements in other experiments are not reassigned to these jobs.

Frontend optimizer wall options 300/900 s fit the backend 3600 s maximum and frontend admission validator's 900 s ceiling. Other default frontend limits (24 visibility calls, 5000 rays, 3,000,000 terrain positions, 2048 cache entries) fit backend maxima (256, 50000, 20,000,000, 4096). Local detailed budget caps at eight including baseline. Wall limits are cooperative; one bounded call can overrun the nominal deadline. Browser per-call timeout is 10 s, polling normally 1.5 s, with backoff and a 60-minute waiting limit; none is a physical computation timer.

Queue/storage: four active jobs, 64 retained jobs, 128 KiB request body, 8 MiB result/individual checkpoint and 16 MiB checkpoint aggregate per job. These bound payloads, not total OS memory or exact SQLite/WAL disk consumption. No hard process RSS limit is implemented. Operator disk retention, supervision and local-only access remain necessary. Duplicate explicit submissions create new jobs; bounded admission mitigates but does not replace authentication/rate limiting for public deployment.

## 10. Recorded vs Live Evidence Separation

**PASS.** The original analysis is LIVE_COMPUTED; its matching replay is PRECOMPUTED with zero new engine work. Optimizer job-level live origin can coexist with checkpoint-backed candidates. Temporal candidate origin/accounting uses per-candidate counter deltas, and existing live/recorded/mixed tests pass. Local output retains job-level new/retained counters; it does not invent a per-candidate live field absent from its schema.

`RECORDED_EVIDENCE_EXPORT` is the portable demo projection, not a new calculation or full optimizer/AnalysisResult response. `REAL_NASA_PROTOTYPE` describes the scientific source layer. `TEST_FIXTURE` labels synthetic infrastructure tests. These labels describe different layers and must not be collapsed into one “live” badge.

Demo manifest byte counts, output hashes and source evidence hashes all matched. Historical raw inputs remain unchanged. Execution COMPLETED can contain a NOT_MET or INCOMPLETE decision; PARTIAL can contain valid completed MET candidates. Planning Suitability Index remains `24and28-planning-score-v1`, not success probability.

## 11. Known Scientific Limitations

**PASS_WITH_LIMITATIONS** for accurate disclosure; the underlying independent scientific gates remain open:

- Absolute product-specific horizontal/vertical registration is UNVERIFIED; overlap/projection compatibility is not absolute accuracy.
- Horizons diagnostics are not fully configuration-equivalent or observational certification.
- Hourly time sampling and 64 disk samples can miss short interruptions/narrow obstacles; no certified continuous duration follows. STRICT refuses unsupported duration certification.
- Interpolated horizon grids are coarse screening evidence; exact scheduled nodes do not prove all intermediate azimuths. No new grid benchmark was run.
- Source-grid slopes and 80 m far terrain do not certify small hazards or landing safety; 20 m remains optional, inactive.
- Local32/8 and Temporal27/4 represent finite partial searches, not global optima.
- Geometric solar visibility is not electrical power; Earth clearance is not an RF link guarantee.
- A local single-host worker stops with the server. Native Windows, public multi-tenant deployment, independent resource isolation and unattended retention are not certified.

## 12. Bugs and Severity Classification

No new reproducible **CRITICAL** or **HIGH** software defect was found within the executed scope; therefore no production patch was justified. This is not a claim that untested paths cannot contain defects.

| Item | Severity / status | Disposition |
|---|---|---|
| Missing local candidate states / unsafe incomplete diagnostics | Historical HIGH / PASS | PR #33 merged; current targeted regressions passed |
| Checkpoint reuse mistaken for new work or unique UTCs | Audit risk MEDIUM / PASS | Counters reconciled; lookup semantics documented |
| Independent DEM/Horizons certification absent | Scientific limitation / PASS_WITH_LIMITATIONS | Remains explicitly open; no tolerance or model changed |
| Native Windows/public deployment assumptions | Deployment limitation MEDIUM / PASS_WITH_LIMITATIONS | Linux/WSL2 local prototype only; no public-readiness claim |
| Test tooling deprecations | LOW / PASS_WITH_LIMITATIONS | Starlette/httpx and Vite native-config import warnings; tests pass; no unrelated dependency change |

Earlier 603/674 test counts and intermediate Command 10 partial results in historical documents are not current-run results. Their later closure sections and this audit establish the applicable scope. No old test count is reused as fresh validation.

## 13. Verified Tests and Evidence

Fresh targeted results:

| Check | Result | Scope |
|---|---|---|
| Backend jobs/API/closure/recorded/local-grid/demo/Horizons/operations/scoring | 170 passed, 0 failed, 0 skipped; 6.28 s | Nine selected files; synthetic and recorded evidence |
| Backend geometry/cache/resource/origin | 51 passed, 0 failed, 0 skipped; 2.32 s | Two live NASA tests explicitly deselected |
| Backend temporal decision-first / comparison / override / policy outcomes | 10 passed, 0 failed, 0 skipped; 0.07 s | 27 unrelated tests deselected |
| Frontend contracts, jobs, local states, A/B, panels, coordinates | 176 passed, 0 failed; nine files; 11.54 s | Existing targeted suite, current main |
| TypeScript typecheck | PASS | `npm run typecheck` |
| Python dependency consistency | PASS | `python -m pip check`; no broken requirements |
| Diff whitespace / finite JSON / audit overwrite refusal | PASS | Checked before commit |
| Source hashes, metadata, persisted records, GET-only HTTP | PASS | New audit JSON and reproducible script |
| Demo manifest integrity | PASS | No backend required to parse the package |
| Full backend/frontend suite | NOT_RETESTED | Intentionally out of this bounded audit scope |
| New real NASA E2E / fresh browser rendering | NOT_RETESTED | Prior live evidence, no new computation |
| GitHub CI | NOT_RETESTED | No CI success claimed |

No new production behavior required a new unit regression. The added audit script provides fail-fast assertions over the real retained artifacts, rather than creating new synthetic scientific outputs.

Reproduction from repository root, with existing dependencies and operator-configured NASA environment (never put private paths into Git):

```bash
export PYTHONPATH=backend:.
python data_pipeline/command13_readonly_audit.py \
  --job-db "$LUNAR_JOB_DB" --api-url http://127.0.0.1:8010 \
  --output /tmp/command13-audit.json
python -m pytest -q backend/tests/test_jobs.py backend/tests/test_job_api.py \
  backend/tests/test_command10_closure.py backend/tests/test_real_command10_closure.py \
  backend/tests/test_local_and_grid.py backend/tests/test_demo_evidence.py \
  backend/tests/test_horizons_reference.py backend/tests/test_operations.py backend/tests/test_scoring.py
python -m pytest -q backend/tests/test_astronomy.py backend/tests/test_windows_cache_origin.py \
  backend/tests/test_visibility_budget.py \
  -k 'not test_real_spice_sun_earth_and_reference and not test_real_libration_continuity_parallax_and_coverage'
python -m pytest -q backend/tests/test_temporal_optimizer.py \
  -k 'ranking_mandatory_first or comparison_rejects_non_equivalent_evidence or requirement_override_7200_preserved or outcomes'
cd frontend
npx vitest run src/features/alternative-explorer/local-status.test.tsx \
  src/features/alternative-explorer/evidence.test.ts src/features/alternative-explorer/jobs.test.tsx \
  src/features/alternative-explorer/transfer.test.tsx src/features/scientific-jobs/useScientificJob.test.tsx \
  src/services/api/jobs.test.ts src/features/analysis-results/validation.test.ts \
  src/features/analysis-results/Panels.test.tsx src/visualization/coordinates/lunarCoordinates.test.ts
npm run typecheck
```

The audit script needs the original private retained jobs and a running loopback server. Missing artifacts cause failure, not fixture substitution or automatic job creation. It opens SQLite read-only, uses GET only, refuses output overwrite and emits no private paths. Source reads/checksums are not visibility calculations. Run with assertions enabled (ordinary Python, not `-O`). Audit JSON includes historical job timing explicitly labelled as historical.

## 14. KOMUT 14 Readiness Decision

**COMMAND_13_COMPLETE_WITH_LIMITATIONS.** The existing local jury prototype is ready for the next delivery review using the documented bounded NASA/job and offline Recorded Evidence flows. This decision does not certify physical mission safety, absolute DEM registration, all-coordinate source coverage, exhaustive optimization or public production deployment.

KOMUT 14 was **not started**. No scientific gaps were hidden or “fixed” by changing algorithms, scores, status codes or fixtures. The audit is submitted for review on a separate branch and must not be automatically merged.
