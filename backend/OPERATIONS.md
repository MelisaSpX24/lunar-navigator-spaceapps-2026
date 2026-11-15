# Operation decision and Planning Suitability Index

This backend-local layer consumes an existing WindowSearchResult. It never opens NASA rasters, loads kernels or computes astronomy. HTTP analysis remains 503/SCIENCE_ENGINE_NOT_READY and science_ready remains false.

## Requests and matching

OperationEvaluationRequest embeds the existing AnalysisRequest. Pydantic rejects missing required input, invalid UTC, invalid numeric thresholds, contradictory joint requirements and duration inconsistencies before any computation. Named sites require an explicit ResolvedSite and matching resolved_site_id; coordinates are never guessed.

Supply evaluation_policy (default STRICT_EVIDENCE), correction (default NONE) and window_evidence_sha256. evidence_identity(window) is SHA-256 over sorted compact JSON of the validated full model. It binds the supplied artifact, not its external authenticity. Matching checks coordinates/frame/latitude type, time and duration, separate device heights, solar threshold, Earth margin, correction, joint availability and evidence digest. Mismatch gives INCOMPLETE/null score. Source metadata must contain DEM hash/frame and kernel filename/hash identities for REAL_NASA_PROTOTYPE. Structural validity does not authenticate NASA files or observational correctness.

Preserve explicitly supplied Requirements fields: use model_dump(exclude_unset=True) when constructing request JSON. Pydantic defaults are contextual thresholds and do not silently enable unrelated rules. Serializing every default and then sending it explicitly enables standalone threshold rules. No profile injects mandatory requirements. Empty custom or other empty profiles produce INCOMPLETE/null score.

Optional SOLAR_1H and EARTH_1H presets supply a 3600-second requirement only if absent. They are EXAMPLE_OPERATION_ASSUMPTION; explicit values, including zero, win. These are not NASA requirements. Effective preset duration must fit the analysis.

## Rules and evidence

All profiles share one evaluator. Minimum Sun total, maximum dark gap, minimum Earth continuous and minimum joint continuous use the matching window metrics. require_simultaneous without a joint duration means at least one positive-duration estimated Joint MET interval, not a single coincident UTC. Joint false adds no joint rule.

Earth margin qualifies the Earth windows already calculated by Command 07. If explicitly supplied with min_earth_continuous_s, the margin rule uses that duration; standalone margin requests require estimated coverage for the whole operation. Standalone explicit solar fraction likewise requires whole-operation sampled solar continuity. Fraction alongside a duration or joint requirement qualifies those windows rather than injecting whole-operation illumination. Actual/required rule durations are in seconds; margin/fraction qualifiers are included in the message and effective requirements.

STRICT_EVIDENCE never treats sampled continuity or interruption durations as physical proof. Only supplied total-duration bounds can support the total Sun-duration rule; total bounds cannot support longest continuous duration. Current NASA pilot bounds are null, so duration rules remain INCOMPLETE. Bounds supplied by another producer are assumed to be honestly qualified; this module cannot independently certify them.

PROTOTYPE_SAMPLED_ESTIMATE compares complete finite-model estimates. Any unknown or unavailable interval in the relevant family conservatively makes that rule INCOMPLETE; this may decline to decide even when a tighter future bound could decide it. Unrelated missing families do not impose unrelated operation conditions. Unknown intervals are never merged into continuous windows. Duration/segment totals, ordering, range and longest values are checked before use.

Decision combination: any supported NOT_MET dominates; otherwise any INCOMPLETE (or no rule) yields INCOMPLETE; otherwise MET. Score never changes the decision. Explanations carry required/actual values, units, source metric, policy and reason codes.

## Score v1

Model version: 24and28-planning-score-v1. Score = 100 × sum(normalized value × weight). Contributions are not rounded internally. Score is not probability of mission success.

Metrics: solar total/duration, solar longest/duration, 1 − longest dark gap/duration, Earth total/duration, Earth longest/duration, joint total/duration. Invalid durations are rejected rather than clipped. No custom weights are exposed in the request; coefficient validation protects the scorer function.

Solar profile weights: total .45, continuity .35, darkness resilience .20, when solar requirements are active. Earth transmission: continuity .65, availability .35, when Earth requirements are active. Other cases and short/custom profiles use equal weights among metrics selected by explicit active conditions: Sun duration, darkness resilience, Earth continuity/availability, joint availability. An explicit fraction alone selects solar duration. Prescribed profile weights are EXAMPLE_OPERATION_ASSUMPTION and versioned engineering choices.

STRICT scores are null because the current model cannot certify every continuity component. Prototype scores require all weighted metrics available with no unresolved intervals. Missing components are not replaced by zero and their weights are not redistributed. A prototype score of 100 with a mandatory NOT_MET rule remains NOT_MET.

## Data quality and provenance

INSUFFICIENT: mismatch, invalid metrics/sources, no active rules, or missing/unknown relevant family. Otherwise LIMITED, including known-source NASA sampled estimates. No current result claims SUFFICIENT physical certification. Operation outcome and quality are independent. Synthetic derivatives retain SYNTHETIC_TEST; recorded NASA artifacts retain REAL_NASA_PROTOTYPE, with an explicit artifact reuse note in validation output.

## CLI

```
PYTHONPATH=backend:. python -m data_pipeline.operations_cli --request operation.json --windows windows.json --output new-result.json
PYTHONPATH=backend:. python -m data_pipeline.operations_validation --output new-validation.json
```

Request follows OperationEvaluationRequest, including nested AnalysisRequest and canonical evidence digest. Windows input may be a full WindowSearchResult or the Command 07 envelope containing its complete pilot field. A summary-only object is rejected. CLI opens user-selected paths only, extracts no archives, performs no path-based writes beyond the explicitly selected output and uses exclusive creation. Existing output is refused. Invalid JSON/Pydantic input fails before output creation. Finite JSON only.

## Limits and future interface

Command 09 may reuse evaluate_operation(request, windows) and evidence_identity(windows), retaining policy, rule evidence, provenance and null scores. No optimizer, profile-specific astronomy, frontend, API integration or scoring of landing safety is included. Solar geometry is not power; Earth geometry is not RF success; time windows are sampled estimates. Original terrain registration and independent astronomy limitations propagate unchanged.
