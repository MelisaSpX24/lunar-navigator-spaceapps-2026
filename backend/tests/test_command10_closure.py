"""Closure regressions: hint isolation, per-candidate origin and partial adapters."""

import json
from pathlib import Path
from copy import deepcopy
from datetime import timedelta
import pytest
from test_visibility import fake
from app.science.temporal_optimizer_models import TemporalOptimizationRequest
from app.science.window_models import WindowSearchResult
from app.services.optimizer_support import hint_compatible


def catalog():
    base = Path("data_pipeline/evidence")
    q = TemporalOptimizationRequest.model_validate(
        json.loads((base / "command-09-temporal-optimizer.json").read_text())[
            "live_result"
        ]["request"]
    )
    h = WindowSearchResult.model_validate(
        json.loads((base / "command-07-windows.json").read_text())[
            "extended_candidate_search"
        ]["event_search"]
    )
    return q, h


@pytest.mark.parametrize(
    "change",
    [
        "none",
        "coordinate",
        "interval",
        "requirements",
        "height",
        "threshold",
        "correction",
        "source",
        "kernel",
        "algorithm",
    ],
)
def test_historical_hint_exact_admission(change):
    canonical, hint = catalog()
    q = canonical.model_copy(deep=True)
    sources = deepcopy(hint.source_evidence)
    if change == "coordinate":
        q.baseline_analysis.site.latitude_deg += 0.001
    if change == "interval":
        q.search_end_utc -= timedelta(days=1)
    if change == "requirements":
        q.baseline_analysis.operation.requirements.min_sun_visible_s = 7200
    if change == "height":
        q.window_template.visibility.solar_height_above_surface_m = 2
    if change == "threshold":
        q.window_template.solar_fraction = 0.8
    if change == "correction":
        q.window_template.visibility.correction = "LT+S"
    if change == "source":
        sources["dem"]["SITE01"]["reference"]["raster_sha256"] = "f" * 64
    if change == "kernel":
        sources["kernel_ids"][0] = "different:" + "f" * 64
    if change == "algorithm":
        hint.schema_version = "different-algorithm"
    assert hint_compatible(q, canonical, hint, sources) is (change == "none")


def test_candidate_specific_live_recorded_mixed(monkeypatch):
    from test_temporal_optimizer import fixture_window
    from app.services.scientific_runner import temporal_batch, operation
    import app.services.optimizer_support as support

    q, _ = catalog()
    q.search_end_utc = q.search_start_utc + timedelta(days=1)
    monkeypatch.setattr(
        support,
        "historical_hints",
        lambda *a: (
            [],
            {"historical_hint_status": "REJECTED_SCENARIO_OR_SOURCE_MISMATCH"},
        ),
    )

    class Budget:
        calls = reused = i = 0

        def used(self):
            return {
                "visibility_evaluations": self.calls,
                "attempted_rays": self.calls * 130,
            }

        def evaluate(self, a, w, policy):
            calls, reused = [(1, 0), (0, 2), (1, 1), (1, 0)][self.i]
            self.i += 1
            self.calls += calls
            self.reused += reused
            r = fixture_window(q, a.time.start_utc)
            return operation(a, r, policy), r

    class Context:
        def update(self, *a, **kw):
            pass

        def capture(self, *a):
            pass

    r = temporal_batch(q, Budget(), Context(), 4)
    cs = [r["baseline"]] + r["candidates"]
    assert [c["evidence_mode"] for c in cs] == ["LIVE", "RECORDED", "LIVE", "LIVE"]
    assert [c["resource_consumption"]["origin_detail"] for c in cs] == [
        "LIVE",
        "RECORDED",
        "MIXED_LIVE_AND_RECORDED",
        "LIVE",
    ]
    assert [c["resource_consumption"]["new_visibility_evaluations"] for c in cs] == [
        1,
        0,
        1,
        1,
    ]
    assert [c["resource_consumption"]["checkpoint_lookups"] for c in cs] == [0, 2, 1, 0]


def test_partial_window_cannot_masquerade_completed_analysis():
    from app.services.scientific_runner import adapt_analysis, operation

    q, _ = catalog()
    w = WindowSearchResult.model_validate(
        json.loads(Path("data_pipeline/evidence/command-07-windows.json").read_text())[
            "pilot"
        ]
    )
    w.execution_status = "PARTIAL"
    op = operation(q.baseline_analysis, w, q.evaluation_policy)
    with pytest.raises(ValueError, match="PARTIAL_WINDOWS"):
        adapt_analysis(q.baseline_analysis, w, op, "PRECOMPUTED", "test")


def test_grid_is_used_for_priority_but_final_windows_remain_exact(
    tmp_path, fake, monkeypatch
):
    from types import SimpleNamespace as NS
    from test_visibility import Session
    from test_horizon import synthetic, req
    from app.science.visibility import VisibilityEngine
    from app.services.scientific_runner import BudgetedEngine, temporal_batch
    from app.services.optimizer_support import GridPriority
    from app.services.models import ResourcePolicy
    from app.jobs.store import JobStore
    from app.jobs.manager import JobManager, JobContext
    import app.services.optimizer_support as support
    import app.science.astronomy as astronomy

    monkeypatch.setattr(
        support,
        "historical_hints",
        lambda *a: (
            [],
            {"historical_hint_status": "REJECTED_SCENARIO_OR_SOURCE_MISMATCH"},
        ),
    )
    monkeypatch.setattr(
        astronomy,
        "calculate",
        lambda *a: NS(
            sun=NS(azimuth_deg=0.5, elevation_deg=2),
            earth=NS(azimuth_deg=180, elevation_deg=3),
        ),
    )
    q, _ = catalog()
    q.window_template.visibility.terrain = req(max_range_m=100)
    q.window_template.duration_s = q.baseline_analysis.time.duration_s = 3600
    q.window_template.step_s = 3600
    q.search_end_utc = q.search_start_utc + timedelta(hours=3)
    q.coarse_start_step_s = 3600
    monkeypatch.setattr(astronomy, "utc_to_et", lambda session, utc: utc.timestamp())
    q.max_detailed_candidates = 3
    with synthetic(tmp_path) as h:
        session = Session()
        session.records = []
        engine = VisibilityEngine(session, h.terrain, 1024)
        engine.horizon = h
        store = JobStore(tmp_path / "db")
        j = store.submit("TEMPORAL", {}).job_id
        ctx = JobContext(JobManager(store, None), j)
        guard = BudgetedEngine(engine, ResourcePolicy(), ctx)
        guard.request_correction = "NONE"
        priority = GridPriority(q, guard, 1.0)
        result = temporal_batch(q, guard, ctx, 3, geometry_priority=priority)
        assert priority.queries == 2
        assert result["discovery"]["coarse_screened_candidates"] == 2
        assert priority.report()["new_grid_resources"]["completed_rays"] == 360
        assert result["baseline"]["evidence_mode"] == "LIVE"
        assert guard.calls >= 3 and result["detailed_completed_including_baseline"] == 3
        assert all(c["evidence_sha256"] for c in result["candidates"])
        old_identity = priority.grids["sun"].identity
        q.window_template.visibility.solar_height_above_surface_m = 2
        other = GridPriority(q, guard, 1.0)
        assert other.grids["sun"].identity != old_identity
        # Provenance mismatch never admits an old grid as an exact scientific ray.
        assert not other.grids["sun"].lookup(0.5)["strict_visibility_evidence"]
        used = guard.used()
        guard.resources = ResourcePolicy(
            max_horizon_rays=used["attempted_rays"],
            max_terrain_samples=used["dem_samples"],
        )
        limited = GridPriority(q, guard, 0.5)
        assert limited.grids["sun"].lookup(0.5)["kind"] == "UNKNOWN"
        assert not limited.grids["sun"].complete_scheduled_grid
        assert all(
            guard.used()[key] == used[key]
            for key in ("attempted_rays", "completed_rays", "dem_samples")
        )
        assert limited.report()["reason_codes"]


def test_local_diverse_selection_covers_separated_regions():
    from types import SimpleNamespace as NS
    from app.optimization.local_site_optimizer import select_detailed, GEOD
    from app.optimization.local_site_models import LocalSiteCandidate
    from app.models.analysis import Coordinates

    q, _ = catalog()
    base = q.baseline_analysis.site
    candidates = []
    for index, (bearing, distance, slope) in enumerate(
        [(0, 100, 1), (1, 110, 1.1), (180, 4500, 2), (90, 3000, 3)]
    ):
        lon, lat, _ = GEOD.fwd(
            base.longitude_deg_east, base.latitude_deg, bearing, distance
        )
        candidates.append(
            LocalSiteCandidate(
                candidate_id=str(index),
                location=Coordinates(latitude_deg=lat, longitude_deg_east=lon % 360),
                distance_m=distance,
                bearing_deg=bearing,
                stage="ELIGIBLE_FOR_DETAIL",
                terrain={"eligible": True, "slope_deg": slope, "resolution_m": [5, 5]},
            )
        )
    old = select_detailed(
        candidates, NS(selection_strategy="SLOPE_ONLY", max_detailed_candidates=3)
    )
    new = select_detailed(
        candidates, NS(selection_strategy="TERRAIN_DIVERSE", max_detailed_candidates=3)
    )
    assert [x.candidate_id for x in old] == ["0", "1"]
    assert [x.candidate_id for x in new] == ["0", "2"]
    assert new == select_detailed(
        candidates, NS(selection_strategy="TERRAIN_DIVERSE", max_detailed_candidates=3)
    )


@pytest.mark.parametrize("change", ["missing", "source_sha", "malformed"])
def test_recorded_catalog_integrity_guard(tmp_path, monkeypatch, request_data, change):
    import app.services.recorded as recorded
    from app.services.models import AnalysisJobRequest

    original = json.loads(recorded.CATALOG.read_text())
    path = tmp_path / "catalog.json"
    if change == "source_sha":
        original["live_windows"][0]["source_evidence"]["dem"]["SITE01"]["reference"][
            "raster_sha256"
        ] = ("f" * 64)
        path.write_text(json.dumps(original))
    elif change == "malformed":
        path.write_text("{invalid")
    monkeypatch.setattr(recorded, "CATALOG", path)
    request_data["options"] = {"include_full_horizon": False}
    q = AnalysisJobRequest(analysis=request_data, registration="PROTOTYPE")
    assert recorded.find_recorded(q) is None


@pytest.mark.parametrize("policy", ["STRICT_EVIDENCE", "PROTOTYPE_SAMPLED_ESTIMATE"])
@pytest.mark.parametrize(
    "profile,requirements,expected,score",
    [
        ("SOLAR_POWERED_EXPERIMENT", {"min_sun_visible_s": 7200}, "NOT_MET", 0),
        ("EARTH_DATA_TRANSMISSION", {"min_earth_continuous_s": 3600}, "MET", 100),
        ("SHORT_SURFACE_OBSERVATION", {"min_earth_continuous_s": 3600}, "MET", 100),
        (
            "CUSTOM_OPERATION",
            {"require_simultaneous": True, "min_joint_continuous_s": 1800},
            "NOT_MET",
            0,
        ),
    ],
)
def test_four_profiles_recorded_http_and_explicit_requirements(
    request_data, policy, profile, requirements, expected, score
):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.models.analysis import AnalysisResult

    request_data["operation"] = {"profile": profile, "requirements": requirements}
    request_data["options"] = {"include_full_horizon": False}
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/analyses",
            params={
                "mode": "recorded",
                "registration": "PROTOTYPE",
                "evaluation_policy": policy,
            },
            json=request_data,
        )
        assert response.status_code == 200, response.text
        r = AnalysisResult.model_validate(response.json())
        assert (
            r.data_origin == "PRECOMPUTED"
            and r.sources
            and r.execution_status == "COMPLETED"
        )
        assert r.decision.status == (
            expected if policy == "PROTOTYPE_SAMPLED_ESTIMATE" else "INCOMPLETE"
        )
        assert r.score.value == (
            score if policy == "PROTOTYPE_SAMPLED_ESTIMATE" else None
        )
        for key, value in requirements.items():
            assert getattr(r.request.operation.requirements, key) == value
        assert not r.horizons and r.score.model_version == "24and28-planning-score-v1"


def test_resume_allows_discovery_admission_but_rejects_scientific_changes(
    tmp_path, request_data
):
    import time
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.services.scientific_runner import template
    from app.models.analysis import AnalysisRequest

    def runner(*args):
        return {"data_origin": "TEST_FIXTURE"}, "PARTIAL"

    a = AnalysisRequest.model_validate(request_data)
    base = {
        "baseline_analysis": request_data,
        "window_template": template(a, "PROTOTYPE").model_dump(mode="json"),
    }
    with TestClient(create_app(job_path=tmp_path / "db", runner=runner)) as c:
        for endpoint, body in [
            ("/local", {"optimization": base}),
            (
                "/temporal",
                {
                    "optimization": base
                    | {
                        "search_start_utc": a.time.start_utc.isoformat(),
                        "search_end_utc": (
                            a.time.start_utc + timedelta(days=1)
                        ).isoformat(),
                    }
                },
            ),
        ]:
            path = "/api/v1/optimizations" + endpoint
            first = c.post(path, json=body)
            assert first.status_code == 202
            job = first.json()["job_id"]
            for _ in range(100):
                if c.get("/api/v1/jobs/" + job).json()["status"] == "PARTIAL":
                    break
                time.sleep(0.01)
            new = deepcopy(body)
            new["resume_from"] = job
            if endpoint == "/local":
                new["optimization"].update(
                    selection_strategy="TERRAIN_DIVERSE", max_detailed_candidates=4
                )
            else:
                new.update(screening_strategy="HORIZON_GRID", grid_spacing_deg=0.5)
            assert c.post(path, json=new).status_code == 202
            bad = deepcopy(new)
            bad["optimization"]["baseline_analysis"]["operation"]["requirements"][
                "min_sun_visible_s"
            ] = 7200
            assert c.post(path, json=bad).status_code == 409


def test_historical_hint_catalog_is_integrity_pinned(tmp_path, monkeypatch):
    from types import SimpleNamespace as NS
    import app.services.optimizer_support as support

    q, hint = catalog()
    for name in ("command-07-windows.json", "command-09-temporal-optimizer.json"):
        (tmp_path / name).write_bytes((support.EVIDENCE_ROOT / name).read_bytes())
    fake_engine = NS(
        engine=NS(
            _source_metadata=lambda: hint.source_evidence["dem"],
            session=NS(
                records=[
                    {"filename": s.split(":")[0], "sha256": s.split(":")[1]}
                    for s in hint.source_evidence["kernel_ids"]
                ]
            ),
        )
    )
    monkeypatch.setattr(support, "EVIDENCE_ROOT", tmp_path)
    assert len(support.historical_hints(q, fake_engine)[0]) == 1
    p = tmp_path / "command-07-windows.json"
    data = json.loads(p.read_text())
    data["extended_candidate_search"]["event_search"]["request"]["step_s"] = 3600
    p.write_text(json.dumps(data))
    hints, audit = support.historical_hints(q, fake_engine)
    assert not hints and audit["historical_hint_status"] == "REJECTED_CATALOG_INTEGRITY"
