"""
User-related helpers for Supabase-backed users (public.users).
"""

import uuid
from typing import Optional
from fastapi import HTTPException

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_user_role(db: AsyncSession, user_id: uuid.UUID) -> Optional[str]:
    """
    Return the role ('admin' or 'general') for a given Supabase user id.

    Returns None if the user does not exist. Database errors propagate.
    """

    result = await db.execute(
        text("select role from public.users where id = :uid"),
        {"uid": str(user_id)},
    )
    row = result.fetchone()
    return row[0] if row else None


async def require_registered_user(db: AsyncSession, user_id: str | uuid.UUID) -> uuid.UUID:
    """Require a public.users row before persisting an authenticated owner."""
    try:
        uid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid authenticated user") from None
    result = await db.execute(
        text("select id from public.users where id = :uid"),
        {"uid": str(uid)},
    )
    if result.fetchone() is None:
        raise HTTPException(
            status_code=400,
            detail="User is not registered in public.users yet. Try signing out and back in.",
        )
    return uid

