"""Opt-in local/WSL acquisition. Default prints requests without network access."""
import argparse
from datetime import timedelta
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener

from app.models.analysis import utc_datetime

ENDPOINT = "https://ssd.jpl.nasa.gov/api/horizons.api"
TIMES = ["2026-11-20T08:00:00Z", "2026-11-20T20:00:00Z", "2026-11-27T08:00:00Z"]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def urlopen(request, timeout):
    return build_opener(NoRedirect()).open(request,timeout=timeout)


def horizons_plan():
    queries=[]
    for target in ("10", "399"):
        for timestamp in TIMES:
            start=utc_datetime(timestamp)
            params={"format":"json", "COMMAND":f"'{target}'", "OBJ_DATA":"'YES'",
                    "MAKE_EPHEM":"'YES'", "EPHEM_TYPE":"'OBSERVER'", "CENTER":"'coord@301'",
                    "COORD_TYPE":"'GEODETIC'", "SITE_COORD":"'222.6,-89.468,0.001'",
                    "START_TIME":f"'{start.strftime('%Y-%m-%d %H:%M:%S')}'",
                    "STOP_TIME":f"'{(start+timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')}'",
                    "STEP_SIZE":"'1m'", "QUANTITIES":"'4,20'", "APPARENT":"'AIRLESS'",
                    "TIME_TYPE":"'UT'", "TIME_ZONE":"'+00:00'", "RANGE_UNITS":"'KM'",
                    "CSV_FORMAT":"'YES'", "ELEV_CUT":"'-90'", "EXTRA_PREC":"'YES'"}
            queries.append({"target":target,"time_utc":timestamp,"parameters":params,
                            "url":ENDPOINT+"?"+urlencode(params)})
    return {"status":"NOT_RUN", "comparison_status":"NOT_VERIFIED", "queries":queries,
            "observer_assumption":"Zero reference-sphere terrain elevation plus 1 m device height.",
            "limitations":["Horizons apparent AZ/EL is not SPICE NONE.",
                           "Actual output header, radius, frames, ephemeris and corrections must be reviewed.",
                           "A retrieved reference alone does not validate our SPICE motor."]}


def save_bounded(url, destination, cap, user_agent):
    """No redirects, retries or overwrite. Refuse missing/oversized HEAD lengths."""
    headers={"User-Agent":user_agent,"Accept-Encoding":"identity"}
    with urlopen(Request(url,headers=headers,method="HEAD"),timeout=20) as head:
        if head.url != url:
            raise ValueError("Redirect rejected; verify the official URL manually")
        size=head.headers.get("Content-Length")
        if size is None or not size.isdecimal() or not 0 < int(size) <= cap:
            raise ValueError("Missing/oversized Content-Length; no download performed")
        expected=int(size)
    partial=destination.with_suffix(destination.suffix+".part")
    if destination.exists() or partial.exists():
        raise FileExistsError("Destination or partial file exists")
    total=0
    created=False
    try:
        with urlopen(Request(url,headers=headers),timeout=30) as response:
            if response.url != url:
                raise ValueError("Redirect rejected")
            with partial.open("xb") as output:
                created=True
                while block := response.read(min(65536, cap-total+1)):
                    total+=len(block)
                    if total>cap:
                        raise ValueError("Download exceeded byte budget")
                    output.write(block)
        if total != expected:
            raise ValueError("GET length differs from HEAD; inspect manually")
        # Exclusive final creation avoids overwriting an existing local file.
        import os
        os.link(partial,destination)
        partial.unlink()
    except Exception:
        if created: partial.unlink(missing_ok=True)
        raise
    return total


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=["plan","kernels","horizons"],default="plan",nargs="?")
    parser.add_argument("--destination",type=Path)
    parser.add_argument("--contact",help="Application contact for the required User-Agent")
    args=parser.parse_args()
    if args.mode=="plan":
        print(json.dumps(horizons_plan(),indent=2))
        return
    if not args.destination or not args.contact:
        parser.error("Explicit --destination and --contact are required for network access")
    args.destination.mkdir(parents=True,exist_ok=True)
    user_agent=f"24and28-Lunar-Reference/0.1 ({args.contact})"
    try:
        if args.mode=="kernels":
            manifest=Path(__file__).parent/"manifests/kernels.json"
            products=json.loads(manifest.read_text())["products"]
            for item in products:
                url=item["download_url"]
                if not url.startswith("https://naif.jpl.nasa.gov/pub/naif/generic_kernels/"):
                    raise ValueError("Only official NAIF kernel URLs are allowed")
                count=save_bounded(url,args.destination/item["filename"],32*1024*1024,user_agent)
                print(f"Retrieved {item['filename']}: {count} bytes; not scientifically validated")
        else:
            # Sequential requests only. No retry when blocked or rate-limited.
            plan=horizons_plan()
            for i,query in enumerate(plan["queries"]):
                path=args.destination/f"horizons-{i}.json"
                # Dynamic API responses may lack Content-Length: bounded GET,
                # explicitly separate from kernel acquisition.
                with urlopen(Request(query["url"],headers={"User-Agent":user_agent}),timeout=30) as response:
                    if not response.url.startswith(ENDPOINT+"?"):
                        raise ValueError("Unexpected Horizons response URL")
                    data=response.read(1024*1024+1)
                    if len(data)>1024*1024: raise ValueError("Reference response exceeds 1 MiB")
                payload=json.loads(data)
                if "error" in payload or "$$SOE" not in payload.get("result",""):
                    raise ValueError("Horizons returned no ephemeris; no reference accepted")
                with path.open("xb") as stream: stream.write(data)
                print(f"Saved raw reference {path.name}; header/conventions NOT_VERIFIED")
            with (args.destination/"requests.json").open("x") as stream:
                json.dump(plan,stream,indent=2)
    except Exception as exc:
        parser.exit(2,f"{type(exc).__name__}: {exc}\nStopped; do not bypass access restrictions.\n")


if __name__=="__main__": main()
