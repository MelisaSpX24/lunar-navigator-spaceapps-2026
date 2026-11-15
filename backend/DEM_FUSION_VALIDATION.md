# Command 04.5 — COMPLETE_WITH_REGISTRATION_LIMITATIONS

Base main 3399088 includes merged PR #7 and PR #10. Branch:
backend/command-04-5-dem-registration-fusion. No horizon or visibility engine.

## Interface and policies

`app.data.fusion.MultiResolutionDem` borrows immutable `open_dem` sessions.
`TerrainRequest` supplies coordinates, preferred resolution, purpose and policy.
Each source uses its own actual CRS/affine and containing cell, with its own
masks and quality layers. A selected `DemSample` retains identity, resolution,
row/column, hash, physical unit/datum, frame evidence, quality and limitations.
`attempts` retains every eligible source outcome, including read failures.
No source heights are averaged, shifted or smoothed.

Registration defaults to STRICT: only product-verified sources are accepted.
These real products therefore give UNKNOWN under strict policy. Explicit
PROTOTYPE policy permits the recorded registration assumptions. Source order is
Site01 then Product90. LROC is excluded unless enable_lroc=true; with preferred
resolution below 5 m it precedes the LOLA sources, otherwise it is last.
Preferred resolution is a preference, not a mandatory minimum or accuracy claim.
Purpose labels the query (including FAR_TERRAIN); it does not silently change
policy. Selection depends on actual coverage/validity, never a distance cutoff.
All valid eligible sources are compared, including when the first succeeds.

An overlap spread over policy.conflict_threshold_m adds a warning; REJECT policy
returns UNRESOLVED_SOURCE_CONFLICT and null height. Default 10 m threshold is
an engineering diagnostic policy, not a NASA error bound. REPORT preserves the
preferred height and the disagreement. Missing/invalid sources can fall back;
no valid acceptable source produces UNKNOWN. A read error remains in attempts.
Source role/family mismatch is rejected. Wrong pinned source hashes fail at open.

`sample_batch` is bounded (default 1024, maximum 4096). `iter_samples` is the
streaming far-terrain interface, with one result retained by the engine at a time.
Callers must manage their retained results and session lifetime. Existing window,
decode, 16 MiB GDAL cache and production dem.coverage 5 km limits are preserved.
No unbounded application cache or full DEM array is introduced.

## Actual sources and documentation

Genuine files: NAC_DTM_ESALL_CR1.TIF and .LBL; Site01 surface, TOTERR and LDEC;
LDEM_80S_80MPP_ADJ.TIF. Hashes are retained in the evidence JSON, including the
quality hashes in the CR1 result. File identity matches prior validation records.
User-uploaded hashes establish identity, not independent publisher authenticity.

The supplied PDS label specifies planetocentric latitude, east longitude, south
polar stereographic projection, 1737.4 km axes, 2 m cells and metre heights above
the map-axis sphere. PRODUCT_VERSION_ID is v1.2; SOFTWARE_NAME names DLR's
photogrammetry software; DESCRIPTION references OBERSTETAL2010. The label does
not give product-specific DE421 registration residuals or absolute error bounds.

Reviewed official product page:
https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_DTM_ESALL_CR1
It identifies DLR stereo production and links confidence/slope products and a
README. Confidence/slope products were not downloaded or fabricated. Earlier
remote README access returned 403; the subsequent user-uploaded README is now
inspected in the addendum below. General standard:
https://doi.org/10.3847/psj/ad54c6 supports family-level interpretation only;
its typical accuracies are not assigned to this DLR CR1 product.
LOLA documentation and unresolved release/datum evidence remain as recorded in
../data_pipeline/LOLA_VALIDATION.md. No invented offsets between nominal spheres.

Evidence classes: CRS_MATHEMATICALLY_COMPATIBLE is established by actual data
and transforms. Source frame is supported at family/standard level, not a new
product-specific absolute verification. RELATIVE_COREGISTRATION_ASSESSED is a
bounded diagnostic below. PRODUCT_SPECIFIC_ABSOLUTE_REGISTRATION_VERIFIED is
not established: independent CR1 check-point/absolute-error evidence is absent.
The README adds LOLA control-fit evidence, not independent absolute validation.
All product_specific_frame_verified flags remain false and error bounds null.

## Relative LROC–Site01 diagnostic

Reproducible code: `python -m data_pipeline.fusion_validation OUTPUT.json`.
Set NASA_LOLA_VALIDATION_DIR, NASA_LROC_CR1_DEM and NASA_LROC_CR1_LABEL, plus
PYTHONPATH=backend:. Output must not exist; no source file is modified.

A 16x16 systematic LROC cell-centre grid (rows/columns 100:2400:150) attempts
256 pairs; 244 are valid, 12 are omitted as invalid (not zero-filled).
Difference sign is LOLA minus LROC. Mean -0.612771 m, median -0.664063 m,
RMSE 1.678667 m; extrema -5.548462 to +7.671021 m. The previous 375-point
RMSE 1.503673 m uses a different sample set and is not substituted for this run.
CR1 retains -2.038574 m. Different containing cells at 2/5 m resolution sample
different physical locations; relief and cell offsets contribute to differences.

A central-difference Site01 slope diagnostic uses 20 m projected baselines;
it is approximate grid slope, not a validated slope product. Below 10 degrees,
91 pairs have RMSE 1.125735 m; the other 153 have RMSE 1.933960 m.
27 sampled cells have LDEC>0 (RMSE 1.500526 m); 217 have LDEC=0
(RMSE 1.699526 m). TOTERR/LDEC per pair are retained. TOTERR is modeled Site01
RMS uncertainty, not combined LROC uncertainty; no inverse-error weighting or
confidence certification follows from these small correlated groups.

Exploratory shift search: query Site01 at LROC projected (x+dx,y+dy), dx/dy in
[-10,10] m at 5 m steps. Train on western columns <1250 (120 pairs); validate
on eastern columns (124 pairs). Fit constant median height difference on train
only when comparing candidate residuals. Best training candidate (0,+5) m:
train RMSE 0.817049 m versus 1.139399 m at zero shift. Validation worsens to
2.439882 m versus 2.236621 m at zero. Therefore no reliable correction is
established or applied. The 5 m grid spacing is search precision, not an error
bar. No statistical confidence interval is justified. Low texture, spatial
correlation, interpolated LOLA, slope and unequal resolution confound estimates.

## Site01–Product90 overlap and transitions

225 systematic shared coordinates: Product90 minus Site01 mean -0.201724 m,
median +0.183472 m, RMSE 4.690036 m, extrema -11.955322 to +12.867554 m.
Approximate 160 m projected slope diagnostic: 85 samples below 10 degrees have
RMSE 2.383278 m; 140 steeper samples have RMSE 5.648260 m. These descriptive
associations do not isolate registration from 5/80 m discretization effects.

Four Site01 boundaries tested at +/-5 m: outside uses Product90, inside Site01.
Successive selected-height jumps are +6.690063, -1.129639, -18.642700,
+7.974854 m. They span two positions 10 m apart and include actual slope and
cell discretization, not pure seam errors. Same-coordinate overlap differences
and selected sources are retained separately in JSON. The 18.64 m jump is not
hidden or smoothed. A future ray consumer must consider resolution and seams.
Genuine LROC NoData exercises opt-in LROC -> Site01 fallback. Genuine Site01
NoData fallback is not claimed; the analogous Site01 case uses synthetic tests.

## Tests, performance and readiness

Full suite with genuine kernels and DEM variables: 214 passed, 0 failed,
1 skipped (31.08 s). 15 new tests: 11 synthetic and 4 genuine fusion tests.
Total genuine tests: 11 (2 SPICE, 2 LROC, 3 LOLA, 4 fusion); other tests: 203.
20MPP remains skipped, never replaced by 80MPP. Existing Starlette warning.
`python -m pip check` and `git diff --check` pass. Commands and performance
measurements are recorded in the evidence JSON. The diagnostic took 17.563 s;
peak RSS was 118692 KiB (~115.9 MiB). A 31x31 point grid across a projected
300 km square streamed 961 queries in 0.482 s (960 Product90, 1 Site01).
This is a sampled point benchmark, not complete surface coverage. RSS is process peak including
imports/GDAL, not a guaranteed memory ceiling or a test on an 8 GB machine.

MULTI_RESOLUTION_DEM_ENGINE: COMPLETE.
LROC_REGISTRATION_EVIDENCE: RELATIVE_COREGISTRATION_ASSESSED_ABSOLUTE_UNVERIFIED.
COMMAND_04_5_FINAL: COMPLETE_WITH_REGISTRATION_LIMITATIONS.
Command 05 can consume the streaming interface with explicit prototype policy.
Strict absolute-registration operation remains blocked by missing evidence.
Unknown terrain, seams, sampling spacing/convergence and registration limits
must be preserved in future horizon results. End-to-end visibility is not ready.
SCIENCE_ENGINE_NOT_READY and science_ready=false remain. Command 05 not started.


## Product README evidence addendum

The uploaded `NAC_DTM_ESALL_CR1_README.TXT` is readable text (10494 bytes,
152 physical lines). Its exact byte hash, selected verbatim line excerpts and
the compared PDS label hash are in `source_research.readme_addendum` of the
Command 04.5 evidence JSON. Line numbers below are 1-based, including blanks.
No original attachment or contact details are added to Git.

| Evidence | Source lines | Meaning and limit |
| --- | --- | --- |
| Project ESALL_CR1 and ESA funding | README 1-4 | Associates the document with this product/site. |
| LOLA tie with reported RMS 0.5 m | README 23-28 | Elevation differences between control LOLA points and DTM; contributions from both datasets. A control-fit statistic, not an independent absolute accuracy bound. |
| About 450 LOLA orbit tracks for CR1 and individual corrections | README 24-25 | Product-associated control method; tracks are not independent ground check points. Radio/crossover-corrected LRO orbits are stated, without a control coordinate/residual list. |
| DLR photogrammetry and 2 m DTM spacing | README 29-30; PDS 22-23, 49 | Consistent processing and spacing metadata; spacing does not establish accuracy. |
| Extent | README 32-36; PDS 50-53 | Agrees to the reported precision. |
| Sphere/projection/latitude/longitude | PDS 33-42, 62-64; README 109-113 | Planetocentric, east-positive, south-polar, 1737.4 km sphere; metre heights. README and label do not explicitly state MOON_ME/DE421 realization. |
| Orthophoto offsets up to 15 m or greater | README 38-40 | Applies to orthophotos versus DTM/each other; must not be used as a DTM horizontal error bound. |
| Possible stereo seams/noise | README 86-99 | Explicitly generic to some DLR DTMs; presence in CR1 is not established. |
| CONF codes 0/1/4/14 | README 146-151 | Outside/NoData, shadow, interpolated/extrapolated, successful correlation. CONF raster was not inspected; no quality promotion. |

README lines 26-28 define the 0.5 m RMS and say it may reflect horizontal and
vertical accuracy. They do not separate those components or provide independent
check points. The reported value is retained as `reported_control_fit_rms_m`,
not placed into absolute_horizontal_error_m, absolute_vertical_error_m or
relative_vertical_error_m. Those fields remain null.

Version/time caveats: README creation date is October 4, 2012 (20-21), while
PDS v1.2 (12) gives creation time 2020-10-13 (28). No version/hash in the README
binds the 0.5 m statistic specifically to the supplied v1.2 TIFF bytes. README
start/stop times (31) are seven hours later than PDS times (24-25); no verified
cause/time convention is supplied, so neither is silently corrected.

The README strengthens product-associated LOLA control evidence. It cannot
establish an independent absolute registration because it lacks explicit
product-specific target-frame realization, independent check-point coordinates
and residuals, and separate absolute horizontal/vertical uncertainty metrics.
It also does not identify this later Site01 product as its original control.
The reported 0.5 m fit and our 1.678667 m Site01 difference use different
references/samples/resolutions and must not be equated.

Decision remains **LROC_ABSOLUTE_REGISTRATION_NOT_VERIFIED**;
product_specific_frame_verified=false. Existing relative analysis and
COMPLETE_WITH_REGISTRATION_LIMITATIONS remain valid with the added documentary
evidence. This update changes evidence/documentation only. Prior 214/0/1 test
results are historical; numerical calculations were not rerun for this update.
