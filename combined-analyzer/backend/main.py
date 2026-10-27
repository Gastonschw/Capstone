"""
Combined Analyzer API

FastAPI application that combines ERD Analysis and Integrity Analysis
into a unified platform.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from config import DATABASE_KIND, FRONTEND_URL
from database import init_db, engine, AsyncSessionLocal
from routers import (
    repositories_router,
    github_router,
    upload_router,
    erd_router,
    integrity_router,
    compliance_router,
    correctness_router,
    usability_router,
    maintainability_router,
    chat_router,
    classes_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Migrate and reconcile interrupted jobs before accepting requests."""
    from services.analysis_lifecycle import recover_interrupted_analyses

    # In-process jobs and a local persistent disk require one application worker.
    # Holding a database session lock prevents a second worker from invalidating
    # live jobs during startup recovery.
    async with engine.connect() as guard:
        acquired = await guard.scalar(text("select pg_try_advisory_lock(2710202602)"))
        if not acquired:
            raise RuntimeError("Another analyzer worker is running; deploy exactly one worker")
        try:
            await init_db()
            async with AsyncSessionLocal() as session:
                await recover_interrupted_analyses(session)
            print("Database: Supabase (Postgres)")
            yield
        finally:
            await guard.execute(text("select pg_advisory_unlock(2710202602)"))
    await engine.dispose()


app = FastAPI(
    title="Combined Analyzer API",
    description="Unified ERD and Integrity Analysis Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
_cors_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    FRONTEND_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(repositories_router)
app.include_router(github_router)
app.include_router(upload_router)
app.include_router(erd_router)
app.include_router(integrity_router)
app.include_router(compliance_router)
app.include_router(correctness_router)
app.include_router(usability_router)
app.include_router(maintainability_router)
app.include_router(chat_router)
app.include_router(classes_router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "combined-analyzer",
        "database": DATABASE_KIND,
    }


# Combined analysis endpoint
@app.post("/api/repository/{repository_id}/analyze")
async def start_combined_analysis(
    repository_id: int,
    run_erd: bool = False,
    run_integrity: bool = False,
):
    """
    Start combined analysis for a repository.

    Can run ERD analysis, Integrity analysis, or both in parallel.
    """
    if not run_erd and not run_integrity:
        return {
            "error": "Please specify at least one analysis type (run_erd or run_integrity)"
        }

    results = {}

    # This endpoint just provides a convenient way to trigger both analyses
    # The actual work is done by the individual routers
    return {
        "message": "Use individual endpoints to start analyses",
        "erd_endpoint": f"/api/erd/repository/{repository_id}/analyze" if run_erd else None,
        "integrity_endpoint": f"/api/integrity/repository/{repository_id}/analyze" if run_integrity else None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
