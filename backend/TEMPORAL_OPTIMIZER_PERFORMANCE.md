# Command 09.1 — measured efficiency and search coverage

## Initial architecture and baseline

Base main e2ed360 includes PR #23 merge b159de0b9eb8e74b6a608b12c69458f0dcf72acf and frontend PR #24. Fresh initial suite: 550 passed, zero failed/skipped (88.49 s). Historical Command 09 424.219-second optimizer run remains historical evidence, not a before/after speed claim.

The existing chain remains discovery → run_windows → candidate evidence_identity → evaluate_operation → decision-first comparison. Only start UTC changes. No decision/scoring/formula, sampling interval, range, source resolution, requirements or operation duration is relaxed.

## Profiling methodology and measured bottlenecks

An optional cProfile runner separates synthetic fixtures, recorded NASA replay and live NASA computation. Same-machine before/final-after runs use one 64-sample CR1 epoch at 2026-11-20T08:00:00Z, 1 m devices, NONE, DE421, PROTOTYPE/REPORT, Site01 5 m + Product90 80 m and 150 km terrain range. Each run measures cold, identical warm and changed-total-budget warm requests in one open session. Setup, initial source hashing and metadata capture precede timing. Profiled timings include instrumentation overhead. One intermediate check and final sidecar guard check made three cold single-UTC live executions total; no new six-hour search was run.

Before: horizon _ray cumulative 53.947 s, terrain/fusion query cumulative 52.038 s, DEM sample cumulative 50.406 s, DEM _read cumulative 14.352 s, quality-window raster helper cumulative 16.911 s. These are nested costs and must not be summed. Raster sampling, coordinate/provenance/quality processing dominate. Geodesic/geometry formulas were not changed.

quality_identity was called 260 times during one 130-ray visibility calculation, costing 2.079 s cumulatively, largely repeated dataset opening. No auxiliary SHA hashing was observed inside this timed workload; initial data hashes remain verified. Preflight also repeats surface/observer/geometry preparation; its measured cost was milliseconds, so broad preparation refactoring was rejected. Disk samples were generated six times, including a duplicate diagnostic pass.

## Applied changes and safeguards

1. Horizon source metadata is captured once per VisibilityEngine session and returned as a deep copy through a guarded provider. Standalone TerrainHorizonEngine retains fresh metadata construction. Source files/known auxiliary files, standard optional sidecars, source references, quality declarations, reader identity and closed-session state are checked before cache lookup and metadata reuse. Ordinary file size/inode/device/mtime/ctime or declaration changes reject the session; reopening re-runs existing source SHA validation. This is not adversarial tamper detection against spoofed filesystem metadata. No initial hash verification is disabled.
2. The same deterministic immutable disk sample tuple is used for fraction integration and diagnostic iteration. Calls fall from six to four per run; azimuth/elevation/weight/order/count are unchanged. Preflight still performs admission inventory.
3. Only COMPLETE_SAMPLED_RANGE rays may use a key independent of max_total_samples. That field is total resource admission allowance, not a scientific sampling parameter. Exact azimuth and all other request fields, including max_samples_per_ray, range, sampling, observer/height/policy and source namespace remain in the key. UNKNOWN/INCOMPLETE results retain exact budget-specific keys. A resource-interrupted ray remains uncached. Original computation evidence ID is retained on reuse, not relabelled as a new calculation. LRU stays session-local and bounded.

Source guarding adds warm-cache overhead; it is an explicit integrity/performance tradeoff. No approximate azimuth lookup, interpolation, incomplete-to-complete promotion, global cache, window cropping or sample-level UTC cache was introduced. Sample-level reuse and broad raster/vectorization changes were rejected as unnecessary risk in this scope.

## Comparable measurements

| Profiled workload | Before | Final after |
|---|---:|---:|
| Live cold visibility | 56.437652 s | 53.394451 s |
| Identical warm visibility | 0.013730 s | 0.140151 s |
| Cold new exact rays / DEM positions | 130 / 58661 | 130 / 58661 |
| Warm hits / misses | 130 / 0 | 130 / 0 |
| Changed-budget warm hits / misses | 0 / 130 | 130 / 0 |
| Cold peak RSS | 143412 KiB | 143860 KiB |
| Synthetic cold | 0.468316 s | 0.513867 s |
| Recorded optimizer replay | 0.008416 s | 0.007138 s |
| New full six-hour window | NOT_MEASURED | NOT_MEASURED |
| New full live optimizer | NOT_MEASURED | NOT_MEASURED |
| New live detailed alternatives/recommendations | NOT_MEASURED | NOT_MEASURED |

Cold live ratio is 1.056995 in this single profiled pair (~5.4% lower elapsed), not a statistical or hardware-independent speed guarantee. Warm and synthetic paths became slower due to guards. Changed-budget elapsed is not a speedup comparison: before returned UNKNOWN, after reused valid completed evidence with zero new DEM positions. This is recovered evaluability, not fabricated science.

Whole scientific visibility payloads (excluding performance fields) match exactly for cold and identical-warm runs, including sources, kernel IDs, horizon identities, body geometry and fractions. Changed-budget after bodies match the complete cold bodies exactly. The previous UNKNOWN is resolved using prior complete rays; partial/unknown evidence is not promoted. Digests and profiler rows are recorded in command-09-1-performance.json.

## Optional coverage-aware discovery

Default LEGACY behaviour remains. selection_strategy=COVERAGE_AWARE stratifies a bounded grid across confinement, reserves event-related candidates and greedily selects temporally separated detailed starts after one event/geometry-prioritized start. Candidate generation, selection and successful scientific verification are separate counts. Remaining pool candidates are NOT_SELECTED_FOR_DETAILED_EVALUATION, not falsely resource-rejected or NOT_MET. Backend-local scope counters distinguish selected, attempted, completed, invalid, evidence-unavailable and scientifically incomplete results. Scientific resource exhaustion is still separate and preserves completed recommendations.

With the same eight-pool-slot/three-alternative-selection budget and recorded event hints, legacy selected span was 4275 s; coverage-aware selected span was 453600 s. Discovery took 0.000030/0.000056 s respectively. Generated counts were seven/eight (legacy baseline consumes one original pool slot); neither benchmark performed new candidate science. Broader discovery span is not evidence of more suitable alternatives. An extreme cap and temporal clustering are covered by deterministic tests. No default strategy change is claimed.

## Validation, limits and reproduction

Use the configured project Python with PYTHONPATH=backend:.:

```
python -m data_pipeline.temporal_optimizer_benchmark --mode synthetic --output fresh-synthetic.json
python -m data_pipeline.temporal_optimizer_benchmark --mode recorded --output fresh-recorded.json
python -m data_pipeline.temporal_optimizer_benchmark --mode live --output fresh-live.json
python -m pytest -q backend/tests -ra
python -m pip check
```

Outputs refuse overwrite and use finite JSON. Existing temporal_optimizer_cli supports the new optional request field without new flags. Source identities and scientific configuration are included in evidence. Recorded replay opens no new NASA science sessions. Existing NASA artifacts and the 675-second bracket remain unchanged. Current model/readiness/API/frontend/contracts/default 5 m + 80 m/STRICT settings remain intact. No GitHub CI execution is claimed.

Command 10 may reuse guarded provenance, complete-ray resource admission separation and optional temporal diversification. It still requires independent coordinate-specific scientific evidence. Finite raster/ray/disk/time sampling, source registration, independent observational validation and global optimum limitations remain.

Final regression: **570 PASSED / 0 FAILED / 0 SKIPPED**, 86.69 s; 20 new regressions. pip check, git diff --check, finite recorded CLI JSON and overwrite refusal passed. Existing recorded NASA profile/strict/unknown regressions passed. GitHub CI was not run by this task. Formatting-only science diff reduction was checked by exact AST equality against the tested implementation.
