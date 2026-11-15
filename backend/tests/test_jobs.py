"""Durable real JobManager tests with deterministic infrastructure-only runners."""

import json, time, threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from app.jobs.store import JobStore, StoreError
from app.jobs.manager import JobManager, JobStop


def wait(store, job, states, timeout=3):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        s = store.status(job)
        if s.status in states:
            return s
        time.sleep(0.01)
    raise AssertionError(store.status(job))


def test_concurrent_queue_persistence_results_and_corruption(tmp_path):
    path = tmp_path / "jobs.sqlite"
    store = JobStore(path, max_active=2)

    def submit(i):
        try:
            return store.submit("ANALYSIS", {"i": i}).job_id
        except StoreError:
            return None

    with ThreadPoolExecutor(max_workers=6) as pool:
        ids = list(pool.map(submit, range(10)))
    ids = [i for i in ids if i]
    assert len(ids) == len(set(ids)) == 2
    m = JobManager(
        store,
        lambda kind, payload, ctx: (
            {"value": payload["i"], "data_origin": "TEST_FIXTURE"},
            "COMPLETED",
        ),
    )
    m.start()
    try:
        for i in ids:
            assert wait(store, i, {"COMPLETED"}).result_available
        with pytest.raises(RuntimeError, match="ALREADY_OWNED"):
            JobManager(JobStore(path), m.runner).start()
    finally:
        m.stop()
    reopened = JobStore(path)
    assert reopened.result(ids[0])["data_origin"] == "TEST_FIXTURE"
    with reopened.connect() as db:
        db.execute("UPDATE jobs SET result=? WHERE id=?", ('{"tampered":true}', ids[0]))
    with pytest.raises(StoreError, match="HASH"):
        reopened.result(ids[0])


def test_restart_marks_running_interrupted_and_preserves_queued(tmp_path):
    s = JobStore(tmp_path / "jobs.sqlite")
    a = s.submit("ANALYSIS", {}).job_id
    b = s.submit("ANALYSIS", {}).job_id
    assert s.claim("old-worker") == a
    s.recover()
    assert s.status(a).status == "INTERRUPTED" and s.status(b).status == "QUEUED"


def test_cancel_queued_running_and_partial_evidence(tmp_path):
    s = JobStore(tmp_path / "jobs.sqlite")
    j = s.submit("ANALYSIS", {}).job_id
    assert s.cancel(j).status == "CANCELLED"
    j = s.submit("ANALYSIS", {}).job_id

    ready = threading.Event()
    release = threading.Event()

    def runner(k, p, ctx):
        ctx.capture({"completed_samples": 1})
        ready.set()
        assert release.wait(3), "test checkpoint was not released"
        while True:
            ctx.check()
            time.sleep(0.005)

    m = JobManager(s, runner)
    m.start()
    try:
        wait(s, j, {"RUNNING"})
        assert ready.wait(1)
        assert s.cancel(j).status == "CANCEL_REQUESTED"
        release.set()
        assert wait(s, j, {"CANCELLED"}).result_available
        assert s.result(j)["completed_samples"] == 1
    finally:
        release.set()
        m.stop()


def test_checkpoint_hash_size_and_failures(tmp_path):
    s = JobStore(tmp_path / "jobs.sqlite", max_bytes=100)
    j = s.submit("ANALYSIS", {}).job_id
    s.checkpoint(j, "a", {"value": 1})
    assert s.load_checkpoint(j, "a") == {"value": 1}
    with s.connect() as db:
        db.execute("UPDATE checkpoints SET payload=?", ('{"value":2}',))
    with pytest.raises(StoreError, match="HASH"):
        s.load_checkpoint(j, "a")
    with pytest.raises(StoreError, match="SIZE"):
        s.checkpoint(j, "large", {"value": "x" * 200})
    m = JobManager(s, lambda *args: (_ for _ in ()).throw(ValueError("private/path")))
    m.start()
    try:
        status = wait(s, j, {"FAILED"})
        assert status.error.error_class == "ValueError"
        assert "private" not in status.model_dump_json()
    finally:
        m.stop()


def test_oversized_result_does_not_kill_worker(tmp_path):
    s = JobStore(tmp_path / "jobs.sqlite", max_bytes=100)
    m = JobManager(s, lambda *args: ({"large": "x" * 500}, "COMPLETED"))
    m.start()
    try:
        a = s.submit("ANALYSIS", {}).job_id
        assert wait(s, a, {"FAILED"}).error.code == "RESULT_STORAGE_LIMIT"
        b = s.submit("ANALYSIS", {}).job_id
        assert wait(s, b, {"FAILED"}).error.code == "RESULT_STORAGE_LIMIT"
        assert m.thread.is_alive()
    finally:
        m.stop()


def test_cancel_before_final_commit_has_atomic_priority(tmp_path):
    s = JobStore(tmp_path / "db")
    job = s.submit("ANALYSIS", {}).job_id
    assert s.claim("owner") == job
    assert s.cancel(job).status == "CANCEL_REQUESTED"
    s.finish(job, "COMPLETED", {"execution_evidence": "TEST_FIXTURE"})
    result = s.status(job)
    assert result.status == "CANCELLED" and result.progress.stage == "CANCELLED"
    assert "USER_CANCELLED" in result.reason_codes
    queued = s.submit("ANALYSIS", {}).job_id
    result = s.cancel(queued)
    assert result.status == result.progress.stage == "CANCELLED"
    assert "USER_CANCELLED" in result.reason_codes
