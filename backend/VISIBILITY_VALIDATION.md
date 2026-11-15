# Command 06 validation

Base main 1429577 includes merged PRs 7,10,12,14,15. No shared API, frontend,
manifest defaults or existing scientific engines were changed. New code is local
to backend and data_pipeline. Readiness remains false. Independent astronomical
validation is NOT_ESTABLISHED; no Horizons equivalent-observer comparison is claimed.

## Actual inputs and pilot

The evidence JSON records original raster/kernel hashes, CRS, dimensions, masks,
request settings, PCK constants, source references, ray identities and timings.
The reassembled 20 m file again matched 2696082051 bytes and user manifest SHA256
09b7ca80f9e6a146f970225d18af72fc02787669b3ef51b888e347d2b6845649.
This is not an independently published NASA checksum. Real NASA originals were
read-only, outside Git. No synthetic source replaced a missing original.

CR1: latitude -89.468, east longitude 222.6, surface 1942.1014404296875 m from
Site01, solar/Earth devices 1 m, 2026-11-20T08:00:00Z, NONE correction.
PROTOTYPE registration, REPORT conflicts, LROC disabled. R=1737400 m.
150 km rays; start 5 m, resolution_factor=8, max_step=640 m. 64 projected-area
disk points per body plus its central ray. Total 130 genuine terrain rays.

| Body | Azimuth deg | Elevation deg | Distance km | Disk radius deg | Center clearance deg | Finite model |
|---|---:|---:|---:|---:|---:|---|
| Sun |186.9517316479|1.0153993811|148032670.54792145|0.2692704279|-0.6893740754|NONE, fraction 0, bounds [0,0]|
| Earth |130.1909102996|3.2466132317|381773.5497517663|0.9561920562|2.8209336431|FULL, fraction 1, bounds [1,1]|

Unknown disk weight is zero for this finite model. This does not bound unsampled
terrain or physical visibility. PCK Sun axes: [695700,695700,695700] km; Earth:
[6378.1366,6378.1366,6356.7519] km. Mean axes define the spherical effective radius.
Earth is not modeled as an ellipsoid. Both silhouettes use actual SPICE distance.

## 20 m comparison

Separate SITE01+PRODUCT90 sessions retain exactly the same Site01 observer.
Measured directions: 0,90,180,270,186.9517316479,130.1909102996 degrees.
Both adaptive runs and the common 100 m distance-grid diagnostic gave zero
signed, maximum absolute, median and RMS horizon differences on these six rays.
The strongest obstructions were in shared Site01 near terrain. A separate
northward 600 m seam diagnostic from projected (-11000,-4200), on a common 5 m
grid, likewise gave zero maximum-angle difference. This does NOT show identical
far terrain or equivalent source accuracy. Source counts, seam transitions,
conflicts and strongest-obstacle distances remain in each run's ray summary.
Common 100 m steps are deliberately diagnostic and coarser than Site01 cells.

Actual 64-point disk comparisons also gave zero fraction/center-clearance delta;
Sun NONE and Earth FULL remained unchanged, with zero unknown weight. Therefore
no automatic 80-to-20 m source replacement is justified by this experiment.
Different sites, times and dominant distant obstructions need separate studies.

## Measured performance

These are local measurements, not hardware-independent guarantees. Setup includes
source hashing; runs exclude setup. DEM samples are terrain query positions on
completed rays, not every underlying raster/quality read. Peak RSS is process-wide.

| Run | Seconds | New rays | Terrain samples |
|---|---:|---:|---:|
| Baseline80 setup |0.898|—|—|
| Baseline80 Sun |17.926|65|31234|
| Baseline80 Earth (centre geometry reused) |14.723|65|27427|
| Baseline80 combined |32.737|130|58661|
| Baseline80 repeated request |0.00401|0|0|
| Experiment20 setup |8.843|—|—|
| Experiment20 Sun |30.451|65|73744|
| Experiment20 Earth |27.494|65|70717|
| Experiment20 combined |58.038|130|144461|
| Experiment20 repeated |0.00720|0|0|

Repeated requests reused 130 exact rays. Baseline centre SPICE call: 0.001431 s.
Peak pilot RSS: 143036 KiB (80 m), 153032 KiB (20 m), about 139.7/149.4 MiB.
Three UTC samples separated by one hour took 4.363 s with a deliberate eight-new-
ray budget per UTC: 130 cache hits, 16 new rays and four UNKNOWN body results.
First UTC reused the pilot; later UTCs exhausted their budgets. They are not
claimed as full time-series visibility coverage or event times.

101 planar segment offsets, measured max fraction error at N=64/256/1024:
0.0335658 / 0.0126861 / 0.00437491. RMS:
0.0128141 / 0.00503244 / 0.00171631. Half-disk tests return exactly 0.5.
Full NASA 256/1024 disk ray sets were deliberately NOT computed. With zero new
ray budget they retain two centre cache hits and unknown_fraction=1 for both
bodies; math/cache evaluation cost was 0.00858/0.02631 s. These are budget safety
benchmarks, not NASA visibility convergence claims.

## Reproduction and limits

Follow VISIBILITY.md CLI examples and set the actual external file paths.
Full tests use PYTHONPATH=backend:. and NASA_KERNEL_DIR, NASA_KERNEL_INDEX,
NASA_LOLA_VALIDATION_DIR, NASA_SITE01_DEM, NASA_PRODUCT90_DEM (actual 20 m),
NASA_LROC_CR1_DEM, NASA_LROC_CR1_LABEL. Baseline before development: 264 passed,
zero failed/skipped, 37.17 s. Final totals are recorded below and in evidence.
No existing test was removed or relaxed. Analytic half-disk failure exposed
boundary-phase bias and was fixed in quadrature, not by loosening the assertion.

Absolute reference registration, datum evidence strength, real error layers,
point-sampling omissions, unresolved narrow ridges, unsampled near distance,
terrain beyond range, Earth flattening, finite disk quadrature and independent
astronomy validation remain limitations. COMPLETE refers to software and the
finite sampled model, never certification for a landing, RF link or solar power.

A nonzero source difference is visible even though maximum horizons match:
on the six common-100 m rays, the baseline reports 57 sampled overlap conflicts
above the configured 10 m threshold, whereas the 20 m experiment reports zero.
The boundary diagnostic reports 20 versus zero. This is an engineering threshold
and containing-cell comparison, not measured absolute registration accuracy.
Adaptive cardinal/centre runs cost 1.548 s / 2867 points (80 m) versus 3.017 s /
6795 points (20 m). Common-lattice runs both read 9006 terrain positions, taking
2.164 versus 2.709 s. Resolution and sampling effects are reported separately.

Final full suite: **340 PASSED / 0 FAILED / 0 SKIPPED**, 83.56 s.
Added 76 cases: 71 analytic/synthetic/unit/CLI, three real NASA scientific
integrations, two unavailable/hash-mismatch guards that open the real baseline.
The old Product90 test passed with the actual 20 m file. pip check and
git diff --check passed; existing Starlette deprecation warning remains.
COMMAND_06_COMPLETE_WITH_LIMITATIONS.

## Command 06.1 — Resource-budget completeness validation

The original command-06-visibility.json and its 20 m/80 m comparison remain
unchanged. The eight-ray series and zero-new-ray high-N diagnostics are explicitly
INTENTIONALLY_RESOURCE_LIMITED_DIAGNOSTIC, not evidence of absent terrain.
New results are in command-06-1-budget-refinement.json. No source-selection,
STRICT-default, API or scientific readiness policy changed.

Baseline before refinement: 340 passed, zero failed/skipped (86.47 s).
Accounting now distinguishes a rejected lookup, an attempted ray and a completed
ray. Runtime horizon budget exceptions carry the actual consumed point count;
failed rays are not cached. Tests exercise inflight exhaustion, nonnegative
remaining budget, immediate rejection, exact-direction separation, changed
configuration/data identity, LRU eviction and preflight estimates. A preflight
regression initially mapped invalid PCK radii to the geometry error; the existing
radius-error test caught this and the original DISK_RADIUS_UNAVAILABLE code was
restored rather than weakening its assertion.

Actual-data scenario: Site01 5 m + Product90 80 m, actual DE421 SPICE, NONE,
PROTOTYPE/REPORT, LROC off, surface 1942.1014404296875 m and two 1 m devices.
All configurations retain 150 km range and factor-8 / max-640 m distance sampling.
The real series uses 08:00,09:00,10:00 UTC on 2026-11-20. Higher-N computations
use the initial UTC and identical conventions. No new 20 m comparison is needed;
the real 20 m regression remains enabled in the full suite.

The sufficient series follows the low-budget experiment in the same cache:
08:00 reuses 130 rays; 09:00 and 10:00 each reuse eight and compute 122.
Each timestamp requires 130 directions in total. Warm sufficient-series time
therefore is not the cost of starting three UTCs from an empty cache. At all
three times the finite model gives Sun NONE / fraction 0 and Earth FULL /
fraction 1, with zero unknown disk weight. This does not remove registration,
finite-terrain-sampling, beyond-range or independent-astronomy limitations.

Fresh-run artifact regression assertions are explicitly distinguished from
live SPICE/terrain tests: they hash the actual baseline rasters and validate the
newly generated run record. The validation CLI itself performed every recorded
ray; no committed historical fixture substitutes for a missing current run.

Measured Command 06.1 results (same process; source setup excluded):

| Scenario | Seconds | Completed new rays | Cache hits | Terrain points |
|---|---:|---:|---:|---:|
| first64 | 31.1079 | 130 | 0 | 58661 |
| repeat64 | 0.0071 | 0 | 130 | 0 |
| low_series | 4.2807 | 16 | 130 | 7723 |
| complete_series | 60.0414 | 244 | 146 | 109865 |
| real256 | 128.5375 | 512 | 2 | 231031 |
| real1024 | 504.8929 | 2048 | 2 | 924125 |

The complete series has zero UNKNOWN bodies; the intentionally limited series has four.
64/256/1024 at 08:00 all return Sun NONE (0), Earth FULL (1), zero unknown weight and identical centre clearances. This saturated pilot does not demonstrate convergence at a grazing partial-disk event.
1024 admission estimate: 2048 new rays, 924734 points, 514.15 s. Measured: 924125 points, 504.89 s, peak RSS 185292 KiB (180.95 MiB). No budget or cache limits were removed.
Aggregate main experiment: 2950 completed rays, 410 cache hits, 1331405 terrain points, zero failed ray attempts. The 244 budget rejections belong to the low-budget diagnostic.
Capacity-4096 cache had zero evictions. A separate actual four-ray sequence [0,90,180,0] at capacity two forced two evictions and recomputation; it is recorded separately, not included in main aggregate.
All new accounting tests and finite JSON CLI checks passed. Source-file integrity remains caller-manifest based; no independent astronomical or absolute registration validation was added.

Final Command 06.1 full suite: **356 passed, 0 failed, 0 skipped**, 84.13 s.
Added 16 cases: 11 synthetic budget/cache guards and five fresh real-experiment
artifact assertions (actual baseline raster hashes checked); live NASA tests
also reran in the full suite. Existing 340 cases preserved, including real 20 m.
pip check, diff check, finite CLI JSON and output overwrite protection passed.
Existing Starlette deprecation warning only. COMMAND_06_1_COMPLETE_WITH_LIMITATIONS.
