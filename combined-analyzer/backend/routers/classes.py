"""
Class management API routes.

Admins (teachers) can create classes, which students can join via a 6-digit code.
A class has a single creator (classes.owner_user_id) and may have any number of
additional admins (class_admins). Any admin (creator or additional) can manage
the roster and rotate the join code, but only the creator can promote members
to admin, revoke admin access, or delete the class.
"""

import random
import string
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, or_

from pydantic import BaseModel

from database import get_db
from models import Class, ClassAdmin, ClassMember
from schemas import (
    ClassSummary,
    MyClassesResponse,
    ClassMemberItem,
    ClassMembersResponse,
    ClassAdminItem,
    ClassAdminsResponse,
)
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


def _parse_uuid(value: str, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {label}")


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


async def _load_class_or_404(db: AsyncSession, class_uuid: uuid.UUID) -> Class:
    result = await db.execute(select(Class).where(Class.id == class_uuid))
    class_obj = result.scalar_one_or_none()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    return class_obj


async def _is_class_admin_member(
    db: AsyncSession,
    class_uuid: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        select(ClassAdmin.id).where(
            ClassAdmin.class_id == class_uuid,
            ClassAdmin.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def _ensure_class_teacher(
    db: AsyncSession,
    class_uuid: uuid.UUID,
    user_id: uuid.UUID,
) -> Class:
    """Require the user to be the class creator or a class admin."""
    class_obj = await _load_class_or_404(db, class_uuid)
    if class_obj.owner_user_id == user_id:
        return class_obj
    if await _is_class_admin_member(db, class_uuid, user_id):
        return class_obj
    raise HTTPException(status_code=403, detail="You do not have permission to manage this class")


async def _ensure_class_creator(
    db: AsyncSession,
    class_uuid: uuid.UUID,
    user_id: uuid.UUID,
) -> Class:
    """Require the user to be the class creator (owner_user_id)."""
    class_obj = await _load_class_or_404(db, class_uuid)
    if class_obj.owner_user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the class creator can perform this action",
        )
    return class_obj


def _class_summary(class_obj: Class, current_user_id: uuid.UUID, include_join_code: bool) -> ClassSummary:
    return ClassSummary(
        id=str(class_obj.id),
        name=class_obj.name,
        description=class_obj.description,
        join_code=class_obj.join_code if include_join_code else None,
        created_at=class_obj.created_at,
        is_creator=class_obj.owner_user_id == current_user_id,
    )


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

    return _class_summary(new_class, user_id, include_join_code=True)


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

    # Teachers (creator or class admin) don't need to be in the member roster.
    is_creator = class_obj.owner_user_id == user_id
    is_admin = await _is_class_admin_member(db, class_obj.id, user_id)

    if not (is_creator or is_admin):
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
        # Clear any pending state
        await db.commit()

    # Students don't need the join code once joined; teachers do.
    include_join_code = is_creator or is_admin
    return _class_summary(class_obj, user_id, include_join_code=include_join_code)


@router.get("", response_model=MyClassesResponse)
async def list_my_classes(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List classes the current user teaches and classes they are enrolled in."""
    user_id = _require_current_user_id(request)

    # Determine current user's role (if available)
    role = await get_user_role(db, user_id)

    # Classes the user teaches: they are the creator or an additional admin.
    teaching_result = await db.execute(
        select(Class)
        .where(
            or_(
                Class.owner_user_id == user_id,
                Class.id.in_(
                    select(ClassAdmin.class_id).where(ClassAdmin.user_id == user_id)
                ),
            )
        )
        .order_by(Class.created_at.desc())
    )
    teaching_classes = teaching_result.scalars().all()

    # Classes where user is a member (student)
    enrolled_result = await db.execute(
        select(Class)
        .join(ClassMember, Class.id == ClassMember.class_id)
        .where(ClassMember.user_id == user_id)
    )
    enrolled_classes = enrolled_result.scalars().all()

    teaching = [
        _class_summary(c, user_id, include_join_code=True) for c in teaching_classes
    ]

    enrolled = [
        _class_summary(c, user_id, include_join_code=False) for c in enrolled_classes
    ]

    return MyClassesResponse(role=role, teaching=teaching, enrolled=enrolled)


@router.get("/{class_id}/members", response_model=ClassMembersResponse)
async def list_class_members(
    request: Request,
    class_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List students in a class. Any teacher of the class may call this."""
    user_id = _require_current_user_id(request)
    class_uuid = _parse_uuid(class_id, "class id")
    await _ensure_class_teacher(db, class_uuid, user_id)

    rows = await db.execute(
        text(
            """
            select cm.user_id::text as user_id, u.email, u.full_name, cm.created_at as joined_at
            from class_members cm
            join public.users u on u.id = cm.user_id
            where cm.class_id = :cid
            order by cm.created_at asc
            """
        ),
        {"cid": str(class_uuid)},
    )
    members = [
        ClassMemberItem(
            user_id=r[0],
            email=r[1],
            full_name=r[2],
            joined_at=r[3],
        )
        for r in rows.fetchall()
    ]
    return ClassMembersResponse(members=members)


@router.delete("/{class_id}/members/{member_user_id}", status_code=204)
async def remove_class_member(
    request: Request,
    class_id: str,
    member_user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a student from a class. Any teacher of the class may call this."""
    user_id = _require_current_user_id(request)
    class_uuid = _parse_uuid(class_id, "class id")
    member_uuid = _parse_uuid(member_user_id, "user id")
    await _ensure_class_teacher(db, class_uuid, user_id)

    if member_uuid == user_id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself from the class roster")

    mem_result = await db.execute(
        select(ClassMember).where(
            ClassMember.class_id == class_uuid,
            ClassMember.user_id == member_uuid,
        )
    )
    member_row = mem_result.scalar_one_or_none()
    if not member_row:
        raise HTTPException(status_code=404, detail="Member not found in this class")

    await db.delete(member_row)
    await db.commit()

    return Response(status_code=204)


@router.post("/{class_id}/rotate-join-code", response_model=ClassSummary)
async def rotate_join_code(
    request: Request,
    class_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Replace the class join code with a new unique code. Any teacher may call this;
    existing members stay enrolled."""
    user_id = _require_current_user_id(request)
    class_uuid = _parse_uuid(class_id, "class id")
    class_obj = await _ensure_class_teacher(db, class_uuid, user_id)

    new_code = await _ensure_unique_join_code(db)
    class_obj.join_code = new_code
    await db.commit()
    await db.refresh(class_obj)

    return _class_summary(class_obj, user_id, include_join_code=True)


@router.get("/{class_id}/admins", response_model=ClassAdminsResponse)
async def list_class_admins(
    request: Request,
    class_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List the admins (teachers) of a class. Any teacher of the class may view."""
    user_id = _require_current_user_id(request)
    class_uuid = _parse_uuid(class_id, "class id")
    await _ensure_class_teacher(db, class_uuid, user_id)

    rows = await db.execute(
        text(
            """
            select user_id::text as user_id, email, full_name, added_at, is_creator
            from (
                select c.owner_user_id as user_id,
                       u.email,
                       u.full_name,
                       c.created_at as added_at,
                       true as is_creator
                from public.classes c
                join public.users u on u.id = c.owner_user_id
                where c.id = :cid
                union all
                select ca.user_id,
                       u2.email,
                       u2.full_name,
                       ca.created_at as added_at,
                       false as is_creator
                from public.class_admins ca
                join public.users u2 on u2.id = ca.user_id
                where ca.class_id = :cid
            ) t
            order by is_creator desc, added_at asc
            """
        ),
        {"cid": str(class_uuid)},
    )
    admins = [
        ClassAdminItem(
            user_id=r[0],
            email=r[1],
            full_name=r[2],
            added_at=r[3],
            is_creator=bool(r[4]),
        )
        for r in rows.fetchall()
    ]
    return ClassAdminsResponse(admins=admins)


@router.post("/{class_id}/admins/{member_user_id}", response_model=ClassAdminItem)
async def promote_class_member(
    request: Request,
    class_id: str,
    member_user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Promote an enrolled class member to class admin. Creator only."""
    user_id = _require_current_user_id(request)
    class_uuid = _parse_uuid(class_id, "class id")
    target_uuid = _parse_uuid(member_user_id, "user id")
    await _ensure_class_creator(db, class_uuid, user_id)

    if target_uuid == user_id:
        raise HTTPException(status_code=400, detail="The class creator is already an admin")

    # Target must currently be a member of the class.
    mem_result = await db.execute(
        select(ClassMember).where(
            ClassMember.class_id == class_uuid,
            ClassMember.user_id == target_uuid,
        )
    )
    member_row = mem_result.scalar_one_or_none()
    if not member_row:
        raise HTTPException(
            status_code=404,
            detail="That user has not joined this class; ask them to join with the code first",
        )

    # If somehow already an admin, clean up and return.
    already_admin = await _is_class_admin_member(db, class_uuid, target_uuid)
    if already_admin:
        await db.delete(member_row)
        await db.commit()
    else:
        await db.delete(member_row)
        db.add(ClassAdmin(class_id=class_uuid, user_id=target_uuid))
        await db.commit()

    detail_rows = await db.execute(
        text(
            """
            select u.email, u.full_name, ca.created_at
            from public.class_admins ca
            join public.users u on u.id = ca.user_id
            where ca.class_id = :cid and ca.user_id = :uid
            """
        ),
        {"cid": str(class_uuid), "uid": str(target_uuid)},
    )
    row = detail_rows.fetchone()
    email = row[0] if row else None
    full_name = row[1] if row else None
    added_at = row[2] if row else None

    return ClassAdminItem(
        user_id=str(target_uuid),
        email=email,
        full_name=full_name,
        is_creator=False,
        added_at=added_at,
    )


@router.delete("/{class_id}/admins/{admin_user_id}", status_code=204)
async def revoke_class_admin(
    request: Request,
    class_id: str,
    admin_user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Revoke a class admin, returning them to regular member status. Creator only."""
    user_id = _require_current_user_id(request)
    class_uuid = _parse_uuid(class_id, "class id")
    target_uuid = _parse_uuid(admin_user_id, "user id")
    class_obj = await _ensure_class_creator(db, class_uuid, user_id)

    if target_uuid == class_obj.owner_user_id:
        raise HTTPException(
            status_code=400,
            detail="The class creator cannot have their admin access revoked",
        )

    admin_result = await db.execute(
        select(ClassAdmin).where(
            ClassAdmin.class_id == class_uuid,
            ClassAdmin.user_id == target_uuid,
        )
    )
    admin_row = admin_result.scalar_one_or_none()
    if not admin_row:
        raise HTTPException(status_code=404, detail="That user is not an admin of this class")

    # Remove from admins and put back as a regular member so they stay enrolled.
    await db.delete(admin_row)

    existing_member = await db.execute(
        select(ClassMember).where(
            ClassMember.class_id == class_uuid,
            ClassMember.user_id == target_uuid,
        )
    )
    if existing_member.scalar_one_or_none() is None:
        db.add(ClassMember(class_id=class_uuid, user_id=target_uuid))

    await db.commit()

    return Response(status_code=204)


@router.delete("/{class_id}", status_code=204)
async def delete_class(
    request: Request,
    class_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a class. Creator only."""
    user_id = _require_current_user_id(request)
    class_uuid = _parse_uuid(class_id, "class id")
    class_obj = await _ensure_class_creator(db, class_uuid, user_id)

    await db.delete(class_obj)
    await db.commit()

    return Response(status_code=204)
