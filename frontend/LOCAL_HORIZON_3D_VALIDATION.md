# Command 07 — interactive local angular horizon

## Scope and base

Frontend only, based on fetched main `9744559` (PR #13 merged at `20e20c4`,
plus backend PR #14). The backend model, API, DEM pipeline, global lunar
coordinates, globe renderer and NASA JPEG were not changed. No deployment.

## Architecture and trust boundary

MissionAnalysis retains Current Scenario, Response Status and seven panels.
LocalHorizon adds a lazy HorizonScene above the existing HorizonData 2D charts
and tables. The shared ScenarioProvider is unchanged. Only completedResult's
current, request-matched, HTTP 200 / COMPLETED / ready response reaches the
scientific view. checkHorizons is reused unchanged for both 2D and 3D.

No response, cancellation, scenario edit, unavailable backend, 503, non-completed
execution, invalid envelope or mismatched request produces scientific geometry.
Orientation preview still works, with explicit text that no measured horizon or
celestial positions are available. An invalid/missing coordinate is not labelled
a scientific observer site. Valid coordinate summaries derive from the same
scenario state as the global sphere marker; camera motion never writes it.

Profile null/empty/invalid/over-limit data leaves orientation guides only. The
existing 2D section retains its distinct data messages. A valid all-null profile
retains metadata with zero known samples, never an unobstructed horizon.

## ENU and rendering handedness

Logical directions use X=East, Y=Up, Z=North:

```
x = cos(elevation) * sin(azimuth)
y = sin(elevation)
z = cos(elevation) * cos(azimuth)
```

Degrees convert to radians. Azimuth is [0,360), elevation [-90,90]. The API
model itself constrains ranges but does not describe handedness. Read-only
`backend/app/science/geometry.py::direction_angles` uses atan2(east,north),
confirming N=0/E=90/S=180/W=270 for the existing astronomical implementation.
The backend team should retain/document this convention for future horizon
producers as well; no measured horizon endpoint is available for end-to-end
scientific verification.

E/U/N in that component order is left-handed. `renderDirection` explicitly
reflects logical North at the Three.js boundary: `(x,y,-z)`. Thus renderer +X
is East, +Y Up, -Z North, with conventional right-handed cameras. Logical data
and UI always use the specified ENU formula. This prevents East appearing on
the left of a north-facing observer or mirrored text. Camera projection tests
verify East/right and positive elevation/up. This local adapter is unrelated
to the existing global latitude/longitude mapping and changes none of it.

## What is drawn

SkyReferences draws coordinate meridians every 30°, elevation reference rings
at -60/-30/0/30/60°, ticks, cardinal labels and elevation labels. These are
explicitly coordinate guides, not terrain. The dark sky contains no fake stars,
Sun, Earth, mountains, ground mesh or inferred shadows.

HorizonSamples converts every known sample of one validated profile into a
point at a fixed display radius of 10. No lines, triangles, filled sectors,
interpolation or seam closure are built from scientific samples. Null samples
create no vertex; numeric zero remains a real vertex. Missing and unsampled
sectors stay unknown. Display radius is not metres or DEM range. There is no
claim of a continuous or physically reconstructed terrain silhouette.

Both renderings use the same server points. 2D continues to show all profiles;
3D selects one, with ID, height in metres, range in metres, coverage and source
IDs. A selection belongs to its response object; new responses or missing IDs
safely fall back to the first current profile. Different heights are not merged
or mapped automatically onto Sun/Earth device heights.

## Camera, mobile, accessibility

ObserverControls keeps camera position (0,0,0), up vector fixed and roll/pan
unavailable. Pointer drag changes azimuth/elevation; wheel/pinch changes FOV.
Pitch is bounded to ±85° to avoid pole singularities; FOV 35–100°. North/East/
South/West, look up/down, level, zoom and reset buttons are keyboard accessible.
The numeric orientation output exposes azimuth/elevation/FOV. All movement is
instant; there are no animations or inertia, including reduced-motion mode.

Coarse-pointer devices start paused. Enable/Pause 3D interaction controls pointer
capture and touch-action; pausing restores native page swipes. Controls and
metadata sit outside the canvas. Canvas heights are 420px desktop/tablet and
340px mobile; controls wrap at 200% text. 2D tables remain the numeric alternative.

## Resource lifecycle and failure

R3F/Three are existing pinned dependencies; no packages were added or upgraded.
The renderer is lazy, uses demand frames and caps DPR at 1.5. No texture/DEM/
NASA network asset is needed by this scene. Cardinal label textures are small
locally generated coordinate labels, not scientific imagery. Geometries and
materials are declarative R3F resources; owned label textures explicitly dispose.
Pointer/wheel/context listeners clean up on pause or unmount. Only the active
route mounts its WebGL scene. Shared renderer code is a lazy build chunk.

Error boundaries cover lazy loading and Canvas errors. Context loss removes the
scene, disables controls, reports unavailability and offers Retry 3D view. 2D
and all other panels stay available. A failed renderer is never reported ready.

## Scientific quality

TEST_FIXTURE has a persistent, scene-adjacent `TEST DATA — synthetic horizon
profile` notice. Production has no fixture import or automatic demo fallback.
QualityNotice preserves LIMITED/INSUFFICIENT/NOT_ASSESSED or unknown coverage.
Incomplete profiles explicitly say `Incomplete terrain horizon coverage`.
Source IDs alone are not independent NASA provenance evidence. Geometry does
not measure occultation, visibility, power, radio links or landing safety.

## Verification evidence

Baseline: npm ci, typecheck, build; 242 Vitest / 115 Playwright PASS.
Final check counts and visual evidence are recorded below after execution.

Test source: directions.test.ts (ENU axes, bounds, camera projection and null/
seam guards); LocalHorizon.test.tsx (metadata, profiles and fallback);
ObserverControls.test.tsx (fixed origin, external commands, listener cleanup);
local-horizon.spec.ts and touch.spec.ts (real Chromium WebGL and interaction).
All populated results are controlled TEST_FIXTURE HTTP responses in tests only.
No real scientific horizon was received or validated.

## Command 08 integration points

localDirection/renderDirection can position future validated angular body
samples. HorizonScene camera state remains separate from selected profile/data.
Profile IDs are preserved for future horizon_id correlation. No time slider,
celestial marker, ephemeris or visibility calculation is implemented here.

### Build and unit checks

- `npm_config_cache=/tmp/lunar-npm-cache npm ci`: PASS; existing 125 packages.
  The cache override uses a writable location; package/lock files are unchanged.
- `npm run typecheck`: PASS.
- `npm run build`: PASS.
- `npm run test -- --run`: **270/270 PASS**, 17 files; no skipped tests.
- Unchanged backend Pydantic check: **3 TEST_FIXTURE JSONs accepted, 4 invalid
  controls rejected**. This is model compatibility, not scientific verification.
- NASA JPEG SHA-256 remains
  `f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170`.

Bundle sizes (decimal kB, raw / gzip): entry JS **327.55 / 102.91**; entry CSS
**19.53 / 4.51**; local HorizonScene **7.33 / 3.06**; shared lazy renderer
**918.46 / 242.63**; globe-specific lazy JS **28.29 / 7.64**.
Baseline entry JS was 324.28 / 101.80 and globe JS 946.56 / 249.72. Vite now
shares existing Three/R3F code between lazy scenes rather than duplicating it.
The existing >500kB renderer warning remains; no claim of hardware-GPU or
physical-device performance verification is made.

### Changed files

All files below are under frontend/:

- README.md
- LOCAL_HORIZON_3D_VALIDATION.md
- e2e/analysis-results.spec.ts
- e2e/globe.spec.ts
- e2e/local-horizon.spec.ts
- e2e/touch.spec.ts
- src/screens/MissionAnalysis.tsx
- src/test/App.test.tsx
- src/visualization/local-horizon/directions.ts
- src/visualization/local-horizon/directions.test.ts
- src/visualization/local-horizon/ObserverControls.tsx
- src/visualization/local-horizon/ObserverControls.test.tsx
- src/visualization/local-horizon/SkyReferences.tsx
- src/visualization/local-horizon/HorizonScene.tsx
- src/visualization/local-horizon/LocalHorizon.tsx
- src/visualization/local-horizon/LocalHorizon.test.tsx
- src/visualization/local-horizon/LocalHorizon.module.css

The existing test expectations changed only where behavior intentionally changed:
Mission Analysis now has a local Canvas and orientation preview, while the global
Canvas still unmounts. Existing 2D data expectations and scientific guards remain.


### Visual review and regression scope

Real Chromium screenshots inspected: desktop/tablet/mobile Orientation Preview;
desktop low/high profiles (changed height and sample positions); mobile populated
profile; tablet unknown-sector/INSUFFICIENT state; mobile WebGL-unavailable;
mobile 200% text. Missing coverage and TEST DATA remain explicit. Reference
labels were enlarged after visual review. A 200%-text panel-width issue found
visually was fixed with an explicit bounded scene width and a button-containment
assertion (page-level overflow alone had not detected it).

Screenshots are generated under ignored test-results/local-horizon-*/:
Orientation-preview.png, Backend-profile-low.png, Backend-profile-high.png,
Unknown-sectors.png, WebGL-unavailable.png, Horizon-200-percent.png.
They are controlled test evidence, not scientific observations. Existing global
Moon screenshots and 2D/table checks remain in the complete regression suite.
Long profile selector text can be visually shortened by the native select at
narrow widths; full active profile ID/height/range are repeated as wrapping text
below it. Mobile/200% content intentionally scrolls vertically.

Real horizon science verification: NOT RUN (no measured backend horizon result).
Physical-device, Safari/Firefox and hardware-GPU performance: NOT RUN.
No production fixture data was found in the built JavaScript chunks.

### Final browser result

`TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e`: **137/137 PASS**, no
skips or failures, after the final 200%-text panel-width fix. This retains all
115 baseline executions and adds 22 executions for local-horizon behavior.
270/270 Vitest, typecheck and production build also passed on this final code.
Real WebGL POINTS draw counts verify known samples and profile changes; resource
checks observe GPU buffer/label-texture deletion after route unmount. Native
Chromium touch events verify rotation/pinch and page scrolling after pause.
The 200% test now checks both document overflow and each button's containment
inside the local scene region. Initial test-selector failures (R3F wrapper vs
actual canvas) were fixed without weakening assertions; final checks pass.

Logs are retained under ignored .validation/command07-baseline-*,
command07-final-unit.log, command07-final-build.log and command07-final-e2e.log.
`git diff --check` passed; protected paths and dependency files have no diff.
