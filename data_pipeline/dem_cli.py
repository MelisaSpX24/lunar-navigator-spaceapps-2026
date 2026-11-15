"""Command 04 local LROC inspection, containing-cell sample and disk coverage."""
import argparse
import json
from pathlib import Path

from app.data.dem import CoverageLimits, open_dem
from app.data.raster import Limits, metadata
from app.models.analysis import Coordinates
from data_pipeline.lroc import inspect_lroc_label


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inspect", "sample", "coverage"])
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--label", type=Path, required=True)
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--longitude", type=float)
    parser.add_argument("--radii-m", type=float, nargs="+", default=[1000, 3000, 5000])
    parser.add_argument("--allow-unverified-registration", action="store_true")
    parser.add_argument("--max-total-pixels", type=int, default=30_000_000)
    parser.add_argument("--max-working-bytes", type=int, default=64*1024*1024)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        reference = inspect_lroc_label(args.path, args.label)
        with open_dem(args.path, reference, Limits(max_working_bytes=args.max_working_bytes)) as dem:
            if args.command == "inspect":
                result = {"reference": reference.model_dump(mode="json"),
                          "raster": metadata(args.path), "science_ready": False}
            else:
                if args.latitude is None or args.longitude is None:
                    raise ValueError("Explicit --latitude and east --longitude required")
                location = Coordinates(latitude_deg=args.latitude, longitude_deg_east=args.longitude)
                options = {"allow_unverified_registration": args.allow_unverified_registration}
                if args.command == "sample":
                    result = dem.sample(location, **options).model_dump(mode="json")
                else:
                    reports = [dem.coverage(location, radius, budget=CoverageLimits(args.max_total_pixels), **options)
                               for radius in args.radii_m]
                    result = {"coverage": [r.model_dump(mode="json") | r.fractions() for r in reports],
                              "science_ready": False}
        text = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output:
            with args.output.open("x") as stream:
                stream.write(text)
        else:
            print(text, end="")
    except Exception as exc:
        parser.exit(2, f"{type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
