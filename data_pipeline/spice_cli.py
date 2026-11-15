"""Local kernel inspection and one-epoch centre geometry; no downloads."""
import argparse
import json
from pathlib import Path

from app.data.manifest import sha256_file
from app.science.astronomy import calculate, et_to_utc
from app.science.geometry import Observer
from app.science.kernels import FILES, KernelSession


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["index","inspect","geometry"])
    parser.add_argument("--directory",type=Path,required=True)
    parser.add_argument("--index",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--utc")
    parser.add_argument("--latitude",type=float)
    parser.add_argument("--longitude",type=float)
    parser.add_argument("--surface-elevation-m",type=float)
    parser.add_argument("--device-height-m",type=float,default=0)
    parser.add_argument("--correction",choices=["NONE","LT+S"],default="NONE")
    args=parser.parse_args()
    try:
        if args.command=="index":
            result={"files":[{"filename":name,"sha256":sha256_file(args.directory/name)} for name in FILES]}
        else:
            if not args.index:
                raise ValueError("--index required; hashes must be pinned explicitly")
            with KernelSession(args.directory,args.index) as session:
                if args.command=="inspect":
                    result={"kernel_records":session.records,"coverage_et":session.coverage,
                            "coverage_utc":{key:[[et_to_utc(session,a),et_to_utc(session,b)] for a,b in ranges]
                                            for key,ranges in session.coverage.items()},
                            "science_ready":False,"reference_comparison":"NOT_VERIFIED"}
                else:
                    if any(v is None for v in (args.utc,args.latitude,args.longitude,args.surface_elevation_m)):
                        raise ValueError("UTC, coordinates and explicit surface elevation required")
                    observer=Observer(latitude_deg=args.latitude,longitude_deg_east=args.longitude,
                                      surface_elevation_m=args.surface_elevation_m,device_height_m=args.device_height_m)
                    result=calculate(session,observer,args.utc,args.correction).model_dump(mode="json")
        text=json.dumps(result,indent=2,allow_nan=False)+"\n"
        if args.output:
            with args.output.open("x") as stream: stream.write(text)
        else:
            print(text,end="")
    except Exception as exc:
        parser.exit(2,f"{type(exc).__name__}: {exc}\n")


if __name__=="__main__":
    main()
