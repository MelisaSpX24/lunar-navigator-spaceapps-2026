# Command 01 validation

Executed with Python 3.12.14 in an isolated virtual environment:

- Editable package installation with test extras: successful.
- `python -m pytest -q`: **39 passed**, 1 third-party warning.
- `python -m pip check`: no broken requirements.
- Uvicorn startup and real HTTP health request: HTTP 200, server healthy,
  science/DEM/kernels not ready.
- Real HTTP POST using the README example: HTTP 503,
  `SCIENCE_ENGINE_NOT_READY`, `INCOMPLETE`, null score.
- `git diff --check`: passed.

The warning is a Starlette TestClient deprecation notice for its httpx adapter;
it does not fail the suite. Tested versions are captured in
`requirements-tested.txt`. This snapshot is not a dependency security audit.

Coverage includes coordinate bounds and pole rejection, named-site syntax,
UTC-only datetime parsing, invalid dates, strict positive durations, nonfinite
values, operation identifiers, contradictory requirements, separate observer
heights, result constraints, OpenAPI routes and absence of fabricated science.

No NASA datasets or kernels were downloaded. No astronomical, terrain, disk,
window or optimizer computations have been implemented or validated. Scientific
dependency compatibility remains deferred until the data/science command.
