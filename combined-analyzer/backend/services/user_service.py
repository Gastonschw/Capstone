"""
User-related helpers for Supabase-backed users (public.users).
"""

import uuid
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import DATABASE_KIND


async def get_user_role(db: AsyncSession, user_id: uuid.UUID) -> Optional[str]:
    """
    Return the role ('admin' or 'general') for a given Supabase user id.

    Returns None if the user does not exist or when not using Postgres/Supabase.
    """
    if DATABASE_KIND != "postgres":
        return None

    result = await db.execute(
        text("select role from public.users where id = :uid"),
        {"uid": str(user_id)},
    )
    row = result.fetchone()
    return row[0] if row else None

