# Local jury demo

This is a local Linux/POSIX prototype. No VPS, public tunnel, domain or cloud service is required. Native Windows is unsupported by the scientific worker's `fcntl` ownership lock; use WSL2 or Linux. Existing startup commands are sufficient; no additional launcher is provided.

## Start two local processes

From the repository root, activate the already installed backend Python environment. Configure trusted local files (placeholders below must be replaced by the operator):

```bash
export PYTHONPATH=backend:.
export NASA_KERNEL_DIR=/trusted/kernels
export NASA_KERNEL_INDEX=/trusted/kernels/kernel-index.json
export NASA_LOLA_VALIDATION_DIR=/trusted/lola
export LUNAR_ENABLE_JOBS=1
export LUNAR_JOB_DB=/private/persistent/lunar-jobs/jobs.sqlite
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --workers 1
```

Keep the private SQLite directory across restarts. Use exactly one scientific worker and one Uvicorn worker; do not start a second process with the same database. Do not put NASA assets, private environment files or job storage in Git. The existing kernel index and trusted DEM manifests bind source hashes; file existence alone is not scientific verification. The default terrain sources remain Site01 5 m plus Product90 80 m. Optional 20 m is not enabled.

In a second terminal, from `frontend/` (with its existing Node version and dependencies installed):

```bash
API_PROXY_TARGET=http://127.0.0.1:8010 npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open `http://127.0.0.1:5173`. This uses the Vite development proxy; the preview server does not inherit that proxy. Avoid a stale `VITE_API_BASE_URL` pointing at a different backend. Do not bind either service publicly for this demo.

Check the actual worker separately from scientific certification:

```bash
curl --fail http://127.0.0.1:8010/api/v1/health
curl --fail http://127.0.0.1:8010/api/v1/capabilities
```

`science_ready=false` is expected. Live mode additionally requires `scientific_job_runner_available`, `configured_science_files_available` and `bounded_live_prototype_supported` to be true. Source hashes/metadata are revalidated inside each scientific session. If files are absent, use Recorded Evidence; do not download large assets during the demo.

## Reuse a previous analysis

Keep the original job ID and exact mission inputs, including **which requirements were explicitly edited**. A short validated example is CR1 (-89.468°, 222.6° east), 2026-11-20 08:00 UTC, 3600 seconds, Solar-Powered Experiment, explicit `min_sun_visible_s=600`, 1 m device heights. Do not substitute a six-hour recorded scenario.

Under Scientific Backend, expand **Reuse a saved analysis checkpoint**, enter the terminal analysis job ID, and choose **Resume Saved Analysis**. This creates a real new HTTP 202 job using `resume_from`; it is not a fabricated acceptance or an imported browser fixture. The backend rejects incompatible scientific settings or a missing/nonterminal checkpoint. There is no automatic fresh-job fallback on rejection. Compatible complete checkpoints can return PRECOMPUTED without new visibility work; missing samples may still require bounded live computation. Inspect the reported origin and new/retained counters.

Only a completed matching analysis with validated `window_evidence.request` enables live optimizers. The frontend does not reconstruct astronomy or invent a window template.

## Local and temporal alternatives

Open Alternative Explorer and select **Live Optimizer**. For Local, choose the original radius (1, 3 or 5 km), search strategy and explicit detailed budget. The budget includes baseline. Start at 4; use at most 8 only if the source and wall budgets permit it.

To extend an existing local job, expand **Resume a saved optimizer checkpoint**, enter its terminal LOCAL job ID and choose **Resume Saved Optimizer**. Keep the same scientific scenario and search radius. Local detailed limits may be raised without changing the scientific request. The server validates compatibility and every source-bound checkpoint; retained costs remain separate from actual new computation. Changing coordinates, UTC, duration or requirements is a new scientific scenario, not a valid resume.

For Temporal, select the same completed analysis, a bounded search horizon and 2–4 detailed evaluations. Use **Run Live Temporal Optimizer**. Local and temporal jobs must run sequentially. Do not start the canonical 30-candidate search for a jury demo. One-hour live results must not be compared against six-hour recorded results.

Both use HTTP 202, then GET `/api/v1/jobs/{job_id}` and GET `/api/v1/jobs/{job_id}/result`. Preserve the returned job ID. Resume submits a new job ID while retaining validated evidence. A PARTIAL search can contain complete, useful candidates; it does not mean the whole search was completed or that uncomputed candidates failed. Radar markers use the supplied geodesic distance/bearing. The globe is a visual coordinate view, not terrain safety evidence. A/B comparison requires equivalent settings and source identities.

## Offline Recorded Evidence fallback

Keep the frontend running. In Alternative Explorer select **Recorded Evidence** and either Temporal or Local. These small repository evidence files are served locally and do not require the backend, NASA binaries or a new science job. They retain their recorded origin and original durations. Do not call them new live computations. Recorded mode in the Scientific Backend analysis panel is different: it calls the backend's exact-match recorded-analysis API.

When the backend stops, its in-process worker stops too. Browser polling cannot establish execution while disconnected; do not show fabricated progress, mark a job completed, or automatically submit a replacement. Use **Check optimizer capabilities** to refresh availability. Live controls are unavailable until the worker returns. SQLite results/checkpoints survive restart; an unfinished lost-worker job is interrupted, not silently completed. Explicitly reconnect/resume after restarting the same private database. Nothing computes while the server is down.

## Scientific interpretation

MET/NOT_MET/INCOMPLETE are mandatory-rule results under the selected evidence policy. The `24and28-planning-score-v1` index is not success probability and does not override a mandatory failure. Hourly/finite-disk estimates do not certify continuous physical visibility. Geometric Sun visibility is not electrical power; Earth clearance is not RF success. Absolute terrain registration remains unverified. Missing horizons, series and windows remain unknown rather than being fabricated from optimizer summary metrics.

The measured local/temporal acceptance run is recorded in `data_pipeline/evidence/nasa-live-optimizer-demo-readiness.json`. Its checkpoint replay, new work and partial search scope are reported separately.
