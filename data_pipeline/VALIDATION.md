# Command 02 validation record

## Repository precondition

Fetched main and verified ancestry of 2699148577f374bdbd3f79c2ddb9e6ef5bf46c31.
Started from main merge commit 2ca5e7c. No merge was performed by this task.

## Executed checks

- Python 3.12.14; NumPy 2.5.4; Rasterio 1.5.2 / GDAL 3.12.2;
  PyProj 3.8.0 / PROJ 9.8.1 installed from compatible binary wheels.
- `python -m pytest -q backend/tests`: **62 passed, 2 skipped**, one existing
  Starlette/httpx TestClient deprecation warning. Includes all 39 Command 01 tests.
- `python -m pip check`: no broken requirements.
- Both CLI manifest validation commands: passed (12 LOLA products, 5 kernel candidates).
- `git diff --check`: passed.

## Real-source checks, not real raster validation

PGDA Product78/Product90 pages inspected with the research tool: requested names
are listed. Two direct raster URLs resolved; metadata/content could not be read
as GeoTIFF through that tool. Official NAIF listings and existing frame docs were
consulted for candidate paths. No raster or kernel downloaded to this workspace.

Workspace `curl` to Product90 and bounded Range probe to the 20 m elevation URL:
proxy CONNECT **403**. Range capability and remote COG read NOT_VERIFIED.
No retry bypass or automatic full download was attempted.

`NASA_SITE01_DEM` and `NASA_PRODUCT90_DEM` were absent: both local-file integration
tests SKIPPED. CR1 coverage (point and 1/3/5 km), valid-pixel quality, absolute
datum, actual file CRS, near/far alignment, source file sizes/hashes and runtime
kernel coverage remain NOT_RUN. No scientific READY result has been established.

All new raster results came from generated synthetic fixtures. No astronomical
geometry, terrain horizon, disk visibility, scoring or optimizer was implemented.
