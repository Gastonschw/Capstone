"""
Maintainability Analysis API routes.
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
from models.maintainability_analysis import MaintainabilityAnalysis
from schemas.maintainability_analysis import MaintainabilityAnalysisResponse, MaintainabilityAnalysisListItem
from services.maintainability_analysis_service import run_maintainability_analysis

router = APIRouter(prefix="/api/maintainability", tags=["maintainability-analysis"])


class StartMaintainabilityAnalysisRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None


def characteristic_report_to_dict(report) -> dict:
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
    """Background task to run Maintainability analysis."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(MaintainabilityAnalysis).where(MaintainabilityAnalysis.id == analysis_id)
        )
        analysis = result.scalar_one_or_none()

        result = await db.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        repository = result.scalar_one_or_none()

        if not analysis or not repository:
            return

        try:
            analysis.status = "processing"
            await db.commit()

            analysis_result = await run_maintainability_analysis(repository, db, api_key=api_key, model=model)

            analysis.status = "completed"
            analysis.modularity_report = json.dumps(
                characteristic_report_to_dict(analysis_result.modularity)
            )
            analysis.reusability_report = json.dumps(
                characteristic_report_to_dict(analysis_result.reusability)
            )
            analysis.analysability_report = json.dumps(
                characteristic_report_to_dict(analysis_result.analysability)
            )
            analysis.modifiability_report = json.dumps(
                characteristic_report_to_dict(analysis_result.modifiability)
            )
            analysis.testability_report = json.dumps(
                characteristic_report_to_dict(analysis_result.testability)
            )
            analysis.overall_score = analysis_result.overall_score
            analysis.summary_report = json.dumps(analysis_result.summary)
            analysis.completed_at = datetime.utcnow()

            await db.commit()

        except Exception as e:
            analysis.status = "failed"
            analysis.error_message = str(e)
            analysis.completed_at = datetime.utcnow()
            await db.commit()


def _get_api_key(body, header_key):
    if body and body.api_key and body.api_key.strip():
        return body.api_key.strip()
    if header_key and header_key.strip():
        return header_key.strip()
    return None


@router.post("/repository/{repository_id}/analyze")
async def start_maintainability_analysis(
    repository_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    body: Optional[StartMaintainabilityAnalysisRequest] = Body(None),
    tamu_api_key: Optional[str] = Header(default=None, alias="X-TAMU-API-Key"),
):
    """Start a Maintainability analysis for a repository."""
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    api_key = _get_api_key(body, tamu_api_key)
    model = (body.model and body.model.strip()) if body else None
    try:
        from services.chat_service import resolve_api_key
        resolve_api_key(api_key)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="TAMU API key is required for maintainability analysis."
        ) from e

    analysis = MaintainabilityAnalysis(repository_id=repository_id, status="pending")
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    background_tasks.add_task(
        run_analysis_task, analysis.id, repository_id, api_key, model,
    )

    return {"id": analysis.id, "status": analysis.status, "message": "Maintainability analysis started"}


@router.get("/repository/{repository_id}/analyses", response_model=List[MaintainabilityAnalysisListItem])
async def list_maintainability_analyses(repository_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MaintainabilityAnalysis)
        .where(MaintainabilityAnalysis.repository_id == repository_id)
        .order_by(MaintainabilityAnalysis.created_at.desc())
    )
    analyses = result.scalars().all()
    return [
        MaintainabilityAnalysisListItem(
            id=a.id, repository_id=a.repository_id, status=a.status,
            overall_score=a.overall_score, created_at=a.created_at, completed_at=a.completed_at
        )
        for a in analyses
    ]


@router.get("/analysis/{analysis_id}", response_model=MaintainabilityAnalysisResponse)
async def get_maintainability_analysis(analysis_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MaintainabilityAnalysis).where(MaintainabilityAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return MaintainabilityAnalysisResponse(
        id=analysis.id,
        repository_id=analysis.repository_id,
        status=analysis.status,
        error_message=analysis.error_message,
        modularity_report=json.loads(analysis.modularity_report) if analysis.modularity_report else None,
        reusability_report=json.loads(analysis.reusability_report) if analysis.reusability_report else None,
        analysability_report=json.loads(analysis.analysability_report) if analysis.analysability_report else None,
        modifiability_report=json.loads(analysis.modifiability_report) if analysis.modifiability_report else None,
        testability_report=json.loads(analysis.testability_report) if analysis.testability_report else None,
        overall_score=analysis.overall_score,
        summary_report=json.loads(analysis.summary_report) if analysis.summary_report else None,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at
    )
