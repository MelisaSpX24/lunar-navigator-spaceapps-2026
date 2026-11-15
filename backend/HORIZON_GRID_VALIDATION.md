# Command 10 — guarded horizon screening grid

The new HorizonGrid/build_grid module binds coordinate, actual observer surface elevation, device height, source namespace/hashes, frame, policy, range, sampling, spacing and algorithm. It distinguishes EXACT_GRID, APPROXIMATE_INTERPOLATION and UNKNOWN. The builder consumes the unchanged exact ray engine; unknown/uncomputed directions remain null. 359–0 wrapping and missing-neighbour behaviour are tested.

Actual CR1, 1 m, 150 km, 5 m + 80 m prototype terrain: the 1° grid computed 360 known scheduled rays in 82.589282 s (160762 DEM positions). The 0.5° grid computed 720 known directions in 84.656825 s, reusing the existing 360 and calculating 360 new directions (160758 new positions). This is complete scheduled-grid coverage, not evidence for every intervening azimuth. Ten thousand lookups took 0.010822/0.011071 s respectively.

Six diagnostic comparisons at 0°,90°,180°,270°,359.75°,17.26° had zero angular difference in this terrain case. That selected-point result does not establish arbitrary interpolation equivalence: narrow ridges can be missed. No interpolated result is accepted as strict visibility evidence. Exact disk verification at the original UTC returned Sun NONE and Earth FULL through the unchanged engine. Across the grid experiment, including probes and exact verification, 852 new rays and 381130 terrain positions were used, with 370 cache hits.

Grid-only geometry discovery generated 27 regular-grid alternatives without the recorded event hint; zero operation candidates were thereby completed. The canonical hinted API batch has 30 alternatives and is a different workload. Full same-candidate A/B optimizer speedup is NOT_MEASURED; grid construction costs must be included before claiming amortized benefit. API defaults retain exact verification and do not silently replace it with interpolation. The grid utility is available for explicitly validated future coarse-priority integrations, not a new source of MET decisions.

## Command 10 workflow integration

Temporal jobs now support explicit HORIZON_GRID coarse prioritization, with source/kernel/request/height-bound persistent grid checkpoints. Unknown lookup directions carry no favorable priority evidence. Grid preparation, new rays and DEM positions are included in accounting; candidate windows still use exact VisibilityEngine results. Grid reuse is charged once per execution, and altered height/source signatures cannot collide. Default EXACT_ONLY is retained pending workload-specific total-cost evidence. Local searches do not borrow another coordinate's grid; terrain/source/diversity screening precedes candidate-specific exact verification.

## Actual optimizer A/B closure result

A controlled one-hour operation searched two start times at CR1, 08:00 and 09:00 on November 20, with the same DEM/SPICE, 64 disk points, hourly windows, 0.5 solar fraction and min_sun_visible_s=600. Both arms used new scientific sessions/caches, with shared OS file cache. The API ran the real optimizer paths sequentially on one worker. Each arm generated one alternative and evaluated baseline plus that alternative with three new exact visibility evaluations and one shared-boundary checkpoint lookup.

| Metric | Exact-only | Grid-assisted + exact final |
|---|---:|---:|
| Pipeline wall seconds | 96.210628 | 181.082771 |
| Grid preparation seconds | 0 | 86.199112 |
| Grid priority seconds | 0 | 0.000882 |
| New exact rays | 390 | 750 |
| Terrain positions | 176249 | 337011 |
| New visibility evaluations | 3 | 3 |
| Exact-ray cache hits | 0 | 0 |

Candidate identities and detailed scientific metrics/decisions matched exactly. Both sampled Solar operations were NOT_MET/0, with no invented recommendations. Grid lookup was cheap, but preparation dominated: measured A/B ratio was 0.531307, so this case showed no total speedup. EXACT_ONLY remains default. The grid is an explicit optional coarse prioritization tool; its 360 scheduled directions and interpolation do not certify continuous azimuth visibility. This one-hour A/B is not a benchmark of the canonical six-hour/seven-day workload.
