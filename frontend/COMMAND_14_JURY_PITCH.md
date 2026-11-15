# Team 24&28 — seven-slide jury presentation

**Final format: exactly seven English slides, including title and closing page. No video delivery.** The team lead supplied the seven-slide submission requirement. The authenticated portal and its current media rules were not independently inspected. This document is the presentation's textual companion, speaker notes and source record; it adds no slide to the PDF.

PDF: [COMMAND_14_JURY_DECK.pdf](COMMAND_14_JURY_DECK.pdf). It is a local deliverable, not a published demo URL. Use the PDF URL for **Link to Project Demo** after approved publication. **Link to Final Project** must separately lead to an accessible approved project/source page.

## Slide 1 — TEAM 24&28 — Lunar Landing Site Navigator

**On slide:** Explore the Moon. Evaluate the conditions. Find a better site.

An end-to-end lunar landing site and operation timing research prototype powered by NASA SPICE and LOLA data, with explicitly documented scientific limitations.

**Visual:** actual app screenshot of the Moon near the south pole; charcoal background, cyan accent, generous space. The image is the existing NASA SVS texture rendered in the app, not generated imagery or elevation data.

**Speaker note (~15 s):** “We are Team 24&28. Our research prototype helps users understand how lunar terrain and operation timing affect modeled Sun and Earth visibility, and compare evaluated alternatives with traceable evidence.”

## Slide 2 — The Lunar Landing Challenge — Problem and Mission Need

**On slide:** A location is only part of the plan.

- Terrain: nearby ridges change the local horizon.
- Time: Sun and Earth directions change with UTC.
- Requirements: different operations need different conditions.

**Visual:** actual historical one-hour CR1 live-analysis horizon panel, cropped to the supplied angular samples. Its caption states this is not a physical terrain mesh or continuity certificate. No synthetic test horizon is presented as NASA evidence.

**Speaker note (~20 s):** “A map alone cannot explain the operation. A ridge can change visibility, and a different start time can change the conditions. We need an understandable connection between terrain, time and the user's requirements.”

## Slide 3 — Our Solution — Mission Planning Workflow

**On slide:** Four steps: Set Up → Analyze → Explore → Compare.

1. Location, profile, UTC, duration and explicit requirements.
2. Geometry, terrain horizon, sampled windows and rule evidence.
3. Nearby coordinates OR alternative starts, preserving the operation.
4. Compatible evidence, mandatory decisions and a transparent index.

**Visual:** four clean vector cards. Footer principle: Analysis → Explanation → Alternatives → Comparison. This is an explanatory diagram, not additional computed science.

**Speaker note (~20 s):** “We preserve the operation as we explore. The local optimizer changes the coordinate; the temporal optimizer changes start UTC. The comparison guard checks that the rest of the scientific scenario is compatible.”

## Slide 4 — NASA SPICE + LOLA — Data and Architecture

**On slide:** SPICE: DE421 ephemeris, lunar orientation/frame, leap seconds and constants. LOLA: default Site01 5 m near terrain and Product90 80 m wider terrain, with inspected count/error layers.

Pipeline: DEM / observer → SPICE / horizon → Disk / windows → Rules / score.

**Visual:** paired source cards and a vector pipeline. Small credits identify NAIF and PGDA Products 78/90. The architecture note identifies React/TypeScript/Three.js, FastAPI, one scientific worker and SQLite checkpoints.

**Speaker note (~25 s):** “The backend uses real hash-pinned NASA source files. Frame, coordinate and correction settings are explicit. Hash identity establishes traceability, but it does not prove absolute terrain registration or independent astronomical validity.”

## Slide 5 — Local & Temporal Optimizers — Measured Prototype Results

**On slide:** historical one-hour live studies, revalidated in Command 13; both remain PARTIAL.

| Local | Temporal |
|---|---|
| 1 km radius, 32 positions | 7 days, 27 alternatives |
| 21 terrain-eligible; eight detailed including baseline | Baseline + three alternatives detailed |
| Six MET / two NOT_MET | Two MET / two NOT_MET |
| Retained point about 932 m / bearing 4.351° | MET / 100: Nov 23 20:00 and Nov 27 02:00 UTC, 2026 |
| Baseline NOT_MET / 0 → candidate MET / 100 | Same site, duration, requirements and source model |

Both use 3600-second operation duration and minimum modeled Sun visibility of 600 seconds, under the prototype sampled policy. Candidate: −89.43734917039663°, 222.8374650555442° E. Requirements are engineering examples, not NASA mission specifications.

**Visual:** equal-weight result cards; PARTIAL is visible, not relegated to a footnote. Counts are historical measurements, not a new experiment performed for the deck.

**Speaker note (~30 s):** “These results show a finite evaluated set. The 932-metre candidate improved the selected modeled condition. We do not infer that uncomputed candidates failed or that the region's optimum was found. The two optimizer studies preserve their own evidence scope.”

## Slide 6 — Interactive 3D Moon, Local Horizon and A/B Comparison

**On slide:** real radar, horizon and A/B application captures with clear captions. The app's south-pole Moon is also shown on slide 1.

**Visual:** three actual screenshot crops. Radar and A/B are from the offline **5 km, one-hour** recorded local study. The horizon is from a historical **one-hour live** analysis. The **six-hour** offline temporal scenario is separate from the one-hour live Temporal4 result. Screenshot crops do not substitute new measurements or fabricated panels.

**Speaker note (~25 s):** “A selected coordinate is shared by radar, globe and comparison. The comparison shows mandatory rules and sampled metrics, not just a score. The offline evidence package keeps these views available without a backend, and its recorded origin stays visible.”

## Slide 7 — Scientific Limitations, Impact and Future Development

**On slide:**

- Absolute DEM registration: UNVERIFIED.
- Equivalent Horizons validation: INCOMPLETE.
- Hourly sampling does not guarantee continuous sunlight.
- Planning index is not mission-success probability.
- Sunlight is not power; Earth clearance is not a verified radio link.
- Finite PARTIAL searches do not establish a global optimum.

`science_ready=false`. Research prototype. No public production deployment.

**Impact:** make lunar operation trade-offs understandable, inspectable and comparable.

**Future:** independent registration, compatible reference geometry and denser event-sensitive sampling.

**Visual:** concise scientific-gate list, impact and next-validation column. No NASA logo or endorsement. AI assistance is disclosed in the footer and full submission text.

**Speaker note (~25 s):** “We preserve unknown evidence and open validation gates. Our value is an explainable research workflow with honest limits, rather than a certification claim. Explore the Moon. Evaluate the conditions. Find a better site.”

## Rehearsal and application sequence

The speaker notes total roughly 2:40; rehearse against the actual local-event limit. These notes are not a video script or an extra PDF slide.

For the local app demonstration, serve the existing frontend over HTTP, open `/#/alternatives`, keep **Recorded Evidence**, choose Local and select the first radar candidate. Toggle the candidate globe and inspect A/B. Then choose Temporal and explain that its offline scenario is six hours. Avoid pressing live-analysis or optimizer actions during the recorded demonstration. The offline package lacks complete analysis series/full horizon profiles; do not simulate these in Mission Analysis. Use the disclosed historical screenshot on slide 2 for that view.

## Likely jury questions

| Question | Answer |
|---|---|
| Which NASA sources are actually used? | Five pinned DE421 kernels; default Site01 5 m and Product90 80 m LOLA terrain with inspected count/error layers. NASA SVS imagery is visual only. |
| Does MET guarantee sunlight for the full operation? | No. Finite disk and hourly temporal samples do not certify physical continuity. |
| What is the score? | The versioned Planning Suitability Index, not success probability. Mandatory NOT_MET stays NOT_MET at any score. |
| What does PARTIAL mean? | Only a bounded subset was completed. Valid completed candidates remain available; uncomputed candidates get no fabricated decision or score. |
| Why compare local and temporal separately? | They change different dimensions and can have different durations. Cross-scenario A/B is blocked. |
| Is Earth visibility a working radio link? | No. It is geometric clearance, without a certified RF model. |
| What happens to missing terrain or slope? | Null/UNKNOWN/INCOMPLETE is retained. It is not promoted to a successful recommendation. |
| Can it work offline? | Recorded Evidence can be served locally without the backend or internet; new live calculations require configured private sources and the backend. |
| What remains scientifically unverified? | Absolute DEM registration, fully equivalent Horizons validation, physical continuity and exhaustive optimization. |
| Can a job continue while the server is stopped? | No. Results/checkpoints are durable, but execution requires the worker to run. |
| Is this open source? | The repository is private and the team has not selected a code license. Access/publication decisions are pending. |
| What did AI do? | Codex/ChatGPT assisted development, debugging, testing and writing. Claude checked for technical gaps; the team reports no resulting implementation change. The deterministic backend produced the scientific values. |

## Sources, image provenance and delivery boundary

- Slide 1: actual current application color rendering, local NASA SVS/LRO texture; no AI-generated image.
- Slides 2/6 horizon: previously captured real CR1 one-hour live AnalysisResult view, from the earlier integration acceptance run. It is not a fresh Command 14 calculation.
- Slide 6 radar/A/B: fresh production-browser captures of `data_pipeline/demo/local_demo.json`; delivered as RECORDED_EVIDENCE_EXPORT from Command 10 source-backed records.
- Slide 5 values: `data_pipeline/evidence/nasa-live-optimizer-demo-readiness.json`, revalidated by `command-13-readonly-audit.json` and the Command 13 report.
- Diagrams are programmatic explanatory graphics, not generated lunar scenes. No NASA logo/mark, music or external icon collection was added.
- Credit: NASA/JPL NAIF; NASA GSFC / LRO LOLA team; NASA SVS/LRO, visualization by Ernie Wright. Full source and rights inventory is in [COMMAND_14_SPACE_APPS_SUBMISSION.md](COMMAND_14_SPACE_APPS_SUBMISSION.md). DejaVu Sans font attribution/license is linked there.
- PDF generated locally using ReportLab/Pillow; seven pages checked with PyMuPDF and reviewed as rasterized pages. Screenshots/large logs remain outside Git; only the compact PDF is part of the submission material.

No public PDF/project URL has been created. Publish only after the team chooses its rights/access option, then test both required links without authentication. The team lead performs the official submission manually.
