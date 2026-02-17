"""
Pydantic schemas for GitHub OAuth.
"""

from pydantic import BaseModel
from typing import Optional


class GitHubAuthStatus(BaseModel):
    """Response for GitHub authentication status."""
    authenticated: bool
    username: Optional[str] = None


class GitHubRepo(BaseModel):
    """Schema for a GitHub repository."""
    full_name: str
    name: str
    description: Optional[str] = None
    private: bool
    html_url: str
    default_branch: str


class GitHubImportRequest(BaseModel):
    """Request to import a GitHub repository."""
    repo_full_name: str
