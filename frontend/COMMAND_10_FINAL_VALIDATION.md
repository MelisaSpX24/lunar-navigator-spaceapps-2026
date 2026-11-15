# Command 10 — final completion validation

## 1. Executive summary

Final classification: **COMMAND_10_FRONTEND_COMPLETE_WITH_EVIDENCE_LIMITATIONS**
subject to the final software results recorded below. Five source-aware cards,
strict transfer gating, one limited research marker and custom mission selection
remain available. No production coordinate is promoted or unlocked without
missing primary-source/frame evidence. Source access is BLOCKED, not VERIFIED.

## 2. Prior PR integration

Initially based on origin/main 7fac3b8, containing PR #24 (Command 10) and PR #25 (10.1),
including the teammate's backend temporal optimizer. During work PR #26 merged
as 38d1795; the task branch was fast-forwarded to preserve those backend-only
performance changes. No frontend/API-model/route change occurred in that update. Local main is not treated
as current. Only frontend files change. Prior validation documents and the
Command 10.1 retrieval JSON are retained. Backend AGENTS.md and scientific/data
handoff documents were read only. Baseline typecheck/build and 374 Vitest /
200 Playwright passed before the final implementation run.

## 3. Official NASA evidence

Eleven official source groups A–K are covered by 13 real GET attempts, including
NTRS entry/PDF pairs. Every attempt failed establishing the tunnel with 403;
origin HTTP status is null, document bytes zero. This is not a NASA-origin 403.
No random proxy/mirror or replacement coordinate list was used. Tool discovery
found no callable web-reading connector. Accessible workspace file discovery
found no local PDF copies or user-supplied primary-source PDFs. No PDF was opened.
Actual URLs/timestamps/errors: evidence/command-10-final-retrieval.json.

All source findings supplied in the request remain EXTERNAL_RESEARCH_REFERENCED
and NOT_REVERIFIED_IN_TASK. Version/section metadata is useful for later review,
not proof that those sections were inspected here. Source labels in the UI use
readable English; evidence codes are retained in source records.

| Group | Official URL | Evidence to inspect |
| --- | --- | --- |
| A | https://ntrs.nasa.gov/citations/20230007818 | ACD-50044 Revision A (2023) |
| A PDF | https://ntrs.nasa.gov/api/citations/20230007818/downloads/ACD-50044%20Lunar%20Surface%20Data%20Book%20Rev%20A.pdf | Appendix A, Table A2-2, pp.58–59 |
| B | https://ntrs.nasa.gov/citations/20250002845 | M2M-30044 Baseline (2025) |
| B PDF | https://ntrs.nasa.gov/api/citations/20250002845/downloads/M2M-30044%20Lunar%20Surface%20Data%20Book%20Baseline_Final.pdf | Appendix A, Table A2.1-1, p.75 |
| C | https://pds-imaging.jpl.nasa.gov/documentation/LRO_Coordinate_System.pdf | V4, 14 May 2008; sections 5.0/6.0/6.1 |
| D | https://pgda.gsfc.nasa.gov/products/81 | South Pole LOLA DEM Mosaic |
| E | https://pgda.gsfc.nasa.gov/products/78 | Site01/04/07 and ROI products |
| F | https://pgda.gsfc.nasa.gov/products/90 | Wide-area LOLA products |
| G | https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/ | 19 August 2022 candidate announcement |
| H | https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/ | 28 October 2024 update |
| I | https://planetarynames.wr.usgs.gov/Feature/16070 | Mons Mouton feature centre |
| J | https://ntrs.nasa.gov/citations/20220015275 | 2022 Data Book C1/CR1 traverse; PDF path/page unresolved |
| K | https://pds.nasa.gov/datastandards/documents/dd/all/current/ch11s37.html | Latitude definitions |

## 4. 2023 Data Book

Externally supplied R01/Site01 Connecting Ridge centre: -89.4632, -137.49 signed
east; R04/Site04 Shackleton Rim centre: -89.7668, -171.87. Values remain source
centres, not landing locations or backend-compatible coordinates. Table page
references 58–59 are supplied research metadata. Latitude definition and exact
table-to-DEM extraction/registration chain remain unverified.

R07/Site07 Peak Near Shackleton (-88.811,123.6901) and SL3 Connecting Ridge
Extension (-89.0324,-101.999) remain research clues in the previous evidence
document; they are not added as substitutes for R04 or CR1.

## 5. 2025 Data Book

The request reports R01/R04 repeated in the newer 2025 baseline, Table A2.1-1,
p.75. SOURCE book2025 and DATA_BOOK_COMPARISON explicitly record this report.
No numerical-difference claim is made: directComparison and numericalDifference
are NOT_VERIFIED, authoritativeSourceForTransfer is UNRESOLVED. The document's
later date does not justify silently replacing source values. Actual PDF contents
must be compared before deciding whether a difference exists or why.

## 6. LRO coordinate standard

The reported LRO standard is planetocentric, east-positive and Mean Earth/Polar
Axis (V4, sections 5/6/6.1). This general standard is not a product-specific
registration/extraction certificate. No table coordinate is promoted from it.

Conceptually, planetocentric latitude follows the radius vector; planetographic
latitude follows the reference-surface normal. They can differ with the adopted
shape/reference model. No shape model, transformation parameters or numerical
error bounds are supplied here to convert the USGS coordinate. PDS K is an
unread primary reference for later technical review, not a directly cited reading.

## 7. PGDA 78

External findings associate Site01 Connecting Ridge, Site04 Shackleton Rim and
Site07 Peak Near Shackleton with 5 m/pixel south-polar LOLA products/ROI metadata.
These names are not interchangeable. Height/slope/count/uncertainty layers have
different meanings; a product's existence proves neither valid observer terrain
at every cell nor far-horizon or end-to-end science readiness.

## 8. PGDA 81

External findings report 5 m/pixel GeoTIFF, south polar stereographic X/Y metres,
MOON_ME and JPL DE421. Source-reference frame is recorded as reported via DEM,
not verified backend compatibility. Missing proof: actual page metadata, table
extraction procedure, latitude convention, exact frame realization and any
required registration/transform. General map projection math alone cannot close it.

## 9. PGDA 90

Repository DEM_HANDOFF/LOLA_VALIDATION documents genuine local Site01 and 80MPP
inputs; 20MPP remains absent. Those statements were reviewed, not re-measured.
No 80MPP substitution for 20MPP, raster download, footprint polygon or implied
continuous valid terrain is introduced.

## 10. NASA 2022 candidates

Connecting Ridge retains externally reported 2022-08-19 candidate context.
The 13-region list was not read here. No 2024 membership is added to Connecting
Ridge. Peak Near Shackleton, Shackleton Rim and Connecting Ridge Extension stay
distinct. Shackleton Rim has no candidate badge from an unproven announcement.

## 11. NASA 2024 candidates

Mons Mouton and Mons Mouton Plateau retain the externally reported 2024-10-28
historical candidate context. A dated nine-region announcement is not a final
2026 flight target or a site-specific analysis-ready list.

## 12. USGS Mons Mouton

Reported feature 16070 centre: -84.60,31.00; Planetographic, +East [-180,180],
LOLA 2011 control network. It is a named-feature centre, not necessarily an
Artemis candidate-region centre. Direct planetocentric transfer stays blocked.
No new globe marker is drawn. Source shape/reference surface, frame transform,
method and error evidence would be required to evaluate any conversion.

## 13. Source access history

Previous Command 10/10.1 failures are preserved. Existing sources append a final
failed GET entry; new sources B/C/J/K are marked first attempted in this task.
The new retrieval file distinguishes origin status from tunnel status. No source
is marked directly reviewed because a request or a software test succeeded.

## 14. Coordinate convention matrix

| Record | Source numeric values | Latitude / longitude | Backend transfer |
| --- | --- | --- | --- |
| R01 reference centre | -89.4632,-137.49 | latitude unknown; signed east reported | blocked |
| R04 reference centre | -89.7668,-171.87 | latitude unknown; signed east reported | blocked |
| Mons Mouton feature | -84.60,31 | planetographic reported; signed east | blocked |
| Mons Mouton Plateau | null | unknown | blocked |
| CR1 research input | -89.468,222.6 E | repository-declared planetocentric/DE421 target | blocked; registration proof absent |

Signed-east representation -137.49 ->222.51 E and -171.87 ->188.13 E uses the
existing adapter. Tests cover this arithmetic, boundaries and invalid values.
It is not a latitude or reference-frame transform. MOON_PA, IAU_MOON and Earth
frames fail the backend input gate; exact poles, NaN/Infinity and stringified
numbers also fail. No new geodetic conversion is introduced.

## 15. Reference-frame chain

SourceReferenceCoordinate, RESEARCH_INPUT and AnalysisCoordinate remain distinct.
The runtime gate now accepts unknown input and validates object shape, numeric
types/ranges, kind, latitude/convention/frame, evidence text, proof fields and
source records before accessing them. Malformed arrays/nulls/non-string metadata
are rejected without crashing. Compile-time source-type separation remains.

A verified transfer needs object-ID-matched, source-URL-matched directly reviewed
primary evidence with latitude/frame confirmation. A boolean VERIFIED flag is
not sufficient. This local evidence policy is not cryptographic NASA document
authentication; future reviewers must supply/inspect actual primary bytes and
record the evidence before editing trusted catalog status.

## 16. R01 / R04 / CR1 separation

R01's 222.51 E is distinct from CR1's 222.6 E, and their latitudes differ.
R04's 188.13 E is not Shackleton Rim B or Peak Near Shackleton. NASA 2022 C1/CR1
passage is now explicitly referenced alongside the repository research input;
its exact PDF page/frame/latitude proof is still unresolved. No rounding or
name similarity merges these records or centres.

## 17. Site catalog

Five stable records remain. Each card presents name/type/status, source/reference
coordinate, actions, coverage/reliability and a disclosure of full sources,
versions/IDs, history and limitations. Long duplicate technical explanations
moved into the disclosure. No missing number or polygon is invented. Sources and
unlock instructions remain keyboard-accessible. Primary-source documentation is
not marked verified when only external findings exist.

## 18. Verified/blocked transfer matrix

| Record | Missing evidence and precise unlock path |
| --- | --- |
| Connecting Ridge | Read 2023 pp.58–59 / 2025 p.75 R01; compare tables; inspect PGDA81/78 and LRO 5/6; establish object-specific latitude/extraction/frame chain before supplying verified research input |
| Shackleton Rim | Same table comparison for R04/Site04; confirm distinct object; prove signed-east/latitude and exact DE421 chain; 188.13 E alone cannot unlock |
| Mons Mouton | Read Gazetteer 16070 and PDS definitions; identify shape/reference surface and source frame; provide supported planetographic-to-planetocentric/frame transformation and error evidence for the correct object |
| Mons Mouton Plateau | Retrieve 2024 announcement; obtain an object-specific numeric centre with latitude, longitude and frame evidence; no centre is supplied today |
| CR1 | Retrieve NTRS 20220015275 PDF and exact C1/CR1 passage; compare repository input, establish conventions and resolve registration/datum limitations; R01 is not a substitute |

All five transfer buttons remain disabled. Positive transfer tests use a clearly
synthetic evidence policy record, never a production NASA location. A later
verified coordinate would still not imply Analysis Ready.

## 19. 3D globe integration

One existing amber CR1 research-reference marker remains, distinct from the cyan
user-selected marker. There are zero verified-coordinate markers and no new
source-only markers. Geometry/raycast behavior is unchanged. Marker size is
illustrative, not a region footprint. List/card actions provide keyboard access.

## 20. Camera focus

Only CR1 has a supported visual focus reference. View on Globe changes a one-shot
camera command and scroll/focus, never scenario coordinates or analysis. Safe
3.2R focus, orbit, zoom, south focus, reset, touch enable/pause and instant
reduced-motion behavior remain. No camera code or global transform was changed.

## 21. Custom coordinates

ScenarioProvider remains the single coordinate source. Verified-test transfer
uses select(), preserves all non-coordinate fields including UTC, duration,
profile, observer heights, requirements and advanced settings, clears a prior
503 response and sends no second POST. Existing route/reset/stale/abort tests
are retained. Invalid custom edits never snap back to a catalog coordinate.

## 22. Data coverage

LROC/LOLA family, bounds, NoData, sampling count, pixel spacing, registration,
vertical datum, observer height, near/far ray coverage and kernel/UTC support
are distinct. Bounds and 5 m/pixel are not valid-data or accuracy guarantees.
No coverage polygon or local science capability is fabricated. Source metadata
is not PRECOMPUTED/LIVE_COMPUTED/TEST_FIXTURE scientific output.

## 23. Backend science readiness

Read-only routes.py still reports science-not-ready health and returns 503
NOT_RUN for analyses. Internal backend modules do not imply exposed completed
API readiness. Global liveness cannot confer site/time-specific support.
Run Analysis, completedResult and current-request matching gates remain unchanged.
Zero catalog sites are declared Analysis Ready.

## 24. UI and responsive behavior

The current globe/form layout is retained. Cards use a compact summary/action
hierarchy with top-aligned grid items; full technical content is disclosed on
inspection. Native disclosure state and Inspect state now synchronize, allowing
close/reopen without a stale pressed button. Exact disabled reasons stay next
to their actions. No WebGL is required to read sources or edit numeric inputs.

## 25. Accessibility

Keyboard actions, disclosure summaries, visible focus styling, named cards and
numeric coordinate text remain. Status uses text as well as color. Existing
safe external links, 390px wrapping, 200% text, reduced-motion, touch/page-scroll
and WebGL fallback are tested. Large source disclosures can be long at 200%,
but the default cards are shorter and technical details remain available.

## 26. Vitest

Baseline: 374 PASS. New tests evaluate actual committed retrieval evidence as
NOT VERIFIED, source IDs/versions and unresolved 2023–2025 comparison, malformed
runtime inputs/wrong frames, all-five unlock instructions and complete scenario
preservation with stale-response clearing. Final counts appended after execution.

## 27. Playwright

Baseline: 200 PASS. Existing real Chromium tests retained; new tests inspect the
compact hierarchy, disclosure reopen, source IDs/versions, object-specific unlock
instructions, 200% layout and absence of automatic POST. Viewports remain
1440×1000, 820×1180 and 390×844. Final results/screenshots appended below.

## 28. GPU/texture regression

Globe, markers, local horizon and texture code remain unchanged. Existing actual
GPU/raycast/texture decode/context-loss/disposal tests run in the full suite.
No new dependency, raster, texture or geometry allocation path is introduced.
Build sizes and NASA JPEG hash are recorded with final evidence below.

## 29. Known limitations

No official source bytes or PDF pages were read. No independent latitude/frame
compatibility, geodetic accuracy or NASA terrain/ephemeris result is claimed.
Three source centres are externally reported; CR1 is a separate repository input.
All eleven official source groups remain unread here despite attempted URLs.
Numerical differences between 2023/2025 are unknown, not zero.

## 30. Evidence still required

Obtain official PDFs/HTML through an authorized accessible source or user-supplied
primary bytes; match IDs and versions, cite exact object rows/passages, establish
latitude/east convention, frame extraction/registration and any justified
conversion/error chain. Inspect evidence before changing trusted catalog status.
A general LRO standard, a product name or a successful mock test cannot unlock it.
No large PDF or raster is committed as part of this frontend task.

## 31. Command 11 integration readiness

Source-only and verified-input boundaries, safe selection hooks and explicit
unlock requirements are ready for later reviewed evidence. No subsequent command,
optimizer, comparison, merge or deployment is initiated. The final classification
stays WITH_EVIDENCE_LIMITATIONS, never COMPLETE_VERIFIED without the primary proof.

### Evidence-chain evaluation (all five records)

The ten checks are evaluated separately, rather than treating a URL as proof:

| Check | Current disposition | Evidence still needed |
| --- | --- | --- |
| Correct source object | External research / repository declaration only | Exact R01/R04/16070/C1 object passage; Plateau identity and numeric centre |
| Numeric coordinate belongs to object | Not independently verified | Actual row/passage in the identified document/version |
| Latitude definition | Unknown for R01/R04; planetographic externally reported for Mons Mouton; target declaration only for CR1 | Source-specific latitude definition and reference shape |
| Longitude convention | Externally reported signed/east conventions | Source definition; arithmetic tests prove representation only |
| Reference frame | Reported DEM association or declared target only | Product/table extraction and exact frame realization evidence |
| Transformation requirement | Unresolved, especially USGS | Shape/reference surface and source/target relationship |
| Transformation mathematics | Only signed-longitude representation software-tested | Reviewed geodetic method/error evidence if transformation is required |
| Independent consistency | No primary comparison performed | Direct 2023/2025 and relevant product comparisons |
| Region/research-point distinction | Preserved in data/UI/tests | Do not promote this naming separation into physical accuracy |
| Supported backend input | None verified in production | Complete object-specific primary proof before editing compatibility flags |

No new geodetic method or transformation threshold is derived by these checks.


### Final software and visual evidence

- PASS: npm ci; baseline typecheck/build, 374 Vitest / 200 Playwright.
- PASS: final typecheck, production build, 391/391 Vitest (26 files),
  203/203 real Chromium Playwright, zero skipped tests.
- PASS: source disclosure close/reopen, all 13 actual retrieval records evaluated
  as NOT VERIFIED, source versions and unresolved comparison, untyped input
  rejection, complete scenario preservation and prior 503-response invalidation.
- PASS: existing WebGL fallback/context-loss/disposal, real marker raycast/focus,
  NASA texture upload/hash, custom input, route/reset, Local Horizon, Sun/Earth,
  UTC playback and Mission Timeline regressions.
- Screenshots actually inspected: default compact R01 desktop/tablet cards,
  source-coordinate panels and mobile 200% Plateau card. Final default hierarchy
  keeps source/status/actions visible with full technical details behind the
  disclosure. Enlarged text wraps vertically; no page overflow or globe/card
  collision was detected by the viewport tests. Long words can wrap at 200%.
- PASS: scientific fixture identifiers absent from production JS. NASA JPEG stays
  byte-identical: f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170.
- PASS: frontend-only scope and git diff --check against current origin/main.
- BLOCKED: 13 URL attempts across A–K, 0 successful origin responses/documents.
- NOT VERIFIED: actual PDF/table contents, 2023/2025 numerical comparison, source
  latitude/frame compatibility. NOT RUN: real NASA geodetic/DEM/ephemeris science.

Final build raw/gzip kB: entry JS 361.58/113.89; CSS 22.54/5.01; LunarGlobe
29.41/8.06; HorizonScene 11.42/4.27; shared renderer 918.47/242.63. Existing
>500kB shared-renderer warning remains; no dependencies or assets were added.

Final catalog counts: 5 records, 1 limited CR1 research marker, 0 verified
coordinate markers, 1 View on Globe action, 0 enabled Use These Coordinates,
0 Analysis Ready locations. User-selected marker is separate and state-dependent.
All three supplied source centres remain external references, not verified
backend inputs. Prior reports and retrieval history are retained.

**COMMAND_10_FRONTEND_COMPLETE_WITH_EVIDENCE_LIMITATIONS**

### Changed files

- `frontend/COMMAND_10_FINAL_VALIDATION.md`
- `frontend/README.md`
- `frontend/e2e/site-final.spec.ts`
- `frontend/evidence/command-10-final-retrieval.json`
- `frontend/src/features/lunar-sites/SiteExplorer.test.tsx`
- `frontend/src/features/lunar-sites/SiteExplorer.tsx`
- `frontend/src/features/lunar-sites/Sites.module.css`
- `frontend/src/features/lunar-sites/coordinateEvidence.test.ts`
- `frontend/src/features/lunar-sites/finalEvidence.test.ts`
- `frontend/src/features/lunar-sites/siteCatalog.ts`
- `frontend/src/features/lunar-sites/siteTypes.ts`
- `frontend/src/features/lunar-sites/siteValidation.ts`
- `frontend/src/features/lunar-sites/sourceEvidence.ts`
