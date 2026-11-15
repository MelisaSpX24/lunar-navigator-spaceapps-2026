# Command 10 — uploaded JPL Horizons reference validation

The two user-supplied JSON files were read without modification. Both contain NASA/JPL Horizons API signature 1.2, a genuine observer ephemeris table bounded by one $$SOE/$$EOE pair and quantity 4 airless apparent target-center azimuth/elevation. Error responses, missing metadata, unavailable values and malformed tables are rejected. Raw private attachments are not committed. Derived values, input hashes and comparison evidence are in data_pipeline/evidence/command-10-horizons-reference.json.

## Reference configuration

| Property | Parsed value |
|---|---|
| Targets | Sun 10; Earth 399 |
| Center | Moon 301; user-defined site |
| Coordinates | East longitude 222.6°, latitude −89.468°, geodetic spherical surface |
| Reference radii | 1737.4 km on all three axes |
| Altitude | 1.94414 km (1944.14 m); printed half-step 0.005 m |
| Center orientation | MEAN_ME, high precision |
| Ephemeris | DE441 |
| Dates | 2026-11-20 08:00 through 2026-11-24 08:00 UTC |
| Step / rows | 360 minutes / 17 per target |
| Angles | North 0°, east 90°, clockwise; local reference-surface zenith |
| Correction | Airless apparent: light time, stellar aberration and gravitational light deflection |

On a sphere, geodetic and planetocentric latitude coincide mathematically. This proves the coordinate construction convention, not equivalence of the MEAN_ME realization in DE441 and backend MOON_ME_DE421. The actual backend DEM observer has surface elevation 1942.1014404296875 m plus a 1 m device, total 1943.1014404296875 m. Its altitude differs from the reference by 1.0385595703125 m, beyond printed rounding. The operation observer is never changed. A separate REFERENCE_ALIGNED_DIAGNOSTIC uses exactly 1944.14 m radial altitude and is not an operational DEM result.

The original query URL/parameter string and retrieval timestamp were not included in the files. They remain null rather than being reconstructed and presented as original metadata. The API origin URL and observed query semantics are recorded. A response signature plus user transfer is not cryptographic publisher authentication.

## Numerical diagnostics, not equivalent-model certification

Fresh SPICE calculations used the five pinned DE421 kernels, both NONE and LT+S, at all 17 exact shared UTCs. No nearest-time matching or interpolation was used. November 23 17:26:15, the 16:15–16:26:15 bracket and November 27 02:00 have no exact reference rows and are explicitly excluded.

Signed azimuth residual is `(backend - reference + 180) % 360 - 180`. Before computing residuals, the equivalent-configuration tolerance was fixed at 0.000001°: six printed decimals contribute at most 0.0000005° quantization. This tolerance cannot override mismatched model metadata and was not widened after seeing results.

Reference-altitude-aligned LT+S diagnostics:

| Angle | Maximum absolute residual (degrees) | RMS residual (degrees) |
|---|---:|---:|
| Sun azimuth | 0.000003284645 | 0.000002871540 |
| Sun elevation | 0.000010926081 | 0.000007135269 |
| Earth azimuth | 0.000004122761 | 0.000003497776 |
| Earth elevation | 0.000011139784 | 0.000010016780 |

For NONE, maximum Sun/Earth azimuth residuals are approximately 0.005967632° and 0.000205952°. This demonstrates why apparent angles are not equated with NONE. LT+S still omits Horizons gravitational bending; DE441 and MEAN_ME realization also differ. The altitude-aligned diagnostic does not remove those differences.

Result: **CONFIGURATION_MISMATCH**, with 17 numerically compared UTCs, zero certified equivalent-configuration matches. The acceptance-matrix gate is PARTIAL: useful numerical software comparison exists, but an equivalent reference PASS and independent observational validation do not. DEM absolute registration remains UNVERIFIED separately.

## Reproduction

With the normal backend environment and the original private attachment paths:

```
python -m data_pipeline.horizons_reference_validation --sun /private/horizons_sun_cr1.json --earth /private/horizons_earth_cr1.json --output /new/horizons-validation.json
```

Optional --observer supplies an explicit Observer JSON; --source-metadata records known provenance; --kernel-dir and --kernel-index otherwise use NASA_KERNEL_DIR/NASA_KERNEL_INDEX. Outputs refuse overwrite and contain no NaN/Infinity. Default observer comes from the existing hash-pinned real DEM window artifact; this diagnostic calculates new SPICE angles without repeating terrain visibility work.
