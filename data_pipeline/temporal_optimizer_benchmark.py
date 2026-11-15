"""Optional bounded profiling; synthetic, recorded and live work stay distinct."""

import argparse, cProfile, json, pstats, time, platform, sys
from pathlib import Path
from contextlib import ExitStack
from app.science.visibility import VisibilityEngine
from app.science.visibility_models import VisibilityRequest
from app.science.temporal_optimizer import optimize, RecordedProvider, discover
from app.science.temporal_optimizer_models import TemporalOptimizationRequest
from app.science.window_models import WindowSearchResult
from data_pipeline.visibility_validation import pilot


def science(result):
    v = result.model_dump(mode="json")
    v.pop("performance")
    for name in ("sun", "earth"):
        v[name].pop("performance")
    return v


def profile(fn):
    p = cProfile.Profile()
    t = time.perf_counter()
    p.enable()
    r = fn()
    p.disable()
    rows = []
    for (file, line, name), (cc, nc, tt, ct, callers) in pstats.Stats(p).stats.items():
        if "/app/" in file or name in ("read", "fwd"):
            rows.append(
                {
                    "file": Path(file).name,
                    "line": line,
                    "function": name,
                    "calls": nc,
                    "self_s": tt,
                    "cumulative_s": ct,
                }
            )
    return r, {
        "seconds": time.perf_counter() - t,
        "functions": sorted(rows, key=lambda x: -x["cumulative_s"])[:100],
    }


def run(mode, output):
    output = Path(output)
    if output.exists():
        raise ValueError("Refusing overwrite")
    report = {
        "mode": mode,
        "environment": {"python": sys.version, "platform": platform.platform()},
        "runs": {},
    }
    if mode == "recorded":
        artifact = json.loads(
            Path(
                "data_pipeline/evidence/command-09-temporal-optimizer.json"
            ).read_text()
        )
        q = TemporalOptimizationRequest.model_validate(
            artifact["live_result"]["request"]
        )
        windows = [
            WindowSearchResult.model_validate(w) for w in artifact["live_windows"]
        ]
        hint = WindowSearchResult.model_validate(
            json.loads(
                Path("data_pipeline/evidence/command-07-windows.json").read_text()
            )["extended_candidate_search"]["event_search"]
        )
        r, stats = profile(lambda: optimize(q, RecordedProvider(windows), hints=[hint]))
        report["runs"]["replay"] = stats
        report["outcome"] = r.outcome
        report["scope"] = r.search_scope
        report["comparison"] = [x.model_dump(mode="json") for x in r.comparisons]
    else:
        with ExitStack() as stack:
            if mode == "synthetic":
                import pytest

                sys.path.insert(0, str(Path("backend/tests").resolve()))
                from test_visibility import fake, Session
                from test_horizon import synthetic, req
                import tempfile

                mp = pytest.MonkeyPatch()
                stack.callback(mp.undo)
                fake.__wrapped__(mp)
                folder = Path(stack.enter_context(tempfile.TemporaryDirectory()))
                h = stack.enter_context(synthetic(folder))
                e = VisibilityEngine(Session(), h.terrain)
                e.horizon = h
                q = VisibilityRequest(
                    terrain=req(max_range_m=100), utc="2026-11-20T08:00:00Z"
                )
            else:
                import os
                from app.science.kernels import KernelSession
                from data_pipeline.visibility_cli import visibility_terrain

                session = stack.enter_context(
                    KernelSession(
                        os.environ["NASA_KERNEL_DIR"], os.environ["NASA_KERNEL_INDEX"]
                    )
                )
                terrain = stack.enter_context(visibility_terrain())
                e = VisibilityEngine(session, terrain)
                q = pilot()
            for name, request in [
                ("cold", q),
                ("warm", q),
                (
                    "budget_changed",
                    VisibilityRequest.model_validate(
                        q.model_dump()
                        | {
                            "max_new_rays": 0,
                            "terrain": q.terrain.model_dump()
                            | {"max_total_samples": 1},
                        }
                    ),
                ),
            ]:
                r, stats = profile(lambda: e.run(request))
                report["runs"][name] = stats | {
                    "science": science(r),
                    "accounting": r.performance["accounting"],
                    "peak_rss_kib": r.performance["peak_rss_kib"],
                }
    with output.open("x") as f:
        json.dump(
            report,
            f,
            indent=2,
            allow_nan=False,
            default=lambda value: value.isoformat(),
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["synthetic", "recorded", "live"], required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    run(a.mode, a.output)
