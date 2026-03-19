"""
Compliance Analysis API routes.
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
from models.compliance_analysis import ComplianceAnalysis
from schemas.compliance_analysis import ComplianceAnalysisResponse, ComplianceAnalysisListItem
from services.compliance_analysis_service import run_compliance_analysis
from concurrency import analysis_semaphore

router = APIRouter(prefix="/api/compliance", tags=["compliance-analysis"])


class StartComplianceAnalysisRequest(BaseModel):
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
    """Background task to run Compliance analysis."""
    async with analysis_semaphore, AsyncSessionLocal() as db:
        result = await db.execute(
            select(ComplianceAnalysis).where(ComplianceAnalysis.id == analysis_id)
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

            analysis_result = await run_compliance_analysis(repository, db, api_key=api_key, model=model)

            analysis.status = "completed"
            analysis.functional_completeness_report = json.dumps(
                characteristic_report_to_dict(analysis_result.functional_completeness)
            )
            analysis.functional_correctness_report = json.dumps(
                characteristic_report_to_dict(analysis_result.functional_correctness)
            )
            analysis.functional_appropriateness_report = json.dumps(
                characteristic_report_to_dict(analysis_result.functional_appropriateness)
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


def _get_api_key(body: Optional[StartComplianceAnalysisRequest], header_key: Optional[str]) -> Optional[str]:
    if body and body.api_key and body.api_key.strip():
        return body.api_key.strip()
    if header_key and header_key.strip():
        return header_key.strip()
    return None


@router.post("/repository/{repository_id}/analyze")
async def start_compliance_analysis(
    repository_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    body: Optional[StartComplianceAnalysisRequest] = Body(None),
    tamu_api_key: Optional[str] = Header(default=None, alias="X-TAMU-API-Key"),
):
    """Start a Compliance analysis for a repository."""
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
            detail="TAMU API key is required for compliance analysis. Provide it in the analyzer TAMU API Key field or set TAMU_API_KEY in the backend .env."
        ) from e

    analysis = ComplianceAnalysis(
        repository_id=repository_id,
        status="pending"
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    background_tasks.add_task(
        run_analysis_task, analysis.id, repository_id, api_key, model,
    )

    return {
        "id": analysis.id,
        "status": analysis.status,
        "message": "Compliance analysis started"
    }


@router.get("/repository/{repository_id}/analyses", response_model=List[ComplianceAnalysisListItem])
async def list_compliance_analyses(
    repository_id: int,
    db: AsyncSession = Depends(get_db)
):
    """List all Compliance analyses for a repository."""
    result = await db.execute(
        select(ComplianceAnalysis)
        .where(ComplianceAnalysis.repository_id == repository_id)
        .order_by(ComplianceAnalysis.created_at.desc())
    )
    analyses = result.scalars().all()

    return [
        ComplianceAnalysisListItem(
            id=a.id, repository_id=a.repository_id, status=a.status,
            overall_score=a.overall_score, created_at=a.created_at, completed_at=a.completed_at
        )
        for a in analyses
    ]


@router.get("/analysis/{analysis_id}", response_model=ComplianceAnalysisResponse)
async def get_compliance_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific Compliance analysis."""
    result = await db.execute(
        select(ComplianceAnalysis).where(ComplianceAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return ComplianceAnalysisResponse(
        id=analysis.id,
        repository_id=analysis.repository_id,
        status=analysis.status,
        error_message=analysis.error_message,
        functional_completeness_report=json.loads(analysis.functional_completeness_report) if analysis.functional_completeness_report else None,
        functional_correctness_report=json.loads(analysis.functional_correctness_report) if analysis.functional_correctness_report else None,
        functional_appropriateness_report=json.loads(analysis.functional_appropriateness_report) if analysis.functional_appropriateness_report else None,
        overall_score=analysis.overall_score,
        summary_report=json.loads(analysis.summary_report) if analysis.summary_report else None,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at
    )
