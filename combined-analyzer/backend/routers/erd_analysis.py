"""
ERD Analysis API routes.
"""

import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Body, Depends, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db, AsyncSessionLocal
from models.repository import Repository
from models.erd_analysis import ERDAnalysis, AnalysisStatus
from schemas.erd_analysis import ERDAnalysisResponse, ERDAnalysisListItem
from services.erd_analysis_service import run_erd_analysis
from concurrency import analysis_semaphore

router = APIRouter(prefix="/api/erd", tags=["erd-analysis"])


class StartERDAnalysisRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None


async def run_analysis_task(
    analysis_id: int,
    repository_id: int,
    db_url: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
):
    """Background task to run ERD analysis."""
    async with analysis_semaphore, AsyncSessionLocal() as db:
        # Get analysis and repository
        result = await db.execute(
            select(ERDAnalysis).where(ERDAnalysis.id == analysis_id)
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
            analysis.status = AnalysisStatus.processing.value
            await db.commit()

            # Run the analysis
            workflow_result = await run_erd_analysis(repository, db, api_key=api_key, model=model)

            if workflow_result.success:
                analysis.status = AnalysisStatus.completed.value
                analysis.uml_structure = json.dumps(workflow_result.uml_structure)
                analysis.report = json.dumps(workflow_result.report)
                analysis.coverage_score = workflow_result.coverage_score
            else:
                analysis.status = AnalysisStatus.failed.value
                analysis.error_message = workflow_result.error
                if workflow_result.uml_structure:
                    analysis.uml_structure = json.dumps(workflow_result.uml_structure)

            analysis.completed_at = datetime.utcnow()
            await db.commit()

        except Exception as e:
            analysis.status = AnalysisStatus.failed.value
            analysis.error_message = str(e)
            analysis.completed_at = datetime.utcnow()
            await db.commit()


def _get_tamu_api_key(body: Optional[StartERDAnalysisRequest], header_key: Optional[str]) -> Optional[str]:
    """Resolve TAMU API key from request body or header."""
    if body and body.api_key and body.api_key.strip():
        return body.api_key.strip()
    if header_key and header_key.strip():
        return header_key.strip()
    return None


@router.post("/repository/{repository_id}/analyze")
async def start_erd_analysis(
    repository_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    body: Optional[StartERDAnalysisRequest] = Body(None),
    tamu_api_key: Optional[str] = Header(default=None, alias="X-TAMU-API-Key"),
):
    """Start an ERD analysis for a repository. Uses TAMU API key from body or header."""
    # Verify repository exists
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    api_key = _get_tamu_api_key(body, tamu_api_key)
    model = (body.model and body.model.strip()) if body else None
    try:
        from services.chat_service import resolve_api_key
        resolve_api_key(api_key)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="TAMU API key is required for ERD analysis. Provide it in the TAMU API Key field or set TAMU_API_KEY in the backend .env."
        ) from e

    # Create analysis record
    analysis = ERDAnalysis(
        repository_id=repository_id,
        status=AnalysisStatus.pending.value
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # Start background task
    background_tasks.add_task(
        run_analysis_task,
        analysis.id,
        repository_id,
        DATABASE_URL,
        api_key,
        model,
    )

    return {
        "id": analysis.id,
        "status": analysis.status,
        "message": "ERD analysis started"
    }


@router.get("/repository/{repository_id}/analyses", response_model=List[ERDAnalysisListItem])
async def list_erd_analyses(
    repository_id: int,
    db: AsyncSession = Depends(get_db)
):
    """List all ERD analyses for a repository."""
    result = await db.execute(
        select(ERDAnalysis)
        .where(ERDAnalysis.repository_id == repository_id)
        .order_by(ERDAnalysis.created_at.desc())
    )
    analyses = result.scalars().all()

    return [
        ERDAnalysisListItem(
            id=a.id,
            repository_id=a.repository_id,
            status=a.status,
            coverage_score=a.coverage_score,
            created_at=a.created_at,
            completed_at=a.completed_at
        )
        for a in analyses
    ]


@router.get("/analysis/{analysis_id}", response_model=ERDAnalysisResponse)
async def get_erd_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific ERD analysis."""
    result = await db.execute(
        select(ERDAnalysis).where(ERDAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return ERDAnalysisResponse(
        id=analysis.id,
        repository_id=analysis.repository_id,
        status=analysis.status,
        error_message=analysis.error_message,
        uml_structure=json.loads(analysis.uml_structure) if analysis.uml_structure else None,
        report=json.loads(analysis.report) if analysis.report else None,
        coverage_score=analysis.coverage_score,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at
    )
