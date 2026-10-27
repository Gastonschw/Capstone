"""Verified Supabase bearer authentication shared by protected APIs."""

from uuid import UUID

import httpx
from fastapi import HTTPException, Request

from config import SUPABASE_ANON_KEY, SUPABASE_URL


async def get_current_user_id(request: Request) -> str:
    """Return only the identity verified by Supabase, never a caller-supplied id."""
    cached = getattr(request.state, "verified_user_id", None)
    if cached is not None:
        return cached
    authorization = request.headers.get("Authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token.strip():
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{SUPABASE_URL.rstrip('/')}/auth/v1/user",
                headers={"Authorization": f"Bearer {token.strip()}", "apikey": SUPABASE_ANON_KEY},
            )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Authentication service unavailable") from None
    if response.status_code in (401, 403):
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Authentication service unavailable")
    try:
        payload = response.json()
        user_id = str(UUID(payload["id"]))
    except (ValueError, TypeError, KeyError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid authentication response") from None
    request.state.verified_user_id = user_id
    return user_id
