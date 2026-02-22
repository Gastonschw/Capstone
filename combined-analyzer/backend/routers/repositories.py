"""
Repository management API routes.
"""

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
    user_id = get_optional_user_id(request)
    q = (
        select(Repository)
        .options(selectinload(Repository.discovered_files))
        .options(selectinload(Repository.erd_analyses))
        .options(selectinload(Repository.integrity_analyses))
        .order_by(Repository.created_at.desc())
    )
    if user_id is not None:
        q = q.where(Repository.owner_user_id == user_id)
    result = await db.execute(q)
    repositories = result.scalars().all()

    return [
        RepositoryListResponse(
            id=repo.id,
            name=repo.name,
            source_type=repo.source_type,
            github_url=repo.github_url,
            created_at=repo.created_at,
            file_count=len(repo.discovered_files),
            erd_analysis_count=len(repo.erd_analyses),
            integrity_analysis_count=len(repo.integrity_analyses),
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

    for file in files:
        if update.analysis_type == 'erd':
            file.is_selected_erd = update.is_selected
        elif update.analysis_type == 'integrity':
            file.is_selected_integrity = update.is_selected
        else:
            raise HTTPException(
                status_code=400,
                detail="analysis_type must be 'erd' or 'integrity'"
            )

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
