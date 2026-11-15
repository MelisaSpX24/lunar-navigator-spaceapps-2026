# Command 08 — celestial samples and shared UTC selection

## Scope and source

Based on fetched main `1429577` (PR #16 local horizon and PR #15 backend terrain
horizon engine). Only frontend files change. The backend-local AnalysisResult
1.0 model and API routes were inspected read-only. Health still reports science
not ready; the analysis route returns 503/NOT_RUN. No real scientific Sun/Earth
time series was obtained. Controlled test responses are explicitly TEST_FIXTURE,
not NASA measurements or scientific verification.

## Trust boundary

MissionAnalysis still uses completedResult(): HTTP 200, COMPLETED, ready health,
and current/sent/echoed request agreement. ScenarioProvider, request cancellation,
readiness and response validation are unchanged. The new CelestialTimeProvider
receives only this gated result. It reuses checkSeries independently for Sun and
Earth, including UTC ordering, bounds, nullable fields, enums and finite numeric
ranges. Invalid Sun data does not suppress valid Earth data (and conversely).
A malformed time axis invalidates both. Existing 5000-record limit applies; no
silent sampling or repair. The 2D panels use the same validator and still retain
all of their chart/table and display-limit behavior.

## One shared selected time

One provider is scoped to the Mission Analysis route. It owns the selected UTC
stamp and caches both validated body sequences. Exact backend sample buttons
preserve microseconds and original UTC strings. The range input covers the
entire request start/end interval with 10,000 presentation subdivisions; it does
not imply scientific sampling at those subdivisions. Exact sample navigation
is independent of that range quantization. BigInt UTC ticks retain ordering;
formatting also handles pre-epoch fractional seconds without truncation errors.

A new response defaults to its first validated sample; an invalidated result
clears selection. Leaving the route discards time selection; returning starts
at the first sample. Form/scenario state remains preserved by ScenarioProvider.
Camera motion and profile/path choices do not change time or mission inputs.
No fetch, analysis, DEM request, worker or scientific solver is triggered by
any time control. Null/empty series disable scientific selection. A single
sample has no previous/next and no animation.

## No interpolation or playback in this version

Only exact backend times produce marker positions and scientific readouts.
Between samples (including sparse intervals), or after the last sample before
the operation end, the UI explicitly states `No sample at selected time` and
withholds current markers/readout values. There is no nearest-sample ambiguity,
interpolation, guessed ephemeris, derived disk fraction or computed visibility.
Optional Play/Pause is intentionally not implemented. Manual controls have no
automatic timer, animation or hidden render loop and respect reduced motion.

359° and 0° directions are converted independently via the existing ENU mapping.
No connecting segment or interpolation can take the long way around the seam.
This conservative choice avoids defining unsupported scientific continuity or
visual interpolation thresholds.

## Markers, trajectories and horizon correlation

Existing localDirection/renderDirection are reused unchanged: logical X East,
Y Up, Z North with North reflected at the right-handed Three renderer boundary.
Global lunar coordinates and NASA texture/material code are untouched.

SUN is an amber ring, EARTH a cyan diamond; sprites have upright text labels.
Labels sit above/below the same angular anchor so coincident directions retain
separate labels, and independent numeric readouts always remain accessible.
Markers are illustrative, not to angular scale; angular_radius_deg is shown as
backend metadata only. Disk state does not hide a geometric direction: NONE is
not equivalent to missing angles. No frontend occultation test is performed.

Sun/Earth paths have independent toggles, initially off. They show only discrete
validated direction points for the supplied operation, no lines or surfaces.
Unknown directions are omitted; known zero values remain. No unknown sector,
time gap or seam is filled. At most 5000 samples per validated body are admitted.
Buffers are memoized against each validated body sequence, not the chosen time.

Each body's horizon_id is compared with current validated profile IDs and the
active 3D profile. Null relation, absent profile and different active profile
have distinct text. Profiles are not merged or selected automatically based on
observer height. A body above a plotted point is not evidence of visibility.
Geometric Earth visibility is not a radio/data-rate guarantee; Sun visibility
is not electrical power. Quality and incomplete-coverage warnings remain.

## 2D / 3D synchronization

The scene UTC, current body marker, Sun/Earth Selected UTC Sample sections and
Mission Timeline UTC readout all consume one provider state. Timeline bars get
a labelled vertical playhead. Supplied [start,end), censored bounds and
null/empty windows remain untouched; the playhead discovers no new window.
Selected-body sections preserve null/zero/false/UNKNOWN/NONE/PARTIAL exactly.
Existing full-series SVGs and accessible numeric tables are not replaced.

## Lifecycle, accessibility and mobile

The existing lazy scene, demand frames, DPR limit, context-loss removal/retry,
fixed observer camera, mobile enable/pause and cleanup behavior are retained.
Marker label textures dispose explicitly; R3F owns sprite materials. Path
geometries own their position attributes and dispose explicitly while those
attributes are still attached, ensuring their WebGL buffers are deleted. No new package, large asset or NASA request is added. When WebGL fails,
UTC controls, numeric samples and existing 2D panels remain available.
Range input is labelled and exposes selected UTC through aria-valuetext. Exact
sample buttons and path checkboxes are keyboard accessible. Status is textual,
not color only. Wrapping controls/readouts are checked at desktop/tablet/mobile
and 200% text. TEST_FIXTURE is identified in the scene and selected-body panels;
production imports no fixture and includes no automatic demo mode.

## Command 09 integration points

Future features may consume the gated result and exact selected stamp. This
command adds no optimizer, A/B comparison, score engine, playback, physical
terrain or visibility solver. New backend conventions require a contract review.

## Verification

Validation was performed with `/usr/bin/chromium` and the production Vite build.
Initial baseline run was contaminated by rebuilding its served dist while it
was still running (135 pass, 2 fail). This was a test orchestration error, not a
clean baseline result. The clean baseline rerun from an isolated origin/main archive passed 137/137
on port 4174. Current-code tests use port 4173 with a stable production build.


### Fixes found during verification

- Legacy no-horizon tests now distinguish valid celestial samples from pure
  orientation preview. The absence of terrain does not invalidate body directions.
- Mobile panel-order assertions capture all rectangles in one browser frame,
  avoiding measurements across a lazy-scene layout change. No overlap allowance
  was relaxed.
- Marker text has an opaque background so coordinate labels do not show through.
- GPU cleanup tests track the two actual marker textures and the two actual
  path buffers rather than guessing total renderer resource counts. Paths now
  own and dispose their complete geometry; detached declarative attributes had
  prevented reliable explicit buffer deletion.

### Scientific evidence and production separation

The test-only three-sample celestial JSON was accepted by the unchanged backend
Pydantic AnalysisResult model. Existing result checks accepted three valid cases
and rejected four invalid cases. This proves fixture/model compatibility, not
astronomical correctness. No live scientific Sun/Earth series was available.

### Visual review

Screenshots were inspected at 1440×1000, 820×1180 and 390×844: exact first/middle/
last directions, 359°/0° sampling, partial visibility, differing horizon IDs,
missing body direction, coincident directions, explicit TEST DATA and incomplete
coverage, WebGL loss with numeric/2D access retained, and a mobile 200% UTC selector.
Labels, controls and readouts remain accessible; arbitrary camera framing can
move a marker outside the view, while the numeric readout remains available.
Screenshots are controlled TEST_FIXTURE evidence, never real NASA observations.

### Reproduction

```sh
npm ci
npm run typecheck
npm run build
npm run test -- --run
TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e
git diff --check
```

Do not rebuild `dist` during an active production-preview browser test run.


### Build sizes (decimal kB, raw / gzip)

| Chunk | Command 07 baseline | Command 08 |
| --- | --- | --- |
| Entry JavaScript | 327.55 / 102.91 | 333.75 / 104.76 |
| Main CSS | 19.53 / 4.51 | 20.34 / 4.64 |
| Lazy HorizonScene | 7.33 / 3.06 | 9.97 / 3.88 |
| Lazy LunarGlobe | 28.29 / 7.64 | 28.29 / 7.63 |
| Shared Three/R3F renderer | 918.46 / 242.63 | 918.46 / 242.63 |

The existing >500 kB shared renderer warning remains. No dependencies were
updated. The production JS was checked for fixture-specific identifiers; none
were present. The existing NASA JPEG remains byte-identical, SHA-256:
`f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170`.


### Changed files

- `frontend/CELESTIAL_TIMELINE_VALIDATION.md`
- `frontend/README.md`
- `frontend/e2e/celestial-timeline.spec.ts`
- `frontend/e2e/local-horizon.spec.ts`
- `frontend/e2e/navigation.spec.ts`
- `frontend/src/features/analysis-results/TimelineData.tsx`
- `frontend/src/features/celestial-timeline/Celestial.module.css`
- `frontend/src/features/celestial-timeline/CelestialTime.test.tsx`
- `frontend/src/features/celestial-timeline/CelestialTime.tsx`
- `frontend/src/features/celestial-timeline/SelectedBody.tsx`
- `frontend/src/features/celestial-timeline/selection.test.ts`
- `frontend/src/features/celestial-timeline/selection.ts`
- `frontend/src/screens/MissionAnalysis.tsx`
- `frontend/src/test/celestialFixture.ts`
- `frontend/src/visualization/local-horizon/CelestialLayer.tsx`
- `frontend/src/visualization/local-horizon/HorizonScene.tsx`
- `frontend/src/visualization/local-horizon/LocalHorizon.tsx`


### Final results

- PASS: npm ci; no dependency or lockfile changes.
- PASS: npm run typecheck.
- PASS: npm run build (existing shared-renderer size warning only).
- PASS: npm run test -- --run — 290/290 tests, 19 files (baseline 270).
- PASS: TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e — 158/158,
  no skipped or failed tests (baseline 137).
- PASS: direct GPU marker matrix/projection checks, two marker texture releases
  and two path-buffer releases on route unmount, all three viewports.
- PASS: git diff --check and frontend-only scope; protected files unchanged.
- PASS: unchanged backend Pydantic model compatibility and production fixture
  identifier exclusion checks.
- NOT RUN: live NASA scientific Sun/Earth time-series validation. No such
  scientific result was available; all populated tests use TEST_FIXTURE.
- NOT RUN: optional visual interpolation and Play/Pause, intentionally omitted.

The earlier full browser run had 155 passes and 3 GPU cleanup failures. The
resource ownership fix above was verified first in all three focused tests and
then in the complete 158-test run. No failing test was skipped or weakened.
