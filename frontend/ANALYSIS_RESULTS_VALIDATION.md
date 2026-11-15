# Frontend Command 06 — validated scientific result presentation

## Base and scope

Initial main: `8a653d8af56465f494456d6f36b2cfb028e8390b`, merge PR #11.
During work main advanced to `33990885b7b3b6a967d0278b2d9a8b70477955be`
(backend LOLA validation, PR #10). The final task commit is rebased onto that
main. Its frontend, analysis API model and routes are identical to the initial
base; no teammate backend/data_pipeline edits are modified by this task.
Initial checkout was clean. Branch: `frontend/command-06-analysis-results`.
Only frontend/ changes. Backend app/models/analysis.py, API routes, existing
frontend/API/scenario screens and backend AGENTS.md were inspected read-only.
No backend, data_pipeline, contracts, root files, dependencies or NASA assets/
coordinate/UV/material/camera implementations are changed. No deployment occurs.

## Contract and trust boundaries

The backend-local AnalysisResult schema is 1.0. Its API minimum-envelope checks
remain in services/api/responses.ts: unknown version, invalid core enums/types or
unsafe core numeric ranges invalidate the whole response as before. New fields
beyond that envelope remain untrusted until the analysis-results guards run.
Within an accepted envelope, deep horizon/body/window/rule/score-component/quality/
source errors are isolated by panel. An invalid Sun sample does not hide a valid
Earth series, score, timeline or decision. A bad source record does not erase
otherwise readable quality metadata. Unsupported scientific content is reported,
not repaired or converted into successful empty data.

The request sent at submission is retained as a snapshot. The API compares all
explicit fields of response.request with it before accepting the response.
Object-key order is irrelevant; UTC Z and equivalent +00:00/microsecond-zero
spellings compare equal. Numbers, booleans, null, extra fields and observer/time/
requirements/options differences do not coerce. The display gate checks that
same snapshot against both the current valid form request and the echo again.
Analysis IDs are not used for scenario correlation or persistent retrieval.

Scientific panels require received HTTP 200, execution COMPLETED, a ready backend
connection and current/sent/echoed request agreement. Idle, submitting, NOT_RUN,
RUNNING, FAILED, 422, 503, network/invalid response, cancellation, reset and edits
cannot populate them. An explicit health recheck temporarily hides panels while
readiness is unknown; an unreachable/not-ready state also keeps them unpopulated.
Scenario navigation, abort/generation guards and the existing globe marker remain.

No backend scientific data was obtained in this task. The current API remains
science_ready=false and returns 503 for valid analyses. All populated browser
screens use controlled TEST_FIXTURE HTTP responses in tests only. Pydantic
compatibility below is not a NASA measurement or scientific validation claim.

## Panels and data semantics

- Local Horizon: separate profile IDs, observer heights and ranges in metres,
  azimuth/elevation scatter SVGs in degrees, source IDs and coverage warnings.
  Null elevation has no marker; no lines, interpolation, DEM or 3D terrain is
  invented. Azimuth must increase strictly in [0,360); elevation is [-90,90]/null.
- Sun and Earth: independent body validators, strict ordered UTC samples inside
  the submitted time range, elevation and disk-fraction scatter SVGs, and a full
  field table. UNKNOWN, NONE, PARTIAL, null, zero and false are retained literally.
  No position, condition, disk fraction or visibility is computed. Geometry is
  explicitly not a guarantee of electrical output or radio/data throughput.
- Mission Timeline: three independent server window lanes. Null means not
  calculated; [] means calculated with no matching windows. UTC intervals are
  [start,end), with censored start/end booleans and definition IDs. Reversed,
  out-of-request or unordered intervals are rejected, never sorted/clipped.
- Assessment: backend status/rules/reasons, with boolean/number/null required and
  actual values. No units are inferred. Empty rules are not success; MET is not
  landing certification and INCOMPLETE is not a positive/negative operation call.
- Score: backend 0–100 value only, never aggregated or calculated. Null displays
  Not calculated; zero remains zero. A non-null score without a model version is
  withheld. Missing/invalid model metadata and bad normalized values/weights are
  explicit. No component weights are invented, summed or renormalized.
- Quality/Sources: NOT_ASSESSED/SUFFICIENT/LIMITED/INSUFFICIENT, nullable coverage,
  limitations and provided ID/kind/product/version/URL/SHA-256. Incomplete or
  unassessed quality is also visible in relevant populated panels and beside the
  score. Null coverage is never complete. Empty sources do not establish NASA
  provenance. Only credential-free HTTP(S) URLs become links; unsafe URLs are
  text. Provided checksums/versions do not independently establish authenticity.

Current Scenario and Response Status remain. Scientific response context names
the matched coordinates/frame, UTC start/end/duration, execution, origin, resolved
site/elevation/datum and quality. Invalid resolved-site metadata is explicitly
shown instead of posing as a measured elevation. TEST_FIXTURE has a prominent
TEST DATA notice in addition to the response-status warning.

## Time and display limits

Calendar validation reuses the existing strict UTC helper; timestamps accept
Z/+00:00 and up to six fractional digits. BigInt microseconds keep order/identity
exact even near years 0001/9999. Time differences for SVG placement are presentation
arithmetic only. No local timezone conversion, invalid-date rollover, sorting,
interpolation, optimizer or scientific solver is added.

Scientific list validation is bounded at 5000 records. Horizons additionally
admit at most 20 profiles and 5000 total points. Oversized panels have an explicit
display-limit message and are not silently sampled. Visibility plots/tables and
window/rule/component/source tables/cards show the first 100 validated records,
with visible total/limit text. Horizon plots cover all admitted points while their
tables separately announce their first-100-row limit. These are display limits,
not backend/model limits or claims that omitted records do not exist.

SVGs have titles, descriptions and explicit textual UTC/degree/fraction axes.
Accompanying captioned tables retain exact values and support keyboard scrolling.
Visible table captions are outside the scroll area; UTC/status strings stay
intact. Tables have bounded height and scroll internally without horizontal page
overflow. Quality/errors use text, not color alone; no unsolicited focus change
is introduced. Filled cards align at the top, preserving empty-state scene layout.

## Executed checks — 2026-11-14

Node 24.22.1, npm 11.9.0, system Chromium 156 on Linux.
Before editing: npm ci/typecheck/build PASS; Vitest 189 and Playwright 91 PASS.
Final checks:

| Command/check | Result |
| --- | --- |
| npm_config_cache=/tmp/lunar-npm-cache npm ci | PASS; 125 packages, unchanged lockfile |
| npm run typecheck | PASS |
| npm run build | PASS; existing large lazy-globe chunk warning retained |
| npm run test -- --run | PASS; 242 tests, 14 files, no failed/skipped tests |
| ../backend/.venv/bin/python -B scripts/check-backend-result.py | PASS; 3 valid TEST_FIXTURE results accepted; 4 invalid controls rejected |
| ../backend/.venv/bin/python -B scripts/check-backend-request.py | PASS; 10 frontend requests accepted; 4 invalid controls rejected |
| TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e | PASS; 115 executions, no failed/skipped tests |

The 53 added unit cases exercise UTC/calendar/microsecond ordering, request
identity and result gating, horizon bounds/coverage/gaps, independent Sun/Earth
validation, unknown/partial/none/zero/false semantics, windows and censoring,
rules, score/model/components, quality/source metadata and unsafe URLs, panel
isolation, accessible SVG/table output and an explicit first-100 rendering limit.

The 24 added browser executions cover complete, partial, invalid per-panel and
wrong-scenario responses, non-COMPLETED states, 503, source/quality warnings,
navigation/marker retention, clearing old charts after edits/reset, 200% text,
keyboard table scrolling and accessible graph names. All three viewport projects
run them: 1440x1000, 820x1180, 390x844. Existing 91 executions remain. Prior
COMPLETED fixture assertions now expect a withheld score when model version is
missing, and delayed-response fixtures echo the actual newly submitted request.
The wrong-scenario response is now rejected deliberately; no checks were waived.

Three test JSONs (full, partial, empty) emitted by Vitest are checked using the
existing backend virtualenv and unchanged AnalysisResult Pydantic class, with
bytecode disabled. Four negative controls reject invalid disk fraction, weight
and SHA-256. Test-only fixtures live under src/test/ and are never imported by
production; no automatic demo or test mode exists. Python writes nothing under
backend/ and makes no HTTP request.

## Browser and visual evidence

Screenshots are ignored outputs under test-results/. Empty-state screens,
controlled full/partial results, invalid panel data, source/quality warnings and
200% text are captured. Visual review covers the three requested sizes and the
mobile chart/table layout. They show TEST DATA explicitly; none is evidence of a
real NASA analysis. Final review included desktop/tablet/mobile Sun and score
panels, the horizontally scrolled mobile table, 200% mobile text, the partial
desktop state, invalid tablet panels and the normal empty mobile screen.

All NASA globe regression checks remain: actual local JPEG HTTP/decode/WebGL
upload including forced delayed material loading, neutral/error/context-loss
fallbacks, camera/zoom/south/reset, raycasting, marker, touch/pinch/page scrolling,
UTC/coordinate math, readiness/503/422/network lifecycle and navigation. No local
horizon WebGL scene is created. Preserved JPEG SHA-256:
`f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170`.

Physical devices, Safari/Firefox, hardware GPU performance, independent source
checksums/authenticity and real completed scientific-engine validation are
NOT RUN. Cloud WebGL is software-rendered; the color texture is not a DEM.

## Bundle and remaining boundaries

No new library or dependency version. Native SVG and HTML tables only.
Command 05 entry JS: 300.72 / 95.45 kB raw/gzip; lazy globe 946.56 / 249.72 kB.
Command 06 final sizes: entry JS 324.28 / 101.80 kB, entry CSS 18.20 / 4.26 kB;
lazy globe JS 946.56 / 249.72 kB and CSS 1.40 / 0.51 kB. The original static JPEG
is unchanged and remains separate. No test payload is embedded in the build.

Display validation is intentionally stricter than Pydantic for ordering,
nonempty usable IDs/model-version strings and request-window bounds. Validating
shape/ranges does not validate SPICE, DEM science, source availability or model
accuracy. Core API-envelope failures still reject the entire response, while
accepted envelopes have independent deeper panel failures. No backend science,
optimizer, landing-safety guarantee, main merge, deployment or Command 07 work.

## Changed files

```text
frontend/ANALYSIS_RESULTS_VALIDATION.md
frontend/API_INTEGRATION_VALIDATION.md
frontend/README.md
frontend/e2e/analysis-results.spec.ts
frontend/e2e/api-lifecycle.spec.ts
frontend/scripts/check-backend-result.py
frontend/src/features/analysis-results/AssessmentData.tsx
frontend/src/features/analysis-results/Panels.test.tsx
frontend/src/features/analysis-results/Presentation.tsx
frontend/src/features/analysis-results/QualityData.tsx
frontend/src/features/analysis-results/ResultContext.tsx
frontend/src/features/analysis-results/Results.module.css
frontend/src/features/analysis-results/TimelineData.tsx
frontend/src/features/analysis-results/VisibilityPanels.tsx
frontend/src/features/analysis-results/requestMatch.ts
frontend/src/features/analysis-results/resultContext.ts
frontend/src/features/analysis-results/types.ts
frontend/src/features/analysis-results/utc.ts
frontend/src/features/analysis-results/validation.test.ts
frontend/src/features/analysis-results/validation.ts
frontend/src/features/scenario/ResponseStatus.tsx
frontend/src/features/scenario/ScenarioProvider.test.tsx
frontend/src/features/scenario/ScenarioProvider.tsx
frontend/src/screens/MissionAnalysis.tsx
frontend/src/services/api/client.test.ts
frontend/src/services/api/client.ts
frontend/src/services/api/responses.ts
frontend/src/test/apiFixtures.ts
frontend/src/test/scientificFixtures.ts
```
