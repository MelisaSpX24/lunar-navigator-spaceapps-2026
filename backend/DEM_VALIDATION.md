# Command 03.5 closure and Command 04 validation

Later LOLA addendum: see `../data_pipeline/LOLA_VALIDATION.md`. Real Site01 and
Product90 80MPP files are now validated; its 199 passed / 1 skipped result
supersedes the absent-LOLA state of this historical Command 04 run.

Date: 2026-11-14 UTC. Base: main `ba9c97f` (includes frontend PRs #5–6 as well as
backend PRs #1–4). Work branch: `backend/command-04-dem-foundation`.
Only backend/ and data_pipeline/ are changed. No NASA source binary or label is
committed. No merge or auto-merge is performed.

## Command 03.5 gate

**PROTOTYPE_DATA_GATE_PASSED_WITH_LIMITATIONS**, separate from API readiness.
Persistent evidence: `../data_pipeline/evidence/command-03-5.json`. This records
the prior 99 passed / 0 failed / 2 skipped run, five kernel filename/hash
identities, the real LROC pair's hashes/sizes, CR1 cell height, approximate disk
coverage, explicitly unknown errors, and open scientific work. It contains no
local/private file paths. Hashes are local integrity evidence, not independent
NASA authentication. The originals were supplied as user attachments.

Real astronomy had used an explicitly assumed 0 m surface and 1 m device;
those saved directions are not relabelled as terrain-corrected. The LROC height
is a separate observation until the documented registration assumptions are
applied in a future combined workflow. General LROC DE421 mapping support:
https://doi.org/10.3847/psj/ad54c6 (not product-specific registration evidence).

## Final checks

Existing Python 3.12 environment and dependencies reused; no package change.
Executed from backend/ with genuine local data paths supplied through:

```sh
export NASA_KERNEL_DIR=/data/lunar/kernels
export NASA_KERNEL_INDEX=/data/lunar/results/kernel-index.json
export NASA_LROC_CR1_DEM=/data/lunar/originals/NAC_DTM_ESALL_CR1.TIF
export NASA_LROC_CR1_LABEL=/data/lunar/originals/NAC_DTM_ESALL_CR1.LBL
python -m pytest -q -ra
python -m pip check
```

The example paths above are placeholders; the actual run used existing external
temporary/attachment paths after checking their presence. Those originals must
be provided again on a clean machine; tests never download missing data.

The initial foundation run passed 139 tests. The expanded formal Command 04
scope adds the coordinate, distance, quality and observer-input interfaces below.
Final full-suite results are recorded after executing that complete scope.

Evidence classes:

| Class | Result | Meaning |
| --- | --- | --- |
| Real NASA SPICE integration | 2 passed | Genuine kernels; geometry, parallax, date coverage and same-toolkit AZLCPO consistency |
| Real LROC integration | 2 passed | Pinned genuine TIFF/LBL hashes, label, CR1 cell and all three disk-coverage checks |
| Other unit/API/math/synthetic/mock tests | See final run below | Software and mathematical invariants, not independent NASA validation |
| Real LOLA integration | 2 skipped | Site01 and Product90 rasters remain unavailable |
| Horizons comparison | NOT_VERIFIED | Not replaced with AZLCPO consistency tests |

New generated fixtures test: containing-cell coordinate/index behavior, analytic
spherical polar-stereographic metre coordinates, negative/zero valid heights,
NoData/NaN/infinity/label missing sentinel masks, outside and edge cells, changed
file hashes, unsupported units/scales/dtypes/grids/radii, memory/decode/work
limits, complete versus partial disks, dense cell-by-cell geodesic count oracle,
bounded window reads, all-invalid/all-exterior coverage, narrow PDS evidence
parsing and mismatches, CLI explicit registration opt-in/no overwrite, and
incomplete future-ray evidence without an unobstructed-visibility claim.
Synthetic PDS fixtures identify themselves as test data; parser tests are not
real-source authentication. Numerical error fields remain null without evidence.

Additional formal Command 04 tests in `test_dem_coordinates.py` and
`test_dem_quality.py` cover:

- Forward/inverse projection round trips (latitude/longitude absolute tolerance
  1e-9 degree at the tested sites), containing-cell index and centre versus corner.
- Input [0,360) longitude enforcement and inverse normalization across zero,
  near-pole behavior and explicit exact-pole rejection.
- Spherical zero/symmetric/equatorial/near-pole/short/antipodal distances, explicit
  radius units, and a demonstrated difference from polar-projection flat distance.
- Associated quality sources, identities/units, separate missing/nonfinite/range
  masks, wrong source/family/frame/unit/hash and mismatched CRS/grid rejection.
- Internal/external elevation masks, external quality masks and bounded windows.
  Large quality source hashes are checked once per immutable DEM session.
- Required unit/radius/datum evidence, non-promotable frame metadata and safe
  LOLA declarations. Page-only LOLA manifests remain unready and LROC stays separate.
- Observer surface/device heights, metre-to-kilometre radial position and retained
  provisional registration evidence; no new SPICE geometry or visibility decision.

The genuine LROC point test additionally checks inverse pixel-centre mapping,
a real NoData cell, an exterior coordinate and an observer-preparation envelope.
Those tests use genuine data but do not verify geodetic registration or accuracy.

## Measured 1 km resource check

`../data_pipeline/evidence/command-04-performance.json` records an actual local
CR1 1 km coverage run through this code: **0.684959 s** coverage time and
**122004 KiB (~119.1 MiB) Linux process peak RSS**, including imports/GDAL memory.
Timing excludes initial label inspection and file hashing. This is one
environment-dependent measurement, not an 8 GB machine test or an absolute
time/memory guarantee. No full DEM array was required. The configured chunk,
pixel, block and GDAL cache guards remain documented in `DEM.md`.

## Final formal Command 04 run

Final suite: **194 passed, 0 failed, 2 skipped**, 25.31 s. This comprises 2 genuine kernel
tests, 2 genuine LROC tests and 190 other unit/API/math/synthetic/mock tests.
Both genuine LOLA integrations remain skipped. The only suite warning is the
existing Starlette/httpx TestClient deprecation. `python -m pip check` reports no
broken requirements; source/diff scope checks are performed before commit.

## Real LROC result through the new code

The real integration tests first require the exact genuine TIFF and LBL hashes
recorded in the closure evidence. Supplied wrong files fail instead of skipping.
The real CLI sample also completed and emitted valid JSON outside the repo.

- Product: NAC_DTM_ESALL_CR1 v1.2, LROC stereo DTM, float32, 2 m/pixel.
- PDS label: metre heights above the declared 1737400 m sphere.
- CR1: -89.468 degrees, 222.6 degrees east; zero-based row 1167, column 1230.
- Stored cell elevation: **1944.1400146484375 m**; display **1944.14 m**.
- `prototype_registration_assumption_used=true`;
  `product_specific_frame_verified=false`; `science_ready=false`.
- All three absolute/relative error fields remain null.

| Radius | Bounds fraction | Valid height fraction | Status |
| --- | --- | --- | --- |
| 1000 m | 1.0000000000 | 0.9871142618 | BOUNDS_COMPLETE_DATA_PARTIAL |
| 3000 m | 0.8377058021 | 0.8030026618 | PARTIAL_RASTER_COVERAGE |
| 5000 m | 0.3182951683 | 0.2984876854 | COVERAGE_INSUFFICIENT_FOR_FULL_5KM |

These are approximate geodesic pixel-centre area fractions on the supplied CRS
sphere. They match the prior temporary streamed analysis; that agreement is a
regression consistency check, not an independent accuracy/registration test.
No interpolation or sphere-filled unknown terrain is used. At 1 km, 100% bounds
coverage still leaves about 1.29% missing heights. At 5 km, about 68.17% of the
disk is outside the raster. No full-region optimization is claimed or run.

## Remaining scientific limitations

- Product-specific horizontal frame/registration evidence and quantified errors.
- Product-specific horizontal/vertical accuracy and confidence products.
- Convention-matched Horizons comparison; true external observational validation
  is also distinct from comparing two JPL model implementations.
- Real LOLA integration, wider terrain coverage, and near/far registration.
- Topographic horizon, disk fractions, operation windows and end-to-end visibility
  verification are future work. RayCoverageEvidence is only a data envelope.

The CR1 cell is not centimetre-accurate certified lander terrain. Pixel spacing
is not positional accuracy. This prototype does not certify safe landing.
`SCIENCE_ENGINE_NOT_READY`, false readiness and null operation score remain.
Command 04's defined foundation is implemented; Command 05 has not started.
Its future input boundary and the unavailable Product90 80 m candidate are
documented in `DEM_HANDOFF.md`. No distant terrain, horizon or optimizer is
silently supplied by that handoff.
