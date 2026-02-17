"""
Integrity Analysis API routes.
"""

import json
from typing import List
from datetime import datetime
from dataclasses import asdict
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.repository import Repository
from models.integrity_analysis import IntegrityAnalysis
from schemas.integrity_analysis import IntegrityAnalysisResponse, IntegrityAnalysisListItem
from services.integrity_analysis_service import run_integrity_analysis

router = APIRouter(prefix="/api/integrity", tags=["integrity-analysis"])


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


async def run_analysis_task(analysis_id: int, repository_id: int, db_url: str):
    """Background task to run Integrity analysis."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(db_url)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
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

            # Run the analysis
            analysis_result = await run_integrity_analysis(repository, db)

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
            analysis.status = "failed"
            analysis.error_message = str(e)
            analysis.completed_at = datetime.utcnow()
            await db.commit()


@router.post("/repository/{repository_id}/analyze")
async def start_integrity_analysis(
    repository_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Start an Integrity analysis for a repository."""
    # Verify repository exists
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Create analysis record
    analysis = IntegrityAnalysis(
        repository_id=repository_id,
        status="pending"
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # Start background task
    from config import DATABASE_URL
    background_tasks.add_task(
        run_analysis_task,
        analysis.id,
        repository_id,
        DATABASE_URL
    )

    return {
        "id": analysis.id,
        "status": analysis.status,
        "message": "Integrity analysis started"
    }


@router.get("/repository/{repository_id}/analyses", response_model=List[IntegrityAnalysisListItem])
async def list_integrity_analyses(
    repository_id: int,
    db: AsyncSession = Depends(get_db)
):
    """List all Integrity analyses for a repository."""
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
    db: AsyncSession = Depends(get_db)
):
    """Get a specific Integrity analysis."""
    result = await db.execute(
        select(IntegrityAnalysis).where(IntegrityAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

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
