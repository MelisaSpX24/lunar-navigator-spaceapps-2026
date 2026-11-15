"""Conservative historical-hint admission and per-candidate provenance accounting."""

import json
import hashlib
from pathlib import Path
from types import SimpleNamespace
from app.science.temporal_optimizer import science_configuration
from app.science.temporal_optimizer_models import TemporalOptimizationRequest
from app.science.window_models import WindowSearchResult

EVIDENCE_ROOT = Path(__file__).resolve().parents[3] / "data_pipeline/evidence"
HINT_CATALOG_SHA256 = "6fc3e5a63363011a93978ebc8204d8ffcba939020cf08385d609e3840617fd5e"
OPERATION_CATALOG_SHA256 = (
    "76d063c328b58cf2b8ddd0a0c2fc6c44173cc62446b88ca67d377e3e2aa4c848"
)


def hint_compatible(request, canonical, hint, sources):
    """The repository hint is licensed only for its recorded operation/search envelope.

    Its discovery interval may differ from the six-hour operation window, but must
    lie inside the exact canonical confinement. No hint is a final visibility proof.
    """
    for attr in (
        "baseline_analysis",
        "search_start_utc",
        "search_end_utc",
        "evaluation_policy",
    ):
        if getattr(request, attr) != getattr(canonical, attr):
            return False
    if (
        request.baseline_analysis.operation.requirements.model_fields_set
        != canonical.baseline_analysis.operation.requirements.model_fields_set
    ):
        return False
    if science_configuration(
        SimpleNamespace(request=request.window_template)
    ) != science_configuration(SimpleNamespace(request=canonical.window_template)):
        return False
    if (
        hint.schema_version != "command-07-v1"
        or hint.data_origin != "REAL_NASA_PROTOTYPE"
    ):
        return False
    if (
        not request.search_start_utc
        <= hint.request.start_utc
        < hint.request.end_utc
        <= request.search_end_utc
    ):
        return False
    v = hint.request.visibility.model_dump(mode="json")
    wanted = request.window_template.visibility.model_dump(mode="json")
    for obj in (v, wanted):
        obj.pop("utc")
        obj.pop("max_new_rays")
        obj["terrain"].pop("max_total_samples")
    if (
        v != wanted
        or hint.request.solar_fraction != request.window_template.solar_fraction
        or hint.request.earth_margin_deg != request.window_template.earth_margin_deg
        or hint.request.joint != request.window_template.joint
    ):
        return False
    return hint.source_evidence == sources


def historical_hints(request, engine):
    root = EVIDENCE_ROOT
    try:
        operation_raw = (root / "command-09-temporal-optimizer.json").read_bytes()
        hint_raw = (root / "command-07-windows.json").read_bytes()
        if (
            hashlib.sha256(operation_raw).hexdigest() != OPERATION_CATALOG_SHA256
            or hashlib.sha256(hint_raw).hexdigest() != HINT_CATALOG_SHA256
        ):
            return [], {"historical_hint_status": "REJECTED_CATALOG_INTEGRITY"}
        catalog = json.loads(operation_raw)
        canonical = TemporalOptimizationRequest.model_validate(
            catalog["live_result"]["request"]
        )
        hint = WindowSearchResult.model_validate(
            json.loads(hint_raw)["extended_candidate_search"]["event_search"]
        )
        sources = {
            "dem": engine.engine._source_metadata(),
            "kernel_ids": [
                r["filename"] + ":" + r["sha256"] for r in engine.engine.session.records
            ],
            "data_origin": "REAL_NASA_PROTOTYPE",
        }
        accepted = hint_compatible(request, canonical, hint, sources)
        return ([hint] if accepted else []), {
            "historical_hint_status": (
                "ACCEPTED_COMPATIBLE"
                if accepted
                else "REJECTED_SCENARIO_OR_SOURCE_MISMATCH"
            ),
            "hint_role": "CANDIDATE_DISCOVERY_ONLY_NOT_EVENT_TIME_OR_OPERATION_PROOF",
        }
    except (OSError, ValueError, KeyError):
        return [], {"historical_hint_status": "UNAVAILABLE_OR_INVALID"}


def candidate_accounting(engine, calls_before, reused_before, before):
    new = engine.calls - calls_before
    reused = engine.reused - reused_before
    after = engine.used()
    return {
        "new_visibility_evaluations": new,
        "checkpoint_lookups": reused,
        "origin_detail": (
            "MIXED_LIVE_AND_RECORDED"
            if new and reused
            else "LIVE" if new else "RECORDED" if reused else "NO_SCIENTIFIC_EVALUATION"
        ),
        "charged_resource_delta": {
            k: after.get(k, 0) - before.get(k, 0) for k in after
        },
    }


class GridPriority:
    """Source-bound coarse ordering only; exact window evaluation remains mandatory."""

    def __init__(self, request, engine, spacing):
        import time
        from app.science.horizon_grid import build_grid, HorizonGrid
        from app.science.horizon_models import HorizonRequest
        from app.data.fusion import TerrainRequest
        from app.data.observer import prepare_observer
        from app.jobs.store import digest

        self.engine = engine
        engine.engine._assert_sources_unchanged()
        self.grids = {}
        self.observers = {}
        self.query_seconds = 0.0
        self.queries = 0
        self.grid_reused = 0
        start = time.perf_counter()
        before = engine.engine.counters()
        r = request.baseline_analysis.operation.requirements
        solar = (
            r.min_sun_visible_s is not None
            or r.max_dark_gap_s is not None
            or r.require_simultaneous
            or "min_solar_disk_visible_fraction" in r.model_fields_set
        )
        earth = (
            r.min_earth_continuous_s is not None
            or r.require_simultaneous
            or "earth_clearance_margin_deg" in r.model_fields_set
        )
        self.roles = ["sun"] if solar else []
        if earth:
            self.roles.append("earth")
        if not self.roles:
            self.roles = ["sun"]
        self.margin = request.window_template.earth_margin_deg
        shared = {}
        for role in self.roles:
            engine.check()
            v = request.window_template.visibility
            height = (
                v.solar_height_above_surface_m
                if role == "sun"
                else v.earth_height_above_surface_m
            )
            h = HorizonRequest.model_validate(
                v.terrain.model_dump() | {"device_height_m": height}
            )
            if height in shared:
                self.grids[role], self.observers[role] = shared[height]
                continue
            engine.ctx.update("COMPUTING_HORIZON")
            key = "screening-grid:" + digest(
                {
                    "signature": engine.signature,
                    "request": h.model_dump(mode="json"),
                    "spacing": spacing,
                    "algorithm": "command-10-screening-grid-v1",
                }
            )
            saved = engine.ctx.store.load_checkpoint(engine.ctx.job, key)
            ancestor = engine.resume_from
            for _ in range(8):
                if saved is not None or not ancestor:
                    break
                saved = engine.ctx.store.load_checkpoint(ancestor, key)
                ancestor = json.loads(engine.ctx.store.row(ancestor)["payload"]).get(
                    "resume_from"
                )
            if saved:
                g = HorizonGrid.model_validate(saved["grid"])
                if (
                    g.source_signature != engine.namespace
                    or g.request != h
                    or g.spacing_deg != spacing
                ):
                    raise ValueError("SCREENING_GRID_IDENTITY_MISMATCH")
                if key not in engine.loaded_grids and key not in engine.created_grids:
                    for k, cost in saved["cost"].items():
                        engine.resume_cost[k] = engine.resume_cost.get(k, 0) + cost
                    engine.loaded_grids.add(key)
                engine.check()
                engine.ctx.store.checkpoint(engine.ctx.job, key, saved)
                self.grid_reused += 1
            else:
                before_grid = engine.engine.counters()
                used = engine.used()
                rays = max(
                    0,
                    min(
                        720, engine.resources.max_horizon_rays - used["attempted_rays"]
                    ),
                )
                points = max(
                    0,
                    min(
                        5000000,
                        engine.resources.max_terrain_samples - used["dem_samples"],
                    ),
                )
                if not points:
                    # Permit exact warm-cache lookup only. New rays remain forbidden;
                    # optional screening must not discard reusable final windows.
                    rays, points = 0, 1
                g = build_grid(
                    engine.engine, h, spacing, rays, points, checkpoint=engine.check
                )
                if g.complete_scheduled_grid:
                    engine.ctx.store.checkpoint(
                        engine.ctx.job,
                        key,
                        {
                            "grid": g.model_dump(mode="json"),
                            "cost": {
                                k: x - before_grid[k]
                                for k, x in engine.engine.counters().items()
                            },
                        },
                    )
            if not saved and g.complete_scheduled_grid:
                engine.created_grids.add(key)
            surface = engine.terrain.sample(
                TerrainRequest(
                    location=h.location,
                    policy=h.policy,
                    preferred_resolution_m=h.preferred_resolution_m,
                )
            )
            observer = (
                prepare_observer(surface.selected, height).observer
                if surface.selected
                else None
            )
            self.grids[role], self.observers[role] = g, observer
            shared[height] = (g, observer)
        self.preparation_seconds = time.perf_counter() - start
        self.new_grid_resources = {
            k: v - before[k] for k, v in engine.engine.counters().items()
        }

    def __call__(self, utc):
        import time
        from app.science.astronomy import calculate

        start = time.perf_counter()
        values = []
        for role in self.roles:
            obs = self.observers[role]
            if obs is None:
                continue
            direction = getattr(
                calculate(
                    self.engine.session, obs, utc, self.engine.request_correction
                ),
                role,
            )
            lookup = (
                self.grids[role].lookup(direction.azimuth_deg)
                if direction.azimuth_deg is not None
                else {"elevation_deg": None}
            )
            if lookup["elevation_deg"] is not None:
                values.append(
                    direction.elevation_deg
                    - lookup["elevation_deg"]
                    - (self.margin if role == "earth" else 0)
                )
        self.query_seconds += time.perf_counter() - start
        self.queries += 1
        # Unknown directions have no favorable ordering evidence, never NOT_MET.
        return min(values) if len(values) == len(self.roles) else -1000000.0

    def report(self):
        return {
            "strategy": "HORIZON_GRID",
            "reason_codes": (
                []
                if all(g.complete_scheduled_grid for g in self.grids.values())
                else ["GRID_SCREENING_INCOMPLETE_RESOURCE_LIMIT_OR_UNKNOWN_TERRAIN"]
            ),
            "role": "COARSE_PRIORITY_ONLY_EXACT_FINAL_VERIFICATION",
            "preparation_seconds": self.preparation_seconds,
            "priority_seconds": self.query_seconds,
            "priority_queries": self.queries,
            "grid_checkpoint_reused": self.grid_reused,
            "new_grid_resources": self.new_grid_resources,
            "grids": {
                role: {
                    "identity": g.identity,
                    "source_signature": g.source_signature,
                    "spacing_deg": g.spacing_deg,
                    "request": g.request.model_dump(mode="json"),
                    "complete_scheduled_grid": g.complete_scheduled_grid,
                    "performance": g.performance,
                }
                for role, g in self.grids.items()
            },
        }
