# Command 05 — COMPLETE_WITH_LIMITATIONS

Base main 9744559 includes merged PRs 7, 10, 12 and 14. Branch:
backend/command-05-terrain-horizon-engine. The existing observer, geometry, DEM,
fusion and evidence modules were inspected. Genuine originals were re-opened
and hashed; no downloads or source raster/kernel modifications were performed.

## Real data and geometry

Actual CR1 observer: planetocentric -89.468 degrees, east longitude 222.6 degrees;
Site01 containing-cell elevation 1942.1014404296875 m; device height 1 m.
Explicit PROTOTYPE registration, REPORT conflicts, LROC disabled. R=1737400 m.
Actual source/quality identities are in the evidence JSON full_profile.sources:
Site01 surface, TOTERR, LDEC and Product90 80MPP. Ground heights and device
height are separate. Existing real SPICE and LROC integrations also reran.

Exact spherical atan2 geometry agrees with the existing Cartesian/ENU helpers
in 20 parameterized direction/device tests, each at 5, 1000, 100000 and 150000 m.
Analytic sphere angles remain negative; at zero device/terrain height the angle
is -s/(2R) radians, unlike a flat approximation's zero. The chosen reference
normal is radial; terrain slopes do not redefine the observer's horizon plane.

## Actual CR1 horizons

Fine cardinal rays use resolution_factor=1: 5 m steps while Site01 is selected,
80 m steps while Product90 is selected, initial distance 5 m and range 150 km.
All four rays have complete scheduled samples under the selected policy.

| Azimuth | Sampled elevation (deg) | Strongest distance (m) | Source |
| --- | --- | --- | --- |
| 0 | 2.2245770555 | 105 | Site01 |
| 90 | 1.1036671257 | 145 | Site01 |
| 180 | 2.1798513147 | 140 | Site01 |
| 270 | 0.0926257339 | 85 | Site01 |

The 72-ray full profile uses 5 degree azimuth spacing and factor=8 (40/640 m
steps), not the finer cardinal settings above. Its largest sampled obstruction
is 3.5811763724 degrees at azimuth 40, distance 85 m, Site01. Next sampled
azimuths 45 and 50 yield 3.4629401302 and 3.4511476210 degrees at 85 m.
Minimum sampled full-profile angle is -0.7043048114 degrees. These discrete
maxima do not bound unsampled azimuths or subcell terrain. No missing directions
are filled by interpolation. Actual source conflicts are retained (fine cardinal
REPORT counts: 265, 207, 258, 77); a complete sampled ray is not conflict-free.

## Sensitivity and convergence

Four cardinal azimuths with factor=4 were compared at 50/100/150 km. Both range
increments gave 0 degrees change in their maxima and no change in strongest
obstacle distance. This supports stability only for those rays/settings; it
cannot rule out obstacles beyond 150 km or on other azimuths.

Factors 4/2/1 give coarse/medium/fine distance sampling (20/320, 10/160, 5/80 m).
Coarse to medium: all four maxima unchanged. Medium to fine: maximum difference
0.0363353541 degrees at 180; RMS 0.0181676771; median absolute difference 0.
Strongest distance shifts from 145 to 140 m there. General step convergence is
not established; point-sampling phase and narrower obstacles remain risks.

The actual 0–30 degree sector was sampled at 5, 2 and 1 degree spacing with the
same factor=4 distance scheme. As a diagnostic only, linearly interpolating
coarser results to the measured 1-degree directions yields:

| Coarse spacing | Max absolute difference | RMS | Median absolute | Largest difference direction |
| --- | --- | --- | --- | --- |
| 5 degrees | 0.1679416556 deg | 0.0661793440 deg | 0.0495443871 deg | 21 degrees |
| 2 degrees | 0.1123699921 deg | 0.0368391305 deg | 0 deg | 29 degrees |

The API does not perform this interpolation. These measured discrepancies are
not tolerances or bounds on true terrain. A synthetic 2 m-wide ridge between
coarse sample positions is missed by 10 m stepping and found at 45 m using
5 m stepping. This intentionally demonstrates the absence of complete-cell
coverage. Synthetic range tests place a distant obstacle near 120 km to ensure
that extending the range can change the maximum.

## Previously identified source boundary

An observer at projected Site01 (-11000,-4200) m looks toward (-11000,-3500)
along azimuth 110.897728960 degrees, with 5 m ray spacing to 600 m. This crosses
the northern boundary near the earlier 18.642700 m difference location.
All source-comparison runs keep the exact same actual Site01 observer elevation.

| Ray sources | Result | Angle | Strongest distance |
| --- | --- | --- | --- |
| Site01 then Product90 | COMPLETE_SAMPLED_RANGE | -13.4325811285 deg | 275 m |
| Site01 only | INCOMPLETE | partial -13.6162980376 deg | 195 m |
| Product90 only | COMPLETE_SAMPLED_RANGE | -0.4309334633 deg | 35 m |

Adding far terrain raises the known Site01-only maximum by 0.1837169090 degrees.
Using Product90 alone changes the complete maximum by 13.0016476653 degrees;
that comparison also changes nearby cells, so it cannot isolate a pure seam
error. The 80 m terrain and a fixed 5 m-source observer can disagree strongly
near the observer; this source sensitivity is not dismissed as negligible.

Actual geodesic samples in this run: at 195 m, Site01 height 652.1597290039 m
and angle -13.6162980376 degrees; at 200 m, Product90 height 633.7189941406 m
and angle -18.1774040368 degrees; at 205 m, the same Product90 cell gives
-17.7623782627 degrees. This ray's 195–205 m height difference is -18.4407348633 m.
It uses different sample coordinates from the earlier projected point pair,
so it is not relabeled as an exact reproduction of the earlier 18.642700 m.
No blending or offsets are applied. Elevation, angle and maximum-obstacle
changes are distinct quantities, all recorded in evidence.

## Performance and bounded I/O

Measurements in this Codex environment, including Python/GDAL overhead (initial
source-session construction excluded). Peak RSS is the process high-water mark,
not incremental per-run memory and not an 8 GB hardware test. The maximum across
this validation process was 126172 KiB (~123.2 MiB). No complete DEM band loaded.

| Run | Rays | Terrain samples | Seconds |
| --- | --- | --- | --- |
| Full 360, 5-degree azimuth, factor 8, 150 km | 72 | 32147 | 16.7724 |
| Four cardinals, factor 4, 100 km | 4 | 3294 | 2.2521 |
| Four cardinals, factor 4, 150 km | 4 | 3920 | 2.2984 |
| 30-degree sector, 1-degree azimuth, factor 4 | 31 | 28740 | 15.4836 |
| Single ray, factor 4, 150 km | 1 | 988 | 0.5739 |
| Same single ray repeated | 1 | 988 | 0.5820 |

Repeated requests produce identical identities/results; no result cache is
claimed. A measured bottleneck was repeated quality-file opens/CRS checks:
7 near-terrain queries took 0.791 s in a profiling run. Quality datasets now
reuse metadata-checked open handles (maximum eight, closed at DEM-session exit).
Every window retains memory/decode and mask checks. Shared low-level window
logic was extracted to avoid duplicating validity rules. Tests cover metadata
changes, mask behavior, handle closure and existing rejection cases. No file
hash is recomputed per terrain point. External quality-mask hashes are included
in result identity, with a test that changing an unrelated mask cell changes
the key while preserving observer/ray numerical results.

The first slow full-profile diagnostic was interrupted to address the measured
I/O cost; it is not counted as a completed run. All reported measurements above
come from the subsequent complete diagnostic. Configuration/request/hash details
for every run are retained in the JSON. No machine-independent speed guarantee.

## Tests and reproduction

Final full suite: **263 passed, 0 failed, 1 skipped** (36.44 s).
New: 44 synthetic/analytic horizon cases, four real horizon cases and one quality
session regression. Genuine NASA total: 15 (2 SPICE, 2 LROC, 3 LOLA, 4 fusion,
4 horizon); 248 remaining unit/API/math/synthetic tests. The absent Product90
20MPP remains skipped and is never substituted with 80MPP. Existing Starlette
warning only. `pip check` and `git diff --check` passed.

Set the actual external paths with NASA_KERNEL_DIR, NASA_KERNEL_INDEX,
NASA_SITE01_DEM, NASA_LOLA_VALIDATION_DIR, NASA_LROC_CR1_DEM, NASA_LROC_CR1_LABEL.
Do not set NASA_PRODUCT90_DEM to an 80MPP file. From the repository root:

```sh
PYTHONPATH=backend:. python -m pytest -q backend/tests -ra
PYTHONPATH=backend:. python -m data_pipeline.horizon_validation evidence.json
PYTHONPATH=backend:. python -m data_pipeline.horizon_cli --request request.json --output result.json
python -m pip check
```

The real CLI was exercised and its JSON validated; it refuses an existing output.
The evidence file contains a REAL_NASA_PROTOTYPE full profile and measured
sensitivity runs. Synthetic tests are explicitly labeled and never used as
NASA fallback. NASA originals remain outside Git; hashes are local identity
checks, not independent publisher authentication.

## Decisions and remaining limits

HORIZON_ENGINE_IMPLEMENTED; HORIZON_VALIDATED_WITH_SYNTHETIC_TESTS;
HORIZON_REAL_DEM_INTEGRATION_PASSED.
COMMAND_05_COMPLETE_WITH_LIMITATIONS.

CR1 prototype ray samples are available; absolute product registration remains
unverified, including LROC. README 0.5 m control-fit RMS is not an absolute
error bound. Point/cell/azimuth gaps, source seams, finer sampling, unsampled
near-observer terrain and beyond-range obstacles remain limitations. Local
TOTERR is statistical source uncertainty, not a certified horizon angle error.

Command 06 can query exact sampled azimuths and inspect complete/partial/unknown
ray evidence. An unsampled azimuth returns None and requires a new ray or a
separately justified future interpolation rule. No Sun/Earth disk visibility,
windows, optimization or operation score is implemented. Shared contracts and
frontend are unchanged; SCIENCE_ENGINE_NOT_READY and science_ready=false remain.
