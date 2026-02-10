from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any, List


# ============== Repository Schemas ==============

class RepositoryCreate(BaseModel):
    name: str
    source_type: str = "folder_upload"
    github_url: Optional[str] = None
    github_repo_full_name: Optional[str] = None


class DiscoveredFileResponse(BaseModel):
    id: int
    file_path: str
    file_type: str
    confidence_score: int
    content_preview: Optional[str] = None
    is_selected: bool

    class Config:
        from_attributes = True


class RepositoryResponse(BaseModel):
    id: int
    created_at: datetime
    name: str
    source_type: str
    github_url: Optional[str] = None
    github_repo_full_name: Optional[str] = None

    class Config:
        from_attributes = True


class RepositoryDetailResponse(RepositoryResponse):
    discovered_files: List[DiscoveredFileResponse] = []


class RepositoryListItem(BaseModel):
    id: int
    created_at: datetime
    name: str
    source_type: str

    class Config:
        from_attributes = True


class FileSelectionUpdate(BaseModel):
    file_ids: List[int]
    is_selected: bool


# ============== GitHub Schemas ==============

class GitHubRepoInfo(BaseModel):
    full_name: str
    name: str
    description: Optional[str] = None
    private: bool
    html_url: str
    default_branch: str


class GitHubImportRequest(BaseModel):
    repo_full_name: str  # e.g., "owner/repo"


class GitHubAuthStatus(BaseModel):
    authenticated: bool
    username: Optional[str] = None


# ============== UML Structure Schemas ==============

class UMLAttribute(BaseModel):
    name: str
    type: str
    visibility: str = "public"  # public, private, protected
    is_primary_key: bool = False
    is_foreign_key: bool = False


class UMLClass(BaseModel):
    name: str
    attributes: List[UMLAttribute] = []
    methods: List[str] = []


class UMLAssociation(BaseModel):
    source: str
    target: str
    association_type: str = "association"  # association, aggregation, composition
    source_multiplicity: str = "1"
    target_multiplicity: str = "*"
    label: Optional[str] = None


class UMLGeneralization(BaseModel):
    parent: str
    child: str


class UMLStructure(BaseModel):
    classes: List[UMLClass] = []
    associations: List[UMLAssociation] = []
    generalizations: List[UMLGeneralization] = []


# ============== Analysis Schemas ==============

class AnalysisCreate(BaseModel):
    user_stories: str


class AnalysisResponse(BaseModel):
    id: int
    created_at: datetime
    image_filename: Optional[str] = None
    user_stories: Optional[str] = None
    repository_id: Optional[int] = None
    uml_structure: Optional[Any] = None
    extracted_erd: Optional[Any] = None
    report: Optional[Any] = None
    status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class AnalysisListItem(BaseModel):
    id: int
    created_at: datetime
    status: str
    repository_id: Optional[int] = None

    class Config:
        from_attributes = True


class StartAnalysisRequest(BaseModel):
    repository_id: int
