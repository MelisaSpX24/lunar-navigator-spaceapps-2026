# Command 03.5 — access evidence and local validation handoff

## Historical access decision: BLOCKED at the original network check

Superseded for local file availability by user-supplied real kernels and CR1
LROC DTM/LBL validation. Current gate:
**PROTOTYPE_DATA_GATE_PASSED_WITH_LIMITATIONS**. See
`evidence/command-03-5.json`, `../backend/DEM.md` and
`../backend/DEM_VALIDATION.md`. Network failures and the uncompleted Horizons/LOLA
checks below remain historical evidence; files described as absent below were
absent at the time of that check. No network bypass or new download is implied.

Main bd18d45 contains merged PRs #1, #2 and #3. The existing kernel session,
geometry, raster reader and CLI are reused; no astronomy/terrain module is rewritten.
No API readiness flag changes. No future scientific modules are introduced.

Executed final checks: `python -m pytest -q backend/tests` — **97 passed, 4
skipped, 0 failed**, one existing Starlette/httpx warning. All 91 prior passing
tests remain passing. The two real kernel and two real DEM integration tests
remain skipped. Six added offline tests cover request planning and acquisition
safety, not NASA data. An initial test-double method-access error was corrected
before the final run. `python -m pip check` and `git diff --check` passed.
The plan CLI generated six requests without network access; network acquisition
modes were not executed successfully in Cloud or on the user's WSL machine.

Runtime access checks, 2026-11-14:

| Actual request | Outcome |
| --- | --- |
| HEAD official NAIF naif0012.tls | Proxy CONNECT 403; no file size or body |
| GET official Horizons API, Sun from coord@301 at CR1, 2026-11-20 08:00 | Proxy CONNECT 403; HTTP connection not established; no reference values |
| HEAD official PGDA Product90 20 m elevation file | Proxy CONNECT 403; no GeoTIFF header |

Each route was tried once in this task; no repeated failed download, policy
bypass, external proxy or mirror was used. A research-tool page fetch is not
equivalent to executable access to kernels or raster files.

All five kernels remain absent: de421.bsp, moon_pa_de421_1900-2050.bpc,
moon_080317.tf, naif0012.tls, pck00011.tpc. Actual sizes/types, SHA-256, load
compatibility and 2026 usable coverage remain NOT_RUN. Official candidate URLs
remain in manifests/kernels.json. No placeholder hash or READY status is added.

Real Sun/Earth calculations at all three requested epochs: NOT_RUN. Reference
azimuth/elevation/distance and numerical SPICE–Horizons residuals: NOT_VERIFIED.
The manifest has not been upgraded merely because source pages are readable.

## Horizons reference plan

Official API: https://ssd-api.jpl.nasa.gov/doc/horizons.html
Manual: https://ssd.jpl.nasa.gov/horizons/manual.html
GUI: https://ssd.jpl.nasa.gov/horizons/app.html

`python -m data_pipeline.reference_access plan` prints six URL-encoded requests:
targets Sun 10 and Earth 399 at 2026-11-20 08:00/20:00 and 2026-11-27 08:00 UTC.
Each request includes an additional minute endpoint; compare the requested first
row, not the extra row. Observer is coord@301, east longitude 222.6, latitude
-89.468, height **0.001 km**. That height is an assumed zero reference-sphere
surface elevation plus a 1 m device, not a measured CR1 elevation.

Requests use OBSERVER, GEODETIC, AIRLESS, UT/+00:00, QUANTITIES 4,20, RANGE_UNITS
KM, CSV output and no elevation clipping above -90. No execution is implied by
the plan. Only the Sun request at the first epoch was attempted here, and failed.
The helper preserves raw JSON; a SOE marker merely establishes an ephemeris body,
not correct observer interpretation or successful scientific validation.

Before accepting any row, review and retain the complete header/footer:

- Target body code 10 or 399 and centre body Moon 301; site must be user-defined,
  not 500@301 (Moon centre) or Earth-based.
- Centre geodetic coordinates, east sign, reference radius/shape and height.
- Lunar body-fixed coordinate interpretation (manual documents DE421 Mean Earth);
  do not confuse target ICRF astrometry with the observer's lunar map frame.
- Time scale and selected first-row epoch; distances and angular units.
- Actual ephemeris source/version, rotation model, aberrations and AIRLESS state.

SPICE NONE is simultaneous geometric. Horizons apparent AZ/EL includes light
time, aberration and possibly gravitational terms; LT+S in our motor does not
exactly replicate every Horizons correction. Ephemeris versions may also differ.
Run optional LT+S for a closer diagnostic, but do not label residuals as code
error or PASS without reviewing these differences and a justified tolerance.
Azimuth difference must wrap to [-180,180), not use raw subtraction across 360.
Distance comparison requires the same light-time convention and observer radius.
If conventions cannot be matched, preserve references as COMPARISON_LIMITED.
These are correlated JPL model products, not independent observational truth.
Horizons does not supply our actual terrain horizon.

## Moon Trek and QuickMap

Moon Trek https://trek.nasa.gov/moon/ rendered only a JavaScript shell through
text research. Its WMTS service is documented at
https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon and PDS lists the portal
as supporting mapped-data search/view/download at https://pds-geosciences.wustl.edu/tools/.
Interactive CR1 selection, elevation-profile export, subsetting result formats,
the selected layer's exact datum/resolution and account requirements were NOT
VERIFIED. Do not interpret general portal capability as a completed CR1 download.
User action: enter CR1, choose an elevation layer, open its metadata/source link,
record product/frame/datum/resolution and download the numeric source, not an
image tile or displayed profile. A profile alone is not a georeferenced DEM.

QuickMap https://quickmap.lroc.asu.edu/ redirects to
https://quickmap.lroc.im-ldi.com/ and requires JavaScript. Actual coordinate entry
and layer interaction were NOT VERIFIED. Official LROC product pages supplied
two concrete regional candidates:

| Product | Page-reported details, not raster-header evidence |
| --- | --- |
| NAC_DTM_SHACKRDGE02 | 3.5 m/pixel, GeoTIFF 9.61 MB; bounds lon 209.81–239.10 E, lat -89.63 to -89.37; project date 2024-04-23 |
| NAC_DTM_ESALL_CR1_P895S2222 | 2 m/pixel; PDS IMG 23.85 MB, supplemental GeoTIFF 5.97 MB; bounds lon 209.97–234.51 E, lat -89.58 to -89.35 |

Sources:
https://data.lroc.im-ldi.com/lroc/view_rdr_product/NAC_DTM_SHACKRDGE02
https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_DTM_SHACKRDGE02
https://data.lroc.im-ldi.com/lroc/view_rdr_product/NAC_DTM_ESALL_CR1_P895S2222

The page boxes include the CR1 coordinate numerically, but that does not prove
valid pixels at the point or 1/3/5 km circle coverage. These are stereo-derived
LROC DTMs, not identical to the LOLA product family. Their exact datum, CRS,
version identifiers, voids and registration with LOLA remain unverified. Obtain
their label/README and confidence product before considering integration.
They are small, user-selected local inspection alternatives, not replacements
silently added to the approved Site01 manifest. No LROC raster was downloaded.

## PGDA DEM handoff

Official product pages checked again:
https://pgda.gsfc.nasa.gov/products/78
https://pgda.gsfc.nasa.gov/products/90

Site01 elevation/quality files remain the near-field candidates. Product90 20 m
elevation (page label 2.6G), slope (3.6G), height error (3.7G) and 80 m elevation
(181M) support planning for near/far data; these are approximate page labels,
not actual byte lengths observed here. Product90 documents COGs, south polar
metre X/Y and DE421 Mean Earth. Product78 documents 5 m spacing with substantial
interpolation. Neither statement establishes actual CR1 pixel quality.

Keep originals under ~/lunar-data/originals, kernels under ~/lunar-data/kernels,
results under ~/lunar-data/results. First inspect official header/label and file
size. Prefer the Site01 local dataset or a user-approved bounded COG subset;
do not automatically fetch all GB-scale Product90 files. Do not treat 5 km data
as sufficient for a 100–150 km provisional horizon calculation. Near/far datum,
grid and valid-data compatibility must be checked before combining products.
The existing reader supports only its explicitly checked lunar spherical CRS;
if a genuine file differs, report unsupported metadata instead of relabelling it.

## Exact WSL workflow (NOT EXECUTED on the user's machine)

Prerequisites: authorized network access to the official hosts, Python 3.12,
the reviewed code branch, sufficient disk and the activated project environment.
If blocked on WSL too, stop and request the local/network administrator's help;
do not change proxy/TLS settings to bypass restrictions.

```sh
cd /path/to/lunar-navigator
python3.12 -m venv /tmp/lunar-validation-venv
source /tmp/lunar-validation-venv/bin/activate
python -m pip install -r backend/requirements-tested.txt
python -m pip install --no-deps -e backend
export PYTHONPATH="$PWD/backend"
mkdir -p ~/lunar-data/results

# Explicit user invocation only; checks HEAD length before each official kernel.
# Per-file cap 32 MiB, no retries/redirects/overwrites; abort on missing length.
python -m data_pipeline.reference_access kernels --destination ~/lunar-data/kernels --contact YOUR_CONTACT
python -m data_pipeline.spice_cli index --directory ~/lunar-data/kernels --output ~/lunar-data/results/kernel-index.json
python -m data_pipeline.spice_cli inspect --directory ~/lunar-data/kernels --index ~/lunar-data/results/kernel-index.json --output ~/lunar-data/results/kernel-inspect.json
export NASA_KERNEL_DIR="$HOME/lunar-data/kernels"
export NASA_KERNEL_INDEX="$HOME/lunar-data/results/kernel-index.json"

# Three requested epochs; explicitly assumed zero terrain height and 1 m device.
i=0
for epoch in 2026-11-20T08:00:00Z 2026-11-20T20:00:00Z 2026-11-27T08:00:00Z; do
  python -m data_pipeline.spice_cli geometry --directory "$NASA_KERNEL_DIR" --index "$NASA_KERNEL_INDEX" --latitude -89.468 --longitude 222.6 --surface-elevation-m 0 --device-height-m 1 --utc "$epoch" --output "$HOME/lunar-data/results/geometry-$i.json" || break
  i=$((i+1))
done
python -m data_pipeline.reference_access plan > ~/lunar-data/results/horizons-plan.json
python -m data_pipeline.reference_access horizons --destination ~/lunar-data/results/horizons --contact YOUR_CONTACT
python -m pytest -q backend/tests
```

Do not rerun into existing files; preserve each acquisition's metadata. Inspect
does not independently authenticate kernels. Locally generated SHA-256 detects
subsequent changes, not NASA authenticity. Save acquisition URLs/headers/time
and inspect actual output; no tool promotes READY based on file presence.

For a manually acquired official Site01 DEM:

```sh
export NASA_SITE01_DEM="$HOME/lunar-data/originals/Site01_final_adj_5mpp_surf.tif"
python -m data_pipeline.cli inspect --path "$NASA_SITE01_DEM"
python -m data_pipeline.cli coverage --path "$NASA_SITE01_DEM" --product-id Site01_final_adj_5mpp_surf.tif
python -m pytest -q backend/tests
```

Coverage checks only projected bounds, not valid-pixel quality: run bounded
`window` checks from the prior guide, inspect NoData/count/error layers and source
datum. Set NASA_PRODUCT90_DEM only if a genuine corresponding file is available.
Do not substitute a small unrelated cutout while claiming full product coverage.

Required human handoff: run these explicit steps on an authorized WSL machine,
review the outputs and provide kernel inspection, geometry/reference headers and
DEM metadata/coverage reports to the team. Never share private paths/contact info
or commit original binary files. No success on that machine is claimed here.
