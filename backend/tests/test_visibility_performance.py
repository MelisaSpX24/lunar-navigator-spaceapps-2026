"""No approximate matching: only completed rays ignore total admission allowance."""

import os
import pytest
from test_visibility import fake, Session
from test_horizon import synthetic, req
from app.science.visibility import VisibilityEngine
from app.science.visibility_models import VisibilityRequest
from app.science.kernels import ScienceError


def test_completed_ray_budget_reuse_and_provenance(tmp_path, fake):
    with synthetic(tmp_path) as h:
        e = VisibilityEngine(Session(), h.terrain)
        e.horizon = h
        q = req(max_range_m=100)
        original = e._ray(q, 359.999, [1, 10000])
        before = e.counters()
        changed = type(q).model_validate(q.model_dump() | {"max_total_samples": 1})
        reused = e._ray(changed, 359.999, [0, 0])
        assert reused == original and reused[1] == original[1]
        assert e.counters()["cache_hits"] == before["cache_hits"] + 1
        assert e.counters()["dem_samples"] == before["dem_samples"]
        assert e._ray(changed, 0.0, [0, 0])[0] is None
        assert (
            e.preflight(VisibilityRequest(terrain=q, utc="2026-11-20T08:00:00Z"))[
                "unique_ray_keys"
            ]
            == 130
        )


@pytest.mark.parametrize("missing", [lambda d: True, lambda d: 50 < d < 70])
def test_incomplete_unknown_not_shared_across_budgets(tmp_path, fake, missing):
    with synthetic(tmp_path, missing=missing) as h:
        e = VisibilityEngine(Session(), h.terrain)
        e.horizon = h
        q = req(max_range_m=100)
        ray = e._ray(q, 0.0, [1, 10000])[0]
        assert ray.coverage_status in ("UNKNOWN", "INCOMPLETE")
        q2 = type(q).model_validate(q.model_dump() | {"max_total_samples": 1})
        assert e._ray(q2, 0.0, [0, 0])[0] is None
        assert e._ray(q, 0.0, [0, 0])[0].coverage_status == ray.coverage_status


@pytest.mark.parametrize("change", ["file", "reference", "algorithm"])
def test_source_mutation_or_algorithm_separation(tmp_path, fake, change):
    with synthetic(tmp_path) as h:
        e = VisibilityEngine(Session(), h.terrain)
        e.horizon = h
        q = req(max_range_m=100)
        e._ray(q, 0.0, [1, 10000])
        if change == "algorithm":
            e.namespace += ":different-algorithm"
            assert e._ray(q, 0.0, [0, 0])[0] is None
        else:
            dem = h.terrain.sources["SITE01"].dem
            if change == "file":
                os.utime(dem.ds.name, None)
            else:
                dem.reference = dem.reference.model_copy(
                    update={"raster_sha256": "a" * 64}
                )
            with pytest.raises(ScienceError, match="DEM_SOURCE_CHANGED"):
                e._ray(q, 0.0, [0, 0])
            assert not e.cache


def test_metadata_copy_and_session_guard(tmp_path, fake):
    with synthetic(tmp_path) as h:
        e = VisibilityEngine(Session(), h.terrain)
        first = e._source_metadata()
        first.clear()
        assert e._source_metadata()
    with pytest.raises(ScienceError, match="DEM_SOURCE_UNAVAILABLE"):
        e._source_metadata()


def test_disk_sample_sequence_reused_unchanged(tmp_path, fake, monkeypatch):
    import app.science.visibility as module

    original = module.disk_samples
    calls = []

    def tracked(*args):
        v = original(*args)
        calls.append(v)
        return v

    monkeypatch.setattr(module, "disk_samples", tracked)
    with synthetic(tmp_path) as h:
        e = VisibilityEngine(Session(), h.terrain)
        e.horizon = h
        e.run(
            VisibilityRequest(terrain=req(max_range_m=100), utc="2026-11-20T08:00:00Z")
        )
    assert len(calls) == 4 and calls[0] == calls[2] and calls[1] == calls[3]


def test_new_sidecar_invalidates_session(tmp_path, fake):
    from pathlib import Path

    with synthetic(tmp_path) as h:
        e = VisibilityEngine(Session(), h.terrain)
        e.horizon = h
        e._ray(req(max_range_m=100), 0.0, [1, 1000])
        Path(h.terrain.sources["SITE01"].dem.ds.name + ".aux.xml").write_text(
            "<PAMDataset/>"
        )
        with pytest.raises(ScienceError, match="DEM_SOURCE_CHANGED"):
            e._ray(req(max_range_m=100), 0.0, [0, 0])
