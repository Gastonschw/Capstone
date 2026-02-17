"""
GitHub OAuth API routes.
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.github import GitHubRepo, GitHubImportRequest, GitHubAuthStatus
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
async def github_auth(request: Request, response: Response):
    """Initiate GitHub OAuth flow."""
    session_id = get_session_id(request, response)

    # Use session_id as OAuth state for CSRF protection
    auth_url = get_github_auth_url(session_id)

    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def github_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub OAuth callback."""
    session_id = request.cookies.get(SESSION_COOKIE)

    # Verify state matches session (CSRF protection)
    if state != session_id:
        return RedirectResponse(
            url="/?github_auth=error&message=Invalid+state+parameter"
        )

    try:
        # Exchange code for token
        token_response = await exchange_code_for_token(code)
        access_token = token_response.get("access_token")

        if not access_token:
            error = token_response.get("error_description", "Failed to get access token")
            return RedirectResponse(
                url=f"/?github_auth=error&message={error}"
            )

        # Get user info
        user_info = await get_github_user(access_token)

        # Save token
        await save_github_token(db, session_id, access_token, user_info)

        return RedirectResponse(url="/?github_auth=success")

    except Exception as e:
        return RedirectResponse(
            url=f"/?github_auth=error&message={str(e)}"
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
    db: AsyncSession = Depends(get_db)
):
    """Import a GitHub repository."""
    session_id = get_session_id(request, response)
    access_token = await get_github_token(db, session_id)

    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with GitHub"
        )

    try:
        # Clone the repository
        repository = await clone_github_repo(
            access_token,
            import_request.repo_full_name,
            db
        )

        # Run file discovery
        await run_file_discovery(repository.local_path, db, repository.id)

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
