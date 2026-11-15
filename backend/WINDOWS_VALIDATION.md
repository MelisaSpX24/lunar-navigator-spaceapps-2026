# Command 07 validation

Base main 6d78a01 includes merged PR #17 (merge bee0daa). All new work is backend-local.

Fresh real NASA CLI pilot: CR1 (-89.468, 222.6 east), MOON_ME_DE421, 2026-11-20 08:00–14:00 UTC, hourly samples including end boundary probe, 1 m devices, NONE, PROTOTYPE/REPORT, Site01 5 m + Product90 80 m. Kernel and DEM identities/hashes are retained in command-07-windows.json. No 20 m source promotion occurred.

All seven samples: solar NOT_MET, Earth MET, joint NOT_MET. Solar and joint sampled window lists are empty. Earth has one censored [08:00,14:00) sampled window, estimated duration 21600 seconds. No transition observed within this hourly search; short events remain possible. Certified duration bounds are null. Unknown sampled temporal duration is zero, which is not continuous physical certification.

Pilot: 288.331790 s, 910 completed exact rays, 413074 DEM positions, zero cache hits (different exact directions), peak RSS 154184 KiB. Performance includes concurrent environment activity.

Extended scan: fifteen SPICE epochs at 12-hour spacing across seven days, geometry cost 0.004017 s. Exact centre rays selected a candidate interval; eight full disk evaluations and six bisections yielded Sun and joint START brackets at 2026-11-23T16:15:00Z–16:26:15Z. Width 675 s, EVENT_BRACKET_NOT_REFINED: configured refinement budget prevented the requested 60 s target. No unique event time is reported. The candidate analysis returned COMPLETED execution, but bracket refinement remains incomplete. This is not an independent observational comparison.

Extended experiment: 291.665660 s overall, 1053 completed rays including 15 candidate centre rays, 444739 DEM positions, two exact-ray cache hits, peak RSS 155904 KiB. Baseline data and kernel sessions were reused within each analysis. Source hashes were not recalculated per UTC.

Tests: 45 new deterministic synthetic/analytical cases, five real-data artifact assertions against the freshly generated CLI pilot. These five assert live experiment output; they are not five independent NASA executions. Existing suite also executes real NASA tests with configured paths. See final evidence test summary for the measured complete suite result.

CLI produced finite JSON and refused a second write to the same output. Synthetic fixtures cover hidden short events, double crossings, UNKNOWN gaps, threshold equality, nonfinite rejection, UTC validation, budgets, censoring and duration semantics. Existing API readiness remains false.

Reproduction: see WINDOWS.md; NASA_WINDOWS_EVIDENCE must point to the fresh windows_cli output for artifact tests. NASA_VISIBILITY_BUDGET_EVIDENCE points to the separate Command 06.1 evidence for its existing assertions. Real data are not committed.

Limitations: finite time/disk/raster/ray samples, unresolved absolute registration, no independent astronomy observation, missed events between samples, no physical duration bounds, no RF/power/operation scoring. NAIF documentation retrieval was blocked by HTTP 403; no new reference retrieval is claimed.

Final full suite: **406 PASSED / 0 FAILED / 0 SKIPPED**, 86.02 s. pip check and diff check passed. One pre-existing Starlette/httpx deprecation warning. Baseline before changes: 356 passed.
