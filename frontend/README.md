# 24&28 — Lunar Landing Site Navigator

Frontend Commands 01–08.1: a responsive React + TypeScript + Vite application
with a shared design system and interactive global lunar geometry.

**Command 03.1:** the user-supplied original 2K JPEG is checksum-verified and
served locally on the interactive globe. No remote NASA texture request is
required. See TEXTURE_VALIDATION.md and public/assets/moon/README.md for
verification evidence and provenance limits.

Explore the Moon. Evaluate the Conditions. Find a Better Site.

## Scope

Three navigable English-language screens: Mission Setup (default), Mission
Analysis and Alternative Explorer. The dark interface uses CSS Modules and
shared CSS variables. Common components cover panels, loading, empty, error and
unsupported-data states. Navigation includes active links, a skip link, keyboard
access, route focus management and document titles.

Mission Setup includes a lazy-loaded Three.js / React Three Fiber sphere.
Mission inputs prepare a validated AnalysisRequest 1.0 preview. A small Fetch
client checks backend health and submits only when the server explicitly reports
scientific readiness. No scientific calculation, generated recommendation or
fabricated score is produced by the frontend. The NASA color asset was supplied
by the user in a ZIP and copied without conversion. All
scientific panels now display independently validated fields only from a matched,
current COMPLETED response. The current backend still reports science_ready=false,
so normal use remains empty and Run Analysis is disabled. Response metadata stays
separate from scientific presentation. Backend, data pipeline and shared contracts are
outside this change.

## Setup and development

Use Node **24.15 or newer within Node 24** and npm. Verified with Node 24.22.1
and npm 11.9.0. Each cloud task is already isolated; use the existing checkout
and do not create a worktree unless explicitly requested.

```sh
cd /workspace/lunar-navigator/frontend
npm ci
npm run dev -- --port 5173 --strictPort
```

The development server listens on all interfaces for cloud use. To restrict it
to this machine, append `--host 127.0.0.1`. No secrets are required. The interface remains usable when the backend is down;
API configuration and optional local backend steps are below. Dependencies are exact-pinned in package.json
and resolved in package-lock.json. React and React DOM use the same version;
the installed Node, Vite, React plugin, TypeScript and Vitest passed the checks
below. Native Node type definitions target Node 24.

## Routes and static hosting

React Router's HashRouter provides routes `/#/`, `/#/analysis` and
`/#/alternatives`. Browser back/forward, direct links and refresh work without
server-side SPA rewrite rules. Under a subdirectory, retain that directory before
the hash (for example `/navigator/#/analysis`). Vite's relative base supports
serving the build under such a directory. Serve `dist/` through HTTP; opening
index.html directly through file:// is not supported.

```sh
npm run build
npm run preview -- --port 4173 --strictPort
```

Upload only `dist/` to a static host. The preview server is for local validation,
not a production hosting service.

## Required checks

```sh
npm run typecheck
npm run build
npm run test -- --run
```

Vitest uses jsdom and React Testing Library. Its unit tests cover all three
screens, explicit unavailable states, navigation, current-page indication,
titles/focus, unknown-route recovery, the skip link, loading/error states and
retry behavior, the unconfigured data mode and accessible scene placeholders.
Added tests cover visual coordinate transforms, actual SphereGeometry UVs,
texture loading/failure/disposal and renderer startup. jsdom scene tests use
explicit renderer/texture mocks; only browser tests exercise real WebGL.
Local JPEG bytes, SHA-256 and JPEG frame dimensions are also checked. Scientific
results are not validated by these tests. Mission-input tests cover strict UTC
calendar handling, duration bounds, coordinate adapters, requirements, null/zero,
request serialization and shared form/globe state. See MISSION_INPUT_VALIDATION.md
for backend model cross-validation and the distinction between mocks and WebGL.

## Real browser checks

```sh
# Install Chromium once if no compatible system browser is available:
npx playwright install chromium
npm run build
npm run test:e2e

# Or use the system Chromium already present in this cloud environment:
TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e
```

Playwright starts the production preview on port 4173, retains the existing navigation and globe coverage, adding local JPEG, GPU upload,
loading/failure and landmark-view checks across 1440×1000, 820×1180 and 390×844
plus one mobile touch scenario (including scientific result presentation and local horizon interaction), then stops its preview server.
It checks rendering, horizontal overflow, uncaught page errors, absence of
unintended scientific API requests, direct hash links, reload, back/forward, keyboard navigation,
skip-link focus and unknown-route recovery. It also checks touch targets, visible
keyboard focus, scene dimensions, mobile panel order, reduced-motion behavior,
200% root text sizing and horizontal text clipping. Full-page screenshots of all three
screens at each size are written to ignored `test-results/`. Port 4173 must be
free; the runner does not reuse or terminate unrelated servers.

Historical Command 03.1 baseline in Chromium 156 on Linux: 43 Vitest tests and
49 Playwright executions passed. Command 04 results and visual review are recorded
in MISSION_INPUT_VALIDATION.md. Current Command 05 evidence is in
API_INTEGRATION_VALIDATION.md. Command 06 result validation and review are in
ANALYSIS_RESULTS_VALIDATION.md. Tablet and
mobile checks are emulated viewports, not physical-device or Safari validation.

## Structure

- `src/app/`: shell, header, navigation and routes.
- `src/screens/`: three screen layouts and their styles.
- `src/components/`: reusable panels and explicit data states.
- `src/styles/`: shared tokens and global styles.
- `src/test/`: component and navigation tests.
- `e2e/`: production-preview browser tests.
- `src/visualization/`: isolated globe, camera, texture lifecycle and coordinate helpers.
- `src/features/mission-input/`: controlled form, backend-local request types, validation and adapters.
- `src/features/scenario/`: shared in-memory scenario, readiness and response lifecycle.
- `src/features/analysis-results/`: per-panel scientific validation, UTC ordering, request matching, SVG and accessible tables.
- `src/services/api/`: Fetch client, minimum response-envelope guards and 422 field mapping.
- `scripts/check-backend-request.py`: read-only Pydantic cross-validation of actual frontend JSON.
- `public/assets/moon/README.md`: official texture URL and acquisition status.

Future celestial-marker and optimizer providers can be introduced
as scoped features without putting scientific calculations in presentation code.
No future-feature stub directories have been created.

## Design system and scene preparation

`src/styles/global.css` defines semantic colors, a 4/8/12/16/20/24/32/48 px
spacing scale at the default font size, label/body/panel typography, border radii,
panel padding, focus rings and button states. Standard input/select/textarea
styles are shared with the controlled mission form. Labels are
at least 12 px and body/panel copy is 14–16 px at the default root size. No web
fonts, UI framework or animation dependencies are loaded. The 2K JPEG is a
local static asset loaded only by the global lunar view.

CSS Modules consume these tokens. PageHeading and StatusBadge keep screen
headings and static mode labels consistent. The header reports the verified backend connection and scientific readiness,
with an explicit Check backend / Retry connection action. Panel headers
are informational and do not display decorative link affordances. Empty,
unsupported, loading and application-error states retain distinct text and
semantics; color alone does not communicate a state.

SceneViewport is used by both the global lunar view and interactive local horizon.
It owns a bounded flex layout, a flexible central surface and separate top/bottom
overlay areas. A later 3D feature can mount its renderer in the surface while
preserving these layout boundaries. Future controls must explicitly enable
pointer events on their own interactive elements; current overlay text has no
interactive behavior. Only the active route mounts a Canvas: the global Moon in Mission Setup or the local orientation/horizon view in Mission Analysis.
The global variant removes surface padding without changing the local layout. Scene minimum heights are 460 px on larger screens
and 380 px at widths of 700 px or less; content can expand for larger text.

At desktop sizes Mission Setup gives the scene roughly 65% of the workspace.
Analysis uses named grid areas for a large horizon, paired visibility panels,
a wide timeline and assessment/score/quality panels. On mobile it follows the DOM
order: horizon, Sun, Earth, timeline, assessment, score, quality. Alternative
Explorer reserves a larger map/list workspace without generating candidates.

Controls have 44 px minimum targets; navigation has at least 48 px height. Short
button color transitions are disabled under prefers-reduced-motion. There are no
continuous animations. See VALIDATION.md for historical Command 02 evidence and GLOBE_VALIDATION.md
for historical 3D validation. TEXTURE_VALIDATION.md records the current local
texture integration, visual checks and limitations.

## Review and limits

All changes belong under `frontend/`. Verify with `git diff --name-only` against
the base commit before integration. Merge only through team review; do not merge
directly into main. This interface is planning support and does not guarantee
landing safety, power generation or radio connectivity.

## Global lunar view

Drag to rotate and scroll/pinch to zoom. Camera distance is constrained to
1.45–6 normalized sphere radii, with panning disabled. Focus South Pole and Reset
View are keyboard-accessible and instant (no animated motion). On coarse-pointer
devices interaction starts paused so normal page swipes work; enable globe
interaction to rotate, pinch or tap, then pause to resume page scrolling.

Click/tap raycasting selects a visual surface coordinate with a small marker.
Latitude and signed east-positive longitude are displayed; E/W notation is also
provided. Longitudes normalize to [-180, 180); +180 and -180 share the -180
representation. Longitude at a pole is undefined, not zero. Mission Setup owns
the raw coordinate fields as the single source for the form and globe marker.
Globe picks update those fields; valid manual coordinates update the marker.
Invalid edits hide the marker, while exact poles retain a visual marker but
explicitly fail backend request validation. Scenario state and its marker survive in-app route changes. Explicit Reset
scenario clears inputs, marker and the current request/response. Full reload
resets in-memory state; localStorage is intentionally not used. R in the camera readout is a normalized scene unit.

The neutral fallback uses an equator/prime-meridian grid and **illustrative
lighting**, never a selected UTC illumination model. The render loop is demand
based, DPR is capped at 1.5, and the globe unmounts outside Mission Setup.
Geometry, event listeners, controls and owned texture resources are disposed.
WebGL initialization errors and context loss leave navigation available.

NASA source: https://svs.gsfc.nasa.gov/4720/ . The user supplied the original
JPEG in a ZIP; local byte/format/size/dimension/hash checks passed. The Vite
base-aware URL is enabled and no NASA-server image download occurs at runtime.
Successful decoding/upload is tested; failure retains the neutral sphere.
See public/assets/moon/README.md for the checksum, source attribution and
qualitative feature-based orientation review. That review is separate from UV
math and is not independent cartographic certification. Current remote usage
notes and NASA-server checksum equality were not independently verified. Do not
derive terrain, heights, visibility or landing safety from the globe or imagery.

## Mission input and request preview

Landing Site, Operation Profile, Time Window, Operation Requirements and
Scenario Summary prepare inputs only. Four backend profile enum values are
retained; changing profile never changes requirements. The optional Request
Preview shows JSON only for valid inputs. Run Analysis requires valid inputs,
verified science_ready=true and no pending submission. The current real backend
reports false, so no frontend POST is made in its present state.

Form longitude is east-positive [0,360), distinct from the visual [-180,180)
readout. Exact +/-90 latitude and manually entered 360 longitude are rejected
without clamping or normalization. Globe picks alone use the visual-to-backend
adapter. Times are explicitly UTC; browser-native date/time presentation may
follow locale, but values serialize directly to ISO with Z without local-time
conversion. Invalid calendar dates cannot roll into another month. Duration
uses whole hours plus 0–59 minutes/seconds and safe positive integer seconds.
Start plus duration must remain within the backend year 0001–9999 range.

Requirement and observer/options initial values match the inspected backend
draft, not NASA-approved mission limits. The initial one-hour duration is a
frontend convenience, not a backend or NASA requirement. Coordinates and UTC
start are initially empty. Optional blank requirements remain null; explicit
zero stays zero. DEM is the surface mode; editable heights refer to devices.

Types in src/features/mission-input/analysisRequest.ts trace to the backend-local
Pydantic model at main 7a5acfbb70543f08410fb61a328ec825b96a6120. They are a
coordinate-only frontend mirror, not a new shared contract or generated schema.
Future backend model changes require a type/validation review.

After Vitest generates ignored .validation/mission-requests.json, validate the
actual ten frontend-produced samples with the existing backend Python environment:

```sh
../backend/.venv/bin/python -B scripts/check-backend-request.py
```

This imports the unmodified Pydantic model, accepts ten valid samples and rejects
four invalid controls. It makes no HTTP request and writes no backend bytecode.
The backend virtualenv must already have its dependencies installed; this command
does not provision it or change the backend.

## API configuration and safe lifecycle (Command 05)

The default browser base is **/api/v1**, rooted at the serving origin and
independent of HashRouter paths and Vite's relative asset base. Local NASA assets
keep their existing base-aware URL. No token or NASA API request is added.

Optional: copy .env.example to ignored .env.local under frontend/.

- VITE_API_BASE_URL: browser API base, default /api/v1; accepts a root-relative
  path or an actual HTTP(S) base URL. A cross-origin deployment must provide CORS
  on its server; this task does not modify backend CORS. VITE_ values are public
  build-time configuration, never secrets.
- API_PROXY_TARGET: Vite **development-only** /api proxy target, default
  http://127.0.0.1:8000. This localhost address is not a production endpoint.

Start the existing backend using its documented environment (no source changes):

```sh
cd /workspace/lunar-navigator/backend
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then start npm run dev in frontend/. The development proxy forwards /api paths;
Vite preview explicitly has no API proxy. A production server must separately
route **/api** to the actual deployed backend, or the build must use its actual
API base URL. Uploading dist/ alone does not deploy an API. No production backend
address is assumed here. Rebuild after changing public VITE_ settings.

Health is checked once on app mount and again only on explicit user action.
There is no polling. StrictMode's discarded mount is cancelled before network
work starts. Health timeout is 10 seconds; analysis timeout is 30 seconds.
Connection errors, malformed responses and explicit science_ready=false remain
distinct. HTTP 200 alone never enables scientific readiness. A verified
SCIENCE_ENGINE_NOT_READY 503 invalidates the earlier ready signal until a fresh
health check; the original health response data is not rewritten.

Requests use JSON, AbortSignal and a synchronous duplicate-submission guard.
Cancellation, reset, unmount and scenario edits abort pending work; generation
counters also reject stale responses if transport ignores cancellation.
Cancellation stops local waiting; no backend cancellation endpoint is assumed. Routes
share one Context, so navigation preserves inputs and pending/received status.
Input edits clear responses belonging to the earlier scenario. No saved analysis
record or GET /analyses/{id} is assumed. Refresh resets state, avoiding silent
reuse of old scenarios or readiness from persistent storage.

The API envelope still checks version 1.0, core field types, enums, nullable
scientific containers and displayed metadata. Command 06 adds strict per-panel
validation before any scientific content is presented. The sent request snapshot,
current valid form request and echoed response.request must agree. Core-envelope
failures invalidate the response; accepted envelopes undergo independent deeper
panel checks. These are data-format checks, not scientific accuracy certification.

Verified 503/NOT_RUN is shown as not_ready with preserved inputs. Other 503s and
HTTP errors are not relabelled as the scientific-engine condition. Validated
FastAPI 422 locations map to known fields; unknown paths remain general errors.
Malformed JSON or unsupported versions produce invalid_response. Messages are
React text, never HTML. HTTP 200 is only received: execution status and TEST_FIXTURE
origin stay explicit. Null score/series never become zero or computed empty data.
Only a current, matched COMPLETED response can populate result panels while the
backend connection is ready. Backend numeric scores need a supplied model version;
no score, operation approval or scientific value is calculated by the frontend.

Existing regression browser tests use a controlled not-ready health response;
new lifecycle tests route controlled API responses strictly within tests. Production
contains no fixture/test mode. Separate live checks against the unchanged local
backend and development proxy are documented in API_INTEGRATION_VALIDATION.md.

## Scientific result presentation (Command 06)

Mission Analysis retains seven panels, Current Scenario and Response Status.
No fixture is imported by production. A TEST_FIXTURE response received through
the API is labelled TEST DATA prominently; live scientific readiness is never
faked. Real backend health is still false, so normal panels remain empty.

- Local Horizon plots backend azimuth/elevation points only, in degrees, with
  explicit observer height/range in metres and separate profiles. Unknown points
  are absent from the plot, not zero; no line or interpolation bridges gaps.
- Sun/Earth panels validate each body's samples independently, show UTC elevation
  and disk-fraction SVGs plus an accessible table retaining UNKNOWN/NONE/PARTIAL,
  null, zero and boolean conditions. Geometry does not guarantee power or radio.
- Timeline displays only supplied ordered UTC [start,end) intervals. Null, empty
  and populated lanes differ; censored boundaries are explicit. Invalid times,
  reversals and out-of-request intervals are not sorted, clipped or repaired.
- Assessment displays server status/rules with literal boolean/number/null values
  and no invented units. MET is not NASA approval or landing certification.
- Planning Score reads, never calculates, 0–100 values. Null is Not calculated;
  a missing model version withholds numeric display. Components and weights are
  bounded by the backend model but never aggregated or renormalized here.
- Data Quality displays status, nullable coverage, limitations and provided source
  product/version/kind/URL/SHA-256 metadata. Empty sources do not establish NASA
  provenance. Only credential-free HTTP(S) URLs become links. Source metadata and
  checksums are not independently verified authenticity evidence.

UTC parsing reuses strict calendar validation and accepts Z or +00:00 with up to
six fractional digits. BigInt microseconds preserve ordering/request identity at
years 0001–9999. Time ratios for SVG positions are presentation arithmetic only.
No ephemeris, horizon, visibility-window, score or optimizer calculation is added.

Scientific arrays over 5000 records are not plotted and receive an explicit limit
message. Horizons additionally cap display at 20 profiles/5000 total points.
Visibility plots/tables and window/rule/component/source tables/cards explicitly
show at most the first 100 records. Horizon charts use all admitted points; their
tables announce a first-100-row limit separately. No silent sampling or gap fill
occurs. Scrollable tables remain keyboard accessible; captions and axes also have
readable text outside the chart/scroll region.

After Vitest emits the ignored test-only JSON samples, run the unchanged backend
model compatibility check without HTTP or backend writes:

```sh
../backend/.venv/bin/python -B scripts/check-backend-result.py
```

Three valid TEST_FIXTURE envelopes are accepted and four invalid controls rejected.
Pydantic model compatibility is not NASA measurement or scientific validation.
See ANALYSIS_RESULTS_VALIDATION.md for exact results, limitations and file scope.

## Interactive local angular horizon (Command 07)

Mission Analysis now opens an observer-centred sky reference view even without
scientific results. **Orientation preview is not measured terrain or celestial
positions.** The selected coordinate comes from the shared scenario; no camera
movement changes it. N/E/S/W, elevation guides and a horizontal reference ring
are coordinate aids only. No physical ground mesh is reconstructed; Command 08 adds celestial markers only for validated backend samples.

A current, matched, validated COMPLETED result can additionally show one backend
horizon profile as separate angular points. Null samples and unsampled sectors
are unknown: no lines, interpolation or seam closure are added. Select profiles
by ID, observer height and range. The existing 2D plots/tables stay underneath;
all other scientific panels and response guards remain intact. TEST_FIXTURE,
quality and incomplete coverage are explicit, including a canvas-adjacent badge.

Drag to look, scroll/pinch to zoom, or use the keyboard-accessible cardinal,
up/down, level, zoom and Reset View buttons. On touch devices enable interaction
first and pause to scroll the page. Camera stays at the origin with bounded
pitch/FOV, no flight, pan, roll, inertia or animation. WebGL failure/context loss
leaves 2D available and exposes an explicit retry. No additional packages or
NASA assets are fetched. Both scenes share lazy Three/R3F chunks.

The logical ENU mapping is X East, Y Up, Z North. An explicit North reflection
at the right-handed Three renderer boundary prevents mirrored compass views;
backend azimuth/elevation and global lunar coordinates are never modified.
See [LOCAL_HORIZON_3D_VALIDATION.md](LOCAL_HORIZON_3D_VALIDATION.md) for current
checks, screenshots, display/quality limits, coordinate convention and Command
08 integration points. No real scientific horizon has been verified by this UI
work; populated browser states are controlled test-only responses.

## Celestial samples and UTC selection (Command 08)

Mission Analysis adds one shared UTC selection for the local 3D scene, Sun/Earth
sample readouts and timeline playhead. It accepts only current matched COMPLETED
responses and independently validated body samples. Exact sample buttons retain
backend UTC precision; the range spans the entire operation. Between samples,
current celestial markers and scientific readout values are withheld explicitly.
No interpolation or optional playback is implemented in this conservative first
version. Controls never submit another analysis or change mission input times.

SUN (ring) and EARTH (diamond) markers have illustrative size, not angular scale.
Separate path toggles show discrete backend directions without joining gaps.
Horizon IDs are checked independently for each body; mismatch/missing/null
relations cannot become visibility decisions. TEST DATA warnings remain explicit.
Existing 2D data tables, global Moon, mobile interaction and WebGL fallback remain.
Time selection resets on route exit or new/invalidated results; scenario inputs
remain in the existing shared store. See [CELESTIAL_TIMELINE_VALIDATION.md](CELESTIAL_TIMELINE_VALIDATION.md).


## Visual motion and playback (Command 08.1)

Exact Samples remains the default. Enable **Smooth visual preview** to show only
accepted direction-only SLERP arcs between neighboring backend samples. Large
angles, long gaps, unknown directions and unknown/changing horizon profiles
withhold the relevant marker. Visibility, disk state, fraction and conditions
are never interpolated or copied to an intermediate UTC.

Play/Pause/Replay share the existing UTC selection. Choose a full-operation
playback duration of 30, 60 or 120 seconds. Manual selection pauses; the operation
end stops without looping. Hidden tabs, timing interruptions, response changes
and route exit stop playback. Reduced-motion keeps manual controls available
while disabling motion. No new API request or scientific calculation occurs.

See [CELESTIAL_MOTION_PLAYBACK_VALIDATION.md](CELESTIAL_MOTION_PLAYBACK_VALIDATION.md)
for guards, lifecycle, tests and known limitations. The Command 08 record above
describes the earlier exact-only implementation; this extension adds optional,
explicitly labeled visual motion without replacing scientific samples.

## Angular panorama (Command 09)

Mission Analysis gives the local horizon a larger, leading canvas. Sample Points
remains the default. Optional **Panoramic Trace** connects only nearby adjacent
known samples under conservative gap/cadence guards; unknown sectors and the
0°/360° seam are never filled. This is an angular observer-centred visualization,
not a physical terrain mesh or visibility calculation. Original points, 2D
charts/tables, profile metadata and scientific quality warnings remain available.

See [PANORAMIC_HORIZON_VALIDATION.md](PANORAMIC_HORIZON_VALIDATION.md) for the gap
policy, source limits, WebGL lifecycle and test evidence.

## South Pole Site Explorer (Command 10)

Mission Setup includes source-review cards for Connecting Ridge, Shackleton Rim,
Mons Mouton, Mons Mouton Plateau and the distinct Site01/CR1 research point.
Official source requests were blocked by HTTP 403 in this environment. Regional
coordinates remain unknown. All production entries are Exploration Only;
**Use These Coordinates is disabled until primary-source compatibility is verified**.

The amber CR1 globe marker is the documented backend research-input reference,
with unverified absolute source registration. View on Globe and marker inspection
preserve mission coordinates. The catalog is not a scientific result, a source of
site-specific readiness, or a landing safety certification. Manual inputs remain
available; the API readiness gate is unchanged.

See [SOUTH_POLE_SITES_VALIDATION.md](SOUTH_POLE_SITES_VALIDATION.md) for source URLs,
repository evidence, coordinate/coverage limits and test status.

## Coordinate evidence recovery (Command 10.1)

External research findings now identify separate Data Book R01/Site01 and
R04/Site04 reference centres, dated 2022/2024 candidate contexts and the USGS
planetographic Mons Mouton centre. Source coordinates are typed separately from
backend analysis inputs and labeled **NOT_REVERIFIED_IN_TASK**: eight fresh GET
attempts still failed at the network tunnel with 403 and yielded no documents.

All five coordinate transfers remain disabled. Longitude representation changes
(e.g. -137.49 → 222.51 E) do not verify latitude or frame. CR1 remains a distinct,
limited visual research input; no source-only marker or readiness claim is added.
See [NASA_COORDINATE_EVIDENCE_VALIDATION.md](NASA_COORDINATE_EVIDENCE_VALIDATION.md)
and [retrieval evidence](evidence/command-10-1-source-retrieval.json). The earlier
Command 10 validation document and its 403 history are preserved.

## Command 10 final completion

The five-card explorer now leads with coordinate/status summaries and actions,
with full source history and exact unlock requirements in expandable details.
The 2025 Data Book, LRO coordinate standard, 2022 CR1 reference and PDS latitude
definitions join the evidence ledger. All A–K source groups were attempted;
13 official URLs again failed at the tunnel with 403 and no documents were read.

The 2023–2025 table comparison remains **NOT VERIFIED**, and all production
coordinate transfers remain locked. Runtime validation now also rejects malformed
untyped source/proof objects safely. The existing CR1 visual reference and manual
mission planning remain available. See [COMMAND_10_FINAL_VALIDATION.md](COMMAND_10_FINAL_VALIDATION.md)
and [final retrieval records](evidence/command-10-final-retrieval.json).

## Scientific backend integration (Command 11)

The scientific job API lives on backend PR #28; this frontend branch does not merge
that backend code. See [COMMAND_11_INTEGRATION_VALIDATION.md](COMMAND_11_INTEGRATION_VALIDATION.md)
for its pinned contract, remaining merge gate and scientific limits.

For a separately running local backend on port 8010:

```bash
API_PROXY_TARGET=http://127.0.0.1:8010 npm run dev -- --host 0.0.0.0
```

Health readiness and bounded research capability are independent. `Run Analysis`
keeps its strict readiness guard. `Run Research Prototype` uses explicit edited
requirements and validated capabilities, then follows a durable job ID. Stop
Waiting does not cancel server computation; Request Cancellation does. Navigation
preserves the job, form and coordinate; input edits/reset invalidate old evidence.
A full reload does not restore an in-memory job reference.

Recorded mode is explicit, PRECOMPUTED and exact-match only; never a live fallback.
No catalog coordinate transfer has been unlocked. Prototype results retain warnings
about source/registration/independent validation and cannot certify landing, power
or radio-link success. Production still needs an operator-provided `/api` reverse
proxy (Vite's development proxy is not a production service).

Optional read-only integration evidence, with an isolated backend checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 /path/to/backend-venv/bin/python scripts/validate_backend_contract.py \
  --backend-root /tmp/lunar-backend28 --fixtures .validation/command11-contract-fixtures.json
TEST_BROWSER_PATH=/usr/bin/chromium LUNAR_FRONTEND_URL=http://127.0.0.1:5174 \
  node scripts/check_real_backend.mjs
```

The unit suite exports the controlled contract fixture into ignored `.validation/`.
The browser script requires an actual backend and Vite proxy; it does not inject
science data or mock network responses. Recorded evidence is not a new live NASA
calculation. Large screenshots/logs stay ignored.

## Alternative Explorer (Command 12)

Open Alternative Explorer and choose **Temporal — Better Start Time** or
**Local — Better Site**. **Recorded Evidence** is the default and works with the
backend/internet unavailable once the frontend is served. Dev/build verifies the
unchanged repository demo manifest, payload checksums and upstream evidence before
embedding them; no preparation command or external data request is required.
The local radar, candidate list and optional NASA globe share selection. Compare
only candidates within the selected scenario; use **Load Candidate Parameters**
to copy inputs into Mission Setup without starting an analysis. Explicit
requirement activation is preserved.

**Live Optimizer** requires configured backend capabilities and a completed,
current live Research Prototype Analysis with server-provided window evidence.
Run it explicitly; recorded demos never unlock readiness. Stop Waiting/navigation
stops local polling, while Request Cancellation asks the server to stop. Partial
results remain partial and live failures never substitute recorded evidence.
See [COMMAND_12_ALTERNATIVE_EXPLORER_VALIDATION.md](COMMAND_12_ALTERNATIVE_EXPLORER_VALIDATION.md)
for contracts, hashes, tests, resource limits and the blocked live NASA validation.
