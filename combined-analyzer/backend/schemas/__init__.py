"""
Pydantic schemas for request/response validation.
"""

from .classes import ClassSummary, MyClassesResponse, ClassMemberItem, ClassMembersResponse
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
from .compliance_analysis import ComplianceAnalysisResponse, ComplianceAnalysisListItem
from .correctness_analysis import CorrectnessAnalysisResponse, CorrectnessAnalysisListItem
from .usability_analysis import UsabilityAnalysisResponse, UsabilityAnalysisListItem
from .maintainability_analysis import MaintainabilityAnalysisResponse, MaintainabilityAnalysisListItem

__all__ = [
    "ClassSummary",
    "MyClassesResponse",
    "ClassMemberItem",
    "ClassMembersResponse",
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
    "ComplianceAnalysisResponse",
    "ComplianceAnalysisListItem",
    "CorrectnessAnalysisResponse",
    "CorrectnessAnalysisListItem",
    "UsabilityAnalysisResponse",
    "UsabilityAnalysisListItem",
    "MaintainabilityAnalysisResponse",
    "MaintainabilityAnalysisListItem",
]
