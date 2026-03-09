"""
Class management API routes.

Admins (teachers) can create classes, which students can join via a 6-digit code.
"""

import random
import string
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from pydantic import BaseModel

from database import get_db
from models import Class, ClassMember
from schemas import ClassSummary, MyClassesResponse
from services.user_service import get_user_role
from dependencies import get_optional_user_id

router = APIRouter(prefix="/api/classes", tags=["classes"])


def _require_current_user_id(request: Request) -> uuid.UUID:
    user_id_str = get_optional_user_id(request)
    if not user_id_str:
        raise HTTPException(
            status_code=401,
            detail="Supabase user id is required (X-User-Id header) to use classes.",
        )
    try:
        return uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Supabase user id")


def _generate_join_code(length: int = 6) -> str:
    # Numeric 6-digit code, zero-padded
    return "".join(random.choices(string.digits, k=length))


async def _ensure_unique_join_code(db: AsyncSession, max_attempts: int = 10) -> str:
    """Generate a unique join code by checking for collisions."""
    for _ in range(max_attempts):
        code = _generate_join_code()
        result = await db.execute(select(Class).where(Class.join_code == code))
        if result.scalar_one_or_none() is None:
            return code
    raise HTTPException(status_code=500, detail="Failed to generate unique join code")


class CreateClassRequest(BaseModel):
    name: str
    description: Optional[str] = None


class JoinClassRequest(BaseModel):
    join_code: str


@router.post("", response_model=ClassSummary)
async def create_class(
    request: Request,
    payload: CreateClassRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new class for the current admin (teacher)."""
    user_id = _require_current_user_id(request)
    role = await get_user_role(db, user_id)

    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admin users can create classes")

    join_code = await _ensure_unique_join_code(db)

    new_class = Class(
        name=payload.name,
        description=payload.description,
        owner_user_id=user_id,
        join_code=join_code,
    )
    db.add(new_class)
    await db.commit()
    await db.refresh(new_class)

    return ClassSummary(
        id=str(new_class.id),
        name=new_class.name,
        description=new_class.description,
        join_code=new_class.join_code,
        created_at=new_class.created_at,
    )


@router.post("/join", response_model=ClassSummary)
async def join_class(
    request: Request,
    payload: JoinClassRequest,
    db: AsyncSession = Depends(get_db),
):
    """Join an existing class by 6-digit code."""
    user_id = _require_current_user_id(request)

    # Ensure the Supabase user exists (avoids FK issues if sync is delayed)
    role = await get_user_role(db, user_id)
    if role is None:
        raise HTTPException(
            status_code=400,
            detail="User is not registered in public.users yet. Try signing out and back in.",
        )

    # Look up class by join code
    result = await db.execute(select(Class).where(Class.join_code == payload.join_code.strip()))
    class_obj = result.scalar_one_or_none()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found for that code")

    # Avoid duplicate membership
    existing = await db.execute(
        select(ClassMember).where(
            ClassMember.class_id == class_obj.id,
            ClassMember.user_id == user_id,
        )
    )
    member = existing.scalar_one_or_none()
    if not member:
        member = ClassMember(class_id=class_obj.id, user_id=user_id)
        db.add(member)
        await db.commit()
    else:
        # Still commit to clear any pending state
        await db.commit()

    return ClassSummary(
        id=str(class_obj.id),
        name=class_obj.name,
        description=class_obj.description,
        join_code=None,  # Students don't need the join code once joined
        created_at=class_obj.created_at,
    )


@router.get("", response_model=MyClassesResponse)
async def list_my_classes(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List classes the current user teaches and classes they are enrolled in."""
    user_id = _require_current_user_id(request)

    # Determine current user's role (if available)
    role = await get_user_role(db, user_id)

    # Classes where user is the owner (teacher/admin)
    teaching_result = await db.execute(select(Class).where(Class.owner_user_id == user_id))
    teaching_classes = teaching_result.scalars().all()

    # Classes where user is a member (student)
    enrolled_result = await db.execute(
        select(Class)
        .join(ClassMember, Class.id == ClassMember.class_id)
        .where(ClassMember.user_id == user_id)
    )
    enrolled_classes = enrolled_result.scalars().all()

    teaching = [
        ClassSummary(
            id=str(c.id),
            name=c.name,
            description=c.description,
            join_code=c.join_code,
            created_at=c.created_at,
        )
        for c in teaching_classes
    ]

    enrolled = [
        ClassSummary(
            id=str(c.id),
            name=c.name,
            description=c.description,
            join_code=None,
            created_at=c.created_at,
        )
        for c in enrolled_classes
    ]

    return MyClassesResponse(role=role, teaching=teaching, enrolled=enrolled)


@router.delete("/{class_id}", status_code=204)
async def delete_class(
    request: Request,
    class_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a class owned by the current admin/teacher."""
    user_id = _require_current_user_id(request)

    try:
        class_uuid = uuid.UUID(class_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid class id")

    result = await db.execute(select(Class).where(Class.id == class_uuid))
    class_obj = result.scalar_one_or_none()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    if class_obj.owner_user_id != user_id:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this class")

    await db.delete(class_obj)
    await db.commit()

    return Response(status_code=204)

