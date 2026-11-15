# Command 09 — observer-centred angular panorama

## Scope and trust boundary

Based on main d1e5dce, including frontend PR #20 and backend PR #19. Backend
AGENTS.md and existing result validation were reviewed; no backend, contracts,
global lunar coordinate, NASA asset or dependency changes are made.

The existing completedResult and per-panel checkHorizons gates remain. A trace
is built only from validated HorizonProfile points. No DEM cells, physical
terrain mesh, visibility, disk fraction, event, score or optimizer is computed.
All filled browser tests use controlled responses; they are not NASA measurements.
PRECOMPUTED and LIVE_COMPUTED origin display tests are controlled enum checks,
not live-source scientific evidence. Unknown origin stays explicitly unknown.

## Panorama and controls

The horizon occupies a full-width desktop dashboard row. The larger canvas leads
the scene in both DOM and visual order. Camera orientation and display mode sit
beside it, with controls below rather than covering the canvas. UTC and body
statuses remain text-accessible. Longer profile metadata follows the scene;
quality, incomplete coverage and TEST DATA warnings remain visible.

The camera remains at the origin. Pointer sensitivity now scales with FOV and
viewport height, giving consistent angular movement across screen sizes and
zoom levels without adding inertia, animation loops or reduced-motion conflicts.
Cardinal buttons, bounded pitch/FOV, reset, touch enable/pause and scrolling are
preserved. Camera state never changes scenario coordinates or UTC.

## Sample Points and Panoramic Trace

Sample Points is the default; original supplied angular points always remain
visible. Panoramic Trace adds thin muted green line segments, visually distinct
from brighter green sample markers and amber Sun/cyan Earth. The checkbox is
keyboard-accessible and can be disabled at any time. It never creates a surface.
A zero elevation point is preserved. A null point creates a gap.

Trace segments require adjacent supplied points with known elevation and a
strictly positive azimuth gap. The maximum gap is the smaller of **5 degrees**
and **twice the lower median of adjacent profile azimuth gaps**. This resists
isolated gaps; sparse profiles can have no accepted edges. No point is skipped
to reach a later known sample. Last and first are never joined across 360/0,
even with coverage_complete=true. This is a conservative visual proximity policy,
not a scientific terrain continuity assertion or a NASA threshold.

The explicit warning says: "Visual trace connects nearby supplied samples.
Terrain between samples has not been independently measured by this view."
When no edge is accepted, "Insufficient sampled coverage for panoramic trace."
appears. Null/empty/all-null profiles produce no measured trace. Orientation
preview remains available without scientific results; unknown sectors never
become flat ground or clear visibility.

## Coordinates, profiles and scientific integration

Existing logical ENU (East X, Up Y, North Z) and North reflection into Three's
right-handed rendering are unchanged. N/E/S/W and elevation guide rings remain
coordinate references, not terrain. No automatic seam closure is performed.

Profile selection changes samples, trace, height, range and source IDs together.
It does not change mission inputs. Existing Sun/Earth horizon-ID mismatch and
missing-profile warnings remain. Trace position relative to a celestial marker
never determines disk visibility. The existing exact/smooth modes, SLERP guards,
UTC playback and shared playhead remain responsible for their prior functions.
2D horizon charts and tables still use the identical backend profile points.

Quality status, coverage flags, limitations and source IDs remain visible through
existing panels. Source IDs and checksums are not independently verified NASA
provenance. TEST_FIXTURE horizon/celestial warnings remain explicit; no fixture
is imported into production code or automatically served as demo content.

## Performance and accessibility

Trace computation is memoized by profile identity. Owned BufferGeometry keeps
its attributes until explicit disposal, ensuring GPU buffer cleanup. Time,
playback and camera changes reuse geometry. No new package or network asset is
needed. Existing lazy loading, demand rendering, DPR cap, context loss/retry,
label cleanup and fallback preserve 2D data access.

Checkbox, profile selector and direction buttons retain labels/focus styling.
Readouts and warnings use text, not color alone. Mobile has a 420px canvas;
desktop uses a 480–680px responsive height. No animated camera transition was
introduced; existing reduced-motion playback behavior remains.

## Verification

Commands: npm ci (using writable /tmp npm cache), npm run typecheck,
npm run build, npm run test -- --run, TEST_BROWSER_PATH=/usr/bin/chromium npm run
test:e2e, git diff --check, git status. Baseline runs from an isolated main archive
on port 4174; current build runs on 4173. Never rebuild dist during active tests.

Final test counts, bundle sizes and reviewed screenshots are appended below.

## Scientific limits and Command 10 integration

No real NASA horizon trajectory/terrain validation was performed. The actual API
is still gated by readiness and normal empty/orientation states remain truthful.
Trace guards can be reviewed against future actual sampling conventions. No
new science endpoint, observer-height computation or optimizer is implied.

During verification, concurrent browser suites overloaded the environment. The
new playback UI test reached the existing >250ms frame-stall safety pause; it
now uses Playwright's controlled clock, as the existing playback tests do. A
concurrent Vitest run also timed out under that load. Final verification is run
sequentially without increasing timeouts or weakening lifecycle guards.


Visual review also found that the provenance badge could cover most of the
mobile sky at 200% text. Its scrollable height is now capped at one quarter of
the canvas; complete warnings also remain in the surrounding text panels.


## Final results

- PASS: baseline 325 Vitest / 176 Playwright from isolated current main.
- PASS: npm ci with /tmp cache, typecheck, production build, git diff --check.
- PASS: final 332/332 Vitest tests (22 files), 188/188 Chromium Playwright tests,
  no skipped tests. All prior regressions retained.
- PASS: trace endpoint/gap/null/seam tests and actual GPU buffer reuse/disposal.
- PASS: fixture-specific identifiers absent from production JS; NASA JPEG hash
  unchanged (f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170).
- Visual screenshots reviewed: desktop/tablet/mobile sample/trace modes, changed
  profile, celestial samples/smooth preview and 200% text. Normal-size panoramas
  show the angular guides, sample markers and celestial labels without overlays
  covering the controls. At mobile 200% text, wrapping produces a very long
  inspector; no horizontal overflow is reported by the browser tests. Full-section
  tall screenshots do not provide clear WebGL imagery at that scale; the numeric
  and 2D alternatives remain available. Do not treat those images alone as proof
  of detailed 200% GPU visual quality.
- Existing WebGL fallback, incomplete/null-sector, touch-scroll, reduced-motion,
  NASA globe, playback and 2D panel tests pass.
- NOT RUN: scientific validation against actual NASA terrain measurements.

Final raw/gzip kB: entry JS 342.24/107.54; CSS 21.07/4.79; lazy HorizonScene
11.43/4.27; LunarGlobe 28.30/7.65; shared renderer 918.47/242.64.
The existing >500 kB shared renderer warning remains. No dependency changes.

## Changed files

- `frontend/PANORAMIC_HORIZON_VALIDATION.md`
- `frontend/README.md`
- `frontend/e2e/panoramic-horizon.spec.ts`
- `frontend/src/screens/MissionAnalysis.tsx`
- `frontend/src/screens/Screens.module.css`
- `frontend/src/visualization/local-horizon/HorizonScene.tsx`
- `frontend/src/visualization/local-horizon/HorizonTrace.tsx`
- `frontend/src/visualization/local-horizon/LocalHorizon.module.css`
- `frontend/src/visualization/local-horizon/LocalHorizon.tsx`
- `frontend/src/visualization/local-horizon/ObserverControls.tsx`
- `frontend/src/visualization/local-horizon/SkyReferences.tsx`
- `frontend/src/visualization/local-horizon/trace.test.ts`
- `frontend/src/visualization/local-horizon/trace.ts`
