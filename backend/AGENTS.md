# Backend development rules

- Scientific correctness takes priority over visual effects.
- Only use NASA data with recorded provenance, product version and reference metadata.
- Preserve planetocentric MOON_ME_DE421 coordinates and east-positive longitude [0, 360).
- Test explicit metre/kilometre, degree/radian and second/time-scale conversions.
- Keep DEM surface elevation separate from panel and antenna heights.
- Never conceal missing data or replace unknown results with zero, empty success or invented values.
- Geometric Earth visibility does not guarantee a radio link; solar visibility does not guarantee electrical output.
- This prototype does not certify safe landing.
- Scientific decisions and scores must not depend on frontend calculations.
- Changes to shared contracts, root configuration or shared documentation require team-lead approval.
- Work in backend/ and backend-owned tests/documentation; do not edit frontend/.
- Develop each scientific module with meaningful tests and provenance checks from its first calculation.
- Work on a separate branch and submit changes for PR review; never merge directly into main.
- Command 03 permits kernel validation and surface-observer SPICE astronomy in backend/ and data_pipeline/. Do not automatically download large datasets or implement terrain horizons, disk visibility, operation scoring or optimizers. API scientific readiness stays false pending validated end-to-end data and models.
