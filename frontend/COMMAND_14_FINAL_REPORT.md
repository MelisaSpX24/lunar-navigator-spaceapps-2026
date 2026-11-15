# Team 24&28 — Command 14 final delivery report

## 1. Final Repository Identity

**PASS.** Base `origin/main`: `c9361a509e819a9cfe68a088a5b9a21ccafb161f`. PR #32, #33 and #34 are merged in its Git history. The working tree was clean before creating `frontend/command-14-final-delivery`. Command 13's **COMMAND_13_COMPLETE_WITH_LIMITATIONS** is preserved.

Only frontend-owned delivery documents, the seven-slide PDF and its Git binary-file attribute are changed. No runtime application, backend algorithm, NASA source, validator, score, checkpoint or shared contract is changed. PR #33's incomplete local-candidate safeguards remain intact.

## 2. Frontend Build Status

**PASS.** `npm run typecheck` and `npm run build` were freshly executed before browser acceptance. Production build completed in 556 ms as reported by Vite (not the full command's wall time). The build's existing large-chunk warning remains: the lazy renderer bundle is approximately 918 kB minified / 243 kB gzip. No last-minute refactor or dependency upgrade was introduced.

Environment: Linux, Node 24.22.1, npm 11.9.0; existing installed dependencies, system Chromium and software WebGL. Vite native-config extension notices and npm update notices are nonblocking tooling messages. No new tools were installed.

## 3. Desktop / Tablet / Mobile Status

**PASS_WITH_LIMITATIONS.** Existing Playwright acceptance was run against the production preview at these exact viewports:

| Viewport | Navigation / setup / analysis | Local/Temporal evidence, radar and A/B | Keyboard, 200% text, layout |
|---|---|---|---|
| 1440 × 900 desktop | PASS | PASS | PASS |
| 768 × 1024 tablet | PASS | PASS | PASS |
| 390 × 844 mobile, touch emulation | PASS | PASS | PASS |

Fresh offline contexts additionally inspected both recorded scenarios at all three sizes with no horizontal overflow. Captured desktop/tablet/mobile screenshots were visually reviewed. Responsive long-text wrapping and explicit missing-data labels were retained. These are Chromium/emulated devices, not physical mobile hardware or Safari certification. Screenshots/logs stay in ignored local validation output, not Git.

## 4. 3D Globe and Horizon Validation

**PASS_WITH_LIMITATIONS.** Targeted browser checks exercised actual WebGL sphere rendering, local NASA texture decoding and GPU upload, South Pole focus/reset, linked candidate selection, horizon camera controls, supplied point rendering, trace toggles, keyboard controls and 2D table access. Missing-WebGL behavior retains explicit fallback plus radar/2D evidence. No visual coordinate or astronomy formula was changed.

Science-bearing horizon/trace browser tests use clearly labelled existing TEST_FIXTURE payloads; passing them demonstrates presentation behavior, not a new NASA validation. The PDF's horizon screenshot is instead a retained actual one-hour CR1 live-analysis capture from the prior E2E run. It is labelled historical. No synthetic science screenshot is represented as NASA measurement.

The shared cloud browser could not start (`Browser runtime unavailable`); system Chromium/Playwright supplied the actual browser validation. PDF pages were rendered with PyMuPDF and visually inspected, with extracted text checked for page-boundary clipping. No out-of-page text block was found.

## 5. Local and Temporal Explorer Validation

**PASS_WITH_LIMITATIONS.** Offline radar/list selection, coordinate transfer, candidate globe synchronization and temporal UTC deltas passed. Fresh real offline acceptance used the production build, no API mocks, no POST and no external resource request. Existing browser regression tests also use explicit fixtures/blocked APIs where documented; those are not new live calculations.

Historical one-hour live results remain unchanged:

- Local8: CR1 −89.468°, 222.6° E, 3600 s, min_sun_visible_s=600, 1 km radius; 32 generated, 21 terrain-eligible, eight detailed including baseline, six MET / two NOT_MET, PARTIAL.
- Preserved site: −89.43734917039663°, 222.8374650555442° E; 931.9756666408481 m, bearing 4.351316121645229°; NOT_MET / 0 baseline → MET / 100 candidate.
- Temporal4: 3600 s, same solar requirement, seven days, 27 alternatives, baseline plus three detailed, two MET / two NOT_MET, PARTIAL. MET / 100 at 2026-11-23T20:00:00Z and 2026-11-27T02:00:00Z.

**No new NASA computation occurred in Command 14.** The offline package is different: a six-hour recorded temporal study and a 5 km one-hour recorded local study with three alternatives. Its counts/radius/duration are not relabelled as the recent live studies.

## 6. A/B Comparison Safety

**PASS.** Browser checks retain same-scenario recorded deltas and candidate parameter transfer without automatically submitting an analysis. Existing guards preserve explicit requirements, source and scientific configuration identity, score version and comparison dimension. PR #33's SLOPE_UNKNOWN/null slope, SCIENTIFICALLY_INCOMPLETE diagnostics withholding and completed-MET recommendation checks remain unchanged; targeted tests passed.

Incomplete operation diagnostics do not become completed science. High score cannot override mandatory NOT_MET. No optimizer summary is transformed into a fabricated AnalysisResult, time series or full horizon. Local and temporal scenarios remain separate.

## 7. Offline Recorded Evidence Demo

**PASS.** Before stopping the configured demo backend, the durable database was checked: no QUEUED/RUNNING/CANCEL_REQUESTED jobs existed. The single-worker backend on loopback port 8010 was then stopped gracefully and its health endpoint was unreachable. The unrelated legacy port-8000 process was left untouched.

A separate production preview served the frontend on loopback port 4184 with no API proxy. New Chromium contexts loaded Local and Temporal Recorded Evidence. Radar, real candidate globe rendering, A/B and limitations worked. Only screenshots are included in the approved PDF; no video is delivered or tracked in Git.

The acceptance log recorded zero POSTs, zero page errors and zero external resource requests. Six responsive scenario checks passed. The UI honestly reported backend unavailability rather than a new live computation. This validates a locally served demo without scientific-server or internet dependency; it is not file:// support or a service-worker/PWA claim.

After inspection, the same configured backend/database was restored with one worker. GET health/capabilities again reported `science_ready=false`, worker_count=1 and bounded_live_prototype_supported=true. No job was submitted during restart. Server downtime does not imply continued scientific execution.

Local use:

```bash
cd frontend
npm run build
npm run preview -- --host 127.0.0.1 --port 4173 --strictPort
```

Open `http://127.0.0.1:4173/#/alternatives`, keep **Recorded Evidence**, choose Local or Temporal. A preview is a local validation server, not a public project link. For actual live development proxy/configuration use [LOCAL_JURY_DEMO.md](../backend/LOCAL_JURY_DEMO.md); no new launcher was needed.

## 8. Scientific Limitations Preserved

**PASS_WITH_LIMITATIONS.** Command 13's findings remain the scientific baseline:

- science_ready=false, with bounded prototype capability separate.
- Absolute DEM registration UNVERIFIED.
- Configuration-equivalent Horizons validation INCOMPLETE: 17 diagnostic UTCs, zero fully equivalent matches.
- Hourly finite-disk samples are not physical continuity certificates.
- Planning Suitability Index (`24and28-planning-score-v1`) is not mission-success probability.
- Geometric sunlight is not power; Earth clearance is not a verified RF link.
- Finite Local8/Temporal4 live searches are PARTIAL; no global optimum is claimed.
- This is a research prototype, without NASA certification or public production deployment.

No new data download, source alteration or NASA calculation was used to change a scientific gate. Historical timing/performance is never presented as a new Command 14 benchmark.

## 9. NASA Space Apps Submission Materials

**PASS for local preparation; BLOCKED for public delivery links.**

- [COMMAND_14_JURY_DECK.pdf](COMMAND_14_JURY_DECK.pdf): exactly seven English 16:9 pages, including title and closing; real app screenshots, concise diagrams, measured-result scope and limitations. No video delivery.
- [COMMAND_14_JURY_PITCH.md](COMMAND_14_JURY_PITCH.md): all seven slide texts/designs, concise speaker notes, technical Q&A and image provenance.
- [COMMAND_14_SPACE_APPS_SUBMISSION.md](COMMAND_14_SPACE_APPS_SUBMISSION.md): copy-ready fields for Project Name, High-Level Project Summary, Link to Project Demo, Link to Final Project, Detailed Project Description, NASA Data, Space Agency Partner & Other Data, Use of Artificial Intelligence, and Project Submission Verification; fuller narrative and references accompany them.

The field names and seven-slide requirement were supplied by the team lead. The authenticated portal was not inspected. Direct challenge/guide retrieval returned 502/timeouts; official indexed challenge/2026 text was available. Do not claim exact portal character/media rules were independently confirmed. The team must check its event timezone and form before submission.

**Link to Project Demo** is the approved published seven-slide presentation/PDF. **Link to Final Project** is a separately accessible source/project page. Neither verified public URL exists yet. A private repository, local filesystem path or localhost address does not satisfy unauthenticated public access. No placeholder URL was invented; no Submit for Judging action was taken.

## 10. Sources and Licensing Review

**BLOCKED for release approval; PASS_WITH_LIMITATIONS for attribution inventory.** Authenticated GitHub metadata confirms `private=true` and `license=null`. No team-approved project LICENSE was found; the user explicitly confirmed there is none and prohibited unilateral licensing or visibility changes. No such change was made.

NASA/JPL NAIF, PGDA Products 78/90 and NASA SVS/LRO are credited with official references. NASA media guidance and source pages were consulted; sources/rights inventory is in the submission document. No NASA logo or mark was added. No NASA raster/kernel binary, private source path/configuration, credential or job database is included. The color texture's previous source/registration limits remain documented.

Installed frontend direct runtime dependencies report MIT. TypeScript/Playwright report Apache-2.0; Vite/Vitest MIT. Lockfile declarations include 124 MIT, 29 Apache-2.0, two BSD-2-Clause, three BSD-3-Clause, 12 MPL-2.0, one BlueOak-1.0.0, two ISC and one 0BSD entries, including optional platform packages. Counts are package metadata, not a count of browser-shipped components. The MPL entries are Lightning CSS and platform variants. Preserve applicable notices if distributing dependency binaries/source; dev/native redistribution obligations were not fully legally certified. PDF fonts are DejaVu Sans with its Bitstream Vera/DejaVu attribution linked in the submission document.

The team's code license is separate from dependency/NASA rights. A public copy cannot solve an undecided original-code license automatically.

Two prepared user-controlled paths:

**A — existing repository public after approval:** choose a code license, confirm contributors' rights, check complete Git history and current files for secrets/private assets/storage, preserve notices, explicitly authorize visibility change, then test access logged out. This task did not certify all historical commits or publish them.

**B — curated public project/package/page:** approve an allowlist (reviewed project text, seven-slide PDF, selected frontend/demo assets with required notices, and only approved source). Exclude private environments, NASA binaries, SQLite/checkpoints and unreleasable material. Confirm actual source-access judging requirements, choose a license for any released team code, approve hosting/publication and verify both required links. No public package/site was created.

## 11. AI Disclosure

**PASS.** Codex and ChatGPT assisted code, debugging, tests, review and writing across the project. The user confirmed Claude checked for technical gaps, with no resulting modification to existing implementation. This precise role is included in the copy-ready disclosure.

No generative-image model was used for the deck. Screenshots are actual application captures; vector diagrams/layout were made with AI-assisted code. Scientific outputs come from the deterministic source-backed backend. The team supplied requirements/data and makes final rights/access/submission decisions; automated software checks and human review do not certify the open scientific gates.

## 12. Actual Tests Executed

| Check | Fresh Command 14 result |
|---|---|
| `npm run typecheck` | PASS |
| `npm run build` | PASS; existing lazy chunk-size warning |
| Targeted Vitest | **40 passed, 0 failed**, four files |
| Targeted production Playwright | **45 passed, 0 failed**, 2.6 min, three exact viewports |
| Real backend-stopped production Recorded Evidence acceptance | PASS; fresh contexts, zero POST, zero external request, zero page error; six responsive scenario checks |
| Demo/source manifest and texture integrity | PASS through build plugin and targeted browser/fixture tests |
| Seven-page PDF structure/text | PASS; seven pages, embedded imagery/fonts, no out-of-page text; rasterized pages visually reviewed |
| git diff whitespace | PASS before commit |
| Full backend / full frontend regression | NOT_RETESTED; no production code changed |
| New live NASA E2E | NOT_RETESTED; intentionally no new science |
| Independent scientific certification | NOT_RETESTED; open Command 13 gates retained |
| GitHub CI | NOT_RETESTED; no CI PASS claimed |

Vitest files: `States.test.tsx`, `GlobeLoading.test.tsx`, local-horizon `trace.test.ts`, Alternative Explorer `local-status.test.tsx`. The previous 231 backend / 176 frontend Command 13 results are historical, not this run's counts.

Playwright selection: navigation, Alternative Explorer offline/radar/globe/fallback, globe rendering/texture, local horizon controls/supplied profiles and panoramic trace tests. Production application code is real; science-bearing presentation fixtures are labelled synthetic in those tests. The separate real offline acceptance contains no mocked API success.

Existing Playwright viewport defaults differ from the requested dimensions. An ignored temporary config supplied 1440×900, 768×1024 and 390×844 without changing the repository test architecture. Target expression:

```text
all screens render|keyboard navigation|scene areas|reduced motion|offline temporal|
local radar rings|candidate globe reuses|200% text, WebGL|real WebGL|local JPEG is|
orientation preview|validated profiles render|panorama trace toggles
```

PDF is 228272 bytes, SHA-256 `e013bdcb2e04a0ca5cb968dde5e3f150c24e4ddbd13f8c6a31326191122e5e09`. Page size is 1280×720 points. The English slide text remains editable in the pitch document; PDF generation used existing ReportLab/Pillow and validation used existing PyMuPDF. Large raw screenshots and logs are not part of the PR.

## 13. Remaining Risks

**BLOCKED — user decisions before official delivery:**

1. Approve original-code licensing/distribution. No LICENSE is added automatically.
2. Select access option A or B and explicitly authorize any publication. Private repository judge access is unverified.
3. Publish the approved presentation and final project separately; verify both without sign-in or private permission.
4. Confirm actual portal/event fields, timezone, character/media limits, member names and contribution details.
5. Review the final materials, manually submit for judging and retain confirmation.

These access/licensing gates do not invalidate the passed frontend/offline acceptance. Scientific limitations, emulated browser coverage, existing renderer bundle size and local-only deployment remain disclosed. Nothing computes while the server is down. No claimed URL or video substitutes for a missing approved public link.

## 14. Changed Files

1. `frontend/COMMAND_14_SPACE_APPS_SUBMISSION.md`
2. `frontend/COMMAND_14_JURY_PITCH.md`
3. `frontend/COMMAND_14_JURY_DECK.pdf`
4. `frontend/COMMAND_14_FINAL_REPORT.md`
5. `frontend/.gitattributes` — marks only this PDF as binary so Git does not apply text whitespace checks to compressed image/font bytes.

No production patch was necessary: no concrete critical UI issue was reproduced. No aesthetic refactor or new feature was introduced.

## 15. Commit and PR

Branch: `frontend/command-14-final-delivery`.

Final PR: [#35 — TEAM 24&28 — COMMAND 14 Final Frontend & Submission Readiness](https://github.com/MelisaSpX24/lunar-navigator/pull/35), opened for review and left unmerged. Presentation/material revision: `7ebfc5104665d313b3b0e45f5414a42b3ee89a14`; this report-link update follows it. The PR head identifies the final documentation revision (a commit cannot embed its own SHA). No CI success, public access, official submission or automatic merge is claimed. No publication is authorized.

## 16. FINAL READINESS DECISION

**COMMAND_14_BLOCKED — public submission access and licensing decisions remain open.**

Frontend production build, targeted tests, actual backend-stopped Recorded Evidence demo, seven-slide English PDF and copy-ready submission fields are prepared. There is no reproduced critical software blocker within this scope. However, a required public demo/final-project link and approved distribution/licensing plan are missing by explicit team decision. Therefore **COMMAND_14_COMPLETE_READY_FOR_SUBMISSION is not claimed**.

The shortest safe completion is a team decision on option A/B and licensing, approved publication of the two separate resources, logged-out access verification, then manual portal submission. No new scientific development, NASA recalculation or additional command is needed to use these prepared materials.
