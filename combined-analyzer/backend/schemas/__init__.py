"""
Pydantic schemas for request/response validation.
"""

from .repository import (
    RepositoryResponse,
    RepositoryListResponse,
    DiscoveredFileResponse,
    FileSelectionUpdate,
)
from .github import (
    GitHubRepo,
    GitHubImportRequest,
    GitHubAuthStatus,
)
from .erd_analysis import ERDAnalysisResponse, ERDAnalysisListItem
from .integrity_analysis import IntegrityAnalysisResponse, IntegrityAnalysisListItem
from .classes import ClassSummary, MyClassesResponse

__all__ = [
    "RepositoryResponse",
    "RepositoryListResponse",
    "DiscoveredFileResponse",
    "FileSelectionUpdate",
    "GitHubRepo",
    "GitHubImportRequest",
    "GitHubAuthStatus",
    "ERDAnalysisResponse",
    "ERDAnalysisListItem",
    "IntegrityAnalysisResponse",
    "IntegrityAnalysisListItem",
    "ClassSummary",
    "MyClassesResponse",
]
