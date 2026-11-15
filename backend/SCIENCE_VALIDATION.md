# Command 03 validation record

Historical record. Later real-data evidence and the Command 03.5 prototype gate
are recorded in `DEM_VALIDATION.md` and
`../data_pipeline/evidence/command-03-5.json`; absent-file statements below
describe this earlier run only.

Base: main ff443cd (merged Command 02 PR #2); Command 01 commit and Command 02
commit are present. No merge or main push was performed by this task.

Environment: Python 3.12.14, SpiceyPy 8.4.0, NumPy 2.5.4. Installed compatible
wheel in the isolated project environment; snapshot updated after installation.

Executed:

- `python -m pytest -q backend/tests`: **91 passed, 4 skipped**, one existing
  Starlette/httpx deprecation warning. The 62 prior passing tests remain passing.
- `python -m pip check`: no broken requirements.
- `git diff --check`: passed.
- CLI inspect against an absent local index: explicit FileNotFoundError, no
  synthetic geometry or READY response.
- Function signatures checked against installed SpiceyPy, including pckfrm's
  required output cell. Signature-constrained test covers that adapter.

Evidence classification:

- Pure geometry tests: synthetic observer positions/vectors, ENU orthonormality,
  metre/km units, compass convention, azimuth wrap, negative elevations,
  pole/height rejection and centre/surface parallax.
- Real CSPICE time calls: use a simplified **synthetic test LSK**, not a real
  NASA leap-second table. Round-trip and elapsed second checks passed.
- Package validation: missing/wrong package, invalid file, bad hash, load failure,
  scope rejection and pre-existing-pool preservation tests passed. Successful
  lifecycle/coverage wiring includes explicitly mocked data, not NASA verification.
- SPKCPO wiring test: mocked target vectors; validates observer/frame/correction
  arguments and result shape, not true Sun/Earth positions.
- Real NASA astronomy integration: **2 tests skipped** because NASA_KERNEL_DIR
  and NASA_KERNEL_INDEX are absent. Intended tests cover distances, NAIF AZLCPO
  consistency, multi-epoch Earth movement, parallax and coverage rejection.
- Real NASA raster integration from Command 02: **2 tests skipped**; files absent.
- Horizons / independent reference comparison: **NOT_VERIFIED**.

Direct HEAD to the official small NAIF naif0012.tls URL returned workspace proxy
CONNECT **403**. No kernel file size could be checked, no kernel was downloaded,
and no access bypass was attempted. NAIF SPKCPO and DE421 frame documentation
were inspected through the research tool; documentation access is not runtime
kernel access. No numerical NASA Sun/Earth result is claimed.

API readiness remains false. DEM datum and CR1 elevation remain unverified.
No terrain, disk fraction, rise/set, visibility-window, scoring or optimizer
module is implemented. Real kernel tests and reference matching must run before
relying on this motor for scientific decisions.
