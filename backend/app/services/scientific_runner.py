"""One borrowed scientific session per job; existing engines remain authoritative."""

import os, time, json
from pathlib import Path
from datetime import timedelta
from contextlib import ExitStack
from app.models.analysis import (
    AnalysisRequest,
    AnalysisResult,
    ResolvedSite,
    TimeSample,
    BodySample,
    Window,
    Windows,
    Source,
    HorizonProfile,
    HorizonPoint,
)
from app.science.window_models import WindowSearchRequest
from app.science.visibility_models import VisibilityRequest, VisibilityResult
from app.science.horizon_models import HorizonRequest, Sampling
from app.data.fusion import TerrainPolicy
from app.science.kernels import KernelSession, ScienceError
from app.science.visibility import VisibilityEngine
from app.science.windows import run_windows
from app.science.operations import (
    evaluate_operation,
    evidence_identity,
    effective_requirements,
)
from app.science.operation_models import OperationEvaluationRequest
from app.science.temporal_optimizer import (
    discover,
    shifted_requests,
    compare,
    candidate_rank,
)
from app.science.temporal_optimizer_models import TemporalCandidate
from app.optimization.local_site_optimizer import optimize_local
from app.services.models import AnalysisJobRequest, TemporalJobRequest, LocalJobRequest
from app.jobs.store import digest
from app.jobs.manager import JobStop
from data_pipeline.visibility_cli import visibility_terrain


def unavailable():
    needed = {
        "NASA_KERNEL_DIR": None,
        "NASA_KERNEL_INDEX": None,
        "NASA_LOLA_VALIDATION_DIR": None,
    }
    if any(not os.environ.get(k) for k in needed):
        return "SCIENCE_SOURCES_NOT_CONFIGURED"
    root = Path(os.environ["NASA_LOLA_VALIDATION_DIR"])
    names = [
        "Site01_final_adj_5mpp_surf.tif",
        "LDEM_80S_80MPP_ADJ.TIF",
        "Site01_final_adj_5mpp_toterr.tif",
        "Site01_final_adj_5mpp_ldec.tif",
    ]
    if (
        any(not (root / n).is_file() for n in names)
        or not Path(os.environ["NASA_KERNEL_INDEX"]).is_file()
    ):
        return "SCIENCE_SOURCE_UNAVAILABLE"
    if any(
        not (Path(os.environ["NASA_KERNEL_DIR"]) / n).is_file()
        for n in (
            "de421.bsp",
            "moon_pa_de421_1900-2050.bpc",
            "moon_080317.tf",
            "naif0012.tls",
            "pck00011.tpc",
        )
    ):
        return "KERNEL_MISSING"
    return None


def validate_analysis(a):
    if a.site.kind != "COORDINATES":
        raise ScienceError("UNRESOLVED_SITE_ID", "Use resolved coordinates")
    r = a.operation.requirements
    if not any(
        (
            r.min_sun_visible_s is not None,
            r.max_dark_gap_s is not None,
            r.min_earth_continuous_s is not None,
            r.require_simultaneous,
            "earth_clearance_margin_deg" in r.model_fields_set,
            "min_solar_disk_visible_fraction" in r.model_fields_set,
        )
    ):
        raise ValueError("REQUIRED_PARAMETERS_MISSING: no active operation requirement")
    if a.time.duration_s > 86400:
        raise ValueError("Prototype analysis duration limited to one day")
    if (
        max(
            a.observer.solar_height_above_surface_m,
            a.observer.earth_height_above_surface_m,
        )
        > 10000
    ):
        raise ValueError("Device height exceeds science limit")


def template(a, registration="STRICT", step_s=3600, disk_samples=64):
    validate_analysis(a)
    r = a.operation.requirements
    h = HorizonRequest(
        location={k: v for k, v in a.site.model_dump().items() if k != "kind"},
        policy=TerrainPolicy(registration=registration),
        sampling=Sampling(start_m=5, min_step_m=1, max_step_m=640, resolution_factor=8),
    )
    return WindowSearchRequest(
        visibility=VisibilityRequest(
            terrain=h,
            utc=a.time.start_utc,
            disk_samples=disk_samples,
            solar_height_above_surface_m=a.observer.solar_height_above_surface_m,
            earth_height_above_surface_m=a.observer.earth_height_above_surface_m,
        ),
        start_utc=a.time.start_utc,
        duration_s=a.time.duration_s,
        step_s=step_s,
        solar_fraction=r.min_solar_disk_visible_fraction,
        earth_margin_deg=r.earth_clearance_margin_deg,
    )


def operation(a, w, policy):
    return evaluate_operation(
        OperationEvaluationRequest(
            analysis=a,
            evaluation_policy=policy,
            window_evidence_sha256=evidence_identity(w),
            correction=w.request.visibility.correction,
        ),
        w,
    )


def adapt_analysis(a, w, op, origin, identity, grids=None):
    if w.execution_status != "COMPLETED":
        raise ValueError("PARTIAL_WINDOWS_CANNOT_FORM_COMPLETED_ANALYSIS")
    grids = grids or {}
    profiles = {
        g.identity: HorizonProfile(
            id=g.identity,
            observer_height_m=g.request.device_height_m,
            range_m=g.request.max_range_m,
            points=[
                HorizonPoint(azimuth_deg=float(az), elevation_deg=value)
                for az, value in sorted(
                    g.elevations.items(), key=lambda item: float(item[0])
                )
            ],
            coverage_complete=g.complete_scheduled_grid,
            dem_source_ids=list(w.source_evidence.get("dem", {})),
        )
        for g in grids.values()
    }
    series = []
    for s in w.timeline:
        bodies = {}
        for name in ("sun", "earth"):
            b = s.bodies.get(name, {})
            d = b.get("direction", {})
            bodies[name] = BodySample(
                azimuth_deg=d.get("azimuth_deg"),
                elevation_deg=d.get("elevation_deg"),
                angular_radius_deg=b.get("angular_radius_deg"),
                center_clearance_deg=b.get("center_clearance_deg"),
                disk_visible_fraction=b.get("visible_fraction"),
                disk_state=b.get("disk_state", "UNKNOWN"),
                horizon_id=grids[name].identity if name in grids else None,
                condition_met={"MET": True, "NOT_MET": False, "UNKNOWN": None}.get(
                    getattr(s, name)
                ),
            )
        series.append(
            TimeSample(
                time_utc=s.time_utc,
                sun=bodies["sun"],
                earth=bodies["earth"],
                joint_condition_met={
                    "MET": True,
                    "NOT_MET": False,
                    "UNKNOWN": None,
                }.get(s.joint),
            )
        )
    sources = []
    for role, value in w.source_evidence.get("dem", {}).items():
        r = value["reference"]
        sources.append(
            Source(
                id=role,
                kind="DEM",
                product=r["product_id"],
                version=r.get("product_version") or "UNSPECIFIED_HASH_PINNED",
                url=r["source_url"],
                sha256=r["raster_sha256"],
            )
        )
    folders = {
        "de421.bsp": ("SPK", "spk/planets"),
        "moon_pa_de421_1900-2050.bpc": ("PCK", "pck"),
        "moon_080317.tf": ("FK", "fk/satellites"),
        "naif0012.tls": ("LSK", "lsk"),
        "pck00011.tpc": ("PCK", "pck"),
    }
    for key in w.source_evidence.get("kernel_ids", []):
        name, sha = key.split(":")
        kind, folder = folders[name]
        sources.append(
            Source(
                id=name,
                kind=kind,
                product=name,
                version="FILENAME_AND_SHA256",
                url="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/"
                + folder
                + "/"
                + name,
                sha256=sha,
            )
        )
    height = next(
        (
            s.bodies["sun"]["observer"]["surface_elevation_m"]
            for s in w.timeline
            if s.bodies.get("sun")
        ),
        None,
    )
    coords = {k: v for k, v in a.site.model_dump().items() if k != "kind"}
    windows = {
        f: (
            None
            if w.sampled_windows.get(f) is None
            else [
                Window(
                    **{
                        k: getattr(p, k)
                        for k in (
                            "start_utc",
                            "end_utc",
                            "definition_id",
                            "start_censored",
                            "end_censored",
                        )
                    }
                )
                for p in w.sampled_windows[f]
            ]
        )
        for f in ("sun", "earth", "joint")
    }
    return AnalysisResult(
        analysis_id=identity,
        execution_status="COMPLETED",
        data_origin=origin,
        request=a,
        resolved_site=ResolvedSite(
            **coords,
            surface_elevation_m=height,
            height_datum_id="ASSUMED_REFERENCE_SPHERE" if height is not None else None
        ),
        series=series,
        horizons=list(profiles.values()) if profiles else None,
        windows=Windows(**windows),
        decision=op.decision,
        score=op.score,
        quality=op.quality,
        sources=sources,
        limitations=op.limitations
        + (
            [
                "Horizon coverage_complete describes scheduled grid directions only; interpolation is not strict evidence."
            ]
            if profiles
            else [
                "Full 360-degree horizon not computed by this request; horizons=null."
            ]
        )
        + [
            "Timeline includes an end boundary probe; operation windows are [start,end)."
        ]
        + (["WINDOW_SEARCH_PARTIAL"] if w.execution_status == "PARTIAL" else []),
    )


class BudgetedEngine:
    def __init__(self, engine, resources, ctx, resume_from=None):
        self.engine, self.resources, self.ctx = engine, resources, ctx
        self.before = engine.counters()
        self.calls = 0
        self.reused = 0
        self.resume_from = resume_from
        self.loaded = set()
        self.created = set()
        self.loaded_grids = set()
        self.created_grids = set()
        self.resume_cost = {k: 0 for k in engine.counters()} | {
            "visibility_evaluations": 0
        }
        ctx.terrain_screen_positions = 0
        ctx.budget_check = self.check
        self.signature = {
            "dem": engine.namespace,
            "kernels": [
                {k: r[k] for k in ("filename", "sha256")}
                for r in engine.session.records
            ],
            "algorithm": "command-10-exact-utc-v1",
        }

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def used(self):
        c = {k: v - self.before[k] for k, v in self.engine.counters().items()}
        c["visibility_evaluations"] = self.calls
        for k, v in self.resume_cost.items():
            c[k] = c.get(k, 0) + v
        c["dem_samples"] += self.ctx.terrain_screen_positions
        return c

    def new_resources(self):
        values = {k: v - self.before[k] for k, v in self.engine.counters().items()}
        values["visibility_evaluations"] = self.calls
        values["dem_samples"] += self.ctx.terrain_screen_positions
        return values

    def check(self, anticipated_samples=0):
        self.ctx.check()
        if time.monotonic() - self.ctx.started >= self.resources.max_wall_time_s:
            raise JobStop("JOB_WALL_TIME_LIMIT")
        u = self.used()
        if (
            u["dem_samples"] + anticipated_samples > self.resources.max_terrain_samples
            or u["attempted_rays"] > self.resources.max_horizon_rays
        ):
            raise JobStop("JOB_RESOURCE_LIMIT")

    def run(self, q):
        self.check()
        self.engine._assert_sources_unchanged()
        scientific = q.model_dump(mode="json")
        scientific.pop("max_new_rays")
        scientific["terrain"].pop("max_total_samples")
        key = digest({"signature": self.signature, "request": scientific})
        saved = self.ctx.store.load_checkpoint(self.ctx.job, "utc:" + key)
        ancestor = self.resume_from
        for _ in range(8):
            if saved is not None or not ancestor:
                break
            saved = self.ctx.store.load_checkpoint(ancestor, "utc:" + key)
            ancestor = json.loads(self.ctx.store.row(ancestor)["payload"]).get(
                "resume_from"
            )
        if saved:
            if saved["signature"] != self.signature or saved["request"] != scientific:
                raise ScienceError(
                    "CHECKPOINT_IDENTITY_MISMATCH", "Checkpoint binding rejected"
                )
            result = VisibilityResult.model_validate(saved["result"])
            self.ctx.store.checkpoint(self.ctx.job, "utc:" + key, saved)
            if key not in self.loaded and key not in self.created:
                for k in self.resume_cost:
                    self.resume_cost[k] += saved["cost"].get(
                        k, saved["result"]["performance"]["accounting"].get(k, 0)
                    )
                self.loaded.add(key)
            self.check()
            self.reused += 1
            return result
        u = self.used()
        if u["visibility_evaluations"] >= self.resources.max_visibility_evaluations:
            raise JobStop("VISIBILITY_EVALUATION_LIMIT")
        values = q.model_dump()
        rays = max(0, self.resources.max_horizon_rays - u["attempted_rays"])
        points = max(0, self.resources.max_terrain_samples - u["dem_samples"])
        values["max_new_rays"] = min(q.max_new_rays, rays) if points else 0
        if points:
            values["terrain"]["max_total_samples"] = min(
                points, q.terrain.max_total_samples
            )
        q = VisibilityRequest.model_validate(values)
        self.ctx.update(
            "COMPUTING_VISIBILITY", completed_visibility_evaluations=self.calls
        )
        self.calls += 1
        before = self.engine.counters()
        result = self.engine.run(q)
        after = self.engine.counters()
        value = {
            "signature": self.signature,
            "request": scientific,
            "result": result.model_dump(mode="json"),
            "cost": {k: after[k] - before[k] for k in before}
            | {"visibility_evaluations": 1},
        }
        if (
            not result.sun.unknown_fraction
            and not result.earth.unknown_fraction
            and not result.performance["accounting"]["budget_rejected_rays"]
        ):
            self.ctx.store.checkpoint(self.ctx.job, "utc:" + key, value)
            self.created.add(key)
        self.ctx.capture(
            {
                "partial_single_utc_visibility": result.model_dump(mode="json"),
                "scientific_signature": self.signature,
            }
        )
        self.ctx.update(
            "EVALUATING_WINDOWS", completed_visibility_evaluations=self.calls
        )
        return result

    def evaluate(self, a, w, policy):
        self.check()
        result = run_windows(self, w)
        self.ctx.update("EVALUATING_OPERATION")
        op = operation(a, result, policy)
        record = {
            "analysis": a.model_dump(mode="json", exclude_unset=True),
            "window": result.model_dump(mode="json"),
            "operation": op.model_dump(mode="json"),
            "signature": self.signature,
        }
        self.ctx.store.checkpoint(
            self.ctx.job, "candidate:" + evidence_identity(result), record
        )
        self.ctx.candidate_results.append(record)
        return op, result


def temporal_batch(q, budget_engine, ctx, limit, geometry_priority=None):
    started = time.perf_counter()
    from app.services.optimizer_support import historical_hints, candidate_accounting

    hints, hint_audit = historical_hints(q, budget_engine)
    rows, discovery = discover(q, hints, geometry_priority=geometry_priority)
    discovery.update(hint_audit)
    baseline = None
    windows = {}
    candidates = []
    completed = 0
    interrupted = False
    plan = [(q.baseline_analysis.time.start_utc, ["BASELINE"])] + rows
    for i, (utc, sources) in enumerate(plan):
        c = TemporalCandidate(
            candidate_id=digest(utc.isoformat())[:16],
            start_utc=utc,
            end_utc=utc + timedelta(seconds=q.baseline_analysis.time.duration_s),
            discovery_sources=sources,
        )
        if i >= limit or interrupted:
            c.evaluation_status = "NOT_EVALUATED_RESOURCE_LIMIT"
            c.reason_codes = ["BATCH_RESOURCE_LIMIT"]
        else:
            ctx.update(
                "GENERATING_CANDIDATES",
                completed_candidates=completed,
                total_candidates=len(plan),
            )
            a, w = shifted_requests(q, utc)
            calls_before, reused_before = budget_engine.calls, budget_engine.reused
            used_before = budget_engine.used()
            candidate_started = time.perf_counter()
            try:
                op, result = budget_engine.evaluate(a, w, q.evaluation_policy)
                c.operation = op
                c.metrics = {k: m.model_dump() for k, m in result.metrics.items()}
                c.evidence_sha256 = evidence_identity(result)
                c.evidence_mode = (
                    "LIVE" if budget_engine.calls > calls_before else "RECORDED"
                )
                c.evaluation_status = (
                    "DETAILED_EVALUATED"
                    if result.execution_status == "COMPLETED"
                    else "PARTIAL"
                )
                windows[c.candidate_id] = result
                completed += 1
            except JobStop as exc:
                if exc.state in ("CANCELLED", "INTERRUPTED"):
                    raise
                interrupted = True
                c.evaluation_status = "PARTIAL"
                c.reason_codes = [exc.code]
            except (ScienceError, ValueError, OSError) as exc:
                c.evaluation_status = "INVALID"
                c.reason_codes = [getattr(exc, "code", type(exc).__name__)]
            finally:
                c.resource_consumption = candidate_accounting(
                    budget_engine, calls_before, reused_before, used_before
                )
                c.seconds = time.perf_counter() - candidate_started
        if baseline is None:
            baseline = c
        else:
            candidates.append(c)
        ctx.capture(
            {
                "baseline": baseline.model_dump(mode="json"),
                "candidates": [x.model_dump(mode="json") for x in candidates],
                "execution_status": "PARTIAL",
            }
        )
    comparisons = []
    recommendations = []
    for c in sorted([x for x in candidates if x.operation], key=candidate_rank):
        comparison = compare(
            baseline, c, windows.get(baseline.candidate_id), windows.get(c.candidate_id)
        )
        comparisons.append(comparison.model_dump(mode="json"))
        if (
            comparison.classification == "IMPROVED_ALTERNATIVE"
            and len(recommendations) < q.max_recommendations
        ):
            recommendations.append(c.model_dump(mode="json"))
    return {
        "schema_version": "command-10-temporal-batch-v2",
        "request": q.model_dump(mode="json"),
        "baseline": baseline.model_dump(mode="json"),
        "candidates": [c.model_dump(mode="json") for c in candidates],
        "comparisons": comparisons,
        "recommendations": recommendations,
        "generated_alternatives": len(rows),
        "discovery": discovery,
        "detailed_completed_including_baseline": sum(
            c.evaluation_status == "DETAILED_EVALUATED" for c in [baseline] + candidates
        ),
        "detailed_evaluated_including_baseline": sum(
            c.operation is not None for c in [baseline] + candidates
        ),
        "scientifically_incomplete_including_baseline": sum(
            c.operation is not None and c.operation.decision.status == "INCOMPLETE"
            for c in [baseline] + candidates
        ),
        "not_evaluated_alternatives": sum(
            c.evaluation_status == "NOT_EVALUATED_RESOURCE_LIMIT" for c in candidates
        ),
        "search_status": (
            "SEARCH_PARTIAL_RESOURCE_LIMIT"
            if interrupted
            or limit < len(plan)
            or any(
                c.evaluation_status != "DETAILED_EVALUATED"
                for c in [baseline] + candidates
            )
            else "SEARCH_COMPLETED_EVALUATED_SET"
        ),
        "seconds": time.perf_counter() - started,
        "resources": budget_engine.used(),
        "checkpoint_reused": budget_engine.reused,
        "science_ready": False,
        "scientific_window_template": q.window_template.model_dump(mode="json"),
        "limitations": [
            "Only complete exact candidate windows support recommendations.",
            "Finite sampled time model; no physical continuity or global optimum certification.",
        ],
    }


def run_science(kind, payload, ctx):
    model = {
        "ANALYSIS": AnalysisJobRequest,
        "TEMPORAL": TemporalJobRequest,
        "LOCAL": LocalJobRequest,
    }[kind].model_validate(payload)
    a = model.analysis if kind == "ANALYSIS" else model.optimization.baseline_analysis
    validate_analysis(a)
    ctx.update("VALIDATING_SOURCES")
    error = unavailable()
    if error:
        raise ScienceError(error, "Configured science assets are unavailable")
    with KernelSession(
        os.environ["NASA_KERNEL_DIR"], os.environ["NASA_KERNEL_INDEX"]
    ) as session, visibility_terrain() as terrain:
        ctx.update("PREPARING_OBSERVER")
        engine = BudgetedEngine(
            VisibilityEngine(session, terrain, model.resources.max_cache_entries),
            model.resources,
            ctx,
            model.resume_from,
        )
        if kind == "ANALYSIS":
            w = template(a, model.registration, model.step_s, model.disk_samples)
            op, result = engine.evaluate(a, w, model.evaluation_policy)
            grids = {}
            if a.options.include_full_horizon and result.source_evidence:
                from app.science.horizon_grid import build_grid, HorizonGrid

                by_height = {}
                for role, height in [
                    ("sun", a.observer.solar_height_above_surface_m),
                    ("earth", a.observer.earth_height_above_surface_m),
                ]:
                    if height not in by_height:
                        ctx.update("COMPUTING_HORIZON")
                        hq = HorizonRequest.model_validate(
                            w.visibility.terrain.model_dump()
                            | {"device_height_m": height}
                        )
                        key = "grid:" + digest(
                            {
                                "signature": engine.signature,
                                "request": hq.model_dump(mode="json"),
                                "spacing": 1.0,
                            }
                        )
                        saved = ctx.store.load_checkpoint(ctx.job, key)
                        if saved is None and model.resume_from:
                            saved = ctx.store.load_checkpoint(model.resume_from, key)
                        if saved:
                            g = HorizonGrid.model_validate(saved["grid"])
                            if g.source_signature != engine.namespace:
                                raise ScienceError(
                                    "CHECKPOINT_IDENTITY_MISMATCH",
                                    "Grid source changed",
                                )
                            for k in engine.resume_cost:
                                engine.resume_cost[k] += saved["cost"].get(k, 0)
                            engine.check()
                            ctx.store.checkpoint(ctx.job, key, saved)
                        else:
                            used = engine.used()
                            before = engine.engine.counters()
                            rays = max(
                                0,
                                min(
                                    360,
                                    model.resources.max_horizon_rays
                                    - used["attempted_rays"],
                                ),
                            )
                            points = max(
                                0,
                                model.resources.max_terrain_samples
                                - used["dem_samples"],
                            )
                            if points <= 0:
                                raise JobStop("JOB_RESOURCE_LIMIT")
                            g = build_grid(
                                engine.engine,
                                hq,
                                1.0,
                                rays,
                                min(points, 5000000),
                                checkpoint=engine.check,
                            )
                            if g.complete_scheduled_grid:
                                ctx.store.checkpoint(
                                    ctx.job,
                                    key,
                                    {
                                        "grid": g.model_dump(mode="json"),
                                        "cost": {
                                            k: v - before[k]
                                            for k, v in engine.engine.counters().items()
                                        },
                                    },
                                )
                        by_height[height] = g
                    grids[role] = by_height[height]
            ctx.update(
                "EVALUATING_OPERATION", completed_candidates=1, total_candidates=1
            )
            origin = (
                None
                if result.data_origin != "REAL_NASA_PROTOTYPE"
                else (
                    "PRECOMPUTED"
                    if engine.calls == 0
                    and engine.engine.counters()["attempted_rays"] == 0
                    and engine.reused
                    else "LIVE_COMPUTED"
                )
            )
            complete = result.execution_status == "COMPLETED" and all(
                g.complete_scheduled_grid for g in grids.values()
            )
            value = (
                adapt_analysis(a, result, op, origin, ctx.job, grids).model_dump(
                    mode="json"
                )
                if complete
                else None
            )
            return {
                "analysis": value,
                "window_evidence": result.model_dump(mode="json"),
                "operation_evidence": op.model_dump(mode="json"),
                "resources": engine.used(),
                "new_resources": engine.new_resources(),
                "checkpoint_resources": dict(engine.resume_cost),
                "checkpoint_reused": engine.reused,
                "horizon_grid_evidence": [
                    g.model_dump(mode="json")
                    for g in {x.identity: x for x in grids.values()}.values()
                ],
            }, (
                "COMPLETED"
                if result.execution_status == "COMPLETED"
                and all(g.complete_scheduled_grid for g in grids.values())
                else "PARTIAL"
            )
        if kind == "TEMPORAL":
            pipeline_started = time.perf_counter()
            priority = None
            if model.screening_strategy == "HORIZON_GRID":
                from app.services.optimizer_support import GridPriority

                engine.request_correction = (
                    model.optimization.window_template.visibility.correction
                )
                priority = GridPriority(
                    model.optimization, engine, model.grid_spacing_deg
                )
            value = temporal_batch(
                model.optimization,
                engine,
                ctx,
                model.max_candidate_evaluations,
                geometry_priority=priority,
            )
            value["new_resources"] = engine.new_resources()
            value["checkpoint_resources"] = dict(engine.resume_cost)
            value["screening"] = (
                priority.report() if priority else {"strategy": "EXACT_ONLY"}
            )
            value["pipeline_seconds"] = time.perf_counter() - pipeline_started
            backed = any(
                c.get("operation")
                and c["operation"]["data_origin"] == "REAL_NASA_PROTOTYPE"
                for c in [value["baseline"]] + value["candidates"]
            )
            value["data_origin"] = (
                (
                    "LIVE_COMPUTED"
                    if engine.calls
                    or engine.engine.counters()["attempted_rays"]
                    > engine.before["attempted_rays"]
                    else "PRECOMPUTED"
                )
                if backed
                else None
            )
            from app.services.models import TemporalBatchResult

            value = TemporalBatchResult.model_validate(value).model_dump(mode="json")
            return value, (
                "PARTIAL" if "PARTIAL" in value["search_status"] else "COMPLETED"
            )
        result = optimize_local(
            model.optimization,
            terrain,
            lambda a, w: engine.evaluate(a, w, model.optimization.evaluation_policy),
            ctx,
        )
        value = result.model_dump(mode="json")
        backed = any(
            c.operation and c.operation.data_origin == "REAL_NASA_PROTOTYPE"
            for c in [result.baseline] + result.candidates
        )
        value["data_origin"] = (
            (
                "LIVE_COMPUTED"
                if engine.calls
                or engine.engine.counters()["attempted_rays"]
                > engine.before["attempted_rays"]
                else "PRECOMPUTED"
            )
            if backed
            else None
        )
        value["scientific_resources"] = engine.used()
        value["new_scientific_resources"] = engine.new_resources()
        value["checkpoint_scientific_resources"] = dict(engine.resume_cost)
        value["checkpoint_reused"] = engine.reused
        value = type(result).model_validate(value).model_dump(mode="json")
        return value, "PARTIAL"
