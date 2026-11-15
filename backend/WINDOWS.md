# Scientific visibility windows

Command 07 provides backend-local `WindowSearchRequest`, `search`, and `run_windows`. Existing HTTP contracts, readiness and DEM defaults remain unchanged. Reuse one open KernelSession, terrain session and VisibilityEngine for an analysis.

Solar MET means the sampled disk lower bound is at least the requested fraction; NOT_MET means its upper bound is below it. Otherwise the condition is UNKNOWN. Earth MET uses centre clearance against the requested margin, never visible Earth disk fraction. Joint uses three-valued AND: NOT_MET dominates UNKNOWN. These are geometric conditions, not electrical power, RF success or final operation decisions.

Requests embed the existing VisibilityRequest. Thresholds, separate device heights, correction, terrain policy, disk sample count, temporal step, midpoint depth, event resolution, evaluation/ray/terrain budgets are explicit. Defaults remain STRICT in the underlying terrain request. Real experiments explicitly use PROTOTYPE/REPORT and Site01 5 m + Product90 80 m.

Civil UTC samples are validated using the existing validator and individually converted by SPICE. Naive/nonzero-offset timestamps are rejected. Intervals spanning unsupported leap-second behaviour are rejected rather than treating UTC as uniform ET. End UTC is evaluated as a boundary probe; output segments are [start,end).

Boundary-first evaluation then coarse grid sampling preserves partial evidence under budget interruption. Optional midpoint subdivision also examines equal-endpoint intervals; it can reveal short interruptions, but cannot exclude still shorter missed events. Opposite known states produce brackets refined by bounded temporal bisection. UNKNOWN stops refinement. Multiple crossings can remain within a bracket; no unique physical event UTC is returned.

Equal known endpoints define only SAMPLED_ESTIMATE segments. Differing or UNKNOWN endpoints define TEMPORAL_INTERVAL_UNRESOLVED segments. Unknown intervals never join two MET windows. Censoring at operation boundaries indicates a window may extend outside the confinement interval, not missing evidence. Certified duration bounds remain null. Estimated total/longest MET and NOT_MET durations sum these finite-model segments; they are not certified continuity or duration.

`sampled_windows` is null when an unresolved interval prevents a complete list; [] means no MET window in the completed sampled estimate. Partial known segments remain available separately. No implicit conversion into the shared Windows contract is provided. Next-event results distinguish bracketed, unresolved, incomplete, coverage-limited and no-observed-event searches. No observed event does not mean all physical events have been excluded.

The optional validation runner first scans bounded SPICE geometry, then exact centre terrain rays to rank candidates, and finally performs full disk evaluations for the first candidate interval. Centre geometry does not establish a Solar Window. The pilot helper assumes equal device heights; production window evaluations preserve separate heights.

## Reproduction

With the existing NASA environment configured and PYTHONPATH=backend:., run:

```
python -m data_pipeline.windows_cli --request request.json --output new-result.json
python -m data_pipeline.windows_validation --output new-candidates.json
python -m pytest -q backend/tests/test_windows.py
```

Request JSON follows WindowSearchRequest. `--cache-size` is bounded by the existing 1–4096 entry engine. `--use-20m` is explicit and optional; baseline selection is unchanged. Outputs use exclusive creation, finite JSON, read-only NASA inputs and no automatic downloads.

Command 08 can consume temporal conditions, segments, brackets, metrics and provenance. It must retain UNKNOWN and sampled-evidence labels. Scoring, operation decisions and optimization are intentionally absent. Frontend animation interpolation cannot create scientific events.

## Reference limitations

NAIF Time Required Reading: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/time.html

NAIF Geometry Finder Required Reading: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/gf.html

New retrieval attempts were blocked by HTTP tunnel 403 in this environment. These references were not newly verified. SPICE GF is not a substitute for this DEM/disk predicate. Independent observational astronomy validation and absolute terrain registration remain unestablished. Finite ray/raster/disk/time sampling can miss obstacles or events. This is not a landing safety certification tool.
