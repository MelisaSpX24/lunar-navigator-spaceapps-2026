# Recorded NASA demo evidence — Command 12

This portable package is an offline projection of reviewed Command 10 calculation records. It opens no DEMs, kernels, HTTP service or scientific engine. No new decision or score is computed. `manifest.json` pins each payload's bytes/SHA-256 and both upstream evidence files. Payload source pointers and window hashes trace every exported candidate back to its record. Unknown publisher versions remain null.

## Files and contract

- `temporal_demo.json`: six-hour CR1 Solar operation, baseline November 20 08:00 UTC versus evaluated November 23 16:26:15 UTC; NOT_MET/0 → MET/100.
- `local_demo.json`: separate one-hour operation on November 20 08:00 UTC, baseline plus all three detailed MET/100 local recommendations. It does not claim the full search disk optimum.
- `manifest.json`: portable checksums, source checksums, origin and limitations.
- `export_demo.py`: deterministic exporter/validator using existing Pydantic request, decision, score, metric and optimizer models. No API or NASA assets required.

`24and28-demo-evidence-v1` is a backend-local **projection**, not AnalysisResult 1.0 and not the full optimizer response. Each scenario contains its original optimizer request, a baseline and selected evaluated alternatives. Each candidate has its exact analysis source request (preserving supplied requirement fields), decision/rule evidence, unchanged score/model version, sampled Sun/Earth/Joint metrics, source identity, window-evidence hash, quality and limitations. Local candidates additionally contain containing-cell elevation, slope/source evidence, distance and bearing. Both scenarios share the source-provenance dictionary identity.

Temporal source requests already contain expanded requirement fields in the original canonical record; the exporter preserves them. Local input explicitly supplied only min_sun_visible_s=600, and that distinction is preserved. Do not add omitted default requirements when constructing a new live request. `source_optimizer_request` includes scientific configuration and historical settings; it is not itself a job submission envelope.

## Frontend panels

Alternative Explorer and A/B Comparison can display requests, UTC/duration, coordinate markers, decision/rule explanations, planning-score components, sampled duration/continuity/interruption metrics and source/quality limitations. Render local longitude as east-positive in [0,360); latitude is planetocentric, frame MOON_ME_DE421. Distance/bearing use the 1737400 m lunar sphere; bearing is clockwise from north. Do not treat screen-plane distance near the pole as geodesic distance.

The selected optimizer summaries do not supply complete horizon profiles, timeline samples or window segment arrays in this package. `analysis_result`, `horizon_profile`, `time_series` and `window_segments` are explicitly null. Do not generate a horizon chart, astronomical animation, event UTC, timeline or exact window boundaries from duration metrics. A requested include_full_horizon flag is not evidence that its profile is in this export. Temporal DEM elevation is not reconstructed; local elevation is the recorded terrain value. Null is unavailable, not zero. Use live results or a separately validated full AnalysisResult for those panels.

Compare temporal candidates only within the six-hour scenario (only start UTC changes). Compare local candidates only within the one-hour scenario (coordinates and corresponding DEM surface change). Profile, explicit requirements, instrument heights, correction, source identity and score version remain common within each pair. **Do not compare their scores/durations as one cross-scenario A/B experiment.**

## Live API handoff

Existing endpoints: POST `/api/v1/optimizations/temporal`, POST `/api/v1/optimizations/local`; GET `/api/v1/capabilities` and `/api/v1/result-schemas`. New live work returns 202 and a job ID; poll GET `/api/v1/jobs/{id}`, retrieve GET `/api/v1/jobs/{id}/result`, cancel with POST `/api/v1/jobs/{id}/cancel`. Full setup and envelopes: `backend/INTEGRATION_HANDOFF.md` and `backend/SCIENTIFIC_JOB_API.md`.

For local jobs put `search_radius_m` inside `optimization`: 1000, 3000 or 5000 for 1/3/5 km, within the current (0,5000] m bound. Changing radius does not turn this fixed 5 km recorded package into a newly evaluated search. Keep baseline_analysis and a matching backend-generated window_template, select budgets and evaluation policy explicitly, and fetch the schemas for the complete request. These files contain no live job IDs; they work when the backend is stopped. New user coordinates/dates require live scientific work rather than relabelling a record.

Show RECORDED_EVIDENCE_EXPORT visibly for playback; the original scientific origin remains REAL_NASA_PROTOTYPE. MET here is under PROTOTYPE_SAMPLED_ESTIMATE, not STRICT certification. Display sampled-estimate labels, null certified bounds, quality/reason codes and limitations. General science_ready remains false. Geometric sunlight is not electrical output, Earth clearance is not RF success, slope estimates are not landing safety, and a planning score is not success probability. Absolute DEM registration remains unverified.

## Reproduce and validate

From repository root with the backend Python dependencies installed:

```
PYTHONPATH=backend:. python -m data_pipeline.demo.export_demo --check
PYTHONPATH=backend:. python -m data_pipeline.demo.export_demo --output-dir /new/export-directory
PYTHONPATH=backend:. python -m pytest -q backend/tests/test_demo_evidence.py
```

Export refuses existing payloads; --check compares deterministic bytes, source bindings and existing Pydantic models without writing. The manifest hashes use SHA-256 over exact file bytes; full-source identity uses the documented sorted JSON encoding. No timestamp or local path is injected. The large upstream files are referenced, never copied. Reading the three JSON files needs no Python process or running backend.
