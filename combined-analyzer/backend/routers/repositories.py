"""
Repository management API routes.
"""

import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from dependencies import get_current_user_id
from models.repository import Repository, DiscoveredFile
from models.classroom import Class, ClassAdmin, ClassMember
from models.erd_analysis import ERDAnalysis
from models.integrity_analysis import IntegrityAnalysis
from models.compliance_analysis import ComplianceAnalysis
from models.correctness_analysis import CorrectnessAnalysis
from models.usability_analysis import UsabilityAnalysis
from models.maintainability_analysis import MaintainabilityAnalysis
from schemas.repository import (
    RepositoryResponse,
    RepositoryListResponse,
    FileSelectionUpdate,
)
from services.folder_service import delete_repository_files
from services.discovery_service import run_discovery_only
from services.repository_access import require_repository_access

router = APIRouter(prefix="/api", tags=["repositories"])

_COMPLETED = "completed"


async def _completed_analysis_counts(
    db: AsyncSession,
    repository_ids: List[int],
    model,
) -> Dict[int, int]:
    """Map repository_id -> count of completed analyses (single indexed query per type)."""
    if not repository_ids:
        return {}
    result = await db.execute(
        select(model.repository_id, func.count())
        .where(
            model.repository_id.in_(repository_ids),
            model.status == _COMPLETED,
        )
        .group_by(model.repository_id)
    )
    return {row[0]: row[1] for row in result.all()}


async def _discovered_file_counts(db: AsyncSession, repository_ids: List[int]) -> Dict[int, int]:
    if not repository_ids:
        return {}
    result = await db.execute(
        select(DiscoveredFile.repository_id, func.count())
        .where(DiscoveredFile.repository_id.in_(repository_ids))
        .group_by(DiscoveredFile.repository_id)
    )
    return {row[0]: row[1] for row in result.all()}


@router.get("/repositories", response_model=List[RepositoryListResponse])
async def list_repositories(
    request: Request,
    db: AsyncSession = Depends(get_db),
    class_id: Optional[str] = Query(None),
    student_user_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List owned repositories, or a student's repositories for their class teachers."""
    current_uid = uuid.UUID(await get_current_user_id(request))
    owner_uuid = current_uid

    if (class_id is None) ^ (student_user_id is None):
        raise HTTPException(
            status_code=400,
            detail="class_id and student_user_id must be provided together",
        )

    if class_id is not None and student_user_id is not None:
        try:
            class_uuid = uuid.UUID(class_id)
            student_uuid = uuid.UUID(student_user_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid UUID in class_id or student_user_id")

        cres = await db.execute(select(Class).where(Class.id == class_uuid))
        cobj = cres.scalar_one_or_none()
        if not cobj:
            raise HTTPException(status_code=404, detail="Class not found")
        if cobj.owner_user_id != current_uid:
            admin_result = await db.execute(
                select(ClassAdmin.id).where(
                    ClassAdmin.class_id == class_uuid,
                    ClassAdmin.user_id == current_uid,
                )
            )
            if admin_result.scalar_one_or_none() is None:
                raise HTTPException(status_code=403, detail="You do not teach this class")

        mres = await db.execute(
            select(ClassMember).where(
                ClassMember.class_id == class_uuid,
                ClassMember.user_id == student_uuid,
            )
        )
        if mres.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="That user is not a member of this class")

        owner_uuid = student_uuid

    q = (
        select(Repository)
        .where(Repository.owner_user_id == owner_uuid)
        .order_by(Repository.created_at.desc(), Repository.id.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(q)
    repositories = result.scalars().all()

    repo_ids = [repo.id for repo in repositories]
    file_c = await _discovered_file_counts(db, repo_ids)
    erd_c = await _completed_analysis_counts(db, repo_ids, ERDAnalysis)
    int_c = await _completed_analysis_counts(db, repo_ids, IntegrityAnalysis)
    comp_c = await _completed_analysis_counts(db, repo_ids, ComplianceAnalysis)
    corr_c = await _completed_analysis_counts(db, repo_ids, CorrectnessAnalysis)
    usa_c = await _completed_analysis_counts(db, repo_ids, UsabilityAnalysis)
    main_c = await _completed_analysis_counts(db, repo_ids, MaintainabilityAnalysis)

    return [
        RepositoryListResponse(
            id=repo.id,
            name=repo.name,
            source_type=repo.source_type,
            github_url=repo.github_url,
            created_at=repo.created_at,
            file_count=file_c.get(repo.id, 0),
            erd_analysis_count=erd_c.get(repo.id, 0),
            integrity_analysis_count=int_c.get(repo.id, 0),
            compliance_analysis_count=comp_c.get(repo.id, 0),
            correctness_analysis_count=corr_c.get(repo.id, 0),
            usability_analysis_count=usa_c.get(repo.id, 0),
            maintainability_analysis_count=main_c.get(repo.id, 0),
        )
        for repo in repositories
    ]


@router.get("/repository/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get a repository with its discovered files."""
    return await require_repository_access(
        request, db, repository_id, with_discovered_files=True
    )


@router.delete("/repository/{repository_id}")
async def delete_repository(
    repository_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Delete a repository and its files."""
    repository = await require_repository_access(request, db, repository_id)

    # Delete local files
    delete_repository_files(repository.local_path)

    # Delete from database (cascade will handle related records)
    await db.delete(repository)
    await db.commit()

    return {"message": "Repository deleted successfully"}


@router.put("/repository/{repository_id}/files/selection")
async def update_file_selection(
    repository_id: int,
    update: FileSelectionUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update file selection for a specific analysis type."""
    await require_repository_access(request, db, repository_id)

    # Update file selections
    result = await db.execute(
        select(DiscoveredFile).where(
            DiscoveredFile.repository_id == repository_id,
            DiscoveredFile.id.in_(update.file_ids)
        )
    )
    files = result.scalars().all()

    selection_field_map = {
        'erd': 'is_selected_erd',
        'integrity': 'is_selected_integrity',
        'compliance': 'is_selected_compliance',
        'correctness': 'is_selected_correctness',
        'usability': 'is_selected_usability',
        'maintainability': 'is_selected_maintainability',
    }

    field = selection_field_map.get(update.analysis_type)
    if not field:
        raise HTTPException(
            status_code=400,
            detail=f"analysis_type must be one of: {', '.join(selection_field_map.keys())}"
        )

    for file in files:
        setattr(file, field, update.is_selected)

    await db.commit()

    return {"message": f"Updated {len(files)} files for {update.analysis_type} analysis"}


@router.post("/repository/{repository_id}/rediscover")
async def rediscover_files(
    repository_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Re-run file discovery for a repository."""
    repository = await require_repository_access(request, db, repository_id)

    discovery_result = await run_discovery_only(
        repository, db, api_key=request.headers.get("X-TAMU-API-Key")
    )

    return {
        "message": "File discovery completed",
        "stats": discovery_result
    }
