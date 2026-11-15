# Third-party attributions

Apache-2.0 applies only to TEAM 24&28's original code. All other materials retain
their respective rights and terms. No NASA sponsorship or endorsement is implied.

## Scientific sources

- NASA/JPL NAIF SPICE: DE421 planetary ephemeris, lunar orientation/frame kernels,
  leap seconds and planetary constants. https://naif.jpl.nasa.gov/naif/
  Use guidance: https://naif.jpl.nasa.gov/naif/rules.html
- NASA GSFC / LRO LOLA: PGDA Product 78 Site01 5 m surface and inspected error/count
  layers; Product 90 default wider-area 80 m DEM. Credit Michael K. Barker and the
  LRO LOLA product teams. https://pgda.gsfc.nasa.gov/products/78 and
  https://pgda.gsfc.nasa.gov/products/90
- NASA/JPL Horizons: diagnostic reference comparisons, not a passed equivalent
  validation. https://ssd.jpl.nasa.gov/horizons/
- USGS/IAU Gazetteer and other official references are identified in the site
  catalog and its evidence documents. Source coordinates are not automatically
  verified backend analysis coordinates.

No SPICE kernel or DEM raster binary is redistributed. Recorded JSON consists of
team-produced derived prototype outputs. Hashes establish recorded byte identity,
not independent NASA authenticity or geodetic certification.

## Lunar imagery and presentation

Imagery: NASA Scientific Visualization Studio / Lunar Reconnaissance Orbiter;
CGI Moon Kit, visualization by Ernie Wright.
https://svs.gsfc.nasa.gov/4720/ · https://svs.gsfc.nasa.gov/help/

The local lroc_color_2k.jpg was supplied by the team and retained without
recompression. It is visual imagery, not numerical terrain or current illumination.
Its user-supplied checksum is not an independently published NASA checksum.
Preserve any source-specific third-party restrictions; a NASA host does not
transfer third-party ownership to this project. The final automated source-page
recheck encountered tunnel 403; historical attribution records remain documented.

The seven-slide PDF contains actual application screenshots and team-created
explanatory diagrams. DejaVu Sans font programs retain the Bitstream Vera/DejaVu
terms: [complete font notice](licenses/DEJAVU_FONT_LICENSE.txt). Helvetica is a PDF
base-font reference, not an included font binary. No generative lunar imagery is
represented as measured NASA terrain.

## Software

React, React DOM, React Router, Three.js and React Three Fiber declare MIT licenses.
Vite/Vitest declare MIT; TypeScript/Playwright declare Apache-2.0. The frontend
lockfile also records BSD, ISC, 0BSD, BlueOak and MPL-2.0 dependencies, including
optional/development packages. These retain their own obligations; they are not
relicensed as team code.

Backend dependencies include FastAPI/Pydantic/SpiceyPy/pyproj (MIT), Uvicorn and
Rasterio (BSD-3-Clause), NumPy (its declared composite notices) and Certifi
(MPL-2.0). Linked native CSPICE, GDAL/PROJ and numerical libraries have separate
upstream terms. No dependency binaries, node_modules, Python environment, wheels
or native libraries are distributed here. Preserve exact upstream notices if
redistributing installed/bundled dependencies. The installed React Three Fiber
package declares MIT but lacked a top-level license file during review; obtain
its full upstream notice before redistributing a compiled bundle.
