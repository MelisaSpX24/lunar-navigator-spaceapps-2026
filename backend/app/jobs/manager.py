"""One owned scientific thread; durable SQLite queue is the source of truth."""

import fcntl, threading, secrets, time
from app.jobs.store import JobStore, StoreError
from app.jobs.models import ScientificJobProgress


class JobStop(Exception):
    def __init__(self, code, state="PARTIAL"):
        self.code, self.state = code, state


class JobContext:
    def __init__(self, manager, job):
        self.manager, self.store, self.job = manager, manager.store, job
        self.started = time.monotonic()
        self.latest = None
        self.candidate_results = []
        self.progress = ScientificJobProgress().model_dump()

    def check(self):
        if self.manager.stopping.is_set():
            raise JobStop("WORKER_SHUTDOWN", "INTERRUPTED")
        if self.store.status(self.job).status == "CANCEL_REQUESTED":
            raise JobStop("USER_CANCELLED", "CANCELLED")

    def update(self, stage, **values):
        self.check()
        self.progress.update(stage=stage, **values)
        self.store.progress(self.job, self.progress)

    def capture(self, value):
        self.latest = value | (
            {"completed_candidate_evidence": list(self.candidate_results)}
            if self.candidate_results
            else {}
        )


class JobManager:
    def __init__(self, store, runner):
        self.store, self.runner = store, runner
        self.owner = secrets.token_hex(16)
        self.stopping = threading.Event()
        self.thread = None
        self.lock = None

    def start(self):
        if self.thread:
            return
        self.lock = open(str(self.store.path) + ".worker.lock", "a")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            self.lock = None
            raise RuntimeError("SCIENTIFIC_WORKER_ALREADY_OWNED")
        self.store.recover()
        self.thread = threading.Thread(
            target=self.loop, name="scientific-worker", daemon=True
        )
        self.thread.start()

    def stop(self):
        self.stopping.set()
        if self.thread:
            self.thread.join(timeout=120)
        if self.thread and self.thread.is_alive():
            return  # retain ownership until process exits
        if self.lock:
            fcntl.flock(self.lock, fcntl.LOCK_UN)
            self.lock.close()
            self.lock = None

    def finish(self, job, status, result=None, **kwargs):
        try:
            self.store.finish(job, status, result, **kwargs)
        except StoreError:
            self.store.finish(
                job,
                "FAILED",
                None,
                error={
                    "code": "RESULT_STORAGE_LIMIT",
                    "error_class": "StoreError",
                    "message": "Result could not be persisted within storage limits.",
                },
                reasons=["RESULT_STORAGE_LIMIT"],
            )

    def loop(self):
        while not self.stopping.is_set():
            job = self.store.claim(self.owner)
            if job is None:
                self.stopping.wait(0.05)
                continue
            ctx = JobContext(self, job)
            try:
                row = self.store.row(job)
                value, status = self.runner(
                    row["kind"], __import__("json").loads(row["payload"]), ctx
                )
                ctx.check()
                ctx.update("PERSISTING_RESULT")
                self.finish(job, status, value)
            except JobStop as exc:
                self.finish(job, exc.state, ctx.latest, reasons=[exc.code])
            except Exception as exc:
                # Keep error class/code, never expose arbitrary local paths or secrets.
                self.finish(
                    job,
                    "FAILED",
                    ctx.latest,
                    error={
                        "code": getattr(exc, "code", "SCIENTIFIC_EXECUTION_FAILED"),
                        "error_class": type(exc).__name__,
                        "message": "Scientific execution failed; inspect server diagnostics.",
                    },
                    reasons=[getattr(exc, "code", "SCIENTIFIC_EXECUTION_FAILED")],
                )
