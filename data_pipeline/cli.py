"""Run from repo root: PYTHONPATH=backend python -m data_pipeline.cli --help."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse

from rasterio.windows import Window

from app.data.manifest import Manifest
from app.data.raster import Limits, coverage, export_window, metadata, projected_window, read_window


def probe_range(url):
    if urlparse(url).scheme != "https" or urlparse(url).hostname not in {"pgda.gsfc.nasa.gov", "naif.jpl.nasa.gov"}:
        raise ValueError("Only explicit official NASA HTTPS hosts are allowed")
    request = Request(url, headers={"Range": "bytes=0-0", "Accept-Encoding": "identity",
                                    "User-Agent": "24and28-Lunar-Data-Preparation/0.1"})
    with urlopen(request, timeout=15) as response:
        if urlparse(response.url).hostname != urlparse(url).hostname:
            raise ValueError("Unexpected redirected host")
        status = response.status
        content_range = response.headers.get("Content-Range")
        # Never consume a full response if the server ignores Range.
        supported = status == 206 and bool(content_range and content_range.startswith("bytes 0-0/"))
        if supported:
            response.read(1)
        return {"range_supported": supported, "status": status, "content_range": content_range,
                "body_bytes_read": 1 if supported else 0, "science_ready": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["manifest", "inspect", "coverage", "window", "cutout", "probe-range"])
    parser.add_argument("--manifest", default="data_pipeline/manifests/lola.json")
    parser.add_argument("--product-id")
    parser.add_argument("--path")
    parser.add_argument("--url")
    parser.add_argument("--latitude", type=float, default=-89.468)
    parser.add_argument("--longitude", type=float, default=222.6)
    parser.add_argument("--xy", nargs=2, type=float)
    parser.add_argument("--radius-m", type=float)
    parser.add_argument("--window", nargs=4, type=int, metavar=("COL", "ROW", "WIDTH", "HEIGHT"))
    parser.add_argument("--output")
    parser.add_argument("--max-pixels", type=int, default=1_000_000)
    parser.add_argument("--max-working-bytes", type=int, default=64*1024*1024)
    args = parser.parse_args()
    try:
        if args.command == "probe-range":
            if not args.url:
                raise ValueError("--url required")
            result = probe_range(args.url)
        else:
            manifest = Manifest.model_validate_json(Path(args.manifest).read_text())
            if args.command == "manifest":
                result = {"products": len(manifest.products), "science_ready": False}
            else:
                if not args.path:
                    raise ValueError("--path required; no implicit network access")
                if args.command == "inspect":
                    result = metadata(args.path)
                else:
                    product = next((p for p in manifest.products if p.id == args.product_id), None)
                    if product is None:
                        raise ValueError("--product-id must identify a manifest product")
                    if args.command == "coverage":
                        result = coverage(args.path, product, args.latitude, args.longitude)
                    else:
                        if args.window:
                            window = Window(*args.window)
                        elif args.xy and args.radius_m:
                            window = projected_window(args.path, *args.xy, args.radius_m)
                        else:
                            raise ValueError("Supply --window or projected --xy and --radius-m")
                        limits = Limits(args.max_pixels, args.max_working_bytes)
                        if args.command == "cutout":
                            if not args.output:
                                raise ValueError("--output required")
                            result = export_window(args.path, product, window, args.output, limits)
                        else:
                            _, result = read_window(args.path, product, window, limits)
        print(json.dumps(result, indent=2, allow_nan=False))
    except Exception as exc:
        parser.exit(2, f"{type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
