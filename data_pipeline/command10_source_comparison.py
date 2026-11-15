"""Read-only 5/20/80 m point/slope comparison; optional 20 m is never a default."""

import argparse, json, time, resource
from pathlib import Path
from app.models.analysis import Coordinates
from app.data.fusion import MultiResolutionDem, TerrainPolicy
from app.optimization.local_site_optimizer import screen
from data_pipeline.visibility_cli import visibility_terrain, LOLA20_HASH


def run(output):
    if output.exists():
        raise ValueError("Refusing overwrite")
    old = json.loads(
        Path("data_pipeline/evidence/command-10-validation.json").read_text()
    )["http_lifecycle"]["runs"]["local"]["result"]["result"]
    points = [old["baseline"]] + old["candidates"]
    rows = []
    start = time.perf_counter()
    with visibility_terrain(True) as upgraded:
        from data_pipeline.horizon_cli import terrain_session

        with terrain_session() as baseline:
            sources = {
                "5m": baseline.sources["SITE01"],
                "20m": upgraded.sources["PRODUCT90"],
                "80m": baseline.sources["PRODUCT90"],
            }
            identity = {
                k: {
                    "sha256": s.dem.reference.raster_sha256,
                    "reference": s.dem.reference.model_dump(mode="json"),
                    "resolution_m": s.dem.ds.res,
                    "shape": s.dem.ds.shape,
                    "bounds": list(s.dem.ds.bounds),
                    "crs": s.dem.crs.to_wkt(),
                    "nodata": (
                        "NaN"
                        if str(s.dem.ds.nodata).lower() == "nan"
                        else s.dem.ds.nodata
                    ),
                    "auxiliary_hashes": s.dem.auxiliary_file_hashes,
                }
                for k, s in sources.items()
            }
            assert identity["20m"]["sha256"] == LOLA20_HASH and tuple(
                identity["20m"]["resolution_m"]
            ) == (20.0, 20.0)
            singles = {k: MultiResolutionDem([s]) for k, s in sources.items()}
            center = Coordinates.model_validate(old["baseline"]["location"])
            disk_coverage = {
                k: s.dem.coverage(
                    center, 5000, allow_unverified_registration=True
                ).model_dump(mode="json")
                for k, s in sources.items()
            }
            for c in points:
                loc = Coordinates.model_validate(c["location"])
                values = {
                    k: screen(t, loc, TerrainPolicy(registration="PROTOTYPE"), 10)
                    for k, t in singles.items()
                }
                a, b = values["20m"], values["80m"]
                rows.append(
                    {
                        "location": loc.model_dump(mode="json"),
                        "distance_m": c["distance_m"],
                        "sources": values,
                        "20_minus_80_height_m": (
                            a.get("surface_elevation_m") - b.get("surface_elevation_m")
                            if a.get("surface_elevation_m") is not None
                            and b.get("surface_elevation_m") is not None
                            else None
                        ),
                        "20_minus_80_slope_deg": (
                            a["slope_deg"] - b["slope_deg"]
                            if a["slope_deg"] is not None and b["slope_deg"] is not None
                            else None
                        ),
                    }
                )
    summary = {
        k: {
            "valid_points": sum(r["sources"][k]["status"] == "VALID" for r in rows),
            "slope_known": sum(r["sources"][k]["slope_deg"] is not None for r in rows),
            "slope_eligible": sum(r["sources"][k]["eligible"] for r in rows),
        }
        for k in sources
    }
    result = {
        "mode": "LIVE_NASA_BOUNDED_SOURCE_GRID_DIAGNOSTIC",
        "default_changed": False,
        "source_identities": identity,
        "sampled_5km_disk_coverage": disk_coverage,
        "rows": rows,
        "summary": summary,
        "seconds": time.perf_counter() - start,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "limitations": [
            "20 m hash matches the user manifest, not an independent publisher checksum.",
            "Containing-cell surface/slope differences are not absolute registration error measurements.",
            "The 3x3 slope support differs by resolution; lower slope is not evidence of safer terrain.",
            "No 20 m operation or landing-safety decision was fabricated.",
        ],
    }
    with output.open("x") as f:
        json.dump(result, f, indent=2, allow_nan=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    run(a.output)
