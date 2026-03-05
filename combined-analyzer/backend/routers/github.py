"""
GitHub OAuth API routes.
"""

import uuid
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.github import GitHubRepo, GitHubImportRequest, GitHubAuthStatus
from config import FRONTEND_URL
from services.github_service import (
    get_github_auth_url,
    exchange_code_for_token,
    get_github_user,
    save_github_token,
    get_github_token,
    get_github_auth_status,
    list_github_repos,
    clone_github_repo,
    delete_github_token,
)
from services.discovery_service import run_file_discovery

router = APIRouter(prefix="/api/github", tags=["github"])

# Session cookie name
SESSION_COOKIE = "session_id"


def get_session_id(request: Request, response: Response) -> str:
    """Get or create a session ID from cookies."""
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            key=SESSION_COOKIE,
            value=session_id,
            httponly=True,
            max_age=86400 * 30,  # 30 days
            samesite="lax"
        )
    return session_id


@router.get("/auth")
async def github_auth(
    request: Request,
    response: Response,
    user_id: Optional[str] = None,
):
    """Initiate GitHub OAuth flow. Optional user_id links the GitHub account to that user (Supabase)."""
    session_id = get_session_id(request, response)

    # State: session_id for CSRF; optional user_id so callback can link token to user
    state = f"{session_id}:{user_id}" if user_id else session_id
    auth_url = get_github_auth_url(state)

    return RedirectResponse(url=auth_url)


def _parse_state(state: str, session_id: str) -> Tuple[str, Optional[str]]:
    """Extract session_id and optional user_id from state. Returns (session_id, user_id or None)."""
    if ":" in state:
        parts = state.split(":", 1)
        return parts[0], parts[1] if len(parts) > 1 and parts[1] else None
    return state, None


@router.get("/callback")
async def github_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub OAuth callback."""
    session_id = request.cookies.get(SESSION_COOKIE)
    expected_session_id, user_id = _parse_state(state, session_id)

    # Verify state matches session (CSRF protection)
    if session_id != expected_session_id:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/?github_auth=error&message=Invalid+state+parameter"
        )

    try:
        # Exchange code for token
        token_response = await exchange_code_for_token(code)
        access_token = token_response.get("access_token")

        if not access_token:
            error = token_response.get("error_description", "Failed to get access token")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/?github_auth=error&message={error}"
            )

        # Get user info
        user_info = await get_github_user(access_token)

        # Save token (optionally linked to Supabase user)
        await save_github_token(db, session_id, access_token, user_info, user_id=user_id)

        return RedirectResponse(url=f"{FRONTEND_URL}/?github_auth=success")

    except Exception as e:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/?github_auth=error&message={str(e)}"
        )


@router.get("/status", response_model=GitHubAuthStatus)
async def github_status(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Check GitHub authentication status."""
    session_id = get_session_id(request, response)
    status = await get_github_auth_status(db, session_id)
    return GitHubAuthStatus(**status)


@router.get("/repos", response_model=List[GitHubRepo])
async def github_repos(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """List GitHub repositories for authenticated user."""
    session_id = get_session_id(request, response)
    access_token = await get_github_token(db, session_id)

    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with GitHub"
        )

    try:
        repos = list_github_repos(access_token)
        return [GitHubRepo(**repo) for repo in repos]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list repositories: {str(e)}"
        )


@router.post("/import")
async def github_import(
    import_request: GitHubImportRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    tamu_api_key: Optional[str] = Header(default=None, alias="X-TAMU-API-Key"),
):
    """Import a GitHub repository. Optionally scoped to user via X-User-Id header.
    Uses TAMU API key from body or X-TAMU-API-Key header for file discovery (same as chat)."""
    from dependencies import get_optional_user_id

    session_id = get_session_id(request, response)
    access_token = await get_github_token(db, session_id)
    owner_user_id = get_optional_user_id(request)

    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with GitHub"
        )

    api_key = import_request.api_key if (import_request.api_key and import_request.api_key.strip()) else tamu_api_key

    try:
        # Clone the repository (linked to current user when X-User-Id is sent)
        repository = await clone_github_repo(
            access_token,
            import_request.repo_full_name,
            db,
            owner_user_id=owner_user_id,
        )

        # Run file discovery (uses TAMU API with provided key, not Anthropic)
        await run_file_discovery(repository.local_path, db, repository.id, api_key=api_key)

        return {
            "id": repository.id,
            "name": repository.name,
            "source_type": repository.source_type,
            "github_url": repository.github_url,
            "message": "Repository imported successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import repository: {str(e)}"
        )


@router.post("/logout")
async def github_logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Log out from GitHub (delete stored token)."""
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        await delete_github_token(db, session_id)

    return {"message": "Logged out from GitHub"}
