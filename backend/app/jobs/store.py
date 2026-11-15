"""SQLite WAL/FULL transactions: metadata, results and hashed checkpoints commit atomically."""

import sqlite3, json, hashlib, secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from app.jobs.models import ScientificJobStatus, ScientificJobProgress

LIMITATIONS = [
    "Single local scientific worker; server downtime suspends processing.",
    "Prototype evidence is not independent physical certification.",
]


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class StoreError(RuntimeError):
    pass


class JobStore:
    def __init__(self, path, max_active=4, max_jobs=64, max_bytes=8 * 1024 * 1024):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_active, self.max_jobs, self.max_bytes = max_active, max_jobs, max_bytes
        with self.connect() as db:
            db.executescript(
                """CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,kind TEXT NOT NULL,status TEXT NOT NULL,identity TEXT NOT NULL,payload TEXT NOT NULL,created TEXT NOT NULL,started TEXT,updated TEXT NOT NULL,finished TEXT,progress TEXT NOT NULL,reasons TEXT NOT NULL,error TEXT,result TEXT,result_hash TEXT,owner TEXT);
            CREATE TABLE IF NOT EXISTS checkpoints(job_id TEXT NOT NULL,key TEXT NOT NULL,payload TEXT NOT NULL,hash TEXT NOT NULL,PRIMARY KEY(job_id,key));"""
            )

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def submit(self, kind, payload):
        raw = canonical(payload)
        if len(raw) > 131072:
            raise StoreError("REQUEST_TOO_LARGE")
        t = now()
        ident = digest({"kind": kind, "payload": payload})
        job = secrets.token_hex(16)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute(
                "SELECT count(*) FROM jobs WHERE status IN ('QUEUED','RUNNING','CANCEL_REQUESTED')"
            ).fetchone()[0]
            if count >= self.max_active:
                raise StoreError("QUEUE_CAPACITY_EXCEEDED")
            if db.execute("SELECT count(*) FROM jobs").fetchone()[0] >= self.max_jobs:
                raise StoreError("JOB_STORAGE_CAPACITY_EXCEEDED")
            db.execute(
                "INSERT INTO jobs(id,kind,status,identity,payload,created,updated,progress,reasons) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    job,
                    kind,
                    "QUEUED",
                    ident,
                    raw,
                    t,
                    t,
                    canonical(ScientificJobProgress().model_dump()),
                    "[]",
                ),
            )
        return self.status(job)

    def row(self, job):
        with self.connect() as db:
            r = db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
        if r is None:
            raise KeyError(job)
        return dict(r)

    def status(self, job):
        r = self.row(job)
        return ScientificJobStatus(
            job_id=r["id"],
            job_type=r["kind"],
            status=r["status"],
            request_identity=r["identity"],
            created_at_utc=r["created"],
            started_at_utc=r["started"],
            updated_at_utc=r["updated"],
            finished_at_utc=r["finished"],
            progress=json.loads(r["progress"]),
            reason_codes=json.loads(r["reasons"]),
            limitations=LIMITATIONS,
            result_available=r["result"] is not None,
            error=json.loads(r["error"]) if r["error"] else None,
        )

    def claim(self, owner):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            r = db.execute(
                "SELECT * FROM jobs WHERE status='QUEUED' ORDER BY created,id LIMIT 1"
            ).fetchone()
            if r is None:
                return None
            db.execute(
                "UPDATE jobs SET status='RUNNING',owner=?,started=?,updated=? WHERE id=?",
                (owner, now(), now(), r["id"]),
            )
            return r["id"]

    def recover(self):
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET status='INTERRUPTED',finished=?,updated=?,reasons=? WHERE status IN ('RUNNING','CANCEL_REQUESTED')",
                (now(), now(), '["WORKER_RESTART_INTERRUPTED"]'),
            )

    def progress(self, job, progress):
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET progress=?,updated=? WHERE id=?",
                (canonical(progress), now(), job),
            )

    def finish(self, job, status, result=None, error=None, reasons=()):
        raw = canonical(result) if result is not None else None
        if raw and len(raw.encode()) > self.max_bytes:
            raise StoreError("RESULT_SIZE_LIMIT")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            # Cancellation has priority even if requested during the final atomic calculation.
            current = db.execute(
                "SELECT status FROM jobs WHERE id=?", (job,)
            ).fetchone()[0]
            if current == "CANCEL_REQUESTED":
                status = "CANCELLED"
                reasons = list(dict.fromkeys([*reasons, "USER_CANCELLED"]))
            progress = json.loads(
                db.execute("SELECT progress FROM jobs WHERE id=?", (job,)).fetchone()[0]
            )
            progress["stage"] = status
            if status == "COMPLETED":
                progress["progress_percent"] = 100
            db.execute(
                "UPDATE jobs SET progress=? WHERE id=?", (canonical(progress), job)
            )
            db.execute(
                "UPDATE jobs SET status=?,result=?,result_hash=?,error=?,reasons=?,finished=?,updated=? WHERE id=?",
                (
                    status,
                    raw,
                    digest(result) if raw else None,
                    canonical(error) if error else None,
                    canonical(list(reasons)),
                    now(),
                    now(),
                    job,
                ),
            )

    def cancel(self, job):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            r = db.execute("SELECT status FROM jobs WHERE id=?", (job,)).fetchone()
            if r is None:
                raise KeyError(job)
            if r[0] == "QUEUED":
                db.execute(
                    "UPDATE jobs SET status='CANCELLED',finished=?,updated=?,reasons=?,progress=? WHERE id=?",
                    (
                        now(),
                        now(),
                        '["USER_CANCELLED"]',
                        canonical(
                            ScientificJobProgress(stage="CANCELLED").model_dump()
                        ),
                        job,
                    ),
                )
            elif r[0] == "RUNNING":
                db.execute(
                    "UPDATE jobs SET status='CANCEL_REQUESTED',updated=? WHERE id=?",
                    (now(), job),
                )
        return self.status(job)

    def result(self, job):
        r = self.row(job)
        if r["result"] is None:
            return None
        value = json.loads(r["result"])
        if digest(value) != r["result_hash"]:
            raise StoreError("RESULT_HASH_MISMATCH")
        return value

    def checkpoint(self, job, key, value):
        raw = canonical(value)
        if len(raw.encode()) > self.max_bytes:
            raise StoreError("CHECKPOINT_SIZE_LIMIT")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            size = db.execute(
                "SELECT coalesce(sum(length(payload)),0) FROM checkpoints WHERE job_id=? AND key!=?",
                (job, key),
            ).fetchone()[0]
            if size + len(raw) > 2 * self.max_bytes:
                raise StoreError("CHECKPOINT_STORAGE_LIMIT")
            db.execute(
                "INSERT OR REPLACE INTO checkpoints VALUES(?,?,?,?)",
                (job, key, raw, digest(value)),
            )

    def load_checkpoint(self, job, key):
        with self.connect() as db:
            r = db.execute(
                "SELECT payload,hash FROM checkpoints WHERE job_id=? AND key=?",
                (job, key),
            ).fetchone()
        if not r:
            return None
        value = json.loads(r[0])
        if digest(value) != r[1]:
            raise StoreError("CHECKPOINT_HASH_MISMATCH")
        return value

    def checkpoint_keys(self, job):
        with self.connect() as db:
            return [
                r[0]
                for r in db.execute(
                    "SELECT key FROM checkpoints WHERE job_id=? ORDER BY key", (job,)
                )
            ]
