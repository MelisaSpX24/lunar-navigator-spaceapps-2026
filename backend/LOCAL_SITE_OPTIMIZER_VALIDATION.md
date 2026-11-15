# Command 10 — real spatial validation

Live HTTP request: CR1 (-89.468,222.6 east), 2026-11-20T08:00:00Z, 3600 seconds, Solar profile, min_sun_visible_s=600, 1 m devices, 64 disk samples, hourly grid, NONE, PROTOTYPE/REPORT terrain and PROTOTYPE_SAMPLED_ESTIMATE operation policy. Example thresholds are EXAMPLE_OPERATION_ASSUMPTION, not NASA requirements.

The 5000 m search generated/screened 16 points including baseline. All 16 had known gradient estimates; eight passed the 10-degree screen. Baseline and one selected candidate received complete two-epoch exact scientific windows, for four live visibility calls, 520 rays and 239613 DEM positions. Job state is PARTIAL because the finite candidate pool was not fully verified.

Baseline slope estimate 0.9804523409811545°, NOT_MET/0. Candidate (-89.43734917039663,222.8374650555442 east), distance 931.9756666408481 m, bearing 4.351316121645229°, slope estimate 1.207912395153901°, MET/100. Source identities match. This real result concerns the requested one-hour operation, not the canonical six-hour temporal mission. No arbitrary elevation/registration offset or 20 m substitution occurred.

The remaining terrain-passing candidates were not scientifically declared suitable. One recommendation is not the global best lunar landing location. Absolute registration, physical continuous illumination, hazard resolution, power and RF success remain unverified. Raw source-backed HTTP evidence is preserved in command-10-validation.json with identifiers redacted for publication.

## Command 10 source-resolution closure diagnostic

The original 16 pilot points were rechecked independently against 5, 20 and 80 m readers, including containing-cell height and bounded 3×3 slope. All 16 were valid and had known slope at each resolution; eight passed the example 10° criterion at each resolution. CR1 slopes were 0.980452° (5 m), 1.107557° (20 m) and 1.055254° (80 m). Heights were 1942.101440, 1942.385254 and 1942.843384 m respectively. Different cells/support lengths produce differences; these are not absolute registration error estimates or evidence that one resolution is necessarily safer.

A streamed 5 km pixel-center coverage calculation found complete sampled disks at all three resolutions: 3,141,778 valid centers at 5 m; 196,369 at 20 m; 12,280 at 80 m. This is a coverage diagnostic, not hazard certification. Metadata, CRS, user-manifest hash and sampled values are in command-10-source-comparison.json. Default Site01 + 80 m remains unchanged.

## Final closure — diverse detailed verification

The same 5 km, one-hour CR1 request was resumed with TERRAIN_DIVERSE admission and four detailed slots including baseline. Sixteen points were screened, sixteen slopes were known and eight passed the example 10° gate. The baseline and three alternatives were actually evaluated. Four retained UTC samples were reused; four new visibility evaluations computed 520 exact rays and 179667 new terrain positions including screening. Measured local processing was 76.739309 s; it is not directly comparable to the initial cold two-entry 125.986 s workload.

| Location (latitude, east longitude) | Distance m / bearing deg | Source-grid slope deg | Prototype decision / score |
|---|---|---:|---|
| −89.468, 222.6 | baseline | 0.980452 | NOT_MET / 0 |
| −89.43734917039663, 222.8374650555442 | 931.976 / 4.351 | 1.207912 | MET / 100 |
| −89.4993463818188, 236.8622046686259 | 4000 / 110.769 | 7.125934 | MET / 100 |
| −89.5387609790589, 239.8923169436484 | 5000 / 123.750 | 4.514302 | MET / 100 |

These are three actual evaluated recommendations, not padded entries. The original nearby recommendation remains preferred at equal score by distance. The local search remains partial over a finite candidate pool: four detailed entries do not exhaust eight terrain-eligible points or establish the optimum of the full disk. No six-hour result is inferred from this one-hour experiment.
