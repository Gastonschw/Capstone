"""
Combined Analyzer API

FastAPI application that combines ERD Analysis and Integrity Analysis
into a unified platform.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import DATABASE_KIND
from database import init_db
from routers import (
    repositories_router,
    github_router,
    upload_router,
    erd_router,
    integrity_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database on startup."""
    await init_db()
    db_label = "Supabase (Postgres)" if DATABASE_KIND == "postgres" else "SQLite"
    print(f"Database: {db_label}")
    yield


app = FastAPI(
    title="Combined Analyzer API",
    description="Unified ERD and Integrity Analysis Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
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
