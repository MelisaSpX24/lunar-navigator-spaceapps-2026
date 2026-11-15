# Command 10.1 — source-reference evidence recovery

## Scope and repository

Based on main e2ed360 (PR #24 frontend catalog and PR #23 backend temporal
optimizer). Only frontend changes. The prior SOUTH_POLE_SITES_VALIDATION.md is
preserved, including its historical 403 evidence. Backend scientific documents,
ScenarioProvider, mission serialization, globe camera/markers and global lunar
coordinate conversions were inspected and retained. No scientific solver,
DEM/raster, kernel, new texture, readiness bypass, optimizer or deployment.

## Retrieval evidence — 2026-11-15

Eight real urllib GET requests were made. All failed while establishing the
network tunnel: `Tunnel connection failed: 403 Forbidden`. This is a proxy/tunnel
status, not an observed HTTP response from NASA/USGS itself. Origin status is
null and document bytes are zero. No PDF, HTML, table, latitude definition or
technical projection document was independently inspected in this task. No
random proxy or mirror was used. Machine-readable request timestamps, URLs and
errors are preserved in evidence/command-10-1-source-retrieval.json.

| Source | URL | Result / section to inspect |
| --- | --- | --- |
| NTRS entry | https://ntrs.nasa.gov/citations/20230007818 | tunnel 403; no metadata body |
| Data Book PDF | https://ntrs.nasa.gov/api/citations/20230007818/downloads/ACD-50044%20Lunar%20Surface%20Data%20Book%20Rev%20A.pdf | tunnel 403; Appendix A, Table A2-2, page 58 of 70 not independently read |
| PGDA 81 | https://pgda.gsfc.nasa.gov/products/81 | tunnel 403; mosaic description not independently read |
| PGDA 78 | https://pgda.gsfc.nasa.gov/products/78 | tunnel 403; Site01/Site04 descriptions not independently read |
| PGDA 90 | https://pgda.gsfc.nasa.gov/products/90 | tunnel 403; no new coverage/metadata verification |
| NASA 2022 | https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/ | tunnel 403; candidate announcement |
| NASA 2024 | https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/ | tunnel 403; updated candidate announcement |
| USGS/IAU | https://planetarynames.wr.usgs.gov/Feature/16070 | tunnel 403; feature centre / coordinate system / control network |

## Evidence origin and historical dates

The following information is retained from the user's external primary-source
research report, with **NOT_REVERIFIED_IN_TASK** on every corresponding record.
It is neither invented nor relabelled as a successful current source inspection.
Dates and candidate membership are externally reported metadata; the UI exposes
this distinction alongside each record and source.

- Data Book: ACD-50044 Revision A, 2023. Appendix A/Table A2-2, page 58/70.
- PGDA 81: reported 5 m/pixel south-polar stereographic LOLA DEM mosaic,
  MOON_ME reference frame of DE421.
- PGDA 78: reported Site01 Connecting Ridge and Site04 Shackleton Rim products,
  5 m/pixel, south-polar stereographic, MOON_ME/DE421.
- NASA 2022: reported 19 August 2022 announcement, 13 candidate regions.
  Connecting Ridge membership is recorded only for this announcement.
- NASA 2024: reported 28 October 2024 update, nine regions including Mons Mouton
  and Mons Mouton Plateau. No Connecting Ridge 2024 membership is asserted.
- Neither historical list is described as the final/current 2026 flight target.
- Shackleton Rim has a Data Book feature reference but no candidate badge from
  either announcement. Shackleton Rim B and Peak Near Shackleton are distinct.
- CR1 is a separate repository research input, not the entire Artemis region.

## Coordinate ledger and unresolved semantics

| Catalog record | Reported source coordinate | Source latitude / longitude | Frame evidence | Production use |
| --- | --- | --- | --- | --- |
| Connecting Ridge R01 / Site01 | -89.4632, -137.49 | latitude UNKNOWN; signed east | MOON_ME/DE421 reported via PGDA81 DEM, table chain not verified | source text only; no new marker or transfer |
| Shackleton Rim R04 / Site04 | -89.7668, -171.87 | latitude UNKNOWN; signed east | same incomplete reported DEM chain | source text only; no new marker or transfer |
| Mons Mouton USGS 16070 | -84.60, 31.00 | PLANETOGRAPHIC, signed +East [-180,180], reported | LOLA 2011 control network reported, precise backend frame UNKNOWN | source text only; no new marker or transfer |
| Mons Mouton Plateau | null | UNKNOWN | UNKNOWN | 2024 historical metadata only |
| Site01 / CR1 Research Point | -89.468, 222.6 E | repository backend input PLANETOCENTRIC / [0,360) east | target MOON_ME_DE421 declared, independent absolute registration unverified | existing explicitly limited visual reference; no transfer |

The externally reported Data Book also lists R07/Site07 Peak Near Shackleton
(-88.811, 123.6901) and SL3 Connecting Ridge Extension (-89.0324, -101.999).
These are preserved here as research clues only, not new catalog entries or
substitutes for R04, CR1 or Connecting Ridge.

R01 signed east -137.49 becomes 222.51 E for representation; it is not CR1's
222.6 E. R04 -171.87 becomes 188.13 E. Existing longitude adapters are reused.
This is NOT a geodetic/frame/latitude conversion. Source numeric digits remain
as reported and are not a physical accuracy or safe landing claim.

A projected DEM's stated frame is insufficient to prove the table centre's
latitude type or the exact coordinate extraction/registration chain. No second
technical document was successfully inspected to close this gap. MOON_ME is
not blindly promoted to a fully verified backend input. USGS planetographic
latitude is never copied into PLANETOCENTRIC. No approximate marker or polygon
is added for these source-only coordinates.

## Types and transfer boundary

- SourceReferenceCoordinate uses kind SOURCE_REFERENCE and separately records
  object ID, source URL/section, latitude type, longitude convention, control
  network, reported frame and review status.
- The legacy explicit visual research input now uses kind RESEARCH_INPUT; the
  prior CR1 marker/focus stays on this path. A runtime kind guard rejects source
  coordinates even if untyped code substitutes one into the research field.
- AnalysisCoordinate uses kind ANALYSIS_INPUT and only backend-compatible
  planetocentric/MOON_ME_DE421 fields. Type tests ensure source coordinates are
  not assignable to analysis inputs.
- transferReason retains bounds, convention, evidence and compatibility gates.
  A VERIFIED flag alone no longer suffices: directly reviewed primary-source
  evidence must match this object's ID and source URL and explicitly verify
  latitude type and frame. Source access/review must also be verified/direct.
- Positive unit tests use explicitly synthetic evidence records; these never
  turn a production location into a verified coordinate or live science result.
- The existing ScenarioProvider.select path retains profile, UTC, duration and
  requirements, invalidates prior analysis and never posts automatically.

Result: zero production backend-compatible coordinates verified; zero enabled
Use These Coordinates actions; zero site/time-specific Analysis Ready claims.
All five production entries remain Exploration Only. Source-reference numbers
can be recorded and useful while transfer remains blocked.

## Coverage and existing scientific documents

Read-only evidence includes backend/SCIENCE.md, DEM_HANDOFF.md, DEM_VALIDATION.md
and data_pipeline/LOLA_VALIDATION.md. Their latest Site01/Product90 80MPP evidence
is kept distinct from older missing-data snapshots. Real local files and finite
samples do not establish complete science support. Raster family, footprint,
NoData, laser spot counts, pixel spacing, registration, datum, device/observer
height, far-horizon range and SPICE time coverage remain separate constraints.
20MPP is not silently replaced by 80MPP. No source-only catalog coordinate is
mapped into an approximate DEM coverage polygon or marked ready by global health.
The current API's science-not-ready / 503 NOT_RUN behavior is preserved.

## UI, marker and accessibility behavior

Source centres and conventions appear in their own text area, with the external
research/reverification label. The historical dates/badges and object distinctions
are per record rather than a single ambiguous 2022/2024 label. Source cards retain
previous 403 history and expose the new GET attempt date/status.

Existing CR1 amber marker, source-inspection click, safe one-shot focus and manual
coordinate state remain unchanged. Source-only R01/R04/Mons Mouton values never
create new markers or focus targets. A catalogue reference remains separate from
the user-selected cyan marker. Manual input, reset, routing, NASA JPEG, WebGL
fallback, reduced-motion behavior and keyboard alternatives remain intact.

New source text wraps within cards at 1440/820/390px and mobile 200% text. Safe
external links retain noopener/noreferrer. No new scientific fixture, network
runtime dependency, heavy library or raster is included.

## Verification

Run sequentially: npm ci (writable /tmp cache), npm run typecheck, npm run build,
npm run test -- --run, TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e,
git diff --check, git status and the main-to-task file comparison. Final counts,
screenshots, build sizes and scope evidence are appended after execution.

## Remaining work and Command 11

Accessible official HTML/PDF bytes and specific source latitude/frame/extraction
proof are still required before any real coordinate transfer is enabled. An
independent physical DEM/ephemeris validation was NOT RUN. This task improves
metadata and safety under the acknowledged access block; it does not claim
recovered primary-source access or NASA-certified geodetic/landing accuracy.
Command 11 can consume the separated source/analysis models after evidence review;
no subsequent feature, merge or deployment is initiated here.


## Final validation evidence

- PASS: baseline 354/354 Vitest and 197/197 Chromium Playwright.
- PASS: npm ci (125 packages, unchanged lockfile/dependencies), TypeScript,
  production build, git diff --check and frontend-only scope.
- PASS: final 374/374 Vitest (25 files) and 200/200 Chromium Playwright tests,
  no skipped tests. Existing globe, WebGL, marker raycast/focus, scenario/reset,
  readiness, UTC playback, Local Horizon, Sun/Earth and timeline tests retained.
- PASS: source/analysis type separation, raw source substitution runtime rejection,
  signed-east boundaries, object-bound primary evidence gate and negative cases.
- PASS: final screenshots inspected at 1440×1000, 820×1180 and 390×844 plus
  mobile 200% text. Initial machine-code labels broke awkwardly at 200%; final
  labels use readable English while raw review codes stay in the evidence model.
  Cards wrap vertically without page overflow; source details remain long at
  enlarged text. Candidate/date, raw source coordinate and transfer limitations
  remain visible. These images show metadata presentation, not physical accuracy.
- PASS: production scientific fixture identifiers absent; NASA JPEG SHA-256 still
  f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170.
- BLOCKED: all eight official source GET attempts, zero document bytes inspected.
- NOT REVERIFIED: three catalog source centres supplied by the user's external
  research report. Existing CR1 is a separate repository-documented input.
- Zero independently verified backend-compatible production coordinates, zero
  enabled production transfers and zero site/time-specific ready locations.
- NOT RUN: independent NASA DEM/ephemeris or geodetic accuracy validation.

Build raw/gzip kB: entry JS 356.95/112.43; CSS 22.01/4.92; LunarGlobe 29.41/8.06;
HorizonScene 11.42/4.27; shared renderer 918.47/242.63. The existing >500kB
renderer warning remains. No new dependencies or raster/texture assets.

## Changed files

- `frontend/NASA_COORDINATE_EVIDENCE_VALIDATION.md`
- `frontend/README.md`
- `frontend/e2e/coordinate-evidence.spec.ts`
- `frontend/evidence/command-10-1-source-retrieval.json`
- `frontend/src/features/lunar-sites/SiteExplorer.test.tsx`
- `frontend/src/features/lunar-sites/SiteExplorer.tsx`
- `frontend/src/features/lunar-sites/coordinateEvidence.test.ts`
- `frontend/src/features/lunar-sites/siteCatalog.test.ts`
- `frontend/src/features/lunar-sites/siteCatalog.ts`
- `frontend/src/features/lunar-sites/siteTypes.ts`
- `frontend/src/features/lunar-sites/siteValidation.ts`
- `frontend/src/features/lunar-sites/sourceEvidence.ts`
