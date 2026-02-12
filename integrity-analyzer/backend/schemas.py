from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# Repository schemas
class RepositoryCreate(BaseModel):
    name: str
    source_type: str
    local_path: str
    github_url: Optional[str] = None
    github_repo_full_name: Optional[str] = None


class DiscoveredFileResponse(BaseModel):
    id: int
    file_path: str
    file_type: str
    language: Optional[str]
    relevance_score: int
    content_preview: Optional[str]
    is_selected: bool

    class Config:
        from_attributes = True


class RepositoryResponse(BaseModel):
    id: int
    name: str
    source_type: str
    local_path: str
    github_url: Optional[str]
    github_repo_full_name: Optional[str]
    created_at: datetime
    discovered_files: List[DiscoveredFileResponse] = []

    class Config:
        from_attributes = True


class RepositoryListResponse(BaseModel):
    id: int
    name: str
    source_type: str
    github_url: Optional[str]
    created_at: datetime
    file_count: int = 0
    analysis_count: int = 0

    class Config:
        from_attributes = True


# Analysis schemas
class CharacteristicReport(BaseModel):
    characteristic: str
    score: float  # 0-100
    status: str  # 'fulfilled', 'partially_fulfilled', 'not_fulfilled', 'not_applicable'
    description: str
    findings: List[dict]  # Each finding has: type, file_path, line_number, code_snippet, explanation
    recommendations: List[str]


class IntegrityAnalysisResponse(BaseModel):
    id: int
    repository_id: int
    status: str
    error_message: Optional[str]
    overall_score: Optional[float]

    confidentiality_report: Optional[dict]
    data_integrity_report: Optional[dict]
    authenticity_report: Optional[dict]
    non_repudiation_report: Optional[dict]
    accountability_report: Optional[dict]
    resistance_report: Optional[dict]
    summary_report: Optional[dict]

    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# GitHub schemas
class GitHubRepo(BaseModel):
    id: int
    name: str
    full_name: str
    description: Optional[str]
    private: bool
    html_url: str
    default_branch: str


class GitHubImportRequest(BaseModel):
    repo_full_name: str


class FileSelectionUpdate(BaseModel):
    file_ids: List[int]
    is_selected: bool
