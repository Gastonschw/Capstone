"""
Optional auth dependency for Supabase user linking.

When the frontend uses Supabase Auth (e.g. Google login), it can send
the current user's id so the backend links GitHub tokens and repositories
to that user. Until Supabase Auth is integrated, this is optional.
"""

import re
from typing import Optional

from fastapi import Request

# UUID v4 pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[4][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

HEADER_USER_ID = "X-User-Id"


def get_optional_user_id(request: Request) -> Optional[str]:
    """
    Return the current user id from the X-User-Id header when present and valid.
    Used to link GitHub tokens and repositories to public.users (Supabase).
    """
    raw = request.headers.get(HEADER_USER_ID)
    if not raw or not raw.strip():
        return None
    value = raw.strip()
    return value if UUID_PATTERN.match(value) else None
