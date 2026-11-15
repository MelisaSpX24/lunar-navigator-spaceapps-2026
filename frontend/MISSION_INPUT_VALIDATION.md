# Frontend Command 04 — mission inputs

> Historical Command 04 evidence. Current API/scenario behavior and checks are
> recorded in API_INTEGRATION_VALIDATION.md.

## Base and scope

Base main: `7a5acfbb70543f08410fb61a328ec825b96a6120` (merge PR #8).
Texture commit `48466c142baa684cbdc5290834bef13fe49767fc` is an ancestor.
The initial tree was clean; work uses `frontend/command-04-mission-inputs`.
All source, tests and documentation changes are under frontend/ only.

Read-only backend references: app/models/analysis.py, app/api/routes.py,
tests/test_api.py and tests/conftest.py. The coordinate-only TypeScript mirror
traces to the backend-local AnalysisRequest 1.0 at the base above. It is not a
new shared contract; backend changes require manual synchronization/review.
Routes still describe an unimplemented scientific analysis returning HTTP 503.
No analysis endpoint is called by this feature or by the cross-validation script.

## Behavior and validation

Mission Setup owns raw typed form state. Coordinates are never silently clamped,
rounded or normalized after manual entry. The globe marker is derived from these
same fields. Globe picks convert visual longitude [-180,180) to backend [0,360).
Manual valid coordinates update the actual marker/readout, and camera motion does
not change coordinates. Invalid edits hide the marker. Exact +/-90 poles retain
a visual marker but fail request validation; undefined polar longitude is not
invented. A Show lunar globe button provides a keyboard-accessible return to the
scene from the long form. Scenario data resets on route exit; persistence is not
implemented in this command.

Four profiles retain backend enums. Switching profile changes no requirement.
UTC date and time are checked explicitly against the Gregorian calendar, with
no JavaScript date rollover or local-time construction. Output always has Z.
Input supports whole-second precision, years 0001–9999. Duration uses integer
hours plus 0–59 minutes/seconds, producing positive safe-integer seconds. End
date cannot exceed the backend datetime range. This entry representation is
intentionally narrower than accepting arbitrary ISO strings or fractional hours.

Requirements preserve blank/null versus explicit zero, finite nonnegative
optional seconds, fraction [0,1], clearance [0,90], simultaneous/joint consistency
and the three minimum-duration bounds. No extra max-dark-gap/duration relation
is invented. Observer heights, DEM mode and options match backend draft defaults.
The one-hour initial duration is a frontend convenience. Initial coordinates and
UTC start are empty. Defaults are not NASA-approved mission limits.

Only a valid form produces the explicit six-section JSON request. Request Preview
is optional and clearly states no scientific analysis has been performed. Run
Analysis stays disabled. There are no fabricated results, scores, NASA data
requests, API calls or changes to the other two scientific empty-state screens.

## Executed validation — 2026-11-14

Node 24.22.1 / npm 11.9.0, system Chromium 156 on Linux.
Baseline before changes: typecheck/build PASS, 43 Vitest tests and 49 Playwright
executions PASS. Final commands and results:

| Command/check | Result |
| --- | --- |
| `npm_config_cache=/tmp/lunar-npm-cache npm ci` | PASS, 125 packages installed; package/lock versions unchanged |
| `npm run typecheck` | PASS |
| `npm run build` | PASS, existing >500 kB lazy-globe warning retained |
| `npm run test -- --run` | PASS, 128 tests / 10 files, 0 failed or skipped |
| `../backend/.venv/bin/python -B scripts/check-backend-request.py` | PASS, 10 frontend-produced JSON requests accepted; 4 invalid controls rejected |
| `TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e` | PASS, 67 executions, 0 failed or skipped |

The plain npm ci retry initially failed because its default cache under
/home/agent/.npm was not writable. The successful command uses a writable /tmp
cache and the exact same lockfile; no version upgrade or integrity bypass occurred.
A first run of the new browser tests exposed an ambiguous text locator, fixed by
identifying the actual field error. No assertion or failing behavior was skipped.

The 85 added Vitest cases cover coordinate adapters, pole/longitude boundaries,
strict dates/times, duration and end-date bounds, requirements, profiles, null/zero,
request shape and form/globe integration. Component tests explicitly mock the
renderer; they are not claimed as WebGL evidence.

The cross-validator imports the existing Pydantic AnalysisRequest using the
backend's existing virtualenv with bytecode disabled. It consumes ten JSON
objects emitted by the real frontend builder during Vitest: all four profiles,
default and edited requirements, and year 0001/9999 boundaries. Four negative
controls check unknown fields, 360 longitude, exact-pole latitude and zero
duration. This is sampled compatibility evidence against the current model,
not an exhaustive proof or a new backend test suite. No backend file is changed.

The 18 added Playwright executions cover real form/globe synchronization,
manual coordinates, profiles, JSON, invalid fields, disabled analysis, observer
options, keyboard error focus and ARIA references. The browser timezone check
compares UTC, Europe/Istanbul and America/New_York across DST, midnight and year
boundaries. All three viewport projects run these checks.

## Browser, visual and 3D regression review

Target sizes: 1440x1000, 820x1180 and 390x844. The form and existing three-screen
navigation remain usable with no page horizontal overflow. Labels, errors and
JSON wrap. Native date/time display follows browser locale, but values are
explicitly UTC and JSON remains unchanged. Text is also tested at 200% root size;
duration columns reflow with available space. The selected profile's full label
is repeated in its wrapping description, since a native select can truncate its
single-line display at large text sizes. Focus goes to the first invalid field;
hidden advanced sections open when an invalid field needs focus.

Screenshots in ignored test-results/ were inspected for normal desktop/tablet/
mobile form layouts, coordinate marker/readout, profile and UTC fields, visible
errors, JSON preview and enlarged mobile text. Normal and south-pole globe views
and the scientific empty-state screens retain the existing browser coverage.
Screenshots are generated review artifacts, not committed binary baselines.

All 49 existing browser checks remain. They verify the local NASA JPEG HTTP 200,
image/jpeg, SHA-256, browser decode and genuine WebGL texture upload; loading and
404 fallback; camera rotation/zoom/focus/reset; raycasting and geographic readout;
UV/coordinate behavior; context loss/unavailable WebGL; mobile touch rotate/pinch/
tap/page scrolling; keyboard navigation and the other two screens. The JPEG and
UV/mesh/camera implementations are unchanged. Preserved JPEG SHA-256:
`f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170`.

The texture remains visual color imagery, not DEM. Lighting is illustrative.
No new cartographic or scientific certification is claimed. Historical image
orientation/provenance limits are in TEXTURE_VALIDATION.md. Physical devices,
Safari/Firefox, hardware GPU performance and independent NASA-server checksum
verification are NOT RUN. Browser WebGL runs through the cloud software renderer;
it does not establish physical GPU performance.

## Bundle and remaining boundaries

No runtime or test dependency was added or upgraded. Build decimal kB (raw/gzip):

| Output | Command 03.1 | Command 04 |
| --- | ---: | ---: |
| Entry JS | 273.57 / 86.85 | 286.05 / 91.23 |
| Lazy globe JS | 947.43 / 250.06 | 946.53 / 249.71 |
| Entry CSS | — | 14.30 / 3.53 |
| Lazy globe CSS | — | 1.40 / 0.51 |

The globe stays lazy-loaded and memoized; changing non-coordinate form inputs
does not change its props. The NASA JPEG is still a separate 457942-byte asset.
Large globe chunk size is an existing warning, not hidden or declared solved.

Command 05 has not started. Live analysis, result state/lifecycle, API error
handling and eventual shared-contract review remain future work. No main merge
or deployment is performed here.
