# Team 24&28 — Space Apps submission copy

Prepared for the 2026 **Lunar Landing Site Navigator** challenge. These are copy-ready English sections. The field names and maximum seven-slide format below were supplied by the team lead; the authenticated portal and its character limits were not independently accessible. The official indexed 2026 page states November 15, 11:59 PM local time; confirm the team's local-event timezone and portal instructions.

**Delivery format: exactly seven English slides, including title and closing page. No video is part of this delivery.** Local PDF: [COMMAND_14_JURY_DECK.pdf](COMMAND_14_JURY_DECK.pdf). The PDF is not a public link until the team approves and performs publication.

**Submission holds:** no team-approved code license; repository private; judge access unverified; no verified public project/demo URL. The team explicitly reserved these decisions. Nothing was published, relicensed or submitted.

## Official form — copy-ready fields

### Project Name

24&28 — Lunar Landing Site Navigator

### High-Level Project Summary

An end-to-end lunar landing site and operation timing research prototype powered by NASA SPICE and LOLA data, with explicitly documented scientific limitations. Team 24&28 links an interactive lunar globe, local horizon, sampled visibility windows and explicit operation requirements. Users can compare evaluated nearby coordinates or alternative UTC starts under compatible scientific settings. A versioned planning index explains model results without overriding mandatory conditions. Real bounded backend jobs support polling, persistent results and checkpoint reuse; an offline Recorded Evidence mode supports demonstrations without new calculations. Source identities, unknown values and partial search scope remain visible. The prototype supports research and education; it does not certify lunar landing safety or mission success.

### Link to Project Demo

**PENDING TEAM PUBLICATION — no URL yet.** Publish the approved seven-slide `COMMAND_14_JURY_DECK.pdf` to a team-approved location that opens without sign-in or private permissions, and paste that actual PDF/presentation URL here. Verify all seven pages in a logged-out browser. A local filesystem path is not a public demo URL. Do not paste the repository URL in this field as a substitute for the presentation.

### Link to Final Project

**PENDING TEAM ACCESS DECISION — no verified public project URL yet.** Current source repository: https://github.com/MelisaSpX24/lunar-navigator (**PRIVATE**, confirmed through the authenticated GitHub API). After the team chooses the access option below, paste an actually public source/project-page URL that opens without sign-in. This is a different field from the presentation/PDF demo link. No localhost address or unapproved URL is a substitute.

### Detailed Project Description

Lunar surface operations depend on terrain, timing and explicit requirements. Our prototype organizes those dependencies into Analysis → Explanation → Alternatives → Comparison. Mission Setup captures lunar coordinates, UTC, operation duration, device heights and one of four profiles. A single scientific pipeline combines NASA SPICE geometry and LOLA terrain to derive observer positions, terrain horizons, finite-disk Sun/Earth visibility and sampled temporal windows. The operation engine evaluates requirements as MET, NOT_MET or INCOMPLETE and produces the explainable Planning Suitability Index.

Local optimization changes coordinates while preserving UTC, duration and requirements. Temporal optimization changes start UTC while preserving the location and operation. Detailed recommendations require completed compatible evidence; coarse screening alone is not a successful operation. The interface connects selected coordinates through a radar, 3D Moon and guarded A/B table. Live jobs use bounded resources, durable SQLite results, polling and cooperative cancellation. Recorded Evidence remains distinctly labelled and works without the scientific server.

Previously executed one-hour CR1 experiments, revalidated in Command 13, illustrate the prototype. A 1 km local search generated 32 locations, found 21 terrain-eligible and detailed eight including baseline: six MET and two NOT_MET, with PARTIAL scope. A retained site about 932 m from CR1 improved baseline NOT_MET / 0 to modeled MET / 100. A separate seven-day temporal search discovered 27 alternatives and detailed baseline plus three: two MET and two NOT_MET, also PARTIAL. MET starts included November 23, 2026 at 20:00 UTC and November 27 at 02:00 UTC. Both use a 3600-second operation and an example 600-second solar requirement.

These are historical model results, not new submission-day computations. The offline six-hour temporal and 5 km one-hour local packages are separate recorded studies. Absolute DEM registration remains unverified, equivalent Horizons validation incomplete, and hourly samples do not guarantee continuous illumination. The index is not success probability; geometric sunlight is not electrical power and Earth clearance is not an RF link. General science readiness remains false, alongside explicitly bounded prototype capabilities. No public production service or global optimum is claimed.

### NASA Data

NASA/JPL NAIF SPICE: DE421 planetary ephemeris (`de421.bsp`), lunar orientation (`moon_pa_de421_1900-2050.bpc`), frame definitions (`moon_080317.tf`), leap seconds (`naif0012.tls`) and planetary constants (`pck00011.tpc`). Default geometry uses MOON_ME_DE421 and explicit NONE correction. Source: https://naif.jpl.nasa.gov/naif/ ; use rules: https://naif.jpl.nasa.gov/naif/rules.html .

NASA GSFC / LRO LOLA terrain: Site01 5 m surface and inspected error/count layers from PGDA Product 78, and default wider-area 80 m DEM from Product 90. Sources: https://pgda.gsfc.nasa.gov/products/78 and https://pgda.gsfc.nasa.gov/products/90 . Credit Michael K. Barker and the LRO LOLA product teams. File hashes preserve the inspected source identity; they do not certify absolute accuracy.

NASA SVS CGI Moon Kit: locally packaged lunar color imagery for visualization only, credited to NASA Scientific Visualization Studio / Lunar Reconnaissance Orbiter, visualization by Ernie Wright. Source: https://svs.gsfc.nasa.gov/4720/ . NASA/JPL Horizons was used for diagnostic reference comparisons with configuration mismatch disclosed, not a passed equivalent validation: https://ssd.jpl.nasa.gov/horizons/ .

### Space Agency Partner & Other Data

No additional space-agency partner dataset was confirmed in this submission's default pipeline. Do not invent a partner source. Other components are open-source software rather than additional scientific measurements: React, TypeScript, Three.js, React Three Fiber, Vite, FastAPI, Pydantic, SpiceyPy, NumPy, Rasterio and pyproj, with their applicable notices. The team's recorded demo JSONs are derived outputs from the identified NASA sources. PDF typography uses DejaVu Sans; the figures are actual application captures and programmatically drawn explanatory diagrams, not AI-generated lunar imagery. See the rights inventory below.

### Use of Artificial Intelligence

OpenAI Codex and ChatGPT assisted with software development, debugging, test preparation, code review and technical/submission writing. Claude was used to check for technical gaps; the team reports that no existing implementation was changed as a result of that review. The scientific values displayed come from deterministic backend calculations using identified NASA source files, not AI-generated ephemerides, terrain or fabricated observations. The team selected the project direction, supplied requirements and source material, made access/licensing decisions and reviewed the work. Automated tests, browser checks and source-hash checks are software evidence; human review does not establish the still-open independent scientific validation gates. No generative-image model was used for the deck: its screenshots show the actual application, while its layout and explanatory vector diagrams were produced with AI-assisted code. No NASA review or endorsement of AI-assisted work is implied.

### Project Submission Verification

**Not yet submitted.** The team lead must verify the actual portal checklist, approve licensing and public access, publish the seven-slide presentation and final project at separate accessible URLs, test both while logged out, confirm member/attribution/AI disclosures, and manually choose Submit for Judging before the event deadline. Retain the portal confirmation. Build/test success does not constitute official submission. Codex has not clicked Submit for Judging.

## Access options — user must choose; no publishing authorized

**A. Existing repository becomes public after review.** The team chooses a code license, checks contributor rights and dependency/asset notices, scans the complete history for credentials/private configuration/binaries/storage, then explicitly authorizes the visibility change. Verify both the source link and a separately published PDF while logged out. No history cleanup, visibility change or license addition was performed here. A current-tree review alone does not certify repository history as safe.

**B. Curated public project package/page.** The team approves a separate reviewed artifact containing only suitable project files or a project explanation, the seven-slide PDF, required credits/notices and any approved code. Exclude private environment files, NASA binaries, SQLite data and unreleasable content. Decide licensing for any distributed original code; a curated copy does not bypass licensing obligations. Confirm whether the actual judging rules require source access rather than only a project page. Approve hosting/publication and then verify the final project and demo URLs separately while logged out. This option was prepared as a plan; no public package/page or URL has been created.

## 1. Project Title

**24&28 — Lunar Landing Site Navigator**

## 2. One-Sentence Pitch

Explore how lunar terrain, illumination and Earth visibility affect an operation, then compare evaluated nearby sites or alternative start times using traceable NASA-derived evidence.

## 3. Project Summary

An end-to-end lunar landing site and operation timing research prototype powered by NASA SPICE and LOLA data, with explicitly documented scientific limitations.

Team 24&28 connects an interactive lunar globe and local horizon visualization to a Python scientific backend. Users define a location, UTC start, duration and operation requirements. The backend combines ephemeris geometry, terrain horizons, finite-disk visibility and sampled time windows to explain whether the selected modeled conditions are met. Bounded optimizers explore nearby coordinates or different start times, while a comparison view preserves the scientific settings and evidence behind each result.

The prototype supports real asynchronous calculations with job polling, cancellation and persistent checkpoints. A lightweight Recorded Evidence mode supports a local demonstration without the backend or internet. It clearly labels historical evidence and preserves unknown values. The result is an explainable research workflow for mission-planning exploration and education, with a transparent boundary between software integration and independent scientific validation.

## 4. The Problem

A promising lunar coordinate is only one part of an operational plan. Local topography changes the apparent horizon, Sun and Earth geometry changes with time, and an operation may require illumination, Earth clearance or both. These interacting constraints are difficult to understand through a map alone. A useful research tool must also explain missing data, finite sampling and the assumptions behind a recommendation.

## 5. Our Solution

Lunar Landing Site Navigator organizes the investigation into **Analysis → Explanation → Alternatives → Comparison**. It lets users inspect modeled Sun/Earth relationships to a local horizon, evaluate explicit requirements and compare only scientifically compatible alternatives. A high planning index cannot override a failed mandatory requirement. Unknown evidence remains unknown, and a partial search reports the evaluated subset instead of claiming an exhaustive optimum.

The challenge asks for accessible comparison of sites and dates using horizon-relative Sun/Earth positions. Our implementation addresses this through linked 3D, radar, timeline, operation-rule and A/B views, backed by source identities and measured scientific execution.

## 6. How It Works

1. **Mission Setup:** choose a profile, planetocentric lunar coordinates, UTC, duration and device heights; supply explicit requirements.
2. **Mission Analysis:** inspect source-backed geometry, available horizon samples, sampled windows, mandatory decisions and the versioned planning index.
3. **Local alternatives:** screen a bounded neighbourhood for terrain coverage and slope, then perform exact scientific evaluation for selected coordinates at the same time and duration.
4. **Temporal alternatives:** hold location and operation settings fixed while evaluating selected UTC starts.
5. **Comparison:** show supported metric differences under matching sources, requirements, policies and score version.
6. **Evidence:** disclose execution state, data origin, provenance, missing fields and scientific limitations.

Long calculations use HTTP 202 admission, a job ID, polling and persisted results. COMPLETED describes execution; MET describes requirements. These concepts remain distinct.

## 7. NASA Data Used

| Source | Actual role | Attribution / identity boundary |
|---|---|---|
| JPL DE421 ephemeris, `de421.bsp` | Sun/Earth/Moon geometry | NASA/JPL NAIF; files pinned by SHA-256 |
| `moon_pa_de421_1900-2050.bpc`, `moon_080317.tf` | Lunar orientation and mean-Earth/principal-axis frames | NASA/JPL NAIF; MOON_ME_DE421 |
| `naif0012.tls`, `pck00011.tpc` | UTC/time conversion and body constants | NASA/JPL NAIF; explicit geometric NONE correction in pilots |
| PGDA Product 78 Site01 5 m DEM | Near-field surface and observer terrain | NASA GSFC / LRO LOLA team; surface plus inspected count/error layers |
| PGDA Product 90 80 m DEM | Wider terrain horizon support | NASA GSFC / LRO LOLA team; default far-terrain source |
| CGI Moon Kit local 2K color texture | Globe visualization only | NASA SVS / LRO; color imagery does not supply elevation or current illumination |

Optional 20 m data was investigated earlier and remains inactive in the default pipeline. Neither source resolution nor a valid file hash establishes landing safety or absolute accuracy. Command 13 rechecked five kernels and four DEM/quality files. See the audit for exact hashes, CRS and provenance limitations.

## 8. Technical Architecture

**Frontend:** React, TypeScript, Vite, Three.js and React Three Fiber; accessible HTML/SVG panels and a locally packaged lunar texture. The frontend validates scientific responses and displays backend evidence rather than calculating operational decisions.

**Scientific backend:** Python, FastAPI, Pydantic, SpiceyPy, NumPy, Rasterio and pyproj. Pipeline: DEM → observer → SPICE → terrain horizon → disk visibility → temporal windows → operation evaluation → planning score. The local optimizer changes coordinates; the temporal optimizer changes UTC.

**Execution:** one POSIX scientific worker, bounded resources, SQLite persistence, cooperative cancellation and source-bound checkpoints. Live prototype capabilities are advertised separately from `science_ready=false`. This is a local/single-host prototype; no public production service is claimed.

**Testing:** analytical and synthetic unit tests, recorded NASA artifact validation, prior real HTTP/WebGL tests, and final production-browser acceptance. Command 13 freshly passed 231 targeted backend and 176 targeted frontend tests; those are historical audit results, not new Command 14 counts.

## 9. Key Features

- Mission Setup, Mission Analysis and Alternative Explorer in one workflow.
- Four operation profiles with explicit requirements and three-state decisions.
- Terrain-aware Sun/Earth disk visibility and sampled Solar/Earth/Joint windows.
- Local radar and globe selection, temporal UTC alternatives and guarded A/B comparison.
- Explainable `24and28-planning-score-v1`, independent of mandatory eligibility.
- Durable asynchronous jobs with polling, cancellation and explicit checkpoint resume.
- Offline Recorded Evidence with manifest checksums and transparent limitations.

## 10. Verified Results

The following are **previously executed real NASA-derived one-hour experiments**, revalidated in Command 13. They are not newly computed for this submission.

**Local study:** CR1 −89.468°, 222.6° E; start 2026-11-20T08:00:00Z; 3600-second Solar operation; minimum modeled solar visibility 600 s; 1 km radius. Thirty-two locations were generated, 21 passed terrain screening, and eight entries including baseline were detailed: six MET and two NOT_MET. The search remains **PARTIAL**.

A retained alternative at **−89.43734917039663°, 222.8374650555442° E**, about **931.976 m**, bearing **4.351°**, scored **MET / 100** versus baseline **NOT_MET / 0** under the prototype sampled policy. It is an evaluated alternative, not the optimum of the whole region.

**Temporal study:** same one-hour operation and 600-second requirement, seven-day search, 27 discovered alternatives, baseline plus three alternatives detailed. Two were MET and two NOT_MET; search **PARTIAL**. MET / 100 starts included **2026-11-23T20:00:00Z** and **2026-11-27T02:00:00Z**.

All thresholds above are **EXAMPLE_OPERATION_ASSUMPTION**, not NASA mission requirements. The offline temporal package is a separate **six-hour** recorded scenario, including 2026-11-23T16:26:15Z; do not present it as the one-hour live experiment. The offline local package is a separate **5 km, one-hour** finite study with three evaluated alternatives, not the later 1 km Local8 result.

## 11. Innovation and Impact

The contribution is the connection between scientific evidence and an understandable planning decision. One scientific pipeline supports different operation profiles, explainable rule outcomes, a transparent index and alternatives along either coordinate or time. Users can see why a modeled option improves, which inputs are held fixed, what evidence was actually computed and what remains uncertain. This supports education and early research exploration while preserving a path toward more rigorous validation.

## 12. Scientific Limitations

- Absolute DEM registration remains **UNVERIFIED**. Projection compatibility, relative overlap and file integrity are not independent absolute control-point validation.
- Configuration-equivalent Horizons validation is **NOT COMPLETED**. Seventeen shared timestamps support diagnostic residuals, but zero samples meet full configuration equivalence. This is not independent observational certification.
- Hourly temporal samples and finite disk samples can miss short interruptions or narrow terrain features. Sampled duration is not a guarantee of physical continuity.
- The planning score is a normalized prototype index, not mission-success probability. A mandatory NOT_MET remains NOT_MET at any score.
- Local and recent live temporal studies are finite and PARTIAL. No global optimum is asserted.
- Geometric sunlight is not electrical power. Earth clearance is not a verified radio link. Slope is not landing safety.
- `science_ready=false` is preserved. Bounded prototype availability is separate from full scientific readiness.
- No public production deployment is provided. An in-process worker cannot continue while its server is stopped.

## 13. Future Development

Independent frame/registration and reference-geometry validation; denser event-sensitive sampling; hazard and instrument models; additional validated terrain coverage; controlled performance improvements; and authenticated, supervised deployment. These are future directions, not delivered capabilities or promises of mission certification.

## 14. Team Contributions

**Team 24 — Frontend and integration:** mission workflow, 3D lunar/horizon visualization, responsive evidence panels, radar, guarded comparisons, offline presentation and jury materials.

**Team 28 — Scientific backend:** source ingestion and provenance, SPICE/terrain visibility, windows, operation rules and scoring, bounded optimizers, persistent job service and scientific validation.

The role split follows the project work packages; the team should confirm individual contributions and replace role labels with approved member names in the portal. Individual names and unverified contributions have not been invented.

## 15. Source References and Rights Review

1. [Official challenge](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/) — indexed challenge summary checked; live page retrieval failed during preparation.
2. [2026 event page](https://www.spaceappschallenge.org/2026/) and [submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide) — confirm actual event/portal requirements; authenticated fields not inspected.
3. [NASA/JPL NAIF SPICE](https://naif.jpl.nasa.gov/naif/) and [SPICE use rules](https://naif.jpl.nasa.gov/naif/rules.html) — credit NAIF and kernel-producing teams; preserve applicable SPICE notices/disclaimers if redistributing its components.
4. [PGDA Product 78](https://pgda.gsfc.nasa.gov/products/78) — Site01 topography, Michael K. Barker and the LRO LOLA team. Use the product page's cited publication when adding a formal bibliography; no unverified DOI is invented here.
5. [PGDA Product 90](https://pgda.gsfc.nasa.gov/products/90) — south-polar LOLA products, Michael K. Barker and team; documented DE421 mean-Earth coordinates.
6. [NASA SVS CGI Moon Kit](https://svs.gsfc.nasa.gov/4720/) — visualization by Ernie Wright, NASA SVS; LRO camera/altimeter source teams. Credit: **Imagery: NASA Scientific Visualization Studio / Lunar Reconnaissance Orbiter**. The checked official page supports the source citation; the local file's user-supplied hash is not a publisher-authenticity certificate.
7. [NASA images/media guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/) — factual source credit, no endorsement, and separate checks for third-party material/marks. Do not use a NASA logo as the team's logo or apply a project license to NASA assets.
8. [JPL Horizons](https://ssd.jpl.nasa.gov/horizons/) — reference diagnostics only, with configuration mismatch disclosed.

### Software and asset notices

PDF fonts: DejaVu Sans, derived from Bitstream Vera; see https://dejavu-fonts.github.io/License.html . Font embedding in this PDF does not license the team’s source code. No NASA logo, generative-model image, external icon pack or music is included in the deck; diagram/layout code was AI-assisted.

The team's own code has **no approved license**. GitHub metadata reports `license=null`; no project LICENSE was found. Dependency licenses do not license the team's code. The user explicitly instructed that this decision and repository visibility remain unchanged. **This is an unresolved submission hold**, not an implicit MIT release.

Frontend direct runtime packages React, React DOM, React Router DOM, Three.js and React Three Fiber report MIT in their installed package metadata. Build/test tools include Vite/Vitest (MIT), TypeScript and Playwright (Apache-2.0). The locked dependency inventory also contains BSD, ISC, 0BSD, BlueOak and MPL-2.0 declarations; preserve the corresponding notices and review distribution obligations before releasing a source/dependency bundle. These are metadata checks, not a complete legal opinion or an assertion that all dev dependencies ship to browsers.

Backend package notices remain applicable separately (FastAPI/Pydantic/Uvicorn/SpiceyPy, NumPy, Rasterio, pyproj and linked native libraries). The final frontend-only review does not certify every native library's redistribution terms. NASA binaries and private storage are excluded from the delivery. The team must approve its code license and any public distribution plan before representing the project as open source.

## 16. AI Tool Disclosure

OpenAI ChatGPT/Codex assisted with code development, debugging, tests, technical review and drafting documentation/presentation material across the project. Claude checked for technical gaps; the team reports no implementation change resulting from that review. The team is responsible for checking generated work, source attribution and the final submission. Scientific results shown here come from the deterministic backend using identified NASA source files and recorded calculations; AI-generated prose is not NASA validation. No AI-generated lunar image is presented as measured terrain. The current command does not add a runtime AI scientific model. The team must supplement this disclosure with any other tools it used and comply with the actual portal's disclosure fields.

## 17. Demo and Repository Links

- Repository: https://github.com/MelisaSpX24/lunar-navigator — **PRIVATE; judge access NOT VERIFIED**.
- Official team project page: **NOT PROVIDED / NOT VERIFIED**.
- Public hosted demo: **NOT PROVIDED**. No deployment or publishing was performed.
- Video: **NOT PART OF DELIVERY**, per the team’s final decision. The demo is the seven-slide PDF.
- Offline local jury demo: `cd frontend && npm run build && npm run preview -- --host 127.0.0.1 --port 4173 --strictPort`; open `http://127.0.0.1:4173/#/alternatives`, choose **Recorded Evidence**. Serve the built files over HTTP; file:// is unsupported. Localhost is not a remotely accessible judge link.
- Optional live local startup: [LOCAL_JURY_DEMO.md](../backend/LOCAL_JURY_DEMO.md). It requires existing private NASA resources, Linux/WSL2 and one scientific worker. No fresh calculation is necessary for the offline pitch.

## 18. Submission Checklist — team action required

- [x] Copy-ready project narrative, NASA attribution, architecture, measured-result scope and limitations.
- [x] Seven-slide content, speaker notes, screenshot provenance and technical Q&A in [COMMAND_14_JURY_PITCH.md](COMMAND_14_JURY_PITCH.md).
- [ ] Team-approved code license and corresponding distribution decision. Do not add a license without approval.
- [ ] Judge access to the private repository or an approved reviewed source delivery. Do not assume authenticated access proves public access.
- [ ] Approved final project and presentation/demo links, tested from a logged-out browser or by the intended judges. No placeholders should be pasted as functioning URLs.
- [ ] Approved member names and contribution details.
- [ ] Check actual project form fields, limits, terms, disclosure rules, local-event timezone and remaining time.
- [ ] Inspect all seven PDF pages and source credits; publish only through a team-approved channel.
- [ ] Preserve dependency/asset notices and keep private NASA paths, binaries, configuration, credentials and SQLite storage out of shared materials.
- [ ] Team lead performs the official portal submission and confirms receipt. No Submit action was taken by Codex.

Software acceptance details and remaining holds: [COMMAND_14_FINAL_REPORT.md](COMMAND_14_FINAL_REPORT.md).
