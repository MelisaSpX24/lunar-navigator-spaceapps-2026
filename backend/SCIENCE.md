# Command 03 — surface-observer SPICE astronomy

Current state: Command 03.5 closed as PROTOTYPE_DATA_GATE_PASSED_WITH_LIMITATIONS
after user-supplied real kernels and a labelled LROC CR1 DTM were tested.
See `DEM.md`, `DEM_VALIDATION.md` and
`../data_pipeline/evidence/command-03-5.json`. The old access record below
describes the earlier network-blocked run, not current local file availability.

Astronomy module scope: Sun/Earth centre direction and distance. No DEM sampling, terrain horizon,
disk fraction, rise/set, visibility windows, profile evaluation or optimizers.
Existing FastAPI analyses still return SCIENCE_ENGINE_NOT_READY and null score;
health readiness is unchanged. No frontend or shared contracts are edited.

## Coordinates and conventions

`app.science.geometry.Observer` requires planetocentric latitude (strictly between
-90 and 90), east longitude [0,360), surface elevation in metres and a separate
nonnegative device height. Frame is MOON_ME_DE421. Exact poles are rejected.
The radius is explicitly **1737400 m**, a spherical reference assumption matching
the intended LOLA reference model, not a verified datum for any actual raster.
The surface elevation defaults to no value: callers must supply it explicitly.
`height_datum=ASSUMED_REFERENCE_SPHERE` is the default; declaring VERIFIED is a
caller assertion that requires external data evidence and is not verified here.

Cartesian position uses `(radius + surface elevation + device height) / 1000`,
giving SPICE kilometres. Local Up is radial; North/East form an orthonormal
right-handed ENU basis. Up is not the sloped terrain normal or true gravity plumb.
The output elevation is relative to the local reference tangent plane, without
terrain or horizon dip. North=0°, East=90°, clockwise azimuth [0,360). At zenith
or nadir azimuth is undefined and returned as null. Negative elevation is retained.

## Kernel package and pool ownership

Command 02's candidate manifest remains page-level documentation, not proof that
files are present or READY. Provide exactly these files, obtained from the
official URLs in `data_pipeline/manifests/kernels.json`:

| File | Role |
| --- | --- |
| de421.bsp | Sun/Earth/Moon ephemerides and SPK chains |
| moon_pa_de421_1900-2050.bpc | DE421 principal-axis orientation |
| moon_080317.tf | PA-to-ME DE421 frame definitions |
| naif0012.tls | UTC/ET conversion and leap seconds |
| pck00011.tpc | Reference shape constants; sphere compatibility checked on load |

Official frame documentation:
https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_080317.tf

MOON_ME_DE421 and MOON_PA_DE421 differ by a defined rotation; they cannot be
substituted without conversion. IAU_MOON is not the selected high-precision frame.
DE440 orientation/frame files are not part of this package. Exact filename-set,
hash, SPICE file-type, frame-ID, PCK frame and sphere checks are performed.
Filename and locally pinned hash do **not** prove official origin or prevent an
operator from deliberately mislabelling an SPK. Preserve trusted acquisition
records; do not treat a self-generated index as NASA authentication.

`KernelSession` owns a process-wide reentrant lock for its entire lifetime,
refuses an already populated kernel pool, and clears only its own pool after
success or failure. All module SPICE calls are made inside that session/lock.
Use a dedicated process; unrelated SPICE callers must not bypass this ownership
protocol. No per-request uncontrolled parallel furnsh/kclear. Do not share a
session across worker processes. The present module never sets scientific READY.

SPK object coverage and binary PCK orientation intervals are read from actual
files, not inferred from filenames. Centre-epoch interval checks are necessary,
not sufficient: complete chains and light-time-shifted target epochs are checked
by SPICE during the calculation. Text FK/PCK/LSK files have no equivalent universal
time-coverage interval; LSK future leap-second assumptions remain a limitation.

## Time and target calculation

UTC strings require ISO 8601 with Z or +00:00; naive dates, other offsets and bad
dates are rejected. Inputs use Python datetime resolution; leap-second labels
such as 23:59:60 are unsupported and rejected. UTC is converted with str2et; ET
is seconds past J2000 TDB. Results use et2utc at six fractional digits, a formatting
precision and **not** a scientific accuracy claim.

`spkcpo(target, et, MOON_ME_DE421, OBSERVER, correction, surface_position,
MOON, MOON_ME_DE421)` includes the actual observer position and lunar orientation.
Official method reference:
https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkcpo_c.html

Default correction NONE means simultaneous geometric centre vectors. Optional
LT+S means reception light-time and stellar-aberration correction, not a full
Horizons apparent-position model including all relativistic terms. Never compare
NONE vectors directly to Horizons apparent AZ/EL and call a difference an error.
The returned target distance uses the same correction as its direction. Frame
orientation is evaluated at the observer epoch. No atmospheric refraction.

`calculate(session, observer, utc, correction)` returns a backend-local typed
GeometryResult with UTC, observer/datum, frame, correction, Sun/Earth azimuth,
elevation, distance_km, filename/hash kernel identities and limitations. Call it
repeatedly for selected epochs; no long-window visibility engine is introduced.
Execution errors raise ScienceError with a reason code, not zero-valued geometry.
`geometry_status=COMPUTED` means that the call completed; `science_ready=false`
preserves the distinction from independently validated end-to-end science.

## Local setup and CLI

Install Python 3.12 dependencies with `pip install -e 'backend[science,data,test]'`
or use the tested snapshot in backend/requirements-tested.txt. Verified wrapper:
SpiceyPy 8.4.0. Kernel files belong outside Git (for example ~/lunar-data/kernels).
Never commit kernels or derived local indexes containing filesystem paths.

From the repository root, in the activated environment:

```sh
export PYTHONPATH="$PWD/backend"
python -m data_pipeline.spice_cli index --directory ~/lunar-data/kernels --output /tmp/kernel-index.json
python -m data_pipeline.spice_cli inspect --directory ~/lunar-data/kernels --index /tmp/kernel-index.json
python -m data_pipeline.spice_cli geometry --directory ~/lunar-data/kernels --index /tmp/kernel-index.json --latitude -89.468 --longitude 222.6 --surface-elevation-m 0 --device-height-m 1 --utc 2026-11-20T08:00:00Z
```

The last command specifies an **assumed zero reference-sphere surface elevation**;
it is not CR1's measured terrain elevation. Do not publish it as a DEM-based
result. `index` reads and hashes local files only; no command downloads files.
`inspect` returns actual coverage in ET and UTC only after successful loading.
No output file is overwritten. Independently review acquisition provenance.

Direct HEAD access to the small official naif0012.tls URL failed with workspace
proxy CONNECT 403. No size could be verified and no kernel was downloaded.
Use the official manifest links on an authorized local/WSL environment; verify
file size and available storage before downloading. The binary SPK is larger
than the text kernels; nothing is fetched automatically. No alternate-source or
network-policy bypass was attempted.

## Validation and limits

Run `python -m pytest -q backend/tests` and `python -m pip check`.
Synthetic tests validate units, axes, compass angles, angle wrap, parallax,
invalid input, kernel handling and SPKCPO wiring. A simplified synthetic LSK
tests actual CSPICE time calls; it is not an official leap-second validation.
Mocked lifecycle and coverage tests do not prove real NASA kernel loading.

Optional real tests require both NASA_KERNEL_DIR and NASA_KERNEL_INDEX. They
exercise actual geometry, physical distance ranges, surface/centre differences,
multi-epoch Earth motion, coverage rejection and comparison with NAIF AZLCPO
using identical NONE convention. AZLCPO comparison is a consistency test of the
same toolkit, not independent observational validation. Missing files cause
explicit SKIPPED results. Wrong provided files cause test failure, not a skip.

Historical Command 03 run: real files were absent at that time. Subsequent
Command 03.5 real kernels passed the two integration tests. LROC label-backed
metre heights above a 1737400 m sphere and the CR1 cell value are now available.
Horizons comparison, product-specific horizontal registration/error evidence and
LOLA integration remain unverified. Prototype Command 04 is authorized with those
limitations visible; neither its data gate nor kernel tests establish API readiness.
