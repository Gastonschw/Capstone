from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from database import Base


class AnalysisStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class RepositorySource(str, enum.Enum):
    folder_upload = "folder_upload"
    github = "github"


class FileType(str, enum.Enum):
    erd_image = "erd_image"
    user_story = "user_story"
    other = "other"


class Repository(Base):
    """Stores repository metadata for folder uploads or GitHub imports."""
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    name = Column(String, nullable=False)
    source_type = Column(String, default=RepositorySource.folder_upload.value)
    github_url = Column(String, nullable=True)
    github_repo_full_name = Column(String, nullable=True)  # e.g., "owner/repo"
    local_path = Column(String, nullable=False)  # Path to extracted/cloned repo
    
    # Relationships
    discovered_files = relationship("DiscoveredFile", back_populates="repository", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="repository", cascade="all, delete-orphan")


class DiscoveredFile(Base):
    """Files discovered by the AI agent in a repository."""
    __tablename__ = "discovered_files"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    file_path = Column(String, nullable=False)  # Relative path within repo
    file_type = Column(String, default=FileType.other.value)
    confidence_score = Column(Integer, default=0)  # 0-100, how confident the AI is
    content_preview = Column(Text, nullable=True)  # First ~500 chars for user stories
    is_selected = Column(Boolean, default=True)  # User can deselect files
    
    # Relationship
    repository = relationship("Repository", back_populates="discovered_files")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Legacy single-file support (nullable for backward compatibility)
    image_filename = Column(String, nullable=True)
    user_stories = Column(Text, nullable=True)
    
    # New repository-based analysis
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True)
    
    # UML structure extracted from ERD (enhanced format)
    uml_structure = Column(Text, nullable=True)  # JSON stored as text
    extracted_erd = Column(Text, nullable=True)  # JSON stored as text (legacy)
    report = Column(Text, nullable=True)  # JSON stored as text
    status = Column(String, default=AnalysisStatus.pending.value)
    error_message = Column(Text, nullable=True)
    
    # Relationship
    repository = relationship("Repository", back_populates="analyses")


class GitHubToken(Base):
    """Stores encrypted GitHub OAuth tokens."""
    __tablename__ = "github_tokens"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    access_token_encrypted = Column(Text, nullable=False)
    github_user_id = Column(String, nullable=True)
    github_username = Column(String, nullable=True)
    session_id = Column(String, unique=True, index=True)  # For session lookup
