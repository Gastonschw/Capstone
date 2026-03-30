"""
Integrity Analysis API routes.
"""

import json
from typing import List, Optional
from datetime import datetime
from dataclasses import asdict
from fastapi import APIRouter, Body, Depends, Header, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db, AsyncSessionLocal
from models.repository import Repository
from models.integrity_analysis import IntegrityAnalysis
from schemas.integrity_analysis import IntegrityAnalysisResponse, IntegrityAnalysisListItem
from services.integrity_analysis_service import run_integrity_analysis
from services.repository_access import require_analysis_access, require_repository_access
from concurrency import analysis_semaphore

router = APIRouter(prefix="/api/integrity", tags=["integrity-analysis"])


class StartIntegrityAnalysisRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None


def characteristic_report_to_dict(report) -> dict:
    """Convert CharacteristicReport dataclass to dict."""
    return {
        'characteristic': report.characteristic,
        'score': report.score,
        'status': report.status,
        'description': report.description,
        'findings': report.findings,
        'recommendations': report.recommendations
    }


async def run_analysis_task(
    analysis_id: int,
    repository_id: int,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
):
    """Background task to run Integrity analysis. Uses TAMU API with api_key and optional model."""
    async with analysis_semaphore, AsyncSessionLocal() as db:
        # Get analysis and repository
        result = await db.execute(
            select(IntegrityAnalysis).where(IntegrityAnalysis.id == analysis_id)
        )
        analysis = result.scalar_one_or_none()

        result = await db.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        repository = result.scalar_one_or_none()

        if not analysis or not repository:
            return

        try:
            # Update status to processing
            analysis.status = "processing"
            await db.commit()

            # Run the analysis (TAMU API with user's key and optional model)
            analysis_result = await run_integrity_analysis(repository, db, api_key=api_key, model=model)

            # Store results
            analysis.status = "completed"
            analysis.confidentiality_report = json.dumps(
                characteristic_report_to_dict(analysis_result.confidentiality)
            )
            analysis.data_integrity_report = json.dumps(
                characteristic_report_to_dict(analysis_result.data_integrity)
            )
            analysis.authenticity_report = json.dumps(
                characteristic_report_to_dict(analysis_result.authenticity)
            )
            analysis.non_repudiation_report = json.dumps(
                characteristic_report_to_dict(analysis_result.non_repudiation)
            )
            analysis.accountability_report = json.dumps(
                characteristic_report_to_dict(analysis_result.accountability)
            )
            analysis.resistance_report = json.dumps(
                characteristic_report_to_dict(analysis_result.resistance)
            )
            analysis.overall_score = analysis_result.overall_score
            analysis.summary_report = json.dumps(analysis_result.summary)
            analysis.completed_at = datetime.utcnow()

            await db.commit()

        except Exception as e:
            # Log full stack trace for debugging, but return a concise message to the UI
            import logging

            logging.getLogger(__name__).exception(
                "Integrity analysis background task failed for analysis_id=%s repo_id=%s",
                analysis_id,
                repository_id,
            )

            analysis.status = "failed"
            analysis.error_message = str(e) or "Internal Server Error"
            analysis.completed_at = datetime.utcnow()
            await db.commit()


def _get_tamu_api_key(body: Optional[StartIntegrityAnalysisRequest], header_key: Optional[str]) -> Optional[str]:
    """Resolve TAMU API key from request body or header."""
    if body and body.api_key and body.api_key.strip():
        return body.api_key.strip()
    if header_key and header_key.strip():
        return header_key.strip()
    return None


@router.post("/repository/{repository_id}/analyze")
async def start_integrity_analysis(
    repository_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    body: Optional[StartIntegrityAnalysisRequest] = Body(None),
    tamu_api_key: Optional[str] = Header(default=None, alias="X-TAMU-API-Key"),
):
    """Start an Integrity analysis for a repository. Uses TAMU API key from body or header."""
    await require_repository_access(request, db, repository_id)

    api_key = _get_tamu_api_key(body, tamu_api_key)
    model = (body.model and body.model.strip()) if body else None
    try:
        from services.chat_service import resolve_api_key
        resolve_api_key(api_key)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="TAMU API key is required for integrity analysis. Provide it in the analyzer TAMU API Key field or set TAMU_API_KEY in the backend .env. See https://docs.tamus.ai/docs/prod/advanced/api/api-docs"
        ) from e

    # Create analysis record
    analysis = IntegrityAnalysis(
        repository_id=repository_id,
        status="pending"
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # Start background task
    background_tasks.add_task(
        run_analysis_task,
        analysis.id,
        repository_id,
        api_key,
        model,
    )

    return {
        "id": analysis.id,
        "status": analysis.status,
        "message": "Integrity analysis started"
    }


@router.get("/repository/{repository_id}/analyses", response_model=List[IntegrityAnalysisListItem])
async def list_integrity_analyses(
    repository_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List all Integrity analyses for a repository."""
    await require_repository_access(request, db, repository_id)
    result = await db.execute(
        select(IntegrityAnalysis)
        .where(IntegrityAnalysis.repository_id == repository_id)
        .order_by(IntegrityAnalysis.created_at.desc())
    )
    analyses = result.scalars().all()

    return [
        IntegrityAnalysisListItem(
            id=a.id,
            repository_id=a.repository_id,
            status=a.status,
            overall_score=a.overall_score,
            created_at=a.created_at,
            completed_at=a.completed_at
        )
        for a in analyses
    ]


@router.get("/analysis/{analysis_id}", response_model=IntegrityAnalysisResponse)
async def get_integrity_analysis(
    analysis_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific Integrity analysis."""
    analysis = await require_analysis_access(request, db, analysis_id, IntegrityAnalysis)

    return IntegrityAnalysisResponse(
        id=analysis.id,
        repository_id=analysis.repository_id,
        status=analysis.status,
        error_message=analysis.error_message,
        confidentiality_report=json.loads(analysis.confidentiality_report) if analysis.confidentiality_report else None,
        data_integrity_report=json.loads(analysis.data_integrity_report) if analysis.data_integrity_report else None,
        authenticity_report=json.loads(analysis.authenticity_report) if analysis.authenticity_report else None,
        non_repudiation_report=json.loads(analysis.non_repudiation_report) if analysis.non_repudiation_report else None,
        accountability_report=json.loads(analysis.accountability_report) if analysis.accountability_report else None,
        resistance_report=json.loads(analysis.resistance_report) if analysis.resistance_report else None,
        overall_score=analysis.overall_score,
        summary_report=json.loads(analysis.summary_report) if analysis.summary_report else None,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at
    )
