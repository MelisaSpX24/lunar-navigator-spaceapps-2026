# Command 12 — Alternative Explorer validation

Validated on 2026-11-15. Branch: `frontend/command-12-alternative-explorer`.
Base: `6637325ebbd9962767b5633d685173c7e2d5c5af` (PR #30), including the merged
Command 11 frontend and backend PR #28. Only frontend files change.

## Recorded evidence and offline delivery

The source of truth remains the unchanged repository files
`data_pipeline/demo/{manifest,temporal_demo,local_demo}.json`. They are evidence
projections, not complete AnalysisResult or optimizer result envelopes.
`scripts/demoEvidence.ts`, installed in Vite configuration, checks manifest
version/origin/readiness, byte sizes, both payload hashes and both referenced
upstream evidence hashes before dev, test or build. Production validators also
check consumed payload fields. Missing, corrupted or unsupported source material
fails preparation; no substitute data is generated. Restart Vite after changing
upstream evidence: the virtual module is captured at configuration startup.

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| temporal_demo.json | 24846 | f4096ae772bc6cc6911dbc40bb76b5d7e58cbc248ad430b98c3fb159fa512f7d |
| local_demo.json | 43772 | 58fc021f8adab3c6ea6d5dbc04cc7a0748031cd87c578b054c42914c72e74bfa |
| command-10-closure.json | manifest reference | a0100f63ef267da6bf4a1957a27b297a9a238fa5fbac3ae78edec887bd869a5d |
| command-10-validation.json | manifest reference | db1bce59bfd6d40562ec2223b1deab112871b5c2edef830390a3e736f8a01f58 |

The verified JSON is embedded through `virtual:recorded-evidence`; no runtime
backend or external data request supplies it. Offline means a locally served
frontend with backend/internet unavailable, not an installable PWA or guaranteed
cold-start page loading without a web server. No duplicate maintained data file
or raster was added. Hash agreement proves repository integrity, not independent
scientific certification or NASA source authenticity.

Recorded delivery is explicitly `RECORDED_EVIDENCE_EXPORT`, original scientific
origin `REAL_NASA_PROTOTYPE`, with `science_ready=false`. It never unlocks live
readiness. Full analysis, horizon, time series and window segments in these
exports are null; no event times, charts or terrain are reconstructed from totals.

## Scenarios, selection and comparisons

`features/alternative-explorer/` owns consumed-field validation, candidate input
adaptation, typed live payloads and the presentation workspace. The screen has
independent scenario and recorded/live selectors. Temporal six-hour evidence
changes start UTC only. Local one-hour evidence changes coordinates and supplied
DEM surface context only. Comparability requires the same scenario, duration,
operation, requirements activation, source/method identity and scoring model;
temporal/local cross-comparison is rejected. Unknown/null is never zero or false.

Recorded temporal baseline is 2026-11-20T08:00:00Z, NOT_MET / 0; the selected
alternative is 2026-11-23T16:26:15Z, MET / 100. UTC shift is +3d 8h 26m 15s.
Recorded local baseline is CR1 (-89.468°, 222.6°E) for 3600 seconds; three supplied
alternatives have MET / 100. Both scenarios retain LIMITED quality. Comparisons
show supplied Sun/Earth/Joint sampled duration, longest continuous period,
interruptions, longest gap, unknown duration, mandatory-rule evidence and score
delta. Delta is presentation subtraction, never a new scientific score. Missing
model versions or invalid evidence withhold the corresponding comparison.

The north-up/east-right SVG radar uses supplied distance and clockwise bearing:
`x = distance * sin(bearing)`, `y = -distance * cos(bearing)`, scaled to a fixed
5000 m display. Rings are 1/3/5 km. It does not infer geodesic coordinates,
coverage, obstacles or an optimizer. Source radius and fixed display scale are
separate. A tiny numeric tolerance accommodates the supplied 5000.000000000037 m
candidate. Unknown positions are not plotted. Buttons, SVG hit targets, Enter,
Space, list selection and optional global globe share one selected candidate.

The existing lazy NASA globe is reused. White baseline, amber selected and cyan
other candidate octahedra have illustrative size, not region boundaries. Global
scale can overlap nearby markers; the radar/list remains the precise selection
interface. Focusing/selecting candidates leaves Mission Setup unchanged until
the explicit transfer action. The JPEG, global coordinate conversion and existing
camera/texture lifecycle are unchanged.

## Atomic candidate transfer

`candidateInput()` checks exact supported request fields and uses existing strict
UTC/form/request helpers. `ScenarioProvider.applyCandidateRequest()` atomically
replaces form inputs and the explicit requirements key set, invalidates prior
analysis/job evidence and records a visible loaded-candidate notice. It does not
submit a POST or silently cancel server computation. Manual edits/reset clear the
notice. Coordinates, UTC, duration, profile, observer/options and requirements
remain available to the normal Mission Setup workflow.

The local export explicitly supplies only `min_sun_visible_s=600`; omitted
requirements remain inactive even though form controls display backend defaults.
The temporal export preserves its seven explicit keys. Null, zero and false are
distinct. Sparse requests are expanded only with the existing backend defaults
where allowed; explicit requirement presence is never inferred from a default.
Unsupported subsecond transfer times, poles, 360° longitude and unknown fields
are rejected instead of silently altered.

## Live optimizer integration

Live mode requires validated current capabilities and a completed, matching live
ANALYSIS job whose result includes a valid `window_evidence.request`. Recorded
optimizer history is not a baseline/window-template substitute. The original
server template is retained, with submitted baseline request and explicit rules.

The existing `useScientificJob` controller now accepts a small optimizer extension
for TEMPORAL or LOCAL. Default ANALYSIS behavior remains guarded by job type.
There is one polling/cancel/reconnect/resume implementation, not a parallel job
system. POST routes are `/api/v1/optimizations/temporal` and
`/api/v1/optimizations/local`; typed accepted/status/result responses must match
job type and identity. Optimizer results are consumed from envelope `result`,
never `result.analysis`.

Temporal controls expose days, strategy and candidate budget; local controls
expose radius, selection strategy and candidate budget. Cooperative wall budgets
and actual nested resource/search fields follow the backend models. Temporal
screening is EXACT_ONLY. Runtime projection validates root schemas
`command-10-temporal-batch-v2` and `command-10-local-v1`, request equivalence after
documented Pydantic defaults, candidate identities and comparability evidence.
It preserves replay/new resource accounting and does not turn unevaluated
candidates into successful science. Backend recommendation filtering is visible
and can be disabled; the full supplied candidate set remains inspectable.

QUEUED/RUNNING, cancellation requested/cancelled, FAILED, INTERRUPTED, PARTIAL,
invalid schema, transport/validation failures and stale identities remain distinct.
PARTIAL evidence may be inspected but is not a completed analysis. Invalid live
responses never fall back to recorded data. Changing settings/scenario aborts
local waiting and invalidates obsolete projections. Leaving the explorer stops
its local polling; server computation may continue. Explicit cancellation is a
separate action. Shared capabilities avoid redundant initial health requests.

## Accessibility, rendering and performance

Existing dark CSS tokens and Modules are reused; no new dependency or lockfile
change. The radar has named keyboard/touch controls, source/quality notices have
text, and comparison tables have a focusable horizontal scroll region and visible
scroll guidance. The page itself does not overflow at 1440×1000, 820×1180 or
390×844, including mobile 200% text. WebGL failure leaves radar/list/form usable.
No new animation loop, DEM request, playback implementation or texture exists.
Candidate geometries/materials use R3F ownership/disposal; existing demand render,
DPR, context-loss and texture handling remain in place.

Production output (decimal kB / gzip kB): main JS 476.43 / 139.21, shared lazy
renderer 918.47 / 242.63, LunarGlobe 30.17 / 8.29, HorizonScene 11.42 / 4.27;
main CSS 24.88 / 5.46. The main bundle includes the verified offline evidence.
The existing renderer chunk warning remains; no heavy package was introduced.
Vite's bundled configuration loader works; it warns about extensionless imports
if a future native configuration loader is adopted. That unrelated migration is
not part of this change.

## Verification evidence

Dependencies already existed and package versions were unchanged; `npm ci` was
unnecessary. Targeted tests preceded one final full regression. Logs and browser
screenshots are ignored artifacts under `.validation/` and `test-results/`.

- TypeScript: PASS (`npm run typecheck`).
- Production: PASS (`npm run build`), including source checksums and runtime schema preparation.
- Vitest: PASS, 462 tests in 31 files, no failures/skips.
- Playwright: PASS, 236 tests across desktop/tablet/mobile, no failures/skips
  (`TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e`, 6.0 minutes).
- New focused coverage: 31 unit tests and 7 browser cases across three viewports.
  This covers both actual recorded exports, bad hashes/schema/source identity,
  nullable metrics, radar axes/ranges, sparse explicit rules, atomic stale-result
  clearing, typed optimizer lifecycle and live error/cancel/partial paths.
- Existing NASA JPEG HTTP/decode/upload, WebGL/camera/raycasting, Local Horizon,
  celestial motion/playback, API/scenario and scientific panel tests are retained.
- Real unchanged backend on port 8011: capabilities and result schemas HTTP 200;
  invalid local optimizer request HTTP 422. Reported `science_ready=false`,
  `configured_science_files_available=false`, `bounded_live_prototype_supported=false`.
- Read-only Pydantic cross-validation: PASS for emitted TemporalJobRequest,
  LocalJobRequest, TemporalBatchResult and LocalSiteOptimizationResult using the
  existing backend virtual environment. Full archive results also pass consumed
  frontend validation. Controlled browser optimizer responses are TEST_FIXTURE,
  explicitly labeled, and are not genuine live NASA calculations.
- Real NASA live optimizer E2E: BLOCKED_ENVIRONMENT. Trusted kernel/LOLA files are
  not configured; no large files or new science jobs were downloaded/computed.

Screenshots actually inspected include recorded temporal/local on desktop and
tablet, mobile local and 200% text, candidate globe, controlled live temporal/local,
PARTIAL evidence and invalid schema. The mobile table was corrected during review
to use its own scroll area rather than per-letter column wrapping. Recorded
warnings, LIMITED/source limitations, TEST DATA and failed-result messaging remain
visible. Source evidence claims are displayed, not independently certified.

## Scientific limits and next integration boundary

Finite evaluated candidates do not establish a global optimum. Sampled visibility
is not physical continuity certification; Sun visibility is not electrical power,
Earth visibility is not RF success, slope is not landing safety, and a planning
score is not mission success probability. Absolute DEM registration, independent
astronomy equivalence and mission suitability remain unverified. Missing full
horizon/time-series/window exports remain missing. Live sources are environment
blocked, separately from working recorded delivery and controlled API tests.

Command 13 is not implemented. Future work may consume additional authenticated
backend evidence through the same validated result/explicit-transfer boundary;
it must not create scientific fields from these summary metrics. No deployment,
backend/data-pipeline edit or main merge is part of this task.

## Changed files

- `COMMAND_12_ALTERNATIVE_EXPLORER_VALIDATION.md`
- `README.md`
- `e2e/alternative-explorer.spec.ts`
- `scripts/demoEvidence.ts`
- `src/features/alternative-explorer/Comparison.tsx`
- `src/features/alternative-explorer/EvidenceWorkspace.tsx`
- `src/features/alternative-explorer/Explorer.module.css`
- `src/features/alternative-explorer/LiveExplorer.tsx`
- `src/features/alternative-explorer/Radar.tsx`
- `src/features/alternative-explorer/evidence.test.ts`
- `src/features/alternative-explorer/evidence.ts`
- `src/features/alternative-explorer/evidenceModule.d.ts`
- `src/features/alternative-explorer/jobs.test.tsx`
- `src/features/alternative-explorer/live.ts`
- `src/features/alternative-explorer/requests.ts`
- `src/features/alternative-explorer/transfer.test.tsx`
- `src/features/analysis-results/resultContext.ts`
- `src/features/scenario/ScenarioProvider.tsx`
- `src/features/scientific-jobs/useScientificJob.ts`
- `src/screens/AlternativeExplorer.tsx`
- `src/screens/MissionSetup.tsx`
- `src/services/api/jobs.ts`
- `src/test/App.test.tsx`
- `src/test/optimizerFixtures.ts`
- `src/visualization/globe/CandidateMarkers.tsx`
- `src/visualization/globe/LunarGlobe.tsx`
- `vite.config.ts`
