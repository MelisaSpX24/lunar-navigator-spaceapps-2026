"""Explicitly enabled, single-owner scientific prototype service."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router


def create_app(*, job_path=None, runner=None, queue_capacity=4):
    enabled = job_path is not None or os.environ.get("LUNAR_ENABLE_JOBS") == "1"

    @asynccontextmanager
    async def lifespan(application):
        if enabled:
            from app.jobs.store import JobStore
            from app.jobs.manager import JobManager
            from app.services.scientific_runner import run_science

            path = job_path or os.environ.get(
                "LUNAR_JOB_DB", "/workspace/data/lunar-jobs/jobs.sqlite"
            )
            manager = JobManager(
                JobStore(path, max_active=queue_capacity), runner or run_science
            )
            manager.runner_requires_sources = runner is None
            manager.start()
            application.state.manager = manager
        try:
            yield
        finally:
            if application.state.manager:
                application.state.manager.stop()

    application = FastAPI(
        title="24&28 Lunar Navigator Backend", version="0.2.0", lifespan=lifespan
    )
    origins = [
        x.strip()
        for x in os.environ.get("LUNAR_ALLOWED_ORIGINS", "").split(",")
        if x.strip()
    ]
    if origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    @application.middleware("http")
    async def bounded_body(request, call_next):
        if request.method == "POST":
            chunks = []
            size = 0
            async for part in request.stream():
                size += len(part)
                if size > 131072:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": {"code": "REQUEST_SIZE_LIMIT"}},
                    )
                chunks.append(part)
            request._body = b"".join(chunks)
        return await call_next(request)

    application.state.manager = None
    application.include_router(router)
    return application


app = create_app()
