# Same-site temporal optimizer

`optimize(request, provider, hints=(), geometry_priority=None)` changes only the UTC start. It reuses Command 07 windows, Command 08 evidence_identity/evaluate_operation, and the existing score. No second decision or score formula exists. No endpoint clipping, operation shortening, requirement relaxation or spatial search is performed.

## Request and confinement

TemporalOptimizationRequest contains baseline_analysis, window_template, evaluation_policy, UTC confinement, coarse/refinement steps and explicit budgets. Named sites need resolved coordinates and matching site ID. Pydantic validates UTC, positive steps/budgets, confinement of at most 31 days, a full operation fitting within the search interval and baseline/template geometry, heights and threshold consistency. Baseline remains a separate reference even if off-grid or outside alternative confinement. Each alternative must fit its entire unchanged duration within the requested interval.

Use exclude_unset=True when serializing requests to preserve explicitly activated Requirements fields. shifted_requests revalidates new AnalysisRequest and WindowSearchRequest objects. The original operation requirements/profile/options/observer are copied with their explicit-field semantics preserved. The candidate evidence hash is computed from its own returned window, never copied from baseline.

## Three stages

1. Discovery merges confined coarse-grid starts, recorded window starts, bracket endpoints and a post-bracket refinement-step candidate. UTC deduplication combines discovery sources. Hints are bounded; candidates beyond the admission cap are not generated indefinitely. Post-bracket candidates are prioritized; an optional geometry callback may order remaining candidates. Live CLI uses fast SPICE solar-centre elevation; this is only a selection heuristic, not a terrain/disc/operation result. Candidates not selected are not NOT_MET.
2. Detailed evaluation processes baseline first and then a bounded subset. RecordedProvider accepts only complete exact-start WindowSearchResult records; it never crops or relabels a wider interval. LiveProvider shares one open kernel/DEM/VisibilityEngine session across starts and calls run_windows. Full operation results come exclusively from evaluate_operation, including its mismatch checks.
3. Ranking prioritizes MET before NOT_MET before INCOMPLETE, then comparable scores and earlier UTC. A separate comparison checks source evidence, scientific configuration, actual observer metadata, operation requirements, score version/weights and evaluation policy. Incomparable evidence has null deltas and cannot recommend. Only completely evaluated MET alternatives classified as improved become recommendations, at most three. Equivalent alternatives remain in comparisons; the list is never padded.

A MET/100 baseline without measured improvement yields KEEP_CURRENT_PLAN. Other outcomes include CANDIDATES_FOUND, ONLY_INCOMPLETE_CANDIDATES and NO_ELIGIBLE_CANDIDATE_IN_EVALUATED_SET. Search completeness is separate: SEARCH_PARTIAL_RESOURCE_LIMIT, SEARCH_PARTIAL_EVIDENCE_UNAVAILABLE or SEARCH_COMPLETED_EVALUATED_SET. The evaluated set is not all physical times.

## Comparison and evidence

Baseline and alternatives carry complete operation provenance: scientific window digest, kernel/DEM identities, frame, UTC range, observer settings, requirements, sampling and policy. Metrics include total/longest/interruption/unknown durations. Score and duration deltas require equivalent methods and available comparable values. Display explanations never imply NASA endorsement, RF success, electrical production, certified continuity or global optimality.

STRICT_EVIDENCE inherits conservative INCOMPLETE/null behaviour for uncertified durations. PROTOTYPE_SAMPLED_ESTIMATE must be explicitly selected and labels every operation result. UNKNOWN never becomes suitability. A high NOT_MET score cannot outrank a qualifying MET decision as an eligible alternative.

## Resources and exact cache

Budgets bound coarse starts (max 512), detailed attempts including baseline (max eight), full visibility calls, new rays, terrain sample positions, cache entries and wall-time admission. Global LiveProvider counters are deltas from the borrowed engine's initial state. The guard checks remaining resources before every atomic visibility call. Zero new rays/points still allows valid exact-cache hits and makes misses UNKNOWN. Existing cache keys are unchanged. Source identity, geometry, height, exact azimuth and terrain policy are never interpolated or conflated.

Wall time is cooperative: an already admitted bounded single-UTC call may finish beyond the deadline. No thread cancels SPICE/raster operations mid-call. Kernel/DEM session setup and hashing occur before optimizer wall timing in CLI and are not included in that field. Candidate timing includes window generation and the small operation evaluation; these are not millisecond scientific searches. Operation-only replay costs are reported separately.

## CLI

```
PYTHONPATH=backend:. python -m data_pipeline.temporal_optimizer_cli --request optimizer.json --mode recorded --recorded baseline-window.json candidate-window.json --hints event-window.json --output new-result.json
PYTHONPATH=backend:. python -m data_pipeline.temporal_optimizer_cli --request optimizer.json --mode live --hints event-window.json --output new-live-result.json --window-output-dir fresh-window-directory
```

The request carries UTC range, limits and policy; no undocumented flags are required. Inputs may use the Command 07 envelope's full pilot via the existing loader. Summary-only evidence is rejected. Live mode uses existing NASA_KERNEL_DIR/NASA_KERNEL_INDEX and terrain configuration, baseline 5 m + 80 m, never automatically 20 m. Recorded mode opens no NASA sessions. Outputs and optional evidence directory use exclusive creation. Paths are explicitly selected by the caller; no archive extraction or candidate-derived directory traversal occurs. Invalid JSON/NaN/UTC/Pydantic input fails before scientific setup. Output JSON is finite.

## Scientific limits and Command 10 interface

The 675-second recorded bracket is only a discovery hint, not sunrise certification or a six-hour mission result. Short events between temporal samples and narrow terrain obstacles can be missed. Absolute registration and independent astronomy validation remain unresolved. Data digests bind supplied records, not independent external authenticity. Discovery ordering is a bounded engineering heuristic, not exhaustive optimization.

Command 10 may reuse candidate verification, operation evaluation, comparison and budgets, while supplying new coordinate-specific evidence. This command does not implement coordinate changes, frontend/API integration, RF/power models or production readiness. science_ready=false and the existing HTTP 503 are preserved.

## Command 09.1 — optional coverage hardening

Request field `selection_strategy` defaults to `LEGACY`; `COVERAGE_AWARE` enables stratified full-range discovery and a diverse detailed prefix. This changes which starts are selected, not their scientific evaluation. Scope counters distinguish strategy non-selection from scientific resource rejection and missing recorded evidence. See TEMPORAL_OPTIMIZER_PERFORMANCE.md for exact-cache admission separation, source mutation guards, performance tradeoffs and measured coverage.
