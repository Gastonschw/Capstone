"""
Repository management API routes.
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import get_optional_user_id
from models.repository import Repository, DiscoveredFile
from schemas.repository import (
    RepositoryResponse,
    RepositoryListResponse,
    FileSelectionUpdate,
)
from services.folder_service import delete_repository_files
from services.discovery_service import run_discovery_only

router = APIRouter(prefix="/api", tags=["repositories"])


@router.get("/repositories", response_model=List[RepositoryListResponse])
async def list_repositories(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List repositories. When X-User-Id header is sent, only that user's repos are returned."""
    user_id_raw = get_optional_user_id(request)
    owner_uuid = None
    if user_id_raw:
        try:
            owner_uuid = uuid.UUID(user_id_raw)
        except (ValueError, TypeError):
            pass
    q = (
        select(Repository)
        .options(selectinload(Repository.discovered_files))
        .options(selectinload(Repository.erd_analyses))
        .options(selectinload(Repository.integrity_analyses))
        .options(selectinload(Repository.compliance_analyses))
        .options(selectinload(Repository.correctness_analyses))
        .options(selectinload(Repository.usability_analyses))
        .options(selectinload(Repository.maintainability_analyses))
        .order_by(Repository.created_at.desc())
    )
    if owner_uuid is not None:
        q = q.where(Repository.owner_user_id == owner_uuid)
    # Only return the most recent 5 repositories for this user (or fewer if less exist)
    q = q.limit(5)
    result = await db.execute(q)
    repositories = result.scalars().all()

    def completed_count(analyses):
        """Count only analyses with status 'completed' so sidebar badges match Latest results."""
        return sum(1 for a in (analyses or []) if getattr(a, "status", None) == "completed")

    return [
        RepositoryListResponse(
            id=repo.id,
            name=repo.name,
            source_type=repo.source_type,
            github_url=repo.github_url,
            created_at=repo.created_at,
            file_count=len(repo.discovered_files),
            erd_analysis_count=completed_count(repo.erd_analyses),
            integrity_analysis_count=completed_count(repo.integrity_analyses),
            compliance_analysis_count=completed_count(repo.compliance_analyses),
            correctness_analysis_count=completed_count(repo.correctness_analyses),
            usability_analysis_count=completed_count(repo.usability_analyses),
            maintainability_analysis_count=completed_count(repo.maintainability_analyses),
        )
        for repo in repositories
    ]


@router.get("/repository/{repository_id}", response_model=RepositoryResponse)
async def get_repository(repository_id: int, db: AsyncSession = Depends(get_db)):
    """Get a repository with its discovered files."""
    result = await db.execute(
        select(Repository)
        .options(selectinload(Repository.discovered_files))
        .where(Repository.id == repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    return repository


@router.delete("/repository/{repository_id}")
async def delete_repository(repository_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a repository and its files."""
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

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
    db: AsyncSession = Depends(get_db)
):
    """Update file selection for a specific analysis type."""
    # Verify repository exists
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id)
    )
    repository = result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

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
    db: AsyncSession = Depends(get_db)
):
    """Re-run file discovery for a repository."""
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Run discovery in background
    discovery_result = await run_discovery_only(repository, db)

    return {
        "message": "File discovery completed",
        "stats": discovery_result
    }
