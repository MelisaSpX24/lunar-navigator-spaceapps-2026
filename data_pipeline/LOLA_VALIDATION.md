# Command 03.5 real LOLA addendum — COMPLETE with scientific limitations

Validated on 2026-11-14 from main be3cc77 after PR #7 had been merged by the team.
Work branch: backend/command-03-5-lola-validation. No merge by this task.
Machine-readable evidence: evidence/command-03-5-lola-addendum.json.
The earlier command-03-5.json is preserved as a historical snapshot.

## Reconstruction and identity

All 14 data attachments were accessible: 13 independent ZIP files and a UTF-8
BOM manifest. Each ZIP had exactly its expected single .bin entry, no traversal,
symlink or encryption. Parts were ordered by their three-digit suffix and read
in 1 MiB chunks (ZIP CRC checked while consuming each entry). Expanded part size
was bounded at 32 MiB; output size bounded by the declared original size. All
four original byte sizes and SHA-256 hashes matched the manifest exactly. TIFFs
were reconstructed outside Git without resampling/re-encoding and reopened by
Rasterio/GDAL. The evidence JSON records both original and reconstructed hashes.
The manifest hashes are user-reported Windows-original hashes, not independently
published NASA checksums. The attachment size limit remains; splitting solved
transfer for these four products, not the platform's general 32 MiB limit.

## Source documentation and remaining metadata limits

- https://pgda.gsfc.nasa.gov/products/78 — Site01 surface height in metres, RMS
  height uncertainty in metres, spot counts, 5 m grid and MOON_ME/JPL DE421.
- https://pgda.gsfc.nasa.gov/products/90 — 80MPP elevation product listed;
  metre height, south polar metre coordinates and MOON_ME/JPL DE421.
- https://svs.gsfc.nasa.gov/4720 — LRO reference-surface convention: 1737.4 km
  sphere. Used for reference convention, not this page's differently encoded
  visualization TIFFs. No half-metre or kilometre conversion is applied here.
- Product78 README https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/README was unavailable:
  research fetch unsupported application/octet-stream; one runtime attempt 403.
  No retries/bypass. Product-specific vertical evidence therefore combines metre
  documentation, mission sphere convention and inspected spherical CRS axes;
  the horizontal CRS alone is not claimed as proof of vertical datum.

No explicit publisher release version was found. A narrow model/adapter change
allows a required-but-null LOLA product_version only with explicit version_evidence.
No invented version or acquisition date masquerades as a version. Hashes identify
these originals. Page-only manifests still fail without explicit datum evidence.
Generic WKT labels (Site01 "unknown", Product90 "Moon (2015)") are not SPICE frame
proof. PGDA documents DE421 separately; product registration/error flags remain
conservative. None of this proves LROC product-specific registration.

## Actual raster and CR1 results

All four rasters: float32, one band, NaN NoData, scale 1, offset 0, band unit field
empty; physical units come from PGDA documentation. Sphere axes 1737400 m,
polar stereographic lat -90/lon 0, false offsets 0, projected metre axes.

Site01 trio: 3200x3200, 5 m/pixel, identical grids, bounds
[-19000,-20000,-3000,-4000] metres; 16x16 km rectangle. CR1 [-89.468,222.6 E]:

- Cell [1574,1616], zero based; height **1942.1014404296875 m**.
- Cell-centre offset from requested coordinate: **3.0349813393 m**.
- TOTERR: **0.22997184098 m**, modeled statistical RMS height uncertainty.
- LDEC: **0** valid counts. Height is available through the interpolated DEM;
  this cell has no direct laser spot. This is not zero height or zero uncertainty.
- TOTERR is not a hard maximum error, an LROC error measurement or a safety score.

| Radius | Disk cells | Bounds/valid height | Internal/outside missing | LDEC>0 fraction | TOTERR mean/median (m) |
| --- | --- | --- | --- | --- | --- |
| 1 km | 125667 | 100% / 100% | 0% / 0% | 9.6676% | 0.37665 / 0.35035 |
| 3 km | 1131042 | 100% / 100% | 0% / 0% | 9.9537% | 0.39405 / 0.36495 |
| 5 km | 3141778 | 100% / 100% | 0% / 0% | 10.7062% | 0.37199 / 0.34244 |

Production dem.coverage was used unchanged (5 km maximum). Whole geodesic disk
is denominator. Quality statistics used 32-row windows and geodesic pixel-centre
selection, with finite/nonnegative separately masked quality values; retained
selected values for exact medians, at most 3.15M float32 values per layer.
Full valid DEM coverage is not full direct-measurement support. Prior LROC valid
fractions were 98.71/80.30/29.85%; genuine Site01 covers more valid cells here.

## Cross-dataset diagnostic

LOLA minus LROC at CR1: **-2.03857421875 m**. A systematic 20x20 grid at LROC
rows/columns 62+125*k gave 375 valid pairs of 400 attempted. Each source sampled
the containing cell at each LROC cell-centre coordinate; no interpolation or
alignment correction. Difference mean -0.73500 m, median -0.55750 m, RMSE
1.50367 m, range [-5.56262,5.65039] m. This supports descriptive consistency of
sampled elevations, not an independently established geodetic registration or
accuracy threshold. 2 m vs 5 m cell locations, slope, datum interpretation,
horizontal offsets and source errors may contribute. No offset is applied.

## Product90 80MPP and wide area

7600x7600 tiled/deflate raster, 80 m pixels; bounds +/-304000 m. CR1 cell
[3948,3663], height **1942.8433837890625 m**. All-longitude footprint includes
the south pole; edge midpoint latitude -80.0001835, rectangle corners extend
to -75.8938043. A square's corner latitude is not a guarantee of valid polar-cap
coverage. Generic CRS naming does not replace PGDA's documented frame definition.

A separate temporary diagnostic checked a **150 km geodesic disk** around CR1
in 16-row windows, with 36 ten-degree azimuth sectors. Enclosing projected
halfwidth 152 km conservatively exceeds the local stereographic scale bound.
**11058822** cell centres: 100% inside, 100% finite/unmasked. All 36 sectors had
zero missing or exterior samples within that disk; counts are saved in JSON.
No production 5 km limit was bypassed or changed. No terrain horizon, angular
obstruction, disk visibility or ray-range convergence was computed. Sampling
fractions are approximate area statistics, not complete continuous-surface proof.
Rasterio windows and 16 MiB GDAL cache in the open DEM session bounded reads;
the full 7600x7600 band was not loaded. This is an actual viable far-terrain input,
not proof that 150 km is sufficient for every future horizon calculation.

## Tests and reproduction

Existing dependencies reused. From repository root, set PYTHONPATH=backend:.
and supply local paths (outside Git) using NASA_KERNEL_DIR, NASA_KERNEL_INDEX,
NASA_LROC_CR1_DEM, NASA_LROC_CR1_LABEL, NASA_SITE01_DEM and
NASA_LOLA_VALIDATION_DIR. The last directory must contain the four exact original
filenames. Leave NASA_PRODUCT90_DEM unset unless the actual **20MPP** file exists.
Run `python -m pytest -q backend/tests -ra` and `python -m pip check`.

Final total: **199 passed, 0 failed, 1 skipped**. Four new tests were added:
2 genuine Site01/80MPP integrations, 2 synthetic/version/identity rejection tests.
The previously skipped Site01 check now passes. The original Product90 20MPP test
remains skipped; 80MPP is tested separately, never renamed/substituted.
Evidence classes: 2 real kernel + 2 real LROC + 3 real LOLA passing tests;
192 other unit/API/math/synthetic/mock tests. No independent Horizons validation.
One existing Starlette/httpx warning. pip check and diff whitespace checks pass.
The integration values are regression checks of the observed originals, not
independent physical ground truth. Wrong supplied hashes fail rather than skip.

## Closure and handoff

03.5_PROTOTYPE_GATE: COMPLETE (previously established).
03.5_SITE01_REAL_DATA_GATE: COMPLETE.
03.5_PRODUCT90_80MPP_REAL_DATA_GATE: COMPLETE.
03.5_LOLA_ADDENDUM: COMPLETE with the documented scientific limitations.

Four-file reconstruction, actual metadata, physical interpretation, samples,
coverage and genuine integrations are complete. Versions remain unknown, README
unavailable, and registration is not independently measured; these limitations
are preserved explicitly. Remaining work belongs to separate stages: LROC
registration, Horizons comparison, 20MPP test, far-field rays/convergence,
Sun/Earth disk visibility and operation windows/decisions. KOMUT 05 not started.
SCIENCE_ENGINE_NOT_READY and science_ready=false remain. No source binaries,
private paths, frontend/contracts or root configuration are committed.
