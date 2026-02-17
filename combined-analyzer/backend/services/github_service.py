"""
GitHub OAuth and Repository Service

Handles GitHub authentication, repository listing, and cloning.
"""

import os
import uuid
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet
from github import Github, GithubException
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
    user_info: dict
) -> GitHubToken:
    """Save or update GitHub token for a session."""
    # Check if token exists for this session
    result = await db.execute(
        select(GitHubToken).where(GitHubToken.session_id == session_id)
    )
    existing = result.scalar_one_or_none()

    encrypted_token = encrypt_token(access_token)

    if existing:
        existing.access_token_encrypted = encrypted_token
        existing.github_user_id = str(user_info.get("id"))
        existing.github_username = user_info.get("login")
        await db.commit()
        return existing

    token_record = GitHubToken(
        session_id=session_id,
        access_token_encrypted=encrypted_token,
        github_user_id=str(user_info.get("id")),
        github_username=user_info.get("login"),
    )
    db.add(token_record)
    await db.commit()
    await db.refresh(token_record)
    return token_record


async def get_github_token(db: AsyncSession, session_id: str) -> Optional[str]:
    """Get decrypted GitHub token for a session."""
    result = await db.execute(
        select(GitHubToken).where(GitHubToken.session_id == session_id)
    )
    token_record = result.scalar_one_or_none()
    if token_record:
        return decrypt_token(token_record.access_token_encrypted)
    return None


async def get_github_auth_status(db: AsyncSession, session_id: str) -> dict:
    """Check if a session has valid GitHub auth."""
    result = await db.execute(
        select(GitHubToken).where(GitHubToken.session_id == session_id)
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
    g = Github(access_token)
    user = g.get_user()

    repos = []
    for repo in user.get_repos(sort="updated"):
        repos.append({
            "full_name": repo.full_name,
            "name": repo.name,
            "description": repo.description,
            "private": repo.private,
            "html_url": repo.html_url,
            "default_branch": repo.default_branch,
        })
        # Limit to 50 repos for performance
        if len(repos) >= 50:
            break

    return repos


async def clone_github_repo(
    access_token: str,
    repo_full_name: str,
    db: AsyncSession
) -> Repository:
    """Clone a GitHub repository and create a Repository record."""
    g = Github(access_token)

    try:
        repo = g.get_repo(repo_full_name)
    except GithubException as e:
        raise ValueError(f"Could not access repository: {e}")

    # Create unique directory for this repo
    repo_uuid = str(uuid.uuid4())
    repo_path = REPOS_DIR / repo_uuid
    repo_path.mkdir(parents=True, exist_ok=True)

    # Download repo as ZIP and extract
    archive_url = repo.get_archive_link("zipball", ref=repo.default_branch)

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
        tmp_path = tmp_file.name

        # Download the archive
        import urllib.request
        urllib.request.urlretrieve(archive_url, tmp_path)

    # Extract the archive
    shutil.unpack_archive(tmp_path, repo_path)
    os.unlink(tmp_path)

    # GitHub archives have a root folder like "owner-repo-hash", move contents up
    extracted_items = list(repo_path.iterdir())
    if len(extracted_items) == 1 and extracted_items[0].is_dir():
        # Move all contents from subdirectory to repo_path
        sub_dir = extracted_items[0]
        for item in sub_dir.iterdir():
            shutil.move(str(item), str(repo_path / item.name))
        sub_dir.rmdir()

    # Create Repository record
    repository = Repository(
        name=repo.name,
        source_type=RepositorySource.github.value,
        github_url=repo.html_url,
        github_repo_full_name=repo_full_name,
        local_path=str(repo_path),
    )
    db.add(repository)
    await db.commit()
    await db.refresh(repository)

    return repository


async def delete_github_token(db: AsyncSession, session_id: str) -> bool:
    """Delete GitHub token for a session (logout)."""
    result = await db.execute(
        select(GitHubToken).where(GitHubToken.session_id == session_id)
    )
    token_record = result.scalar_one_or_none()
    if token_record:
        await db.delete(token_record)
        await db.commit()
        return True
    return False
