"""
Enforce multi-tenant access to repositories and derived analyses.

Allow access if the caller owns the repo (owner_user_id) or is an admin who teaches
at least one class that includes the repo owner as a student.
"""

import uuid
from typing import Type, TypeVar

from fastapi import HTTPException, Request
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from dependencies import get_current_user_id
from models.classroom import Class, ClassAdmin, ClassMember
from models.repository import Repository

AnalysisT = TypeVar("AnalysisT")


async def admin_teaches_student(
    db: AsyncSession,
    admin_uuid: uuid.UUID,
    student_uuid: uuid.UUID,
) -> bool:
    """True if the caller creates or administers a class containing the student."""
    result = await db.execute(
        select(ClassMember.id)
        .join(Class, Class.id == ClassMember.class_id)
        .where(
            or_(
                Class.owner_user_id == admin_uuid,
                Class.id.in_(select(ClassAdmin.class_id).where(ClassAdmin.user_id == admin_uuid)),
            ),
            ClassMember.user_id == student_uuid,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def require_repository_access(
    request: Request,
    db: AsyncSession,
    repository_id: int,
    *,
    with_discovered_files: bool = False,
) -> Repository:
    """
    Load repository if caller may access it; otherwise raise 404 (no enumeration).
    Requires a verified bearer identity. Ownerless repositories are inaccessible.
    """
    caller = uuid.UUID(await get_current_user_id(request))

    q = select(Repository).where(Repository.id == repository_id)
    if with_discovered_files:
        q = q.options(selectinload(Repository.discovered_files))
    result = await db.execute(q)
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    owner_id = repo.owner_user_id
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    if owner_id == caller:
        return repo

    if await admin_teaches_student(db, caller, owner_id):
        return repo

    raise HTTPException(status_code=404, detail="Repository not found")


async def require_analysis_access(
    request: Request,
    db: AsyncSession,
    analysis_id: int,
    model_cls: Type[AnalysisT],
) -> AnalysisT:
    """Load analysis row and ensure caller may access its repository."""
    await get_current_user_id(request)
    result = await db.execute(select(model_cls).where(model_cls.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    await require_repository_access(request, db, analysis.repository_id)
    return analysis
