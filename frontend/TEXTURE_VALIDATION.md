# Frontend Command 03.1 — verified local NASA color texture

## Outcome and provenance

The original user-supplied JPEG is now served locally and displayed on the
existing 3D sphere. No NASA request, network-policy bypass, mirror, image
generation, resizing, recompression or format conversion was used.

The downloadable attachment `lunar-nasa-texture.zip` contained one member:
`lroc_color_2k.jpg`. Before copying, its actual bytes passed JPEG magic, full
Pillow decoding, dimensions, length and SHA-256 checks. After copying to
`public/assets/moon/lroc_color_2k.jpg`, the target was checked again.

| Check | Result |
| --- | --- |
| Original JPEG length | 457942 bytes — PASS |
| Format / complete decoding | JPEG — PASS |
| Dimensions | 2048 × 1024 — PASS |
| Original SHA-256 | f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170 |
| Copied SHA-256 | same — PASS |
| Comparison with user's expected checksum | PASS |
| Independent NASA-server checksum equality | NOT RUN; not claimed |

The official source URL and credit are recorded in public/assets/moon/README.md
and visible in the application. Provenance is user-supplied. Historic 403 evidence
remains in GLOBE_VALIDATION.md, explicitly marked historical. Current NASA usage
page text and product dating were not rechecked; this task specifically avoids
retrying the network blocker. No NASA endorsement is implied.

## Runtime verification

VERIFIED_TEXTURE_URL uses import.meta.env.BASE_URL and the local assets path.
The application never requests the remote NASA JPEG. Browser checks establish:

- HTTP 200 and image/jpeg response.
- Response body length and SHA-256 identical to the copied JPEG.
- Browser image.decode() succeeds with natural dimensions 2048 × 1024.
- Genuine WebGL texImage2D/texSubImage2D calls receive the decoded local image.
  Observation is injected only by the browser test; no production test globals
  or mocked Three.js renderer are used in that test.
- Existing MoonMesh assigns the texture object to meshStandardMaterial.map;
  screenshots show the actual maria, craters and surface rays on the sphere.
- Loading does not announce success prematurely. Success displays exactly
  “NASA color texture loaded — visual imagery only”. A routed 404 displays the
  honest neutral-sphere fallback and preserves camera controls.

The existing sphere, UV geometry, camera controls, raycasting, selection marker,
lazy loading, GPU-resource lifecycle and context-loss handling are preserved.
Mission Setup, Mission Analysis and Alternative Explorer source files are
unchanged by this follow-up. No new dependencies are required.

## Geographic orientation — separate evidence from UV math

Existing cardinal-axis, inverse, pole, seam and actual SphereGeometry UV tests
remain. No coordinate convention, UV buffer or flipY setting needed changing.

The decoded JPEG and rendered sphere were visually compared using recognizable
features: Copernicus north-west of the origin, Tycho south of the equator, and
Mare Crisium to the north-east. Approximate reference positions used for browser
review are respectively (9.62°, -20.08°), (-43.31°, -11.36°), (17°, 59.1°).
Raycast readouts are checked against these positions within 0.5°, reflecting
coarse global-mesh picking, not survey accuracy. Mare Crisium is brought away
from the perspective limb before selection. Screenshots place the marker on the
recognizable feature, providing image evidence in addition to mathematical tests.

East 90°, west 90° and far-side ±180° views were captured. Qualitative inspection
found no horizontal mirror, inverted north/south or obvious seam discontinuity.
North-side maria and the southern Tycho ray system agree with the original map;
south-focus shows the southern polar terrain image. The longitude convention is
still east-positive, canonical [-180,180), with undefined longitude at exact poles.

**PASS for qualitative orientation and image/readout consistency.** Independent
high-precision cartographic registration, polar fill accuracy, actual elevation
and scientific frame/terrain certification are NOT RUN and are not claimed.
The 2K color texture is not a DEM; lighting remains illustrative.

## Executed checks — 2026-11-14

Node 24.22.1, npm 11.9.0, system Chromium on Linux.

| Command/check | Result |
| --- | --- |
| npm ci | PASS |
| npm run typecheck | PASS |
| npm run build | PASS; existing lazy-chunk size warning remains |
| npm run test -- --run | 43 passed, 0 failed, 0 skipped |
| TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e | 49 passed, 0 failed, 0 skipped |
| JPEG integrity and header dimensions | PASS |
| Real browser decode / WebGL texture upload | PASS |
| 404 fallback / pending loading message | PASS |
| Camera drag / wheel limits / focus / reset | PASS |
| Raycast / marker / coordinate-UV mathematics | PASS |
| Context loss / unavailable WebGL / navigation | PASS |
| Touch rotate / pinch / tap / native page swipe | PASS in mobile emulation |

Coverage retains previous 40 unit tests and 34 browser executions, updating only
the old default-unavailable texture expectation. Added checks cover the real local
asset, loading/failure, GPU upload and landmark/cardinal views. The supplied JPEG
is never replaced with a synthetic image to obtain a successful result.

All three target viewports (1440×1000, 820×1180, 390×844) passed. Normal and south
views were visually inspected at each size, as were landmark/cardinal screenshots.
Browser tests also retain responsive layout, keyboard and other-screen checks.
Generated screenshots remain under ignored test-results/.

Physical devices, Safari/Firefox, hardware GPU performance, and independent
NASA-server authenticity checks were NOT RUN. Prior SwiftShader limitations
still apply. No critical console errors occurred in normal scene checks;
intentional failure tests exercise missing imagery and unavailable/lost WebGL.

## Build and scope

No package changes. Entry JS remains 273.57 kB raw / 86.85 kB gzip; the lazy globe
chunk is 947.43 / 250.06 kB. The local JPEG adds 457942 bytes as a separate static
asset, not an embedded JavaScript payload. Loading from a relative Vite base is
preserved. The >500 kB Vite warning is not hidden.

Only frontend/ is changed on frontend/command-03-3d-moon. The JPEG is to be tracked
as an original binary. The existing PR #8 is updated by pushing this same branch;
no new PR, Draft-state change, main merge or Command 04 work is authorized here.
