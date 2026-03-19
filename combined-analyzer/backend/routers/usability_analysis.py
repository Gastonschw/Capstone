"""
Usability Analysis API routes.
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
from models.usability_analysis import UsabilityAnalysis
from schemas.usability_analysis import UsabilityAnalysisResponse, UsabilityAnalysisListItem
from services.usability_analysis_service import run_usability_analysis
from concurrency import analysis_semaphore

router = APIRouter(prefix="/api/usability", tags=["usability-analysis"])


class StartUsabilityAnalysisRequest(BaseModel):
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
    """Background task to run Usability analysis."""
    async with analysis_semaphore, AsyncSessionLocal() as db:
        result = await db.execute(
            select(UsabilityAnalysis).where(UsabilityAnalysis.id == analysis_id)
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

            analysis_result = await run_usability_analysis(repository, db, api_key=api_key, model=model)

            analysis.status = "completed"
            analysis.appropriateness_recognizability_report = json.dumps(
                characteristic_report_to_dict(analysis_result.appropriateness_recognizability)
            )
            analysis.learnability_report = json.dumps(
                characteristic_report_to_dict(analysis_result.learnability)
            )
            analysis.operability_report = json.dumps(
                characteristic_report_to_dict(analysis_result.operability)
            )
            analysis.user_error_protection_report = json.dumps(
                characteristic_report_to_dict(analysis_result.user_error_protection)
            )
            analysis.user_engagement_report = json.dumps(
                characteristic_report_to_dict(analysis_result.user_engagement)
            )
            analysis.self_descriptiveness_report = json.dumps(
                characteristic_report_to_dict(analysis_result.self_descriptiveness)
            )
            analysis.inclusivity_report = json.dumps(
                characteristic_report_to_dict(analysis_result.inclusivity)
            )
            analysis.user_assistance_report = json.dumps(
                characteristic_report_to_dict(analysis_result.user_assistance)
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
async def start_usability_analysis(
    repository_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    body: Optional[StartUsabilityAnalysisRequest] = Body(None),
    tamu_api_key: Optional[str] = Header(default=None, alias="X-TAMU-API-Key"),
):
    """Start a Usability analysis for a repository."""
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
            detail="TAMU API key is required for usability analysis."
        ) from e

    analysis = UsabilityAnalysis(repository_id=repository_id, status="pending")
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    background_tasks.add_task(
        run_analysis_task, analysis.id, repository_id, api_key, model,
    )

    return {"id": analysis.id, "status": analysis.status, "message": "Usability analysis started"}


@router.get("/repository/{repository_id}/analyses", response_model=List[UsabilityAnalysisListItem])
async def list_usability_analyses(repository_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UsabilityAnalysis)
        .where(UsabilityAnalysis.repository_id == repository_id)
        .order_by(UsabilityAnalysis.created_at.desc())
    )
    analyses = result.scalars().all()
    return [
        UsabilityAnalysisListItem(
            id=a.id, repository_id=a.repository_id, status=a.status,
            overall_score=a.overall_score, created_at=a.created_at, completed_at=a.completed_at
        )
        for a in analyses
    ]


@router.get("/analysis/{analysis_id}", response_model=UsabilityAnalysisResponse)
async def get_usability_analysis(analysis_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UsabilityAnalysis).where(UsabilityAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return UsabilityAnalysisResponse(
        id=analysis.id,
        repository_id=analysis.repository_id,
        status=analysis.status,
        error_message=analysis.error_message,
        appropriateness_recognizability_report=json.loads(analysis.appropriateness_recognizability_report) if analysis.appropriateness_recognizability_report else None,
        learnability_report=json.loads(analysis.learnability_report) if analysis.learnability_report else None,
        operability_report=json.loads(analysis.operability_report) if analysis.operability_report else None,
        user_error_protection_report=json.loads(analysis.user_error_protection_report) if analysis.user_error_protection_report else None,
        user_engagement_report=json.loads(analysis.user_engagement_report) if analysis.user_engagement_report else None,
        self_descriptiveness_report=json.loads(analysis.self_descriptiveness_report) if analysis.self_descriptiveness_report else None,
        inclusivity_report=json.loads(analysis.inclusivity_report) if analysis.inclusivity_report else None,
        user_assistance_report=json.loads(analysis.user_assistance_report) if analysis.user_assistance_report else None,
        overall_score=analysis.overall_score,
        summary_report=json.loads(analysis.summary_report) if analysis.summary_report else None,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at
    )
