# NASA color texture — verified local asset

## Current file, 2026-11-14 (Command 03.1)

The user supplied `lunar-nasa-texture.zip`, containing exactly one
`lroc_color_2k.jpg`. Its original bytes were copied without resizing, conversion
or recompression into this directory.

| Check | Result |
| --- | --- |
| File | lroc_color_2k.jpg |
| Size | 457942 bytes |
| Format | JPEG; magic FF D8 FF; full Pillow decode passed |
| Dimensions | 2048 × 1024 |
| SHA-256, archive member and copied file | f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170 |

The checksum matches the **user-provided file checksum**. It is not an
independently published or downloaded NASA-server checksum. Archive member and
copied file are byte-for-byte identical. Browser HTTP response bytes are tested
against the same size and hash; browser decoding and real WebGL texture upload
are checked separately.

Official source identified by the user: https://svs.gsfc.nasa.gov/4720/

Official 2K URL identified by the user:
https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_2k.jpg

Credit: **Imagery: NASA Scientific Visualization Studio / Lunar Reconnaissance
Orbiter.** No NASA logo or endorsement is implied.

## Runtime and orientation

The application serves this JPEG locally through
`${import.meta.env.BASE_URL}assets/moon/lroc_color_2k.jpg`; no remote NASA texture
request is required. A loading label precedes success; a missing or failed image
retains the neutral sphere and explicit unavailable-texture message.

The local image is treated as a 0°-centred equirectangular map: north at the top,
east increasing to the right. Actual sphere UV tests cover cardinal axes, north
and south and both ±180° seam copies. Browser screenshots and raycast selections
qualitatively cross-check Copernicus (north-west), Tycho (south) and Mare Crisium
(north-east) against recognizable features. East/west and far-side seam views
are recorded too. This is visual orientation review, not an independent
high-precision lunar cartographic registration or a NASA-server authenticity
check. Numeric picking precision is not imagery/terrain accuracy.

## Historical network blocker and remaining scientific limits

Before the local upload, requests to the official source, JPEG and NASA usage
page returned proxy CONNECT 403. No image bytes were obtained then. During
Command 03.1 no attempt was made to resolve or bypass that network policy.
Current official page text, product date/version and detailed usage notes were
not independently rechecked; source provenance is supplied by the user.

This color map is visual imagery, not LOLA elevation, current illumination,
visibility or a certified landing surface. Polar image gaps may contain
supplementary imagery, as described in the task's source notes. Do not infer
heights, solar visibility or terrain fidelity from color or photographic shadows.
