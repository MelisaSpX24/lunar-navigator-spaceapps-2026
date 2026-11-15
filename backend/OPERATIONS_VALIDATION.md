# Command 08 validation

Started from main d1e5dce, which merges PR #19 including the cache/origin correction. Baseline was freshly run: 417 passed, zero failed/skipped in 86.69 seconds.

The existing command-07-windows.json is an envelope with a full pilot WindowSearchResult. The nested pilot was parsed directly; it was not reconstructed from summary metrics. No new NASA astronomy or DEM computation was needed for operation evaluation. The regression suite still runs its existing live NASA tests where configured.

Recorded source: CR1 (-89.468, 222.6 east), MOON_ME_DE421, 2026-11-20 08:00–14:00 UTC, 21600 seconds, separate 1 m devices, DE421 five-kernel package, NONE, 64 disk samples, hourly timeline, PROTOTYPE/REPORT terrain, Site01 5 m + Product90 80 m. Source hashes and complete window request are preserved in each operation provenance record. Original Command 07 evidence and the 675-second bracket are unchanged.

Example assumptions (EXAMPLE_OPERATION_ASSUMPTION): Earth minimum 3600 s; solar minimum 3600 s; joint minimum 1800 s with simultaneous=true; short observation minimum Earth 3600 s and no solar requirement. Prototype outcomes: Earth MET/100, Solar NOT_MET/0, Joint NOT_MET/0, Short MET/100. All four STRICT outcomes are INCOMPLETE/null because relevant physical duration/continuity evidence is unavailable. These are recorded NASA model evaluations, not new observations or guaranteed mission outcomes.

Synthetic tests cover decision dominance, profile isolation, empty requirements, explicit presets/overrides, threshold equality, strict/prototype evidence, unknown family handling, unneeded missing Earth data, invalid metrics, sources, time/location/height/correction mismatch, named resolution, zero/null scores, high score with failed mandatory conditions, deterministic contributions and coefficient validation. Real artifact tests evaluate the four profiles and both policies against the recorded pilot. CLI tests check finite JSON, invalid request rejection and overwrite refusal.

Measured operation-layer timings and final test counts are in command-08-operations.json. Timings are machine-specific; explanation building is included in the full operation timing, not separately benchmarked. Input validation and scoring are also benchmarked without NASA session initialization.

No independent observational validation, absolute terrain registration guarantee, certified continuous visibility, electrical output, RF budget, mission success probability or landing certification is claimed. Strict scoring stays null. The conservative unknown policy may return INCOMPLETE where future tighter bounds could decide. No custom scoring request configuration is offered in v1.

Final regression: **492 PASSED / 0 FAILED / 0 SKIPPED**. New cases: 71 synthetic/analytical/CLI, four recorded real NASA artifact evaluations (each also checks STRICT). pip check and git diff --check passed. Existing Starlette/httpx deprecation warning remains. CLI was additionally executed against the real Command 07 envelope and refused overwrite. No new operation-stage NASA calculations.
