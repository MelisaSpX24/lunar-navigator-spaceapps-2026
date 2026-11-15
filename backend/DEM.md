# Command 04 — evidence-bound DEM foundation

Command 03.5 closed as **PROTOTYPE_DATA_GATE_PASSED_WITH_LIMITATIONS**.
The later four-file real LOLA validation is recorded in
`../data_pipeline/LOLA_VALIDATION.md`. A LOLA release version may remain null
only with explicit `version_evidence`; a file hash identifies the inspected
original. An absent version is never replaced with a guessed version number.
The evidence snapshot is `../data_pipeline/evidence/command-03-5.json`.
This gate permits prototype development; it does not set API `science_ready`.
The analysis endpoint still returns `SCIENCE_ENGINE_NOT_READY`, INCOMPLETE and
null score. Astronomy is unchanged. No terrain horizon, disk visibility,
operation-window calculation or optimizer is implemented. Command 05 has not begun.

## Architecture and supported input

- `app.data.dem_models`: backend-local reference, sample and coverage evidence.
  Existing shared contracts and HTTP response schemas are unchanged.
- `app.data.coordinates`: forward/inverse source-grid transforms, zero-based
  cell centres/indices, coordinate validation and spherical distance.
- `app.data.lola`: controlled LOLA declaration adapter; rejects absent metre,
  datum or version evidence instead of promoting the page-only manifests.
- `app.data.quality`: associated, exactly aligned quality windows/cells with
  separate masks and source identities; no confidence/hazard scoring.
- `app.data.observer`: observer-input preparation retaining DEM/device heights
  and source evidence; no astronomical calculation.
- `app.data.errors`: backend-local DemError codes, not HTTP API changes.
- `app.data.dem`: hash-bound local DEM session, containing-cell sampling and
  streamed geodesic-disk coverage. Reuses the existing CRS/window/block guards.
- `data_pipeline.lroc`: deliberately narrow adapter for the supplied
  `NAC_DTM_ESALL_CR1` float32 PDS3/GeoTIFF pair; not a general PDS parser.
- `data_pipeline.dem_cli`: local inspect/sample/coverage commands. No downloads.

The adapter checks product identity, label dimensions, sample type, projection,
radius, pixel scale, missing value convention and explicit height description.
Unsupported labels, image representations and inconsistent metadata fail instead
of acquiring guessed conversions. SHA-256 binds subsequent use to inspected files;
a locally calculated hash is not independent NASA authentication. The caller
must preserve trusted acquisition records. The generic `DemReference` constructor
is an explicit evidence declaration, not an independent metadata verifier.

Supported grids: one float32/float64 elevation band, north-up/unrotated south
polar stereographic lunar CRS, 1737400 m spherical axes, identity scale/offset,
metre units evidenced by a label/declaration. The LROC adapter specifically
requires float32. uint8 previews are rejected; other numerical height encodings
require their own explicit conversion adapter. The old Command 02 LOLA tools
retain their behavior and are not silently supplied LROC-as-LOLA declarations.
Nonzero prime meridians are rejected rather than applying an undocumented offset.

## Reference and accuracy evidence

The supplied LBL explicitly defines **Height [m] equals DN**, above its map-axis
sphere, with all axes 1737.4 km. GeoTIFF band units are empty; the PDS label is
the metre/datum evidence. No correction offset is applied.

The general LROC mapping standard supports DE421 Mean Earth/Mean Rotation:
[Speyerer et al., 2024, Where Is That Crater?](https://doi.org/10.3847/psj/ad54c6).
This is general evidence, **not product-specific registration or error proof**.
Recorded separately:

```json
{
  "declared_lunar_radius_m": 1737400,
  "vertical_unit": "m",
  "vertical_reference": "HEIGHT_ABOVE_REFERENCE_SPHERE",
  "source_frame_evidence": "SUPPORTED_BY_LROC_STANDARD",
  "product_specific_frame_verified": false,
  "target_spice_frame": "MOON_ME_DE421",
  "registration_uncertainty_status": "NOT_QUANTIFIED",
  "absolute_horizontal_error_m": null,
  "absolute_vertical_error_m": null,
  "relative_vertical_error_m": null
}
```

Product-specific numerical errors need their own evidence reference. General
standard evidence cannot promote product-specific frame verification. Unknown
errors are null, not zero. No +/-2 m or <=10 m accuracy is assigned to this DTM.

Coordinates are planetocentric latitude, east longitude [0,360), target frame
MOON_ME_DE421. Exact poles are rejected consistently with the backend site model.
Transforming those coordinates into this product without verified registration
requires **explicit** `allow_unverified_registration=True`. The result retains
`prototype_registration_assumption_used=true` and the full reference evidence.
This permits an identified research assumption; it does not prove alignment.
`declared_source_frame` is separate from the target SPICE frame and may remain
null for LROC. Explicitly incompatible frames fail even with prototype opt-in.
Result `frame_status` distinguishes PRODUCT_SPECIFIC_VERIFIED,
SUPPORTED_BY_SOURCE_STANDARD, PROVISIONAL, UNKNOWN and INCOMPATIBLE.
The radius, vertical unit and vertical reference are required evidence fields;
they cannot be omitted and silently defaulted to a known datum.

## Public coordinate and distance interfaces

`dem.grid` is a `LunarGrid` initialized once from the actual dataset. Its
mathematical source-grid methods are:

- `geographic_to_xy(Coordinates)` -> (x_m, y_m).
- `xy_to_geographic(x_m, y_m)` -> (planetocentric latitude, east longitude).
- `xy_to_pixel(x_m, y_m)` -> zero-based row/column and an inside-raster flag.
- `pixel_center_xy(row, column)` -> (x_m, y_m), using +0.5 cell offsets.
- `pixel_center_geographic(row, column)` -> source-grid geographic tuple.

Source geographic tuples alone do not claim verified MOON_ME_DE421 registration.
Longitude 360 is rejected as input under [0,360); inverse output normalizes the
0/360 seam. Exact poles are rejected to preserve the observer convention rather
than invent a longitude/azimuth. Nonfinite, rotated, Earth or unsupported grids
fail explicitly. Boundary indices follow the half-open raster extent; outside
X/Y gives an outside flag, while an outside pixel-centre request is an error.

`surface_distance_m(first, second, reference_radius_m)` computes the shortest
geodesic with PyProj Geod on the explicitly supplied sphere. It does not use
Earth radii or flat X/Y distance. Radius is in metres, without automatic kilometre
conversion. The raster adapter currently supports the declared 1737400 m sphere;
the independent distance function accepts any explicitly positive finite radius.
Projection scale distortion is retained, tested, and bounded in disk coverage.

## Sampling and missing data

`open_dem(path, reference)` checks the file hash once on entry and owns the local
GDAL dataset/environment until exit. Keep originals immutable during the session.
`dem.sample(location, allow_unverified_registration=True)` selects the containing
cell by inverse affine mapping, not bilinear interpolation. Reports zero-based
row/column, projected metres, raw value, source hash and surface elevation.
Device/panel/antenna height is not part of the DEM elevation.
Results include actual resolution/CRS, provider/family/version, frame evidence,
reason codes, limitations and separate quality evidence. External masks are
honored and hashes of GDAL-reported auxiliary files are recorded at session open.
Those companion hashes are observations, not independently pinned authentication;
keep both the raster and its sidecars immutable during the session.

VALID gives a finite metre elevation. Negative heights and real zero heights
remain valid. NODATA and OUTSIDE_RASTER give null surface elevation. GDAL masks,
nonfinite values and label missing constants are all honored. A finite NoData DN
may be preserved as `raw_value`; it is never a surface height. No fallback zero,
silent clipping, extrapolation or interpolation is provided. A missing analysis
point must not be used as a valid DEM observer location. Regional coverage may
still be inspected to report what is missing.

At CR1 (-89.468, 222.6 E), cell [1167,1230] stores 1944.1400146484375 m.
Display as **1944.14 m above the reference sphere**. This is a cell value, not
centimetre accuracy, certified lander elevation or an exact continuous-point
measurement. Prior SPICE geometry used an assumed 0 m surface; it has not been
silently relabelled as DEM-based geometry.

## Associated quality and LOLA preparation

`lola_reference(path, product, vertical_evidence=...)` requires a PGDA LOLA
ELEVATION declaration with documented metre unit, supported reference-sphere
datum, real product version, matching filename and supported actual file CRS.
The page-only manifests still lack sufficient datum/version evidence and fail
this path. Their declarations and READY status are not changed. Explicit
manifest frame declarations remain PROVISIONAL rather than product-verified.

`QualityLayer(path, product, sha256)` binds one COUNT, HEIGHT_ERROR, SLOPE or
EFFECTIVE_RESOLUTION file. `read_quality_window(dem, layer, window)` and
`sample_quality_layers(dem, sample, layers)` preserve separate masked measurements.
The layer must be explicitly associated by ID and source product family in the
DEM reference. Exact CRS, affine and dimensions must match before reading. The
existing LOLA unit/frame/window checks are reused; no forced registration or
implicit resampling is performed. LROC cannot silently use unrelated LOLA layers.
Future LROC quality products need their own evidenced association/adapter.
Each quality-file hash is verified once per open DEM session to avoid repeatedly
streaming large originals. Keep quality rasters and their sidecars immutable for
that session, just like the elevation source. External quality masks are honored;
their TIFF hash alone does not independently authenticate the companion mask.

`dem.sample(..., quality_layers=[...])` attaches cell-level quality. Missing layers
give QUALITY_NOT_ASSESSED, not zero errors/counts. Present but invalid quality
gives PARTIAL_QUALITY_DATA independently of the elevation cell validity.
All valid layer measurements give QUALITY_LAYERS_PRESENT, **not a reliability
or landing-safety verdict**. Counts must be nonnegative integers, errors/effective
resolution nonnegative and slopes in [0,90]; masks remain independent. Disk
coverage reports QUALITY_NOT_ASSESSED for region-wide quality distribution.

## Observer preparation and failure codes

`prepare_observer(sample, device_height_m)` returns an ObserverPreparation envelope
containing the original DEM sample, observer, frame status and reason codes.
Missing/outside heights and incompatible frames fail. Surface height remains
separate from device height; the existing observer-position helper converts
`(radius + surface + device) / 1000` to SPICE kilometres. No datum offset is used.
Until frame registration is product-verified, the old observer's coarse datum
flag stays ASSUMED_REFERENCE_SPHERE. The envelope separately preserves the
label-documented vertical evidence. Do not discard that envelope when designing
future astronomy integration; the unchanged astronomy motor alone has no DEM
registration-evidence field. This task calls no SPICE calculation with this input.

DemError exposes `.code` and an explanatory message, for example
INVALID_COORDINATE, UNSUPPORTED_CRS, UNSUPPORTED_GRID, UNKNOWN_VERTICAL_UNIT,
UNKNOWN_VERTICAL_DATUM, SOURCE_HASH_MISMATCH, FRAME_NOT_PRODUCT_VERIFIED,
INCOMPATIBLE_FRAME, MISALIGNED_QUALITY_GRID and INVALID_DEM_OBSERVER. Invalid
declaration models also raise Pydantic validation errors. Missing files and
window/budget failures remain explicit errors; they never produce valid heights.
Sample status, coverage status, quality evidence, frame evidence and the disabled
operation-analysis readiness are separate concepts.

## Coverage and resource limits

`dem.coverage` counts pixel centres within a surface-geodesic disk on the
declared sphere, including raster-exterior samples in the denominator. Bounds,
valid heights, internal missing area and external area remain separate. The
unweighted pixel count estimates area; it is not an exact polygon intersection.
COMPLETE_SAMPLED_DISK describes finite sampled cells in a bounded disk only,
not full scientific accuracy, a complete terrain horizon or operational readiness.

The enclosing projected square uses a conservative stereographic scale bound:
`radius * max(1,k0) * sec(theta_max/2)^2`, where theta_max is the maximum angular
distance from the south pole over the surface disk. This bounds the projected
length of each shortest radial geodesic; one pixel is added on each side before
streaming. The disk must remain in the southern hemisphere and radius <=5000 m.
The original grid is preserved; no resampling is performed.

| CR1 radius | Raster bounds | Valid heights | Status |
| --- | --- | --- | --- |
| 1 km | 100.00% | 98.71% | BOUNDS_COMPLETE_DATA_PARTIAL |
| 3 km | 83.77% | 80.30% | PARTIAL_RASTER_COVERAGE |
| 5 km | 31.83% | 29.85% | COVERAGE_INSUFFICIENT_FOR_FULL_5KM |

These are coverage diagnostics, not coordinate optimization. No 3/5 km full
regional optimizer runs. A 1 km bounds-complete result is not 100% valid data.

Defaults: 30 million total enclosing-square samples; 131072 samples/chunk;
conservative 128 bytes/chunk sample within the existing 64 MiB working budget;
16 MiB GDAL cache. Existing decoded-block and per-read pixel guards still apply.
Too-fine/large data requests fail before allocating a large mesh. Total work
remains proportional to the enclosing disk square, including exterior samples.
The source file is streamed once for hashing. Library/cache overhead means these
guards are not an absolute RSS or elapsed-time guarantee.

## Future incomplete ray evidence (model only)

`RayCoverageEvidence` carries UNKNOWN or INCOMPLETE coverage and a separately
nullable partial maximum obstruction angle. UNKNOWN cannot contain a computed
angle. An INCOMPLETE result may retain genuinely calculated partial information,
but `unobstructed_visibility_confirmed` is always false. No tracing populates
this model in Command 04. Missing terrain is never assumed flat or replaced
with the sphere. The sphere is geometric reference, not unknown remote terrain.

## Local use

From the repository root in the existing Python 3.12 data/test environment:

```sh
export PYTHONPATH="$PWD/backend"
python -m data_pipeline.dem_cli inspect --path /data/NAC_DTM_ESALL_CR1.TIF --label /data/NAC_DTM_ESALL_CR1.LBL
python -m data_pipeline.dem_cli sample --path /data/NAC_DTM_ESALL_CR1.TIF --label /data/NAC_DTM_ESALL_CR1.LBL --latitude -89.468 --longitude 222.6 --allow-unverified-registration
python -m data_pipeline.dem_cli coverage --path /data/NAC_DTM_ESALL_CR1.TIF --label /data/NAC_DTM_ESALL_CR1.LBL --latitude -89.468 --longitude 222.6 --radii-m 1000 3000 5000 --allow-unverified-registration
```

Optional `--output /data/results/new.json` refuses overwrite. Data and local
reports stay outside Git. No new dependencies are needed. Full validation
commands and the real/synthetic evidence distinction are in `DEM_VALIDATION.md`.
