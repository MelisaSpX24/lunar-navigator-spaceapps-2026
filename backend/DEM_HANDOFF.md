# DEM to horizon input boundary

Update: Command 04.5 provides the virtual multi-resolution interface in
`app.data.fusion`. See `DEM_FUSION_VALIDATION.md` and its evidence JSON. Site01
and Product90 80MPP are genuine validated local inputs; 20MPP remains absent.
Use `TerrainRequest` and explicit registration policy. Strict policy rejects
these unverified absolute registrations; prototype policy preserves limitations.
Use `iter_samples` for bounded far-terrain reads. UNKNOWN, source conflicts,
resolution changes and every source attempt must remain visible to future rays.
Command 05 now implements sampled terrain horizons; see HORIZON.md and
HORIZON_VALIDATION.md. No visibility or operation decisions are implemented.

Command 04 provides DEM access; Command 05 consumes it through
TerrainHorizonEngine. Complete scheduled rays, partial maxima and UNKNOWN
are separate. Exact-azimuth lookup is available to Command 06. This does not
establish end-to-end scientific readiness.

1. Open immutable local data with `open_dem(path, reference, Limits(...))`.
   Keep family, provider, version, hashes, actual CRS and vertical/frame evidence.
   Mathematical CRS compatibility is not product-specific SPICE registration.
2. Request `dem.sample(Coordinates(...), allow_unverified_registration=True)` only
   under the documented prototype assumption. Inspect status and reason codes.
   NODATA/outside samples cannot become observers. Use `prepare_observer` to
   separate surface/device height and retain the complete evidence envelope.
3. Source cell centres and source coordinates are available through `dem.grid`.
   `dem.read_elevation_window(Window(...))` returns a bounded masked array and
   evidence. Unknown cells remain masked, never replaced with a sphere or zero.
4. `dem.coverage` reports whole-disk bounds/valid/missing fractions, quality status,
   frame status and the approximation method. High coverage is not accuracy,
   confidence, a terrain horizon or operational suitability.
5. Associated quality layers use `QualityLayer`, `read_quality_window` and
   `sample_quality_layers`. Require explicit association and exact grid equality;
   do not use raw corresponding indices on a different grid. No implicit
   resampling, cross-family registration, confidence score or hazard score exists.
6. `RayCoverageEvidence` is a result envelope only. Future rays with unknown
   terrain must remain UNKNOWN/INCOMPLETE; preserve a calculated partial maximum
   separately. Partial known obstacles cannot prove unobstructed visibility.

## Near/far data requirement

The local LROC CR1 raster covers roughly 5 x 5 km. It provides only about 29.85%
valid height coverage over a 5 km-radius disk. It is insufficient for a complete
far terrain horizon, even where the 1 km disk is 98.71% valid.

Wide-area input **LDEM_80S_80MPP_ADJ.TIF**, PGDA Product90, is available and
validated through real integration tests. It is selected outside valid Site01
coverage. Its 80 m cells require an explicit sampling/convergence assessment for
future horizon rays. Do not substitute this product for the absent 20MPP file.

Before combining near LROC and far LOLA, inspect each file's real CRS, sphere,
height unit/datum, registration evidence, masks, resolution and source identity.
Equal nominal spheres are insufficient evidence of matching geodetic alignment.
Do not apply undocumented vertical offsets or relabel a generic lunar datum as
product-verified DE421. The virtual selector records containing-cell methods and source contributors.
Resampling/mosaicking is not implemented; no implicit correction is applied.
Keep unknown seams/terrain unknown; sphere geometry is not distant terrain.

Open scientific work: product-specific registration/error evidence, independent
Horizons convention matching, near/far seam effects, ray sampling/convergence and eventual
end-to-end terrain visibility validation. API SCIENCE_ENGINE_NOT_READY remains.


README evidence update: CR1's uploaded product README documents LOLA control
(~450 orbit tracks) and a reported 0.5 m DTM-to-LOLA elevation RMS. This is not
an independent absolute error bound; do not populate observer/DEM error fields
from it. The explicit target-frame realization and independent check-point
validation remain absent. See DEM_FUSION_VALIDATION.md and its line-cited
addendum. Strict/prototype policies and readiness are unchanged.

Command 10 update: Product90 20 m is physically available and rechecked against the user-manifest SHA-256; it is not independently NASA-checksummed and is not the default. See SCIENTIFIC_VALIDATION_COMMAND_10.md. Historical absence statements above describe earlier tasks.
