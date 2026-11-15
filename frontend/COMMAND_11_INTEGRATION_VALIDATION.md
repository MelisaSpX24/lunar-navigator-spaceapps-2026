# Command 11 — scientific API integration validation

## 1. Executive summary
Frontend-only integration with backend PR #28. Strict scientific readiness remains separate from bounded research availability. No science solver, optimizer interface, fixture fallback, deployment or backend modification was introduced. Backend merge and combined-main regression remain pending.

## 2. Frontend base main SHA
`d7a30a769458feb9a68ae53dcd3e095b09cfe70f`, merge of PR #27. Branch: `frontend/command-11-scientific-integration`.

## 3. Backend PR #28 starting SHA
`2d2211831b19ca0a380892d88202e20a35e6e1ef`. Inspected through the remote ref and an isolated `/tmp/lunar-backend28` archive; never merged or cherry-picked into this branch.

## 4. Backend PR #28 final SHA
Final fetch on 2026-11-15: `2d2211831b19ca0a380892d88202e20a35e6e1ef`, unchanged. No route/model/envelope/capability/schema drift. Main also remains at the base SHA. GraphQL PR metadata is inaccessible (`Forbidden`); git refs remain available. PR #28 is not in the inspected main history.

## 5. API contract matrix
| Method / endpoint | Frontend handling |
|---|---|
| GET `/api/v1/health` | Existing strict readiness behavior preserved |
| GET `/api/v1/capabilities` | Runtime-checked availability, limits, reasons; 404 means integration unavailable |
| POST `/api/v1/analyses` | Existing strict request, or explicitly selected `mode=recorded` |
| POST `/api/v1/analyses/jobs` | Typed, bounded research request; HTTP 202 acceptance |
| GET `/api/v1/jobs/{id}` | Validated job state and identity |
| GET `/api/v1/jobs/{id}/result` | Validated terminal envelope; complete analysis only from `result.analysis` |
| POST `/api/v1/jobs/{id}/cancel` | Cooperative cancellation; never DELETE |
| GET `/api/v1/result-schemas`, `/openapi.json` | Inspected from real isolated backend for contract evidence |
| Temporal / local optimization endpoints | No requests or new UI in Command 11 |

Backend-local source models: `app/models/analysis.py`, `app/services/models.py`, `app/jobs/models.py`, `app/api/routes.py`; handoff, job API and validation documents. These TypeScript types are not an independently approved shared contract.

## 6. Health and capabilities
One initial check per mounted provider, including StrictMode's discarded setup. Explicit recheck, no capability polling. Reachability, worker availability, configured files, bounded prototype support and independent validation are separate facts. Files existing is not proof of hash/metadata validation or all-site/time coverage.

## 7. Research prototype admission
“Run Research Prototype” requires a valid form, explicitly activated operation requirement, validated capability support, no strict submission, and no unresolved active job. Live additionally requires the configured source/worker flags. Strict “Run Analysis” still requires health readiness. No catalog coordinate gate was relaxed.

## 8. 202 job submission
`AnalysisJobRequest`: existing builder's coordinate/frame/heights/time/options, `PROTOTYPE_SAMPLED_ESTIMATE`, `PROTOTYPE`, step 3600 s, 64 disk samples. Server-owned ResourcePolicy defaults: 900 s cooperative wall admission, 24 visibility evaluations, 5000 rays, 3000000 terrain samples, 2048 cache entries. These may produce PARTIAL, not guaranteed completion. No arbitrary client file paths. A 202 means queued, never scientific completion.

## 9. Request identity
Retain the exact submitted wire request, expanded form snapshot, accepted job ID and opaque server request identity. Validate that all subsequent status messages have the same ID/type/identity. Never invent the backend's hash algorithm. Server URLs must exactly match canonical `/api/v1/jobs/{32-lowercase-hex-id}` paths with the correct suffix. Hosts, protocol-relative paths, queries, fragments, traversal, encoding and wrong IDs are rejected. Fetch reconstructs known API paths instead of following arbitrary returned URLs.

## 10. Job status polling
QUEUED, RUNNING, COMPLETED, PARTIAL, FAILED, CANCEL_REQUESTED, CANCELLED and INTERRUPTED remain distinct. Serialized 1500 ms polls, no overlap. Display only returned stages/counts/percent; null percent stays unknown. Reject terminal-state regression and RUNNING/CANCEL_REQUESTED regression to earlier states. Polling remains owned by ScenarioProvider across in-app routes.

## 11. Job cancellation
Stop Waiting aborts local HTTP/timers only, preserving the job ID; server computation may continue. Request Cancellation sends the documented POST. CANCEL_REQUESTED is not CANCELLED; continue polling until a terminal response. Terminal partial evidence is retained but not fed into complete-result panels.

## 12. Reconnect
Reconnect reads the same job, without automatically re-POSTing. INTERRUPTED remains visible. Explicit resume is offered for a terminal non-COMPLETED live job with the unchanged request; the backend owns checkpoint/source verification. Page reload persistence is not added; a full reload loses the in-memory job reference. No claim that the worker runs during server shutdown.

## 13. Result envelope
Require matching job ID/type, terminal envelope state matching the validated status and an object `result`. Only COMPLETED + a runtime-valid AnalysisResult 1.0 + execution COMPLETED + matching current/submitted/echoed scenario enters scientific panels. PARTIAL/FAILED/CANCELLED/INTERRUPTED never become complete science. Retain `window_evidence` and other result metadata as untrusted, read-only evidence for later adapters; no optimizer configuration is executed.

## 14. Pydantic request normalization
The form builder remains unchanged. Research wire serialization sends only requirement keys the user explicitly edited; untouched defaults are omitted, blank optional edited values remain null, 0/false remain explicit. Full form and sparse wire snapshots are separate. Documented Pydantic defaults may be expanded for semantic response matching, never coercing explicit values or removing unknown fields. Timestamp comparison accepts equivalent UTC zero-offset spelling. Original submitted key presence is retained for backend `fields_set`/resume identity. A source-compatible Pydantic cross-check verifies this distinction.

## 15. Strict vs prototype readiness
The original `completedResult` strict gate remains intact. `completedPrototypeResult` is a separate trust path for validated research completion; global science_ready=false does not erase a properly matched prototype response. A new/failed/in-progress research request cannot fall back to an old strict result. Input edits/reset abort local operations and invalidate evidence; the backend job is not silently cancelled.

## 16. Source provenance
LIVE_COMPUTED, PRECOMPUTED, TEST_FIXTURE and null remain distinct. Existing source/quality validators and safe source URL rendering remain in use. `UNSPECIFIED_HASH_PINNED` is displayed verbatim. Checksums and official data do not independently certify source authenticity, absolute registration or NASA endorsement.

## 17. Recorded vs live
Recorded is explicitly selected, never an automatic live fallback. Uses POST `/analyses?mode=recorded&registration=PROTOTYPE&evaluation_policy=PROTOTYPE_SAMPLED_ESTIMATE&step_s=3600`; response must be HTTP 200, COMPLETED, PRECOMPUTED and match the submitted scenario. The backend owns exact scientific configuration matching and operation evaluation; frontend never swaps another record or changes user inputs on a 404.

Backend-owned historical window records: CR1 −89.468°, 222.6° E, six hours, 2026-11-20T08:00:00Z or 2026-11-23T17:26:15Z; MOON_ME_DE421 planetocentric, 1 m Sun/Earth device heights, PROTOTYPE, 64 disk samples, 3600 s step, NONE correction in the backend window template, solar fraction .5 and Earth margin 0. `include_full_horizon=false` is required; other frontend options use documented defaults. Tests explicitly set a 600 s minimum Sun requirement. This is a user/example operation assumption, not a NASA limit. Backend reevaluates the requested operation against the matching stored window evidence. No catalog transfer is enabled by this example.

## 18. Local Horizon data
Existing runtime horizon checks and 2D/3D presentation consume the validated response without a new terrain solver. Full live profiles can be supplied by backend; recorded results have horizons=null. The real recorded browser flow therefore shows celestial samples and orientation guides, explicitly no measured terrain horizon. No flat/clear terrain is inferred.

## 19. Sun/Earth integration
Existing body validation, ENU/render conversion, null/UNKNOWN separation, horizon-ID warnings and illustrative marker scale remain unchanged. Complete matched results feed the existing 3D celestial layer and accessible full series. Sun geometry is not electricity; Earth geometry is not an RF link guarantee.

## 20. Timeline
One existing UTC selection, exact samples, guarded visual interpolation, discrete paths and Play/Pause/Replay remain in use. Windows preserve null versus empty, censored boundaries and [start,end). Selection/playback creates no new API/DEM calls or scientific events.

## 21. Operation assessment
Backend MET/NOT_MET/INCOMPLETE and required/actual/message are displayed by existing checked panels. No unit is guessed, rule or safety decision recomputed. Sampled evidence is not continuous physical certification.

## 22. Planning score
Backend score only. null is not 0; 100 is not a probability of success or safety certification. Existing model-version/component/quality checks remain. Score and quality regions reference the accessible prototype limitation notice.

## 23. Data quality
Existing coverage, source metadata, reason codes and limitations are preserved. LIMITED/INSUFFICIENT/NOT_ASSESSED warnings remain visible. One prototype notice is linked from score/quality, avoiding repeated long notices on every panel.

## 24. Scientific limitations
Absolute terrain registration, independent astronomical/observational validation, source authenticity, continuous physical event boundaries, power production and RF performance are not established. No live NASA kernel/raster computation was possible in this workspace. Recorded backend evidence is not a new independent scientific experiment.

## 25. API errors
Preserve HTTP statuses and typed 422 issues. Typed-job `body.analysis.*` issues map to existing form errors; other messages are safe React text. 404 (old backend/recorded mismatch/unknown job), 409, 413, 422, 429, 500, 502/504 and 503 are never promoted to results. Malformed JSON, unsupported schema, invalid progress/IDs/URLs and mismatched results are rejected. Connection loss means unknown server execution, not FAILED.

## 26. Timeout and polling
10 s timeout per HTTP call, not a whole-job 30 s deadline. Three automatic backoff retries at 1.5/3/6 seconds for transport/502/504 problems, then explicit reconnect. Successful ongoing polling has a 60 minute local waiting limit, after which the user must explicitly reconnect. No automatic new POST or infinite retry. Sequence guards reject late responses even if abort is ignored. Provider unmount aborts controllers/timers; route navigation preserves the single provider. A submission timeout before an accepted ID leaves backend execution unknown and cannot reconstruct an unknown job ID.

## 27. Frontend unit tests
PASS: **429/429 Vitest**, 28 files, no skips. New coverage includes capabilities, unsafe URLs, IDs, all job states, normalization/key presence, independent readiness/completion gates, duplicate submission, stale/aborted work, long jobs, stop/reconnect, bounded backoff, cancellation, recorded 404/no fallback per-request timeout and explicit terminal-job resume binding a new job ID/identity without duplicate POST or changed scientific inputs. Baseline 391 passed.

## 28. Playwright
PASS: **215/215 Playwright**, no failures or skips, 5.4 minutes, all three viewport projects. Baseline initially 202/203: one existing playback clock test attempted to pause its installed clock in the past. It now installs and pauses at an explicit fixed future offset; assertions are unchanged. New job tests cover all three viewport projects, the seven panels, partial/failed states, navigation, cancellation and 200% text. Earlier runs exposed six expected test-harness mismatches: the new capabilities GET was classified as a scientific request or returned an unmocked preview 404. Controlled availability is now provided to isolated globe/navigation tests; navigation explicitly checks exactly one capabilities GET and still forbids analysis/DEM requests. No error or scientific assertion was suppressed.

## 29. Real backend HTTP tests
Unmodified isolated backend started with the existing venv, PYTHONDONTWRITEBYTECODE=1, one worker, LUNAR_ENABLE_JOBS=1, and SQLite under `/tmp/lunar-command11-jobs`. Real health/capabilities/result-schemas/OpenAPI: 200; live typed job: 503 SCIENCE_SOURCES_NOT_CONFIGURED; malformed job: 422; unknown ID: 404. Explicit exact recorded request: 200 PRECOMPUTED/COMPLETED; changed date: 404. Real request/result validated using actual Pydantic models. Unmocked Chromium + Vite proxy completed recorded flow at all three viewports, no page errors. Controlled fixture job lifecycle is separately labelled test evidence.

## 30. NASA live test status
BLOCKED: trusted kernel/index/LOLA source files are not configured/present. Found pytest dummy kernel paths were not used. Real live 202/status/completed horizon computation NOT RUN. No REAL_NASA_E2E_PASS claim. The existing local NASA JPEG remains the visual globe asset, not a scientific DEM.

## 31. Screenshots
Ignored `.validation/command11-real-browser/` contains real recorded desktop/tablet/mobile analysis and local 3D views plus mobile 200% status. Playwright `test-results/scientific-jobs-*` contains queued/running/completed/partial/failed/offline/recorded mismatch captures. Images are actually opened during review; large logs/images are not committed.

## 32. Mobile/accessibility
1440×1000, 820×1180, 390×844 and mobile 200% text. Named controls, explicit mode label, visible text for status, live region changes only when job messages change, React text errors, wrapped IDs/reasons. Lengthy capability/settings metadata uses native keyboard-accessible disclosure controls; scientific limitations stay visible. Local WebGL/table fallback and existing touch interaction remain unchanged.

## 33. NASA texture regression
JPEG unchanged: SHA-256 `f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170`. Existing real Chromium texture loading, camera, raycasting, late material load and context-loss tests remain required. No new dependency or texture asset.

## 34. Backend file modification check
Only frontend/ changes are permitted/staged. Isolated backend archive and SQLite are outside the git worktree. No backend/main merge, cherry-pick or backend source mutation. Verify git diff --check and frontend-only paths before commit.

## 35. Known limitations
Backend PR merge and combined-main verification remain pending. No authentication/public deployment added. In-memory job references do not survive a full refresh. No arbitrary-job-ID entry UI. Resume explicitly reuses only the current terminal job/request with the same bounded resources; no resource-extension editor. Public runtime validators cover the consumed envelope/fields; retained optimizer metadata is still untrusted. Existing lazy Three renderer chunk exceeds Vite's 500 kB warning threshold. Final main JS: 382.97 kB / 120.03 kB gzip (baseline 361.58 / 113.89); increase 21.39 / 6.14 kB. Lazy renderer remains 918.47 / 242.64 kB; horizon 11.42 / 4.28; globe 29.41 / 8.06. No dependency/lockfile changes. Controlled fixture product names and test-only markers were checked absent from production JS.

## 36. Pending backend merge
Frontend PR must be Draft while backend PR #28 is not merged. After merge, fetch main and rerun full unit/browser suites against the combined code, actual configured-source capabilities, typed 202/poll/result, cancel/reconnect/restart/resume, recorded exact/mismatch and 3D/UTC/quality regressions. Check any backend API drift first. Do not call this production-ready before that review.

## 37. Command 12 readiness
Completed validated analysis envelope and immutable window_evidence metadata are retained for a future typed optimizer adapter. No temporal/local optimizer UI is implemented. Stop at Command 11.

## Final verification and changed files

Status: **COMMAND_11_INTEGRATION_VERIFIED_WITH_LIMITATIONS**, specifically unmocked PRECOMPUTED HTTP/browser integration; live NASA computation remains BLOCKED, backend merge pending.

PASS: npm ci (125 packages), typecheck, production build, 429 Vitest, 215 Playwright, six Pydantic model checks plus fields_set, real recorded HTTP/browser flow (3 viewports), mobile 200% text, frontend-only scope and git diff --check.

BLOCKED / NOT RUN: real live 202, live scientific polling/completion/cancellation/resume with configured NASA sources; independent NASA scientific validation; combined main after PR #28 merge. Mock job lifecycle checks are not a substitute.

Changed files (22; generated build/logs/screenshots excluded):

- `frontend/.env.example`
- `frontend/COMMAND_11_INTEGRATION_VALIDATION.md`
- `frontend/README.md`
- `frontend/e2e/celestial-motion.spec.ts`
- `frontend/e2e/globe.spec.ts`
- `frontend/e2e/navigation.spec.ts`
- `frontend/e2e/scientific-jobs.spec.ts`
- `frontend/scripts/check_real_backend.mjs`
- `frontend/scripts/validate_backend_contract.py`
- `frontend/src/features/analysis-results/resultContext.ts`
- `frontend/src/features/mission-input/analysisRequest.ts`
- `frontend/src/features/scenario/ScenarioProvider.test.tsx`
- `frontend/src/features/scenario/ScenarioProvider.tsx`
- `frontend/src/features/scientific-jobs/ScientificBackend.tsx`
- `frontend/src/features/scientific-jobs/useScientificJob.test.tsx`
- `frontend/src/features/scientific-jobs/useScientificJob.ts`
- `frontend/src/screens/MissionAnalysis.tsx`
- `frontend/src/screens/MissionSetup.tsx`
- `frontend/src/services/api/jobs.test.ts`
- `frontend/src/services/api/jobs.ts`
- `frontend/src/services/api/normalizedRequest.ts`
- `frontend/src/test/jobFixtures.ts`


## Final sync and closure — 2026-11-15

This section supersedes the earlier pending-backend-merge status without deleting
historical evidence. Backend PR #28 is merged. Current main:
`fa0561c42a59bd48a5290d6f261e5eaa92652413`, including backend development
`a8312e5916681ceb6adc98c2d18b201b2e4f32aa`.

Main was merged normally into the existing frontend branch, without conflict,
rebase or force push (sync commit `53f76426f24b013b9bd55604abd2a2a7d2d012c9`).
Previous frontend `3c3786f6cd2e50d11a4ae54d4b80ab3f44ee112b` remains an ancestor.
Final tested frontend source/test commit:
`5266084d868e9c90da3f1440fc77d8460086dc7d`. The subsequent closure commit changes
only this document; its delivery SHA is available in git history and the final report.

- API compatibility: PASS. Compared the old `2d221183` backend with `a8312e59`
  for routes, job/service models and the two handoff documents. AnalysisJobRequest,
  job status/envelopes and capabilities remain compatible. Added optimizer fields
  and optimizer resume/resource accounting are outside this frontend command.
- Production frontend changes: none. API, lifecycle, scientific gates, state,
  camera/texture, result panels and bundle output are unchanged.
- PARTIAL/null: PASS. Added only two missing lifecycle regressions: PARTIAL with
  analysis=null retains window_evidence without publishing completed science;
  COMPLETED with analysis=null is invalid. Updated the existing browser partial
  case to the current null-analysis shape. Existing tests cover valid completion,
  INCOMPLETE decisions, null scores, FAILED/CANCELLED/INTERRUPTED and identity mismatch.
- Targeted phase: 40/40 API/lifecycle tests passed.
- Final combined-main phase, one full run: TypeScript PASS; production build PASS;
  Vitest **431 passed / 0 failed / 0 skipped**, 28 files;
  Playwright **215 passed / 0 failed / 0 skipped**, 5.4 minutes.
  No npm ci was needed: installed dependencies were present and functional.
- Current merged backend HTTP smoke: PASS. Unmodified current worktree backend on
  loopback 8011, one worker, private SQLite outside the repository and bytecode
  writes disabled. Health/capabilities returned 200 with science_ready=false;
  configured_science_files_available=false and bounded_live_prototype_supported=false.
  One exact recorded request returned 200, COMPLETED, PRECOMPUTED. No full historical
  HTTP/browser rerun or heavy optimizer experiments were repeated. Six Pydantic
  model checks plus explicit requirement activation also passed against merged main.
- Real NASA live E2E: BLOCKED. Trusted kernel/LOLA files are not configured/available;
  no data downloads or dummy-source live success claims. Independent astronomy,
  absolute terrain registration, continuous visibility and mission safety/power/RF
  certification remain scientific limitations; they do not negate frontend test passes.
- Scope: PR diff against current origin/main is frontend-only. Backend/data_pipeline
  match current main exactly. No production refactor, new feature, merge to main or deployment.
- PR #29 delivery: branch commits were pushed. GitHub REST read and GraphQL
  description/Ready-for-Review actions return Forbidden. The prepared final PR body
  is `/tmp/lunar-command11-closure-pr.md`; remote description/review state could not
  be updated or verified. Git pull-request head ref can still verify code delivery.
- Final status: **COMMAND_11_FINAL_BLOCKED**, solely for the external GitHub PR
  description/Ready-for-Review management barrier. Frontend software checks and
  merged-backend compatibility are complete. No additional frontend development
  command is required. No automatic merge; stop before Command 12.
