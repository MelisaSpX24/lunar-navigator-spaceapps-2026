# Historical Frontend Command 03 — before the local texture upload

> Current status: Command 03.1 supplied and verified the local JPEG, enabled
> texturing and exercised the real browser/GPU path. See TEXTURE_VALIDATION.md.
> The blocker and results below describe the earlier run, not the current asset.

## Historical outcome

**PARTIAL / BLOCKED for the real NASA texture acceptance criterion.** The
interactive neutral sphere works; it must not be described as a NASA-textured
Moon. No scientific operation analysis is implemented.

Base: main `ba9c97fa9a6e082c14f3a36b4f70ea2d52b54834`, merge PR #6.
Command 02 `b7f900d2b986ecef4f3b0b818a63921e53eb1b00` is an ancestor.
Initial working tree was clean. Work uses `frontend/command-03-3d-moon` and is
confined to frontend/. Backend, data_pipeline, contracts and root files remain
unchanged. Mission Analysis and Alternative Explorer source files are unchanged.

## Official source and acquisition evidence — 2026-11-14

- Page: https://svs.gsfc.nasa.gov/4720/
- File: https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_2k.jpg
- Usage guide: https://www.nasa.gov/nasa-brand-center/images-and-media/

Each HTTPS request returned proxy CONNECT **403 Forbidden**, before any image
body. No JPEG was downloaded. JPEG magic/decoding, byte length, 2048×1024 size,
SHA-256, 2025 product dating, current usage notes and actual image orientation
are **NOT VERIFIED**. No substitute image, mirror, large TIFF/EXR or invented
checksum is used. The expected size/date and 0° centre convention were supplied
in the task; inaccessible source text has not been presented as inspected.

`public/assets/moon/README.md` records the blocker and future verification steps.
VERIFIED_TEXTURE_URL is null, so the app does not make a knowingly failing image
request. It displays “NASA texture unavailable — geometric preview only”. The
source link and attribution context remain visible, explicitly stating that NASA
imagery is not displayed. Use conditions remain an external prerequisite.

## Packages and rendering

Three.js 0.187.0, React Three Fiber 9.8.2, @types/three 0.187.0; existing React
and React DOM 19.3.1 are unchanged. Registry peer metadata was inspected: Fiber
requires React >=19 <19.4 and Three >=0.156. Drei 10.7.9 would accept React 19,
Fiber 9 and Three >=0.159, but is not installed: native Three OrbitControls are
sufficient. Exact versions and transitive resolutions are locked.

Only Mission Setup dynamically loads the 3D module. The sphere uses 64×32
segments, normalized radius 1, a neutral material and illustrative lights. The
fallback equator and prime-meridian lines are geometric references, not terrain.
DPR is capped at 1.5. Frames render on demand; no rotating animation, starfield,
postprocessing or second local-horizon Canvas is introduced.

Controls disable panning and constrain camera distance to 1.45–6 R. South focus
uses (0.18, -3.2, 0.18), about -85.5° camera latitude, avoiding an exact-pole
up-vector singularity. Reset restores (3.2, 0.7, 0.8). Buttons move instantly,
including for reduced-motion users. Camera readouts are actual visual camera
state in normalized units, not ephemerides or mission parameters.

Touch interaction starts paused on coarse-pointer devices. Enabling interaction
allows rotate/pinch/tap. Pausing disables OrbitControls and the Canvas event
layer and restores page swipes. Drag distance is tracked across the gesture,
including returning to the start point, to avoid unintended selections.

Owned texture results, late asynchronous texture results, geometry, controls
and custom event listeners are disposed. Canvas is unmounted on route exit and
after context loss. Error boundaries isolate render failure from navigation.

## Coordinate math versus real image alignment

Visual axes: +Y north; +X equator/0°; -Z equator/90°E. Forward coordinates use
radians and x=R cosφ cosλ, y=R sinφ, z=-R cosφ sinλ. Inverse coordinates use
the measured vector radius, clamped asin and atan2(-z,x). Invalid/zero vectors
are rejected. Longitude is canonical [-180,180); +180 and -180 share -180.
At poles it is null/undefined, never invented zero.

The actual SphereGeometry UV buffer is explicitly calibrated to the assumed
equirectangular convention: u=(longitude+180)/360, v=(latitude+90)/180; prime
meridian at u=.5, east 90° at u=.75, west 90° at u=.25. Duplicate seam UVs and
pole UV copies are retained. Tests inspect actual generated geometry attributes,
not only the coordinate helper. **PASS for math/geometry; BLOCKED for actual
NASA-image meridian, east-west direction and landmark calibration.** An image
must be inspected and landmark-matched before claiming that separate result.

## Executed checks

Node 24.22.1, npm 11.9.0, Chromium 156 on Linux.

| Check | Result |
| --- | --- |
| Baseline typecheck/build | PASS |
| Baseline Vitest / Playwright | 13 / 18 passed |
| `npm ci` | PASS |
| `npm run typecheck` | PASS |
| `npm run build` | PASS, large lazy-chunk warning retained |
| `npm run test -- --run` | 40 passed, 0 failed, 0 skipped |
| `TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e` | 34 passed, 0 failed, 0 skipped |
| Real NASA image download/render/landmark match | BLOCKED |

Unit tests include all six reference axes, inverse axes, boundary normalization,
invalid inputs, near/exact poles, 500 seeded round trips, actual sphere UVs,
texture loading/failure/late disposal and a mocked renderer loading state.
Synthetic texture objects exercise lifecycle only; they are not NASA imagery.

The 18 existing browser executions remain, with 15 real globe scenarios across
1440×1000, 820×1180 and 390×844, plus one mobile touch scenario. Checks cover
WebGL2 context and actual visible sphere, keyboard camera buttons, drag and wheel
limits, raycast selection, route unmount, simulated initialization failure and
real WEBGL_lose_context behavior. Mobile CDP gestures exercise rotate, pinch,
tap and a frame-paced native page swipe after pausing. They are browser
emulation, not physical-device testing. No failed assertion was disabled.

Renderer evidence: WebGL 2.0, ANGLE Vulkan **SwiftShader**. This is genuine browser
WebGL rendering through a software renderer; physical GPU/mobile GPU performance
was NOT RUN. Normal scene tests detect uncaught JS errors and console errors.
Three.Clock deprecation and screenshot ReadPixels driver warnings were observed;
they are warnings, not fabricated passes or hidden exceptions.

## Visual review and bundle comparison

All three screen layouts were reviewed at the three target sizes. Additional
south-focus and selected-marker screenshots confirm neutral-sphere rendering,
camera orientation and visible selection. They cannot validate missing imagery.
Screenshots remain generated outputs under ignored test-results/.

Vite decimal kB (raw / gzip):

| Output | Command 02 | Command 03 |
| --- | ---: | ---: |
| Entry JavaScript | 270.70 / 85.73 | 273.57 / 86.85 |
| Lazy globe JavaScript | — | 947.15 / 249.91 |
| Entry CSS | 12.78 / 3.24 | 12.43 / 3.17 |
| Lazy globe CSS | — | 1.32 / 0.49 |

Entry JS increases by 2.87 kB raw / 1.12 kB gzip. The sizeable 3D chunk loads when
Mission Setup renders, including on default startup, and is not needed for direct
analysis/alternatives visits. No texture payload is included. The >500 kB Vite
warning is not suppressed. No real-device FPS, GPU-memory or field-performance
claim is made.

## Remaining prerequisites

Restore permitted access to the official source (or provide the exact officially
obtained 2K asset with acquisition/usage metadata), verify and document the JPEG
and hash, enable the verified local URL, then perform real image loading and
landmark alignment checks. Until then Command 03 is not fully accepted. No
backend, NASA elevation/astronomy, visibility, optimizer or landing-safety result
is implemented or claimed. Command 04 has not been started.
