# Command 02 — controlled LOLA preparation

Current real-file status: `LOLA_VALIDATION.md` records reconstructed Site01
height/quality and Product90 80MPP validation. The original absent-file notes
below are historical. Source binaries remain external; science_ready stays false.

This page preserves Command 02's original LOLA workflow and evidence state.
Current Command 03.5 closure and the separate labelled LROC Command 04 adapter
are documented in `../backend/DEM.md` and `../backend/DEM_VALIDATION.md`.
The old absent-file/NOT_RUN statements below are historical, not current claims
about the user-supplied kernels or LROC files. LROC is not substituted for LOLA.

See `ACCESS_VALIDATION.md` for the Command 03.5 network recheck, newly identified
small LROC DTM candidates and explicit WSL kernel/Horizons validation workflow.

Run from the repository root with Python 3.12. Commands never auto-download
rasters or kernels. `local/` and `cache/` are ignored; keep original data outside
Git. No API readiness or analysis behavior is changed.

## Evidence and sources

- Product 78: https://pgda.gsfc.nasa.gov/products/78 — Site01 Connecting Ridge
  elevation, count, slope, height/slope uncertainty and ROI names were checked on
  the product page. File headers and exact footprint were **not inspected**.
- Product 90: https://pgda.gsfc.nasa.gov/products/90 — wide-area COG elevation,
  slope, uncertainty, effective resolution and counts. The page describes south
  polar stereographic coordinates in metres, DE421 Mean Earth. Exact projection
  parameters, datum, NoData and byte lengths remain unknown without file headers.
- Candidate kernel provenance is in `manifests/kernels.json`. Frame definitions:
  https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_080317.tf
- CR1: latitude -89.468, east longitude 222.6, MOON_ME_DE421. Research point cited
  in the NASA NTRS-hosted Future Lunar Surface Network Study (Nokia, 2024), p.88:
  https://ntrs.nasa.gov/citations/20240003815

Manifests distinguish page documentation from file inspection. Null versions,
hashes, exact sizes, datum and NoData are intentional. Listed sizes are page
labels, not measured byte counts. Only two raster download URLs were resolved;
the remaining links must be obtained from official product pages, not guessed.
No real file exists locally; nothing is READY. Kernel time coverage is unverified
and text PCK radius compatibility is unresolved. No SPICE loading/calculation occurs.

## Installation

```sh
python3.12 -m venv /tmp/lunar-data-venv
/tmp/lunar-data-venv/bin/pip install -r backend/requirements-tested.txt
/tmp/lunar-data-venv/bin/pip install --no-deps -e backend
source /tmp/lunar-data-venv/bin/activate
export PYTHONPATH="$PWD/backend"
```

For a new dependency resolution, install `backend[data,test]` instead and rerun
tests before replacing the tested snapshot. Verified here: Python 3.12.14,
Rasterio 1.5.2 / GDAL 3.12.2, NumPy 2.5.4, PyProj 3.8.0 / PROJ 9.8.1.

```sh
python -m data_pipeline.cli manifest
python -m data_pipeline.cli manifest --manifest data_pipeline/manifests/kernels.json
python -m data_pipeline.cli inspect --path /absolute/local/DEM.tif
python -m data_pipeline.cli coverage --path /absolute/local/DEM.tif --product-id LDEM_80S_20MPP_ADJ.TIF
python -m data_pipeline.cli window --path /absolute/local/DEM.tif --product-id LDEM_80S_20MPP_ADJ.TIF --window 0 0 100 100
python -m data_pipeline.cli cutout --path /absolute/local/DEM.tif --product-id LDEM_80S_20MPP_ADJ.TIF --window 0 0 100 100 --output data_pipeline/cache/cut.tif
```

Create the output directory yourself. Pixel windows use `column row width height`.
Projected windows instead accept `--xy X Y --radius-m R`; X/Y must be in the
actual file's projected metre coordinates. No fallback projection is invented.
Coverage uses the file CRS geodetic sphere and requires a declared DE421 frame;
the CRS alone does not prove the frame. It reports projected bounding-square
coverage for 1/3/5 km, not geodesic-circle coverage or valid-data quality.
Pixel masking/statistics must then be checked in bounded windows. Exact geodesic
search-circle coverage and near-pole optimizer geometry belong to later work.

`read_window` returns a masked array and provenance/statistics. Invalid values
include NoData, NaN, infinity and invalid slope/quality ranges. Unknown units,
unexpected scaling, missing/unsupported CRS and out-of-bounds windows fail
explicitly. Missing raster units use the manifest declaration and are reported
as MANIFEST_ONLY evidence, not independently verified units. All-invalid windows
return null extrema. Export preserves the mask (zero-filled invalid storage is
never valid zero height) and adds a JSON sidecar, source identity and SHA-256.
`aligned` checks the CRS, transform and dimensions of local layers. It does not
resample mismatched quality rasters or invent missing layers.

## WSL / remote access

Place an explicitly selected file, obtained from the official NASA page, under
`~/lunar-data/originals/`, or read it from `/mnt/c/...`. Suggested layout:

```text
~/lunar-data/originals/   # immutable local originals and original metadata
~/lunar-data/kernels/    # future approved kernel files
~/lunar-data/derived/    # bounded cutouts and sidecars, never committed
```

Before approving a large local download, check disk space and the official file
size. A controlled Range probe can be run with:

```sh
python -m data_pipeline.cli probe-range --url https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_20MPP_ADJ.TIF
```

The probe requests one byte and consumes no body if Range is ignored. No full-file
download command is built in. Here, both the page curl request and Range probe
failed at the workspace proxy (CONNECT 403). Therefore remote Range support,
actual transfer cost and remote COG regional reads are **NOT VERIFIED**.
This implementation reads **local GeoTIFF/COG windows only**; it does not silently
fall back to GDAL remote downloads. Working remote range/COG access remains an
explicit follow-up, not a demonstrated feature. Use local files on WSL meanwhile.

## Budgets and scientific boundaries

Default limits: 1,000,000 pixels; 64 MiB estimated array working budget; GDAL cache
16 MiB. Override via `--max-pixels` and `--max-working-bytes`. Whole raster reads
are never implicit. Oversized decode blocks are rejected even for small windows.
These are allocation guards, not a guarantee on process RSS or file transfer.
Compressed block I/O, library overhead and export checksumming add cost. Export
hashes the source by streaming the entire local file, potentially slow for GB files.

For planning only, a 6 km-wide square has about (6000/20)^2 pixels at 20 m and
(6000/5)^2 at 5 m. One float32 band uses 4 bytes/pixel before masks, processing
copies, quality bands, compression and alignment. Actual cutout disk sizes are
not guaranteed. Wide 100–150 km terrain windows can exceed budgets and require
tiling/multiple resolutions; no horizon ray tracing is implemented.

Near field: Site01 5 m / Product90 20 m candidates. Far field: Product90 80 m
candidate. Pixel spacing is not measurement accuracy; interpolated gaps and
coarse-raster suppression of narrow ridges affect later horizon estimates.
CR1 point, 1/3/5 km data quality, near/far alignment, height datum and horizon
range convergence remain **NOT_RUN**. Do not label any region analysis-ready.

## Tests and next step

```sh
python -m pytest -q backend/tests
python -m pip check
```

Synthetic tests create tiny rasters at runtime, including a local COG. They test
windows, masks, nonfinite values, units, projection rejection, grids, memory
guards, cutouts and hashes. They are not NASA validation. Optional local-file
integration checks use `NASA_SITE01_DEM` and `NASA_PRODUCT90_DEM`; when absent,
they are skipped. Providing these variables is an operator assertion about the
file identity; provenance must still be checked before scientific use.

Command 03 prerequisites: obtain/access genuine files, inspect CRS/datum/NoData,
verify source hashes and CR1 coverage, load/check kernel contents and date
coverage under that command. No astronomical, horizon, disk or optimizer engine
has been added; the API still returns SCIENCE_ENGINE_NOT_READY and null score.
