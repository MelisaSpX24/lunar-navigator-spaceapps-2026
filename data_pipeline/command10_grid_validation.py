"""Bounded actual NASA horizon-grid experiment; never uses interpolation as disk evidence."""

import argparse, json, time, os, resource
from pathlib import Path
from app.science.kernels import KernelSession
from app.science.visibility import VisibilityEngine
from app.science.horizon_grid import build_grid
from app.science.geometry import Observer
from app.science.astronomy import calculate
from app.science.temporal_optimizer import discover
from app.science.temporal_optimizer_models import TemporalOptimizationRequest
from app.science.window_models import WindowSearchResult
from data_pipeline.visibility_validation import pilot
from data_pipeline.visibility_cli import visibility_terrain


def run(output):
    output = Path(output)
    if output.exists():
        raise ValueError("Refusing overwrite")
    report = {"science_ready": False, "origin": "LIVE_NASA_GRID_VALIDATION", "runs": {}}
    with KernelSession(
        os.environ["NASA_KERNEL_DIR"], os.environ["NASA_KERNEL_INDEX"]
    ) as s, visibility_terrain() as terrain:
        e = VisibilityEngine(s, terrain, 4096)
        q = pilot()
        # Exact metadata and observer are shared; each finer direction remains a real ray.
        for spacing in (1.0, 0.5):
            g = build_grid(e, q.terrain, spacing, max_new_rays=720, max_samples=1000000)
            report["runs"][str(spacing)] = {
                "identity": g.identity,
                "complete_scheduled_grid": g.complete_scheduled_grid,
                "known_directions": sum(x is not None for x in g.elevations.values()),
                "performance": g.performance,
            }
            started = time.perf_counter()
            for i in range(10000):
                g.lookup((i * 0.137) % 360)
            report["runs"][str(spacing)]["lookup_10000_seconds"] = (
                time.perf_counter() - started
            )
            probes = []
            for az in (0.0, 90.0, 180.0, 270.0, 359.75, 17.26):
                ray, ident, code = e._ray(q.terrain, az, [1, 100000])
                approx = g.lookup(az)
                actual = ray.horizon_elevation_deg if ray else None
                probes.append(
                    {
                        "azimuth_deg": az,
                        "lookup": approx,
                        "exact_deg": actual,
                        "signed_difference_deg": (
                            None
                            if actual is None or approx["elevation_deg"] is None
                            else approx["elevation_deg"] - actual
                        ),
                    }
                )
            report["runs"][str(spacing)]["exact_comparisons"] = probes
        old = json.loads(
            Path(
                "data_pipeline/evidence/command-09-temporal-optimizer.json"
            ).read_text()
        )
        request = TemporalOptimizationRequest.model_validate(
            old["live_result"]["request"]
        )
        window = WindowSearchResult.model_validate(old["live_windows"][0])
        surface = window.timeline[0].bodies["sun"]["observer"]
        observer = Observer.model_validate(surface)

        def priority(utc):
            direction = calculate(s, observer, utc, "NONE").sun
            h = g.lookup(direction.azimuth_deg)
            return (
                direction.elevation_deg - h["elevation_deg"]
                if h["elevation_deg"] is not None
                else -1000
            )

        rows, stats = discover(request, geometry_priority=priority)
        report["grid_only_discovery"] = {
            "generated_alternatives": len(rows),
            "performance": stats,
            "scientific_candidates_completed": 0,
            "note": "Screening only; no MET/NOT_MET operation decisions inferred.",
        }
        t = time.perf_counter()
        r = e.run(q)
        report["exact_disk_verification"] = {
            "seconds": time.perf_counter() - t,
            "sun_state": r.sun.state,
            "earth_state": r.earth.state,
            "accounting": r.performance["accounting"],
            "sources": r.sources,
            "kernel_ids": r.kernel_ids,
        }
        report["resources"] = e.counters()
        report["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with output.open("x") as f:
        json.dump(report, f, indent=2, allow_nan=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    a = p.parse_args()
    run(a.output)
