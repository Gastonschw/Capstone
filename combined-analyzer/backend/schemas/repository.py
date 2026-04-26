"""
Pydantic schemas for Repository and DiscoveredFile.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DiscoveredFileResponse(BaseModel):
    """Response schema for a discovered file."""
    id: int
    file_path: str
    file_type: str
    language: Optional[str] = None
    confidence_score: int
    relevance_score: int
    content_preview: Optional[str] = None
    is_selected_erd: bool
    is_selected_integrity: bool
    is_selected_compliance: bool = False
    is_selected_correctness: bool = False
    is_selected_usability: bool = False
    is_selected_maintainability: bool = False

    class Config:
        from_attributes = True


class RepositoryResponse(BaseModel):
    """Full repository response with discovered files."""
    id: int
    name: str
    source_type: str
    local_path: str
    github_url: Optional[str] = None
    github_repo_full_name: Optional[str] = None
    created_at: datetime
    discovered_files: List[DiscoveredFileResponse] = []

    class Config:
        from_attributes = True


class RepositoryListResponse(BaseModel):
    """Summary response for repository listing."""
    id: int
    name: str
    source_type: str
    github_url: Optional[str] = None
    created_at: datetime
    file_count: int = 0
    erd_analysis_count: int = 0
    integrity_analysis_count: int = 0
    compliance_analysis_count: int = 0
    correctness_analysis_count: int = 0
    usability_analysis_count: int = 0
    maintainability_analysis_count: int = 0

    class Config:
        from_attributes = True


class FileSelectionUpdate(BaseModel):
    """Request schema for updating file selections."""
    file_ids: List[int]
    is_selected: bool
    analysis_type: str  # 'erd', 'integrity', 'compliance', 'correctness', 'usability', 'maintainability'


class FileTypeUpdate(BaseModel):
    """Request schema for changing a discovered file's type."""
    file_type: str  # 'erd_image', 'user_story', 'code', 'config', 'other'
