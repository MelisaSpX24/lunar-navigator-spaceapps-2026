# Frontend Command 02 — validation record

## Repository evidence

Base: `15d8b63da3ff9b6c4233829b7ff93cc23a4e97f7`, the main merge of PR #5.
The Command 01 commit `f85e756e75d2a0fe9f7b99a3eb6ead69a1d004c4` is an
ancestor. Main was read through the existing HTTPS Git proxy and fetched before
creating `frontend/command-02-design-system`. The initial working tree was clean.

Only frontend files are in scope. No backend, data pipeline, contracts or root
files are changed. No new dependencies or lockfile changes are needed.

## Executed checks — 2026-11-14

Node 24.22.1, npm 11.9.0, system Chromium 156.0.8078.79 on Linux.

| Check | Command 01 baseline at main | Command 02 |
| --- | --- | --- |
| `npm ci` | PASS | PASS |
| `npm run typecheck` | PASS | PASS |
| `npm run build` | PASS | PASS |
| `npm run test -- --run` | 11 passed | 13 passed |
| `TEST_BROWSER_PATH=/usr/bin/chromium npm run test:e2e` | 12 passed | 18 passed |

The original component and browser scenarios remain. Added checks cover the
honest data-mode placeholder and accessible renderer-independent SceneViewport;
browser checks cover viewport dimensions, 44 px touch targets, visible keyboard
focus, mobile analysis panel order, reduced motion and 200% root text sizing.
Text block scroll widths are checked to catch clipping hidden by panel overflow.

That stronger check initially found one parameter description clipping on tablet
and two state headings clipping on mobile with enlarged text. Supported word
wrapping was added; all 18 browser executions then passed, with no skips or
remaining failures. No assertion was disabled or relaxed to conceal the issue.

## Visual review

Full-page Chromium screenshots of Mission Setup, Mission Analysis and Alternative
Explorer were inspected at 1440×1000, 820×1180 and 390×844 (nine screenshots).
They are generated under ignored `test-results/` by the browser suite. The scenes,
header, responsive navigation, panel hierarchy and unavailable-data labels were
reviewed; no horizontal overflow was observed. Enlarged text is separately
checked by automation. The mobile analysis order is horizon, Sun, Earth, timeline,
assessment, score, quality. Global and local scene containers meet their 380 px
mobile minimum, and the global view dominates the desktop setup workspace.

Selected solid text/background token pairs were measured using WCAG relative
luminance: primary text/panel 14.70:1; muted text/raised surface 7.91:1;
accent/panel 11.32:1; warning/warning surface 8.83:1; error/error surface 9.54:1.
This is a palette check, not a complete accessibility certification. Keyboard
focus, skip navigation and semantic regions are covered by automated tests.

## Production output comparison

Both builds used the same dependency lockfile and environment. Vite-reported
decimal kB, including minification; gzip values are estimates from the build.

| Asset | Command 01 | Command 02 | Difference |
| --- | ---: | ---: | ---: |
| JavaScript | 270.39 kB | 270.70 kB | +0.31 kB |
| JavaScript gzip | 85.46 kB | 85.73 kB | +0.27 kB |
| CSS | 9.45 kB | 12.78 kB | +3.33 kB |
| CSS gzip | 2.62 kB | 3.24 kB | +0.62 kB |

No new UI framework, 3D package, network asset, web font or ongoing animation is
introduced. The scene background uses bounded CSS decoration. Buttons use only
short color transitions, disabled when reduced motion is requested.

## Limits

No real-device, Firefox, Safari, screen-reader, WebGL or GPU performance tests were
run. Mobile and tablet results use Chromium emulation. The 200% check changes the
root text size; it is not a physical-device or browser-zoom certification. Bundle
size checks do not establish future 3D performance. No NASA data, mission analysis,
candidate ranking, scientific form logic or API integration was exercised or
implemented. Current missing-data messages are intentional.
