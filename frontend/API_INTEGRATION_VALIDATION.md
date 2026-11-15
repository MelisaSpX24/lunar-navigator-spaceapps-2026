# Frontend Command 05 — API, shared scenario and safe response lifecycle

> Historical Command 05 evidence. Command 06 scientific presentation and current
> request matching are documented in ANALYSIS_RESULTS_VALIDATION.md.

## Repository and scope

Base main: `be3cc775a4c166989d28ea057086ab04ab4b4aa3`, merge PR #9.
Initial tree was clean. Branch: `frontend/command-05-api-integration`.
The unchanged backend model/routes/README and backend AGENTS.md were read;
no backend, data_pipeline, contracts or root source file is modified. No dependency
was added or upgraded. AnalysisRequest construction and coordinate math are reused.

## Architecture and behavior

- services/api/client.ts uses Fetch, JSON Content-Type/Accept and AbortSignal.
  HTTP status is retained. Transport, HTTP and malformed/unsupported body outcomes
  are distinct. Runtime guards check the version, displayed fields, enums, finite
  score range, null/array containers and validation-issue shape before use.
- Scientific arrays remain opaque and are not rendered. This is a minimum envelope
  validator, not full validation of all scientific samples/provenance. A future
  visualization must validate the fields it consumes. Unknown versions fail closed.
- ScenarioProvider owns the single typed raw form state, derived marker, health
  and analysis lifecycle above routes. Navigation retains them; Reset scenario
  clears inputs/marker/request status. Refresh resets state. No localStorage or
  persistent readiness is used, avoiding silent stale scenario/readiness reuse.
- Health states: checking, reachable_not_ready, ready, unreachable, invalid_response.
  There is one initial health check (StrictMode's discarded setup is cancelled),
  plus explicit checks; no polling. Retry does not move focus or erase inputs.
- Run Analysis requires valid builder output, verified readiness and no pending
  request. A synchronous lock prevents duplicate POSTs. There is no automatic POST
  on mount, validation, route change or health refresh.
- Analysis states: idle, submitting, not_ready, validation_error, network_error,
  server_error, invalid_response, received. AbortController and generation counters
  protect edits, reset, cancellation, unmount and superseded responses. Navigation
  can retain a pending request; changing its scenario aborts and clears it.
- Health timeout is 10 seconds and analysis timeout 30 seconds. Cancellation stops
  local waiting; server-side work is not assumed cancelled (there is no cancellation
  endpoint). No GET /analyses/{id}, persistence or fake readiness is introduced.
- A validated 503 requires NOT_RUN, INCOMPLETE, SCIENCE_ENGINE_NOT_READY and null
  scientific values. It becomes not_ready and invalidates the earlier ready signal
  until an explicit health check. The actual earlier health response is retained,
  not rewritten. Other 503 bodies remain HTTP or invalid-response errors.
- FastAPI 422 maps only recognized body paths; unknown/discriminator-unrecognized
  paths remain general messages. CoordinateSite's COORDINATES branch is supported.
  Input values remain unchanged. Unknown reserved object-property names are also
  handled as general errors. Backend messages are React text, never HTML.
- HTTP 200 means received. Execution COMPLETED is described only when present;
  it is not treated as operation approval. TEST_FIXTURE has a visible warning.
  Null score/series remain null; numeric scores/graphs are not displayed. Response
  IDs are explicitly not saved records/retrieval links.

Mission Analysis now adds Current Scenario and Analysis Connection / Response
Status above the unchanged seven scientific panel contents. Mission Setup shows
its request status too. Alternative Explorer has no optimizer changes; its shared
header uses the same health and its navigation preserves the scenario.

## Configuration

.env.example documents VITE_API_BASE_URL (browser default /api/v1) and
API_PROXY_TARGET (development proxy default http://127.0.0.1:8000). Only the
/api development route is proxied. HashRouter and the local NASA asset URL remain
unchanged. Vite preview explicitly has no API proxy. Production must provide
/api routing itself or use the actual configured API base; no production host
or secret/token is invented. Cross-origin CORS is the deployment server's concern.
See README.md for exact launch/configuration instructions.

## Real backend checks — separate from controlled tests

The existing backend virtualenv ran uvicorn at 127.0.0.1:8000 with
PYTHONDONTWRITEBYTECODE=1; its source was not changed. Vite dev ran on port 5173.
Actual checks, with no API route mocking:

1. Direct GET /api/v1/health: HTTP 200, status ok, science_ready=false,
   dem_ready=false, kernels_ready=false, SCIENCE_ENGINE_NOT_READY.
2. The same GET through Vite's /api proxy: HTTP 200, identical JSON.
3. A real frontend-builder request, sent by an external Node API control through
   the development proxy: HTTP 503, NOT_RUN, INCOMPLETE, expected reason code,
   null score/series/horizons/resolved_site/data_origin. The production envelope
   guards also accepted these actual response bodies.
4. Chromium against the dev proxy at all three target sizes: actual not-ready
   header, valid preserved form, NASA texture, disabled Run Analysis, no frontend
   POST and no uncaught page errors. Navigating to Analysis retained the scenario.
5. The backend process was stopped. Actual connection refusal through Vite's
   proxy yielded an HTTP 5xx (502 in the final check) and was shown as unreachable. At all three sizes the
   interface, retry and navigation stayed usable, inputs survived, Run Analysis
   remained disabled, and no frontend POST or uncaught page error occurred.

The external POST never bypassed or changed the UI readiness gate. No actual
ready/COMPLETED scientific response exists in the current backend. Those paths
are explicitly controlled test envelopes, not live scientific validation.
Logs/JSON and live screenshots are ignored outputs in .validation/.

## Executed checks and regression evidence

Node 24.22.1, npm 11.9.0, system Chromium 156 / Linux.
Before changes: npm ci/typecheck/build PASS, 128 Vitest tests and 67 Playwright
executions PASS. Final checks:

| Command/check | Result |
| --- | --- |
| npm_config_cache=/tmp/lunar-npm-cache npm ci | PASS, same lockfile, 125 packages |
| npm run typecheck | PASS |
| npm run build | PASS; existing large lazy-globe warning retained |
| npm run test -- --run | PASS, 189 tests / 12 files, no failed/skipped tests |
| ../backend/.venv/bin/python -B scripts/check-backend-request.py | PASS, 10 actual frontend requests accepted; 4 invalid controls rejected |
| TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e | PASS, 91 executions, no failed/skipped tests |
| Real local backend/proxy checks above | PASS |

The 61 added unit cases cover client/envelope validation and provider transitions,
network refusal/DNS/proxy errors, HTTP 404/500/502/504, valid and unexpected 503,
422 mapping, malformed JSON, unknown version/enums, cancellation, timeouts,
duplicate calls, StrictMode, reset and adversarial delayed responses. Unknown
scientific values are never replaced with defaults. Controlled response fixtures
are imported only by tests; production has no mock/test mode.

The 24 added browser executions cover ready/not-ready gating, exactly one POST
with real AnalysisRequest body, loading/cancel, field/global errors, explicit
keyboard retry, stale response exclusion, preserved form/globe marker through
all screens, reset, fixture labelling, NOT_RUN versus COMPLETED and null values.
The existing 67 runs remain, adjusting only intentional health/status behavior.
Normal regression tests mock only the known not-ready health endpoint; live
backend checks above are a separate, unmocked exercise.

## Texture regression found and fixed

One complete browser run had 90 passes and one GPU-upload failure. Trace images
showed a real plain white sphere while CPU texture loading had succeeded. Three.js
had compiled the initial material without a map; a later map assignment did not
select the textured shader variant. A forced delayed-JPEG check reproduced this
failure before the fix; it was not waived as a timing-only test failure.

MoonMesh now replaces only the material when the texture identity changes. R3F
disposes the old material and texture ownership remains with the existing hook.
The JPEG, texture loader settings, UVs, coordinates, camera and scene geometry
are unchanged. The loading regression now forces a first neutral draw and then
requires a genuine upload of the decoded original JPEG. Expectations were not
relaxed. Normal and delayed upload checks passed 18/18 focused executions across
all three sizes, repeated three times, before the final full suite.

Existing coverage still checks HTTP 200/image/jpeg, byte/hash equality, browser
decoding and genuine WebGL upload, texture loading/404 fallback, camera/zoom,
raycasting/marker, context loss, unavailable WebGL, touch/pinch/page scrolling,
UV/coordinate math and all screen navigation. JPEG SHA-256 remains:
`f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170`.

## Responsive, visual and accessibility review

1440x1000, 820x1180 and 390x844 are exercised. Live Analysis screenshots at all
three sizes were reviewed: current input summary, readiness, response status and
seven unpopulated panels remain clear. Live Setup/NASA and backend-off screenshots
are retained for review. Controlled 422/503/fixture and 200% status screenshots
were inspected in test-results/. The actual backend-off mobile header at 200%
text was also inspected. Labels, errors and server messages wrap; new
status text uses status/alert semantics and does not rely on color alone. Retry
and Cancel are keyboard buttons. Existing 200% text/overflow/focus tests remain.

Browser WebGL uses the cloud software renderer (SwiftShader), not proof of
hardware GPU performance. Physical-device, Safari/Firefox and real ready-engine
scientific validation are NOT RUN. There is no claim of cartographic, mission
safety, power or communication certification.

## Build and remaining boundaries

No dependency change. Command 04 entry JS was 286.05 / 91.23 kB raw/gzip and lazy
globe JS 946.53 / 249.71 kB. Final Command 05 sizes: entry JS 300.72 / 95.45 kB, lazy globe JS
946.56 / 249.72 kB; entry CSS 15.58 / 3.75 kB and lazy globe CSS 1.40 / 0.51 kB.
Entry JS increases by 14.67 kB raw / 4.22 kB gzip over Command 04.
The globe remains lazy-loaded, with the original 457942-byte static JPEG.
Health/readiness can become stale between explicit checks; automatic polling is
intentionally absent, and server rejections are still handled safely. Request
state is in-memory only; HTTP response ID is not persistent storage.

No main merge, deployment or Command 06 work is performed. Future result panels
require real validated backend results, scientific field/provenance validation
and explicit scope approval.

## Changed files

```text
frontend/.env.example
frontend/API_INTEGRATION_VALIDATION.md
frontend/MISSION_INPUT_VALIDATION.md
frontend/README.md
frontend/e2e/api-lifecycle.spec.ts
frontend/e2e/globe.spec.ts
frontend/e2e/mission-input.spec.ts
frontend/e2e/navigation.spec.ts
frontend/e2e/touch.spec.ts
frontend/src/app/App.tsx
frontend/src/app/Header.tsx
frontend/src/features/mission-input/MissionForm.tsx
frontend/src/features/mission-input/MissionSetup.test.tsx
frontend/src/features/scenario/ConnectionStatus.tsx
frontend/src/features/scenario/ResponseStatus.tsx
frontend/src/features/scenario/Scenario.module.css
frontend/src/features/scenario/ScenarioProvider.test.tsx
frontend/src/features/scenario/ScenarioProvider.tsx
frontend/src/features/scenario/ScenarioSummary.tsx
frontend/src/screens/MissionAnalysis.tsx
frontend/src/screens/MissionSetup.tsx
frontend/src/services/api/client.test.ts
frontend/src/services/api/client.ts
frontend/src/services/api/fieldErrors.ts
frontend/src/services/api/responses.ts
frontend/src/test/App.test.tsx
frontend/src/test/apiFixtures.ts
frontend/src/test/setup.ts
frontend/src/visualization/globe/MoonMesh.tsx
frontend/vite.config.ts
```
