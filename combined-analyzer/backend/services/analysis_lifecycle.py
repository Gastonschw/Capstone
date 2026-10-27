"""Submission snapshots and terminal-state handling for analysis jobs."""

import asyncio
from datetime import datetime, timezone
from functools import wraps

from fastapi import HTTPException
from sqlalchemy import update

from database import AsyncSessionLocal
from models.compliance_analysis import ComplianceAnalysis
from models.correctness_analysis import CorrectnessAnalysis
from models.erd_analysis import ERDAnalysis
from models.integrity_analysis import IntegrityAnalysis
from models.maintainability_analysis import MaintainabilityAnalysis
from models.usability_analysis import UsabilityAnalysis

ANALYSIS_MODELS = (
    ERDAnalysis, IntegrityAnalysis, ComplianceAnalysis, CorrectnessAnalysis,
    UsabilityAnalysis, MaintainabilityAnalysis,
)


def snapshot_selected_files(repository, analysis_type):
    """Validate selected sources before creating a job, and freeze their identities."""
    selected_files = [
        {"file_path": item.file_path, "file_type": item.file_type}
        for item in repository.discovered_files
        if getattr(item, f"is_selected_{analysis_type}")
    ]
    if not selected_files:
        raise HTTPException(status_code=400, detail="Select at least one file before starting analysis.")
    if analysis_type == "erd":
        from services.erd_analysis_service import validate_selected_files
    else:
        from services.integrity_analysis_service import validate_selected_files
    try:
        validate_selected_files(repository.local_path, selected_files)
    except (ValueError, OSError, UnicodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return selected_files


async def mark_analysis_failed(session, model, analysis_id, error):
    """Discard a failed transaction before recording the job's terminal state."""
    await session.rollback()
    await session.execute(
        update(model)
        .where(model.id == analysis_id, model.status.in_(("pending", "processing")))
        .values(
            status="failed",
            error_message=str(error) or "Analysis was cancelled before completion.",
            completed_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()


def tracked_analysis(model):
    """Cover failures and cancellation, including while waiting for concurrency."""
    def decorate(worker):
        @wraps(worker)
        async def run(analysis_id, *args, **kwargs):
            try:
                return await worker(analysis_id, *args, **kwargs)
            except (Exception, asyncio.CancelledError) as exc:
                async with AsyncSessionLocal() as session:
                    await mark_analysis_failed(session, model, analysis_id, exc)
                if isinstance(exc, asyncio.CancelledError):
                    raise
        return run
    return decorate


async def recover_interrupted_analyses(session):
    """Run once at startup to terminate jobs left unfinished by a prior process."""
    completed_at = datetime.now(timezone.utc)
    for model in ANALYSIS_MODELS:
        await session.execute(
            update(model)
            .where(model.status.in_(("pending", "processing")))
            .values(
                status="failed",
                error_message="Analysis interrupted by a server restart. Start a new analysis to retry.",
                completed_at=completed_at,
            )
        )
    await session.commit()
