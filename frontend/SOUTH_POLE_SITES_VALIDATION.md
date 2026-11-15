# Command 10 — south-pole catalog and coordinate trust

## Repository and scope

Based on main 66a65fa, including frontend PR #22 and backend PR #21. Only frontend
changes. Backend/data_pipeline/models/manifests were read without modification.
The original NASA JPEG, global coordinate math and API contracts are unchanged.
No DEM/ephemeris analysis, coverage polygons, score, optimizer or deployment.

## Source research and access evidence

All six official URLs below were actually requested through Python urllib on
2026-11-15. Every attempt failed with `Tunnel connection failed: 403 Forbidden`.
No response document or PDF bytes were obtained. No alternate image, mirror,
coordinate table or guessed map point was substituted. The NASA Data Book's
Appendix A/Table A2-2, USGS latitude type and PGDA pages were therefore **NOT
VERIFIED in this task**. A source URL or an article year is not frame evidence.
Publication dates remain null; reference years 2022 and 2024 come from the user
request, not an independent inspection of the blocked articles.

| Reference | Official URL | Current review |
| --- | --- | --- |
| NASA 2022 candidate regions | https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/ | BLOCKED 403 |
| NASA 2024 updated regions | https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/ | BLOCKED 403 |
| ACD-50044 Revision A | https://ntrs.nasa.gov/api/citations/20230007818/downloads/ACD-50044%20Lunar%20Surface%20Data%20Book%20Rev%20A.pdf | BLOCKED 403; Appendix A/Table A2-2 not read |
| Mons Mouton Gazetteer | https://planetarynames.wr.usgs.gov/Feature/16070 | BLOCKED 403; latitude type unknown |
| PGDA Product 78 | https://pgda.gsfc.nasa.gov/products/78 | BLOCKED 403 |
| PGDA Product 90 | https://pgda.gsfc.nasa.gov/products/90 | BLOCKED 403 |

## Catalog evidence matrix

| Record | Kind | Coordinate | Frame / latitude | Visual reference | Form transfer |
| --- | --- | --- | --- | --- | --- |
| Connecting Ridge | Region | null | NOT VERIFIED | none | blocked |
| Shackleton Rim | Region | null | NOT VERIFIED | none | blocked |
| Mons Mouton | Region | null | NOT VERIFIED; no planetographic conversion assumed | none | blocked |
| Mons Mouton Plateau | Region | null | NOT VERIFIED | none | blocked |
| Site01 / CR1 Research Point | Research point | -89.468, 222.6 E | backend input declares PLANETOCENTRIC / MOON_ME_DE421; independent absolute registration NOT VERIFIED | documented backend-input reference only | blocked |

The four region names are retained from the requested research scope. Their
membership in a particular NASA list was not independently confirmed here.
The UI does not assert that all four belong to 2022, 2024 or any current list.
The historical lists are distinct and do not establish a current landing target.
No region centre or boundary is guessed. Site01 raster, Connecting Ridge region
and CR1 research point are kept distinct; the CR1 marker is not a region polygon.

## Repository evidence actually reviewed

- backend/README.md, Analysis contract: coordinate-only CR1 example specifies
  -89.468 latitude, 222.6 east, MOON_ME_DE421, PLANETOCENTRIC. Its older coverage
  warning is not treated as the latest data-validation result.
- backend/SCIENCE.md: observer convention and frame definitions; IAU_MOON,
  MOON_PA_DE421 and MOON_ME_DE421 are not interchangeable.
- backend/DEM.md and DEM_VALIDATION.md: actual LROC CR1 sampling, sphere/metre
  evidence, product-specific frame registration false and unquantified errors.
- backend/DEM_HANDOFF.md: near/far boundary, real Site01/Product90 80MPP inputs,
  missing 20MPP, strict/prototype registration policies and readiness limits.
- data_pipeline/LOLA_VALIDATION.md: later actual Site01 trio and Product90 80MPP
  validation supersedes earlier page-only manifests for file availability.
- data_pipeline/README.md and manifests/lola.json: product families and historical
  page-only metadata; NOT_INSPECTED entries are not silently upgraded.
- backend/app/models/analysis.py and api/routes.py: coordinate bounds, request
  schema 1.0, science-not-ready health and 503/NOT_RUN analysis endpoint.

No raster, kernel or existing evidence measurement was re-run by this frontend
work. These are reviewed repository statements, not new NASA authentication.
The LROC local raster alone has incomplete distant-horizon coverage. Site01
finite pixels can be interpolated with zero direct laser spot counts. Product90
80MPP does not substitute for absent 20MPP resolution; footprints, NoData,
registration/datum, ray range, sampling and UTC kernel coverage remain separate.
No approximate coverage polygon is drawn from those statements.

## Coordinate and capability policy

Place documentation, coordinate compatibility and analysis readiness are separate.
All production records remain Exploration Only and Coordinate NOT VERIFIED.
Scientific Coverage Unknown and Analysis Unavailable are explicit. CR1 also
shows limited local evidence, without implying site/time-specific support.
No production record is Coordinate Verified or Analysis Ready.

Numeric bounds require finite -90 < latitude < 90, 0 <= east longitude < 360.
Planetographic, unknown frame/convention, negative catalog longitude, 360 and
exact poles cannot be transferred. No geodetic conversion is implemented.
The existing eastLongitudeToVisual adapter is reused for marker/camera placement.
A visual reference additionally requires an explicit backend-input frame and
coordinate-evidence text. That gate is separate from verified transfer evidence.

CR1 is shown solely because the repository explicitly defines this research
input in the requested target convention. This does NOT establish source-product
registration. Both the card and globe legend say so. Other records have no marker.
No primary-source coordinate compatibility was independently established here.

Transfer requires VERIFIED compatibility plus a VERIFIED primary-source record,
a safe source URL and a nonempty citation. None passes today. Unit tests use an
explicitly synthetic policy record to test this future path; it is never imported
into production. Once real evidence is reviewed, the normal action uses
ScenarioProvider.select, retaining all non-coordinate mission inputs and clearing
old analysis/cancellation state. Requests remain COORDINATES, never SITE_ID.
Global readiness is unchanged and cannot confer site-specific coverage.

## State, camera and marker interaction

The form remains the only mission-coordinate source. Inspected catalog ID and a
one-shot sequenced camera command are UI state only. View on Globe scrolls/focuses
the globe and instantly orients a safe 3.2R camera toward the existing coordinate
mapping. It does not select coordinates, run analysis or change UTC/profile.
Near-pole orbit limits allow CR1 while remaining away from the exact singularity.
Manual orbit, reset and south focus remain available; no camera tween is added.

An amber octahedron at 1.025R distinguishes the catalog reference from the cyan
user marker. Its illustrative size is not a physical footprint. Its pointer
handlers stop propagation; a click inspects the source card rather than picking
the sphere below. Drag threshold prevents accidental catalog clicks. Keyboard
users have equivalent Inspect/View actions in the list. Marker geometry/materials
are R3F-owned and disposed on unmount; position records are prepared once.

A verified site label is derived from coordinate equality, with only 1e-12 degree
roundoff tolerance for the existing visual/east adapter. This is not a geographic
search radius or snapping. Manual edits break the match; reset clears inspection
and command state. Route navigation preserves form state under ScenarioProvider;
local inspection need not persist. Unverified CR1 never becomes an exact verified
catalog match even if the user independently types its coordinate.

## UI, accessibility and fallback

Cards expose named-region/research-point type, source status, coordinate metadata,
unknown coverage, disabled reasons and source/limitation details. No automatically
fetched NASA content is required at runtime. External links pass safeSourceUrl and
use target=_blank with rel=noopener noreferrer. Sources are read as text if unsafe.
Inspect, source disclosure and available View actions work from the keyboard.
WebGL failure retains the list and manual form; verified future transfer is
independent of WebGL. Mobile interaction toggles, page scrolling, reduced-motion
instant camera commands, lazy loading, demand frames, DPR and texture reuse remain.

## Verification and remaining science blockers

Run sequentially: npm ci (writable /tmp cache), npm run typecheck, npm run build,
npm run test -- --run, TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e,
git diff --check and git status. Baseline: 332 Vitest / 188 Playwright PASS.
Final counts/screenshots/build evidence are appended after execution.

Blocked: independent official source inspection, actual NASA regional coordinates,
Data Book/USGS coordinate types, source frame compatibility, any real verified
coordinate transfer and site/time-specific scientific readiness. No DEM/ephemeris
scientific validation is claimed. Resolving these requires accessible primary
source bytes and reviewed registration evidence, not relaxing the UI gate.
Command 11 may build on this catalog after evidence review; no subsequent task
or deployment is started here.


## Final evidence

- PASS: npm ci (125 packages, no dependency/lockfile changes), TypeScript,
  production build and git diff --check.
- PASS: 354/354 Vitest tests (24 files), preserving the 332-test baseline.
- PASS: 197/197 Chromium Playwright tests across desktop 1440×1000, tablet
  820×1180 and mobile 390×844, preserving the 188-test baseline; no skips.
- PASS: actual CR1 marker raycast does not pick the underlying sphere; focus
  reports -89.5° latitude/-137.4° signed longitude at 3.2R while form/UTC remain.
- PASS: source/transfer gates, future verified-policy record uses shared scenario,
  manual/custom transitions, reset, unreachable/not-ready and WebGL fallback.
- PASS: original NASA JPEG hash and production scientific fixture exclusion.
- Screenshots inspected: desktop/tablet/mobile CR1 focus and source/coverage
  messages, desktop/mobile 200% WebGL-unavailable cards. Enlarged source details
  are long and wrap vertically; no horizontal page overflow or overlapping
  globe/card controls was detected. No populated NASA scientific result is shown.
- NOT VERIFIED: every production catalog record's independent primary-source
  coordinate compatibility. No real production transfer is enabled or claimed.
- BLOCKED: six official source retrievals (403); NASA region list membership,
  Data Book table contents and Gazetteer coordinate type remain unverified.
- NOT RUN: new DEM/SPICE or independent physical/geodetic science verification.

Initial transfer integration assertion exposed existing adapter roundoff
222.60000000000002 rather than 222.6. Numeric comparison and the explicit 1e-12
matching tolerance preserve representation semantics without normalizing user
input or asserting a scientific accuracy. The final full suite passed.

Build raw/gzip kB: entry JS 351.00/110.69; main CSS 22.01/4.92;
LunarGlobe 29.41/8.06; HorizonScene 11.42/4.28; shared renderer 918.47/242.64.
Existing >500kB renderer warning remains. No extra NASA asset or GIS library.

## Changed files

- `frontend/README.md`
- `frontend/SOUTH_POLE_SITES_VALIDATION.md`
- `frontend/e2e/lunar-sites.spec.ts`
- `frontend/src/features/lunar-sites/SiteExplorer.test.tsx`
- `frontend/src/features/lunar-sites/SiteExplorer.tsx`
- `frontend/src/features/lunar-sites/Sites.module.css`
- `frontend/src/features/lunar-sites/siteCatalog.test.ts`
- `frontend/src/features/lunar-sites/siteCatalog.ts`
- `frontend/src/features/lunar-sites/siteTypes.ts`
- `frontend/src/features/lunar-sites/siteValidation.ts`
- `frontend/src/screens/MissionSetup.tsx`
- `frontend/src/visualization/globe/GlobeControls.tsx`
- `frontend/src/visualization/globe/LunarGlobe.tsx`
- `frontend/src/visualization/globe/SiteMarkers.tsx`
