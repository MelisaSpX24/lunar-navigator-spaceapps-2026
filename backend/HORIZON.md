# Sampled lunar terrain horizons

`app.science.horizon.TerrainHorizonEngine` uses the existing
`MultiResolutionDem` and backend-local models in `horizon_models.py`. The
shared analysis/API contracts are unchanged. Sun/Earth disks, times, operations
and scores are outside this module. Scientific API readiness remains false.

## Geometry and observer

R = 1737400 m; planetocentric latitude, east longitude and MOON_ME_DE421 target
convention. North/east/south/west are 0/90/180/270 degrees. Azimuth increases
clockwise. Exact poles follow existing coordinate rejection. `Geod(a=R,b=R)`
advances along a great circle; projected straight lines are not used.

For distance s, alpha=s/R, observer radius R+h_surface+h_device and terrain
radius R+h_terrain, elevation is atan2(r_t*cos(alpha)-r_obs,r_t*sin(alpha)).
Implementation uses the exact identity cos(alpha)-1=-2*sin(alpha/2)^2 to avoid
short-distance cancellation. Output is degrees above the local reference
sphere tangent, not the sloping terrain normal. Negative angles remain negative.
Geometry is tested against existing Cartesian/ENU helpers, including their km
conversion. Nonfinite inputs, nonpositive physical radii and negative device
heights fail. The observer comes from a valid DEM sample; `prepare_observer`
preserves surface/device separation and reference evidence. Invalid observer
evidence gives UNKNOWN rays without invented surface height.

## Policy and sampling

Registration remains STRICT by default. Actual prototype studies must explicitly
select PROTOTYPE. Source selection and conflict REPORT/REJECT are delegated to
fusion. LROC is off unless explicitly enabled. Rejected terrain makes a ray
incomplete; REPORT disagreements remain counted and warned. The default 10 m
conflict threshold is an engineering policy, not a NASA accuracy bound.

Sampling starts at start_m (default 5 m); the next distance increment is the
last selected cell resolution times resolution_factor, clipped to configured
min/max step. Missing samples use the requested resolution for the next step.
The final requested distance is always sampled. No fixed near/far distance is
used to select sources. Original containing cells and their masks are retained.

This is point sampling, not complete crossed-cell traversal. A narrow ridge,
NoData island, source boundary or an obstacle between azimuths may be missed.
Returning into a finer raster may initially retain the previous coarse step.
The interval between the observer and start_m is unsampled. Resolution-factor
and phase sensitivity must be assessed; smaller steps do not improve intrinsic
DEM accuracy. No raster or gap is smoothed or replaced with zero.

Each ray reports COMPLETE_SAMPLED_RANGE, INCOMPLETE or UNKNOWN. Only complete
rays expose horizon_elevation_deg. Incomplete rays expose only
partial_max_obstruction_deg; all-unknown rays have no angle/obstruction.
Complete refers to scheduled samples, not continuous terrain or beyond-range
visibility. Range convergence remains NOT_ESTABLISHED on individual runs;
validation comparisons are separate evidence rather than automatic certification.

## Profiles, metadata and reuse

FULL_HORIZON samples [0,360) without duplicate 360. SECTOR_HORIZON includes
both endpoints and supports crossing zero. Results are sorted by azimuth.
RAYS accepts unique explicit directions. All modes share the same ray kernel.
`result.horizon_at_azimuth(a)` returns the exact sampled ray, normalizes 360 to
0, and returns None for unsampled directions. It performs no interpolation.
Callers must check ray completeness and retain frame/quality limitations.

The obstruction contains its geodesic distance, query coordinate, angle and
complete TerrainSample (selected cell, elevation, identity/hash, quality,
registration and alternative-source attempts). Ray summaries retain source
counts, resolutions, transitions, invalid/conflict/outside/read-error counts,
reason counts, quality status counts and registration warnings. Unknown
fractions use attempted ray samples, not area. Invalid observers have no
attempted ray samples and therefore null unknown_fraction.

Result identity hashes the algorithm version, request including budgets/policy,
observer height and source, all supplied DEM reference metadata, actual CRS and
affines, auxiliary hashes and quality identities. No UTC is included. There is
no persistent result cache: identical requests may reuse the same identity;
callers must not substitute a different DEM, observer height or policy. Hashing
identifies data, not publisher authenticity. Original files are immutable during
a session. Synthesized fixture sources carry SYNTHETIC_TEST; real data CLI
sources are pinned and carry REAL_NASA_PROTOTYPE. Mixed sources are labeled.

## Budgets and reproduction

Ray and total sample budgets fail explicitly before or during calculation.
Partial work from a budget exception is not returned as a completed result.
Configured range is bounded at 150 km; this is a work limit, not a physical
proof of no farther obstacles. Existing DEM window/decode/cache guards and
5 km local coverage limit remain. Only per-ray aggregates and the strongest
obstruction are retained; samples stream one at a time. Result size also scales
with azimuth count (bounded by configuration). Quality-layer datasets reuse checked metadata and open handles within the
immutable DEM session (at most eight handles, closed at session exit). Window
and decode limits remain checked on every read; metadata changes get a new key. No timing or RAM guarantee is made.

Set NASA_LOLA_VALIDATION_DIR to the four original reconstructed LOLA files.
Optional LROC requires NASA_LROC_CR1_DEM and NASA_LROC_CR1_LABEL. No downloads.
Create a JSON HorizonRequest with location and explicit policy; then run:

```sh
PYTHONPATH=backend:. python -m data_pipeline.horizon_cli --request request.json --output result.json
PYTHONPATH=backend:. python -m data_pipeline.horizon_validation evidence.json
```

CLI input is bounded to 64 KiB and existing output files are never overwritten.
Output includes identity, provenance, missing rays, settings and measured cost.
Original NASA binaries are kept outside Git. See HORIZON_VALIDATION.md for
actual runs and remaining registration/sampling/range limitations.
