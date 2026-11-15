# Command 09 validation

Base main 66a65fa includes merged PR #21 (82bd262). Fresh baseline suite: 492 passed / zero failed / zero skipped in 86.27 s.

## Actual live scientific experiment

One new shared kernel/DEM session computed both the full six-hour baseline and a different six-hour candidate. CR1: -89.468, 222.6 east, MOON_ME_DE421, real Site01 observer height, separate 1 m devices, NONE, DE421 five-kernel package, Site01 5 m + Product90 80 m, PROTOTYPE/REPORT, 64 disk samples, hourly temporal grid. Source hashes, observer metadata, window digests and complete new WindowSearchResult objects are in command-09-temporal-optimizer.json. No 20 m promotion or source mutation occurred.

Baseline: 2026-11-20T08:00:00Z–14:00:00Z. Seven new live epochs: 08:00,09:00,10:00,11:00,12:00,13:00,14:00 (end boundary probe). Solar NOT_MET, Earth MET, joint NOT_MET. Solar operation minimum 3600 seconds under prototype policy: NOT_MET/0. Window generation 225.889947 s; 910 rays; 413074 DEM positions.

Candidate: 2026-11-23T17:26:15Z–23:26:15Z. Seven new live epochs at hourly offsets including the end probe. Solar/Earth/joint all MET. The unchanged solar operation is MET/100 under PROTOTYPE_SAMPLED_ESTIMATE. Estimated solar and joint duration each increased by 21600 s; Earth duration delta 0; score delta +100; unknown duration delta 0. Candidate window generation 198.315758 s; 910 rays; 383385 DEM positions. The same candidate is not a STRICT certified recommendation.

The recorded Command 07 bracket 16:15:00–16:26:15 (675 s, EVENT_BRACKET_NOT_REFINED) generated the post-bracket +1-hour candidate. It was not treated as exact sunrise or proof of six-hour suitability. The full new candidate calculation supplies that finite-model evidence.

Search: 20–27 November, 6-hour coarse grid plus evidence hints. Thirty unique alternatives; two detailed windows including baseline; 29 alternatives not evaluated because the configured detailed limit was two. One improved recommendation, CANDIDATES_FOUND and SEARCH_PARTIAL_RESOURCE_LIMIT. This is not an exhaustive or globally optimal result.

Optimizer total: 424.219248 s, discovery 0.004771 s, SPICE-only priority scan 0.004688 s. Setup/hash time precedes this timer. Combined detailed candidate timings include window work plus small operation overhead. Total 1820 exact new rays/cache misses, zero cache hits/evictions, 796459 DEM positions, 14 full single-UTC visibility calls, peak RSS 178768 KiB (~174.6 MiB). This was within 4000 rays, 3000000 positions, 14 visibility calls and 900 s admission limits. Exact azimuths differed, so no real cache speedup is claimed. Synthetic static-direction tests demonstrate cache reuse without interpolation.

## Recorded replays and test scope

The two fresh live artifacts were replayed through the current optimizer for Solar, Earth, Custom Joint and Earth-only Short profiles in both policies. These eight replays are not additional NASA geometry calculations. Prototype Solar/Joint: improved MET/100 candidate from NOT_MET/0 baseline. Earth/Short: KEEP_CURRENT_PLAN with MET/100 baseline and equivalent MET/100 alternative. All four STRICT cases: INCOMPLETE/null, no suitable recommendation. Replays took about 3.4–5.6 ms; this is operation/evidence processing, not new scientific window computation.

Eight real recorded-artifact pytest cases cover the previous NASA pilot and the two new live artifacts across four profiles, including strict checks. Synthetic tests cover UTC/range validation, fixed requirements and duration, deduplication, source/height/sampling mismatch, deterministic decision-first ranking, unknown evidence, no improvement, global visibility/ray/terrain/time budgets and exact-cache reuse. CLI finite JSON, invalid input and overwrite rejection are tested. Real recorded CLI and live CLI were both run.

Original Command 07/08 evidence, the 675-second bracket, existing science code, frontend/contracts, API 503, STRICT terrain defaults and science_ready=false are preserved. No NASA binary is committed. Cooperative wall admission can overrun by one bounded atomic UTC call; setup time is separate. Finite time/disk/raster samples can miss short events/obstacles; absolute terrain registration and independent observational astronomy validation remain unresolved.

Full final regression and quality-check counts are recorded in the evidence test_summary field.

Final package: **550 PASSED / 0 FAILED / 0 SKIPPED**, 85.06 s. Added 50 synthetic/analytical/CLI regressions and eight recorded real-data artifact cases. The two new live scientific windows/14 epochs were executed by the live CLI, not by eight independent NASA tests. pip check and git diff --check passed. One existing Starlette/httpx deprecation warning remains.

Command 09.1 validation is recorded separately in TEMPORAL_OPTIMIZER_PERFORMANCE.md and command-09-1-performance.json. The original Command 09 evidence and its live experiment are preserved. Recorded Solar baseline/alternative remain NOT_MET/0 and MET/100; Earth/Short KEEP_CURRENT_PLAN, Joint improvement and STRICT incomplete behaviour remain tested.
