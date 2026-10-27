"""
GitHub OAuth and Repository Service

Handles GitHub authentication, repository listing, and cloning.
"""

import asyncio
import uuid
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from github import Github
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import (
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    GITHUB_REDIRECT_URI,
    ENCRYPTION_KEY,
    REPOS_DIR,
)
from models.github_token import GitHubToken
from models.repository import Repository, RepositorySource
from services.user_service import require_registered_user


# Initialize Fernet cipher
_fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


def encrypt_token(token: str) -> str:
    """Encrypt a GitHub access token."""
    return _fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a GitHub access token."""
    return _fernet.decrypt(encrypted_token.encode()).decode()


def get_github_auth_url(state: str) -> str:
    """Generate GitHub OAuth authorization URL."""
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "repo read:user",
        "state": state,
    }
    return f"https://github.com/login/oauth/authorize?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    """Exchange OAuth code for access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()


async def get_github_user(access_token: str) -> dict:
    """Get authenticated GitHub user info."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        response.raise_for_status()
        return response.json()


async def save_github_token(
    db: AsyncSession,
    session_id: str,
    access_token: str,
    user_info: dict,
    *,
    user_id: str,
) -> GitHubToken:
    """Persist a fresh server-generated session for its registered owner."""
    link_uid = await require_registered_user(db, user_id)
    encrypted_token = encrypt_token(access_token)

    token_record = GitHubToken(
        session_id=session_id,
        access_token_encrypted=encrypted_token,
        github_user_id=str(user_info.get("id")),
        github_username=user_info.get("login"),
        user_id=link_uid,
    )
    db.add(token_record)
    await db.commit()
    await db.refresh(token_record)
    return token_record


async def get_github_token(db: AsyncSession, session_id: str, user_id: str) -> Optional[str]:
    """Get a token only when both session and verified owner match."""
    result = await db.execute(
        select(GitHubToken).where(GitHubToken.session_id == session_id, GitHubToken.user_id == uuid.UUID(user_id))
    )
    token_record = result.scalar_one_or_none()
    if token_record:
        try:
            return decrypt_token(token_record.access_token_encrypted)
        except InvalidToken:
            # Encryption key has changed or token is corrupted; remove stale record
            await db.delete(token_record)
            await db.commit()
            return None
    return None


async def get_github_auth_status(db: AsyncSession, session_id: str, user_id: str) -> dict:
    """Check an owner-bound session."""
    result = await db.execute(
        select(GitHubToken).where(GitHubToken.session_id == session_id, GitHubToken.user_id == uuid.UUID(user_id))
    )
    token_record = result.scalar_one_or_none()
    if token_record:
        return {
            "authenticated": True,
            "username": token_record.github_username,
        }
    return {"authenticated": False, "username": None}


def list_github_repos(access_token: str) -> List[dict]:
    """List repositories accessible to the authenticated user."""
    with Github(access_token) as github:
        return [{
            "full_name": repo.full_name,
            "name": repo.name,
            "description": repo.description,
            "private": repo.private,
            "html_url": repo.html_url,
            "default_branch": repo.default_branch,
        } for repo in github.get_user().get_repos(sort="updated")]


async def clone_github_repo(
    access_token: str,
    repo_full_name: str,
    db: AsyncSession,
    *,
    owner_user_id: Optional[str] = None,
) -> Repository:
    """Download safely in a worker, then flush into the caller's transaction."""
    from services.folder_service import extract_zip_safely, flatten_single_root_directory, run_file_operation, CHUNK_SIZE
    from config import MAX_UPLOAD_SIZE

    link_uid = await require_registered_user(db, owner_user_id)
    repo_path = REPOS_DIR / str(uuid.uuid4())

    def download():
        with Github(access_token) as github:
            repo = github.get_repo(repo_full_name)
            archive_url = repo.get_archive_link("zipball", ref=repo.default_branch)
            repo_path.mkdir(parents=True, exist_ok=False)
            with tempfile.TemporaryDirectory(prefix="github-download-") as temporary:
                zip_path = Path(temporary) / "archive.zip"
                with httpx.Client(follow_redirects=True, timeout=60) as client:
                    with client.stream("GET", archive_url) as response:
                        response.raise_for_status()
                        size = 0
                        with zip_path.open("wb") as destination:
                            for chunk in response.iter_bytes(CHUNK_SIZE):
                                size += len(chunk)
                                if size > MAX_UPLOAD_SIZE:
                                    raise ValueError("Compressed archive exceeds upload limit")
                                destination.write(chunk)
                extract_zip_safely(zip_path, repo_path)
            flatten_single_root_directory(repo_path)
            return repo.name, repo.html_url

    try:
        name, html_url = await run_file_operation(download)
        repository = Repository(
            name=name,
            source_type=RepositorySource.github.value,
            github_url=html_url,
            github_repo_full_name=repo_full_name,
            local_path=str(repo_path),
            owner_user_id=link_uid,
        )
        db.add(repository)
        await db.flush()
        return repository
    except BaseException:
        shutil.rmtree(repo_path, ignore_errors=True)
        raise


async def delete_github_token(db: AsyncSession, session_id: str, user_id: str) -> bool:
    """Delete only the verified owner's session."""
    result = await db.execute(
        select(GitHubToken).where(GitHubToken.session_id == session_id, GitHubToken.user_id == uuid.UUID(user_id))
    )
    token_record = result.scalar_one_or_none()
    if token_record:
        await db.delete(token_record)
        await db.commit()
        return True
    return False
