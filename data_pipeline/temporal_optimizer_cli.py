"""Same-site temporal search with explicit recorded/live modes."""

import argparse, json, os
from pathlib import Path
from app.science.temporal_optimizer_models import TemporalOptimizationRequest
from app.science.temporal_optimizer import optimize, RecordedProvider, LiveProvider
from data_pipeline.operations_cli import load_windows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--request", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--mode", choices=["recorded", "live"], default="recorded")
    p.add_argument("--recorded", type=Path, nargs="*", default=[])
    p.add_argument("--hints", type=Path, nargs="*", default=[])
    p.add_argument("--window-output-dir", type=Path)
    a = p.parse_args()
    if a.output.exists():
        p.error("Refusing overwrite")
    if len(a.recorded) > 32 or len(a.hints) > 32:
        p.error("At most 32 evidence files")
    q = TemporalOptimizationRequest.model_validate_json(a.request.read_text())
    hints = [load_windows(x) for x in a.hints]
    if a.mode == "recorded":
        r = optimize(
            q, RecordedProvider([load_windows(x) for x in a.recorded]), hints=hints
        )
    else:
        from app.science.kernels import KernelSession
        from app.science.visibility import VisibilityEngine
        from data_pipeline.visibility_cli import visibility_terrain
        from app.data.fusion import TerrainRequest
        from app.data.observer import prepare_observer
        from app.science.astronomy import calculate

        with KernelSession(
            os.environ["NASA_KERNEL_DIR"], os.environ["NASA_KERNEL_INDEX"]
        ) as session, visibility_terrain() as terrain:
            engine = VisibilityEngine(session, terrain, q.max_cache_entries)
            provider = LiveProvider(engine, q)
            if a.window_output_dir:
                # Fresh directory only: no overwriting precomputed evidence.
                a.window_output_dir.mkdir(exist_ok=False)
                original = provider.get

                def save(wreq):
                    w = original(wreq)
                    path = a.window_output_dir / (
                        wreq.start_utc.strftime("%Y%m%dT%H%M%S") + ".json"
                    )
                    with path.open("x") as f:
                        json.dump(w.model_dump(mode="json"), f, allow_nan=False)
                    return w

                provider.get = save
            v = q.window_template.visibility
            surface = terrain.sample(
                TerrainRequest(
                    location=v.terrain.location,
                    policy=v.terrain.policy,
                    preferred_resolution_m=v.terrain.preferred_resolution_m,
                )
            )
            if surface.selected is None:
                raise ValueError("No accepted observer for geometry discovery")
            sun_observer = prepare_observer(
                surface.selected, v.solar_height_above_surface_m
            ).observer

            # Cheap centre elevation orders discovery only, never certifies visibility.
            def geometry(utc):
                return calculate(
                    session, sun_observer, utc, v.correction
                ).sun.elevation_deg

            r = optimize(q, provider, hints=hints, geometry_priority=geometry)
    with a.output.open("x") as f:
        json.dump(r.model_dump(mode="json"), f, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
