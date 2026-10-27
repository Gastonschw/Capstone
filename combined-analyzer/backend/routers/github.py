"""Verified-owner GitHub OAuth and repository import routes."""

import asyncio
import hashlib
import secrets
import shutil
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import FRONTEND_URL, GITHUB_REDIRECT_URI
from database import get_db
from dependencies import get_current_user_id
from models.github_token import GitHubOAuthState, GitHubOAuthTicket, GitHubToken
from schemas.github import GitHubRepo, GitHubImportRequest, GitHubAuthStatus, GitHubAuthResponse
from services.user_service import require_registered_user
from services.github_service import (
    get_github_auth_url, exchange_code_for_token, get_github_user,
    save_github_token, get_github_token, get_github_auth_status,
    list_github_repos, clone_github_repo, delete_github_token,
)
from services.discovery_service import run_file_discovery

router = APIRouter(prefix="/api/github", tags=["github"])
SESSION_COOKIE = "session_id"
STATE_COOKIE = "github_oauth_binding"
COOKIE_PATH = "/api/github"
COOKIE_SECURE = GITHUB_REDIRECT_URI.startswith("https://")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def get_session_id(request: Request) -> str:
    return request.headers.get("x-session-id") or request.cookies.get(SESSION_COOKIE) or ""


@router.post("/auth", response_model=GitHubAuthResponse)
async def github_auth(response: Response, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    owner = await require_registered_user(db, user_id)
    ticket = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    await db.execute(delete(GitHubOAuthTicket).where(GitHubOAuthTicket.expires_at <= now))
    await db.execute(delete(GitHubOAuthState).where(GitHubOAuthState.expires_at <= now))
    db.add(GitHubOAuthTicket(ticket_hash=_digest(ticket), user_id=owner, expires_at=now + timedelta(minutes=2)))
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
    # Derive from trusted deployment config, never a caller-controlled Host header.
    authorize_url = GITHUB_REDIRECT_URI.rsplit("/", 1)[0] + "/authorize"
    return {"authorization_url": f"{authorize_url}?ticket={ticket}"}


@router.get("/authorize")
async def github_authorize(ticket: str, db: AsyncSession = Depends(get_db)):
    """Set the browser binding in first-party navigation, not cross-site fetch."""
    now = datetime.now(timezone.utc)
    result = await db.execute(delete(GitHubOAuthTicket).where(
        GitHubOAuthTicket.ticket_hash == _digest(ticket),
        GitHubOAuthTicket.expires_at > now,
    ).returning(GitHubOAuthTicket.user_id))
    owner = result.scalar_one_or_none()
    await db.commit()
    if owner is None:
        raise HTTPException(400, "Invalid or expired GitHub authorization ticket")
    await require_registered_user(db, owner)
    state = secrets.token_urlsafe(32)
    binding = secrets.token_urlsafe(32)
    db.add(GitHubOAuthState(state_hash=_digest(state), cookie_hash=_digest(binding), user_id=owner, expires_at=now + timedelta(minutes=10)))
    await db.commit()
    response = RedirectResponse(get_github_auth_url(state))
    response.set_cookie(STATE_COOKIE, binding, max_age=600, httponly=True, secure=COOKIE_SECURE, samesite="lax", path=COOKIE_PATH)
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/callback")
async def github_callback(code: str, state: str, request: Request, db: AsyncSession = Depends(get_db)):
    binding = request.cookies.get(STATE_COOKIE)
    if not binding:
        raise HTTPException(400, "Missing OAuth browser binding; restart GitHub sign-in")
    # DELETE RETURNING makes replay and simultaneous callback consumption atomic.
    result = await db.execute(delete(GitHubOAuthState).where(
        GitHubOAuthState.state_hash == _digest(state),
        GitHubOAuthState.cookie_hash == _digest(binding),
        GitHubOAuthState.expires_at > datetime.now(timezone.utc),
    ).returning(GitHubOAuthState.user_id))
    owner = result.scalar_one_or_none()
    await db.commit()
    if owner is None:
        raise HTTPException(400, "Invalid or expired OAuth state")
    try:
        await require_registered_user(db, owner)
        token_response = await exchange_code_for_token(code)
        token = token_response.get("access_token")
        if not isinstance(token, str) or not token:
            raise ValueError("GitHub authorization failed")
        info = await get_github_user(token)
        session_id = secrets.token_urlsafe(32)
        # Reconnecting rotates all prior sessions for this owner.
        await db.execute(delete(GitHubToken).where(GitHubToken.user_id == owner))
        await save_github_token(db, session_id, token, info, user_id=str(owner))
        response = RedirectResponse(f"{FRONTEND_URL}/?github_auth=success&session_id={session_id}")
        response.set_cookie(SESSION_COOKIE, session_id, max_age=86400 * 30, httponly=True, secure=COOKIE_SECURE, samesite="lax", path=COOKIE_PATH)
    except Exception:
        await db.rollback()
        response = RedirectResponse(f"{FRONTEND_URL}/?github_auth=error&message=GitHub%20authorization%20failed")
    response.delete_cookie(STATE_COOKIE, path=COOKIE_PATH, secure=COOKIE_SECURE, httponly=True, samesite="lax")
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/status", response_model=GitHubAuthStatus)
async def github_status(request: Request, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return GitHubAuthStatus(**await get_github_auth_status(db, get_session_id(request), user_id))


@router.get("/repos", response_model=List[GitHubRepo])
async def github_repos(request: Request, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    token = await get_github_token(db, get_session_id(request), user_id)
    if not token:
        raise HTTPException(401, "Not authenticated with GitHub")
    try:
        return [GitHubRepo(**repo) for repo in await asyncio.to_thread(list_github_repos, token)]
    except Exception as exc:
        raise HTTPException(502, "Failed to list GitHub repositories") from exc


@router.post("/import")
async def github_import(import_request: GitHubImportRequest, request: Request, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db), tamu_api_key: Optional[str] = Header(default=None, alias="X-TAMU-API-Key")):
    token = await get_github_token(db, get_session_id(request), user_id)
    if not token:
        raise HTTPException(401, "Not authenticated with GitHub")
    api_key = import_request.api_key if import_request.api_key and import_request.api_key.strip() else tamu_api_key
    repository = None
    try:
        repository = await clone_github_repo(token, import_request.repo_full_name, db, owner_user_id=user_id)
        await run_file_discovery(repository.local_path, db, repository.id, api_key=api_key)
        await db.commit()
        return {"id": repository.id, "name": repository.name, "source_type": repository.source_type, "github_url": repository.github_url, "message": "Repository imported successfully"}
    except BaseException:
        await db.rollback()
        if repository is not None:
            shutil.rmtree(repository.local_path, ignore_errors=True)
        raise


@router.post("/logout")
async def github_logout(request: Request, response: Response, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    await delete_github_token(db, get_session_id(request), user_id)
    response.delete_cookie(SESSION_COOKIE, path=COOKIE_PATH)
    return {"message": "Logged out from GitHub"}
