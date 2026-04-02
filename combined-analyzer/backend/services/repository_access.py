"""
Enforce multi-tenant access to repositories and derived analyses.

Allow access if the caller owns the repo (owner_user_id) or is an admin who teaches
at least one class that includes the repo owner as a student.
"""

import uuid
from typing import Type, TypeVar

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import DATABASE_KIND
from dependencies import get_optional_user_id
from models.classroom import Class, ClassMember
from models.repository import Repository
from services.user_service import get_user_role

AnalysisT = TypeVar("AnalysisT")


async def admin_teaches_student(
    db: AsyncSession,
    admin_uuid: uuid.UUID,
    student_uuid: uuid.UUID,
) -> bool:
    """True if admin_uuid owns a class containing student_uuid."""
    if DATABASE_KIND != "postgres":
        return False
    role = await get_user_role(db, admin_uuid)
    if role != "admin":
        return False
    result = await db.execute(
        select(ClassMember.id)
        .join(Class, Class.id == ClassMember.class_id)
        .where(
            Class.owner_user_id == admin_uuid,
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
    Requires X-User-Id. Repos without owner_user_id are not accessible.
    """
    user_id_str = get_optional_user_id(request)
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        caller = uuid.UUID(user_id_str)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user id") from exc

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
    result = await db.execute(select(model_cls).where(model_cls.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    await require_repository_access(request, db, analysis.repository_id)
    return analysis
