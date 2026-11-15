"""Local read-only scientific temporal windows CLI."""

import argparse, json, os
from pathlib import Path
from app.science.window_models import WindowSearchRequest
from app.science.windows import run_windows
from app.science.visibility import VisibilityEngine
from app.science.kernels import KernelSession
from data_pipeline.visibility_cli import visibility_terrain


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--request", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--cache-size", type=int, default=2048)
    p.add_argument("--use-20m", action="store_true")
    a = p.parse_args()
    if a.output.exists():
        p.error("Refusing overwrite")
    if a.request.stat().st_size > 65536:
        p.error("Request exceeds 64 KiB")
    r = WindowSearchRequest.model_validate_json(a.request.read_text())
    with KernelSession(
        os.environ["NASA_KERNEL_DIR"], os.environ["NASA_KERNEL_INDEX"]
    ) as session, visibility_terrain(a.use_20m) as terrain:
        result = run_windows(VisibilityEngine(session, terrain, a.cache_size), r)
    with a.output.open("x") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
