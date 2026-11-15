"""Actual window/visibility chain with synthetic kernels for checkpoint invariants."""

import pytest
from test_visibility import fake, Session
from test_horizon import synthetic, req
from app.science.visibility import VisibilityEngine
from app.science.visibility_models import VisibilityRequest
from app.jobs.store import JobStore, StoreError
from app.jobs.manager import JobManager, JobContext, JobStop
from app.services.scientific_runner import BudgetedEngine
from app.services.models import ResourcePolicy


def test_resume_exact_sample_and_source_binding(tmp_path, fake):
    with synthetic(tmp_path) as h:
        session = Session()
        session.records = [{"filename": "synthetic", "sha256": "a" * 64}]
        store = JobStore(tmp_path / "jobs.sqlite")
        old = store.submit("ANALYSIS", {}).job_id
        manager = JobManager(store, None)
        ctx = JobContext(manager, old)
        engine = VisibilityEngine(session, h.terrain)
        engine.horizon = h
        first = BudgetedEngine(engine, ResourcePolicy(), ctx)
        q = VisibilityRequest(terrain=req(max_range_m=100), utc="2026-11-20T08:00:00Z")
        result = first.run(q)
        assert first.calls == 1 and store.checkpoint_keys(old)
        new = store.submit("ANALYSIS", {}).job_id
        engine2 = VisibilityEngine(session, h.terrain)
        engine2.horizon = h
        second = BudgetedEngine(
            engine2, ResourcePolicy(), JobContext(manager, new), old
        )
        reused = second.run(q)
        assert result == reused and second.calls == 0 and second.reused == 1
        assert second.used()["attempted_rays"] == first.used()["attempted_rays"]
        assert first.new_resources()["attempted_rays"] == 130
        assert second.new_resources()["attempted_rays"] == 0
        assert second.resume_cost["attempted_rays"] == 130
        assert all(
            second.used()[key]
            == second.new_resources()[key] + second.resume_cost.get(key, 0)
            for key in second.new_resources()
        )

        # A different epoch cannot use the previous scientific sample.
        changed = VisibilityRequest.model_validate(
            q.model_dump() | {"utc": "2026-11-20T09:00:00Z"}
        )
        second.run(changed)
        assert second.calls == 1
        session.records = [{"filename": "synthetic", "sha256": "b" * 64}]
        other = store.submit("ANALYSIS", {}).job_id
        third = BudgetedEngine(
            engine2, ResourcePolicy(), JobContext(manager, other), old
        )
        third.run(q)
        assert third.calls == 1 and third.reused == 0


def test_visibility_and_wall_limits_safe(tmp_path, fake):
    with synthetic(tmp_path) as h:
        session = Session()
        session.records = []
        store = JobStore(tmp_path / "db")
        job = store.submit("ANALYSIS", {}).job_id
        ctx = JobContext(JobManager(store, None), job)
        e = VisibilityEngine(session, h.terrain)
        e.horizon = h
        guard = BudgetedEngine(e, ResourcePolicy(max_visibility_evaluations=1), ctx)
        q = VisibilityRequest(terrain=req(max_range_m=100), utc="2026-11-20T08:00:00Z")
        guard.run(q)
        different = VisibilityRequest.model_validate(
            q.model_dump() | {"utc": "2026-11-20T09:00:00Z"}
        )
        with pytest.raises(JobStop):
            guard.run(different)
        ctx.started -= 1000
        with pytest.raises(JobStop):
            guard.check()


def test_chained_resume_materializes_prior_evidence(tmp_path, fake):
    with synthetic(tmp_path) as h:
        session = Session()
        session.records = []
        s = JobStore(tmp_path / "db")
        manager = JobManager(s, None)
        q = VisibilityRequest(terrain=req(max_range_m=100), utc="2026-11-20T08:00:00Z")
        previous = None
        for index in range(3):
            payload = {"resume_from": previous} if previous else {}
            job = s.submit("ANALYSIS", payload).job_id
            e = VisibilityEngine(session, h.terrain)
            e.horizon = h
            guard = BudgetedEngine(
                e, ResourcePolicy(), JobContext(manager, job), previous
            )
            guard.run(q)
            assert s.checkpoint_keys(job)
            assert (
                guard.used()["attempted_rays"] == guard.used()["completed_rays"] == 130
            )
            if index:
                assert guard.calls == 0 and guard.reused == 1
            previous = job
