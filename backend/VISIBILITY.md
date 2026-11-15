# Sampled Sun and Earth disk visibility

Backend-local implementation; the shared API still returns SCIENCE_ENGINE_NOT_READY
and science_ready=false. Defaults remain STRICT registration and Site01 5 m plus
Product90 80 m. PROTOTYPE must be explicitly requested. No operations, power,
RF budgets, rise/set roots, optimization or frontend changes are implemented.

## Mathematical model

Existing SPKCPO surface-observer geometry supplies directions and distances in
MOON_ME_DE421. Separate solar and Earth device heights are passed to both SPICE
and terrain rays. DEM containing-cell surface elevation is not a configurable
constant. No accepted observer under the requested policy raises INVALID_OBSERVER.

PCK RADII are read inside the owned KernelSession; the effective spherical radius
is the arithmetic mean of the three axes. Alpha=asin(radius_km/distance_km), using
the same NONE or LT+S centre distance. SPHERICAL_BODY_DISK_APPROXIMATION remains
explicit: Earth's oblateness and differential stellar aberration across the
apparent disk are not modeled. This is geometric silhouette area, not illuminated
Earth area or solar brightness/panel output. Missing radii fail explicitly.

Disk quadrature uses equal projected-area annuli with antipodal sample pairs and
golden-angle orientations. Orthographic coordinates x,y map to the unit sphere
as sqrt(1-x²-y²)*centre+x*basis1+y*basis2. Each of N points has weight 1/N.
The phase offset avoids placing the first antipodal pair exactly on the central
horizontal cut; the half-disk regression exercises this. Polar centre azimuths
remain null; a basis orientation is chosen internally, not published as north.

Analytic circle segments test the small-angle planar limit at radius 0.27 deg.
The N^-1/2 test envelope is a conservative numerical regression criterion, not a
rigorous error bound for arbitrary discontinuous terrain. A 101-offset sweep
reports measured maximum/RMS errors separately at 64,256,1024 points. Disk
convergence must never be called terrain accuracy or absolute registration.

## Evidence and unknown area

Every sample queries its exact azimuth through TerrainHorizonEngine and
horizon_at_azimuth; no neighbor interpolation. COMPLETE_SAMPLED_RANGE permits
comparison in the finite point-ray model. INCOMPLETE partial maxima can prove
sample blockage when sample elevation <= partial maximum; they cannot prove
visibility. Missing rays, null azimuth and exhausted budgets become UNKNOWN.

Any unknown disk weight gives state UNKNOWN and visible_fraction=null; known
visible/blocked/unknown weights and [visible,visible+unknown] bounds remain.
These are bounds on the finite sample model only. FULL, PARTIAL and NONE do not
certify unsampled disk area, narrow ridges or terrain beyond the chosen range.
Center clearance is null unless the central ray is complete. Equality is treated
as blocked; tangency has zero continuous area but finite quadrature can alias it.

## Resource and cache contract

VisibilityRequest embeds HorizonRequest (location, policies, range, sampling and
point limits), UTC, two device heights, correction, disk_samples and max_new_rays.
Defaults: 64 disk points, 132 new rays, maximum 150 km via existing horizon model.
Each new azimuth costs a real ray. N=1024 is supported mathematically but does not
promise 2050 real rays within the default budget. Request-wide terrain point and
new-ray limits apply; unsupported work is unknown, never silently interpolated.
On an interrupted ray the existing horizon engine discards partial work; reported
DEM sample counts include completed rays only (a lower bound if budget fails).
Counts describe terrain query positions, not every physical source/quality pixel
read. RSS is process peak memory, not incremental per-operation memory.

Cache is an LRU of at most 512 rays by default (hard maximum 4096), owned by one
engine borrowing immutable open DEM/kernel sessions. Namespace includes source
hashes, references, CRS/affines and auxiliary/quality identities; request keys
include location, device height, policies, sampling, range and limits. UTC is not
included. Never mutate/replace sources within a session; construct a new engine.
Closed DEM sessions are rejected. A new UTC often requires different azimuths;
only identical directions reuse evidence. No interpolation-based cache hits.

Series accepts 1..12 samples at 1..86400 second steps. Each UTC has its own bounded
ray/point budget. No transition time is inferred between samples. Source/hash
validation occurs when opening sessions, outside per-body timing. Same-height
Sun/Earth geometry is computed once and reused; Earth spice_seconds can therefore
be effectively zero. KernelSession ownership/cleanup remains unchanged.

## CLI

From the repository root with dependencies installed and external NASA paths set:

```sh
export PYTHONPATH=backend:.
# NASA_KERNEL_DIR, NASA_KERNEL_INDEX, NASA_LOLA_VALIDATION_DIR are required.
# NASA_PRODUCT90_DEM is only used with --use-20m or by the optional data test.
python -m data_pipeline.visibility_cli --request request.json --output single.json
python -m data_pipeline.visibility_cli --request request.json --output series.json --count 3 --step-seconds 3600
python -m data_pipeline.visibility_cli --request request.json --output twenty.json --use-20m
python -m data_pipeline.visibility_validation evidence.json
```

Example request (save outside the repository):

```json
{"terrain":{"location":{"latitude_deg":-89.468,"longitude_deg_east":222.6},"policy":{"registration":"PROTOTYPE","conflict":"REPORT"},"sampling":{"resolution_factor":8,"max_step_m":640}},"utc":"2026-11-20T08:00:00Z","solar_height_above_surface_m":1,"earth_height_above_surface_m":1,"correction":"NONE","disk_samples":64,"max_new_rays":132}
```

Input is limited to 64 KiB. Outputs use exclusive creation, forbid NaN/Infinity,
and never overwrite existing files. NASA files are read-only and never committed.
Scientific errors retain codes; invalid configuration fails rather than producing
fake percentages. A completed execution can contain UNKNOWN visibility.

20 m experiments use a separate fusion session with one PRODUCT90 role and the
same Site01 observer. User manifest hash matching is not independent NASA checksum
authentication. Existing vertical evidence combines PGDA unit documentation and
the LRO sphere convention; no product-specific absolute registration is promoted.
Sources: https://pgda.gsfc.nasa.gov/products/78 and /products/90;
https://naif.jpl.nasa.gov/pub/naif/generic_kernels/.

Future adapters may map BodyVisibility.direction/alpha/fraction to BodySample and
UTC samples to TimeSample, preserving unknowns; no such shared contract change
is made here. INDEPENDENT_ASTRONOMY_VALIDATION_NOT_ESTABLISHED remains in every run.

## Command 06.1 — Resource-budget completeness validation

`VisibilityEngine.preflight(request)` computes the actual SPICE disk directions
and exact cache keys before terrain work. It reports unique keys, current hits,
new-ray requirements, minimum/maximum lattice point counts and (when measured
history exists) an empirical mean-cost estimate. Minima only reject obviously
impossible budgets; an empirical estimate is not a guarantee. The maximum lattice
count is deliberately conservative and can exceed the allowed work budget.
Per-ray and per-request limits still stop execution; sources are never resampled.

Performance.accounting separates attempted_rays, completed_rays,
failed_budget_attempts, budget_rejected_rays, cache_hits/cache_misses,
cache_evictions and dem_samples. A completed ray here means completed computation,
not necessarily COMPLETE_SAMPLED_RANGE scientific evidence. Cache misses count
uncached lookups including rejected ones; legacy new_rays retains the attempted
ray meaning for compatibility. A HorizonBudgetError carries consumed ray queries,
so failed attempts consume point budget and cannot become cached evidence.
Counts are terrain positions, not every source/quality pixel read, and exclude
observer preparation queries. No budget becomes negative. Per-body unknown_directions
records actual azimuth and budget/terrain reason without replacing missing data.

The LRU default stays 512, hard maximum 4096. CLI now exposes --cache-size; 4096
accommodates the 64/256/1024 comparison without early eviction. Exact float azimuth
keys are never rounded or interpolated. Cache namespaces pin source and auxiliary
identities; session immutability remains required. UTC changes only the requested
body directions, not terrain evidence for an identical direction.

Run the genuine baseline-only experiment with existing NASA environment paths:

```sh
PYTHONPATH=backend:. python -m data_pipeline.visibility_budget_validation /tmp/budget-evidence.json
# Optional admission opt-out (reports real 1024 as resource-limited, never complete):
PYTHONPATH=backend:. python -m data_pipeline.visibility_budget_validation /tmp/budget-small.json --no-1024
```

The runner preserves the old evidence and writes a separate checkpoint/final
artifact. It runs first/repeated 64, intentionally low-budget and sufficient-budget
three-UTC series, real 256, and admits real 1024 only when measured cost estimates
fit 900 seconds / the existing point budget and observed RSS is below 1 GiB.
These time/RSS values are admission checks, not OS-enforced runtime limits; hard
ray/point/cache limits remain enforced throughout. It does not read the 20 m
comparison raster. Actual file-backed regression tests still check that source.

Fresh experiment-artifact assertions require NASA_VISIBILITY_BUDGET_EVIDENCE
pointing to this run's output; they validate source hashes and measured results,
not an invented NASA fixture. Existing integration tests also rerun live SPICE
and terrain calculations. Analytic convergence remains separate from terrain
accuracy; even complete finite-model visibility is not absolute scientific proof.
