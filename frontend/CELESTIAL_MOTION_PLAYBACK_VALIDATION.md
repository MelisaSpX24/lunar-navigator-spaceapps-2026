# Command 08.1 — guarded visual motion and UTC playback

## Scope and baseline

Based on main `6d78a01`, containing PR #18 (frontend Command 08) and PR #17
(backend disk visibility work). Backend models/routes were inspected read-only.
Only frontend files change; no dependencies, NASA JPEG, global globe conversion,
backend code or shared contracts change. Command 08's validation document remains
as the historical exact-sample implementation record.

Clean baseline: `npm ci`, typecheck and build succeeded; 290 Vitest and 158
Chromium Playwright tests passed. The production `dist` is never rebuilt while
its browser tests are active.

## Trust boundary and cached tracks

The existing `completedResult()` and ScenarioProvider remain unchanged: only
HTTP 200, COMPLETED, current/sent/echoed request matches and ready health allow
scientific rendering. `checkSeries()` validates Sun and Earth independently;
invalid UTC axes invalidate the series, and an invalid body does not invalidate
the other body. Validated data is cached for the response, with at most 5000 rows.
Preparation computes direction vectors, neighboring-segment guards and cadence
once. Selection and exact readout use binary searches, not per-frame validation.
Source rows, request, windows, decision and score objects are never mutated.

## Exact Samples and Smooth Visual Preview

Exact Samples is the default. Exact timestamps always use the unmodified backend
sample direction, even when smooth preview is on. Between samples, exact mode
withholds the markers and scientific readouts as in Command 08.

Smooth visual preview must be explicitly enabled. Each body independently returns:

- **BACKEND SAMPLE**: a validated exact sample with known direction.
- **VISUAL INTERPOLATION**: only a display direction between accepted neighbors.
- **NO SUPPORTED POSITION**: marker hidden, with the rejection reason in text.

An exact sample with unknown angles still retains its backend scientific fields
in the readout, but has no supported marker position. Interpolated objects have
only a direction, endpoint timestamps and horizon ID. They cannot carry disk
state, fraction, condition, clearance or joint-condition values. Intermediate
readouts state that no exact sample exists and visibility has not been evaluated.

## SLERP, ENU and wrap

Endpoint azimuth/elevation values pass through existing `renderDirection(..., 1)`.
Logical ENU remains X East, Y Up, Z North; the existing renderer reflection makes
North negative Z in right-handed Three.js. No global lunar conversion changes.

For an accepted pair of unit vectors, spherical linear interpolation uses the
selected UTC's fractional position between the two endpoint UTC ticks. Very
small separations use normalized linear blending to avoid division by zero.
Results are normalized unit vectors, scaled only by the illustrative radius 9
inside the renderer. 359°→1° and 1°→359° therefore cross North, not 180°.

This shortest visual arc is not a proven astronomical trajectory. No inverse
angle values are written into backend models, and no visibility solver runs.

## Conservative presentation guards

A segment is accepted only when both adjacent validated samples have known
azimuth/elevation, their timestamps increase, and all these conditions hold:

- Gap is at most **600 seconds** and at most **3 × lower-median series cadence**.
- Angular separation is at most **15 degrees**.
- Both horizon IDs are identical, non-null and present in validated profiles.

The cadence rule rejects isolated gaps even within the absolute cap. The lower
median is used deliberately to resist isolated long intervals. These are
conservative UI limits, not NASA mission thresholds or scientific accuracy
bounds. Some legitimate trajectories will be withheld. No claim is made that
one cap works for every lunar data product. Future adjustment needs review of
actual sampling conventions; the UI does not silently relax a guard.

No skipped-null bridges, extrapolation, antipodal arc, different-profile bridge
or large-angle guessed path is drawn. Missing horizon/quality/coverage never
becomes clear visibility. Existing quality and incomplete-coverage warnings stay
visible. Even a permitted arc may contain unknown scientific events; no event,
visibility fraction, window boundary, energy, radio link, decision or score is
inferred. Existing paths remain discrete backend points, independent of motion.

## One UTC clock and lifecycle

CelestialTimeProvider owns the same selected UTC for slider, scene, readouts and
Mission Timeline playhead. The playback hook owns only a run anchor and elapsed
wall time, not a second independently rendered UTC. Play is explicit; no autoplay.

Playback speeds are full-operation equivalents of 30, 60 or 120 wall-clock
seconds. Starting partway through the operation takes the corresponding remaining
fraction of that duration. Pause preserves UTC. Replay explicitly resets to the
operation start and runs. The operation end clamps exactly and stops; no loop.
Manual slider/sample selection, mode or speed change pauses first.

One requestAnimationFrame loop uses measured elapsed milliseconds. UTC arithmetic
uses integer microseconds and clamps to operation bounds. React updates are
capped at approximately 30 Hz. A frame interruption over 250 ms pauses without
jumping; the user must restart. Hidden tabs pause and never auto-resume. This
conservative rule may pause on overloaded devices rather than leap across data.

Effects cancel frames/listeners on pause, unmount, response replacement, invalid
results or scenario reset. StrictMode setup/cleanup leaves one active loop.
Route re-entry defaults to exact mode and the first sample, with playback paused;
ScenarioProvider still preserves mission inputs. WebGL failure pauses playback
and removes the Canvas; an explicit retry restores the scene. Time controls and
2D data remain accessible, and numeric playback can be explicitly restarted
without forcing a WebGL renderer to run or retry.

Playback is disabled for null/empty/single-sample data or fewer than two known
body directions. Smooth playback additionally requires at least one accepted
segment. Unsupported sections within the full operation still hide markers.

## Accessibility, mobile and resource ownership

Reduced-motion disables smooth preview and playback while leaving manual sample
controls available. A preference change stops playback. All controls have labels,
keyboard access and existing focus styling. Playback status announces transitions;
rapid UTC outputs have aria-live off while playing, avoiding frame-rate speech.

Existing mobile Enable/Pause 3D interaction, page scrolling, capped DPR, lazy
scene, demand rendering and fixed observer camera remain. Camera state does not
change UTC and visual motion does not change camera state. SUN/EARTH labels stay
billboarded, with illustrative rather than astronomical disk size.

Textures remain memoized by body name and are explicitly disposed. Path buffers
are memoized by immutable source rows and disposed with their geometry. Changing
time does not allocate sprite textures or rebuild sample paths. No new asset,
HTTP/DEM request or dependency is introduced. Existing 2D tables and window
half-open/censored/null/empty semantics remain intact.

## Tests and scientific limits

Controlled populated states exist only in test code and remain TEST_FIXTURE.
The scene/readouts keep `TEST DATA — synthetic celestial positions` and add
`VISUAL INTERPOLATION — not a computed science sample` when applicable.

The real API still returns science-not-ready / 503 NOT_RUN. Backend's newly
merged internal disk engine is not treated as an available completed API result.
No real NASA scientific Sun/Earth series was validated by this frontend task.
Passing Pydantic or UI tests establishes model/display compatibility only.

Reproduction:

```sh
npm ci
npm run typecheck
npm run build
npm run test -- --run
TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e
git diff --check
```

## Final evidence

- PASS: npm ci, typecheck, production build and git diff --check.
- PASS: 325/325 Vitest tests, 21 files (baseline 290).
- PASS: 176/176 Chromium Playwright tests, no skips (baseline 158).
- PASS: actual GPU marker matrices at intermediate times; stable texture and
  buffer upload counts during time changes; existing disposal regressions.
- PASS: production JS excludes test fixture-specific identifiers.
- Screenshots inspected at desktop 1440×1000, tablet 820×1180 and mobile 390×844:
  interpolated markers, playing, exact samples, rejected gaps, operation end,
  WebGL fallback and mobile 200% controls. All populated scenes are TEST_FIXTURE.
- Native select text can truncate when closed at mobile 200% text; its options
  remain accessible when opened. No horizontal page overflow was detected.
- NOT RUN: real NASA scientific trajectory verification; no completed live series.

Build raw/gzip kB: entry JS 341.81/107.43; main CSS 20.48/4.67;
lazy HorizonScene 9.85/3.82; LunarGlobe 28.30/7.65; shared renderer
918.47/242.64. Existing >500 kB shared renderer warning remains.

Initial new unit assertions exposed floating-point normalization precision and
an ambiguous status selector; assertions now use 12-decimal vector precision
and the labeled playback status. Final full suites passed without skipped tests.


## Changed files

- `frontend/CELESTIAL_MOTION_PLAYBACK_VALIDATION.md`
- `frontend/README.md`
- `frontend/e2e/celestial-motion.spec.ts`
- `frontend/src/features/analysis-results/TimelineData.tsx`
- `frontend/src/features/celestial-timeline/Celestial.module.css`
- `frontend/src/features/celestial-timeline/CelestialTime.test.tsx`
- `frontend/src/features/celestial-timeline/CelestialTime.tsx`
- `frontend/src/features/celestial-timeline/PositionStatus.tsx`
- `frontend/src/features/celestial-timeline/SelectedBody.tsx`
- `frontend/src/features/celestial-timeline/motion.test.ts`
- `frontend/src/features/celestial-timeline/motion.ts`
- `frontend/src/features/celestial-timeline/playback.test.tsx`
- `frontend/src/features/celestial-timeline/selection.ts`
- `frontend/src/features/celestial-timeline/usePlayback.ts`
- `frontend/src/visualization/local-horizon/CelestialLayer.tsx`
- `frontend/src/visualization/local-horizon/HorizonScene.tsx`
- `frontend/src/visualization/local-horizon/LocalHorizon.tsx`
