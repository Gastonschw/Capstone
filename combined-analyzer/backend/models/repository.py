"""
Repository and DiscoveredFile models.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from database import Base


class RepositorySource(str, enum.Enum):
    folder_upload = "folder_upload"
    github = "github"


class FileType(str, enum.Enum):
    # ERD Analysis file types
    erd_image = "erd_image"
    user_story = "user_story"
    # Integrity Analysis file types
    code = "code"
    config = "config"
    documentation = "documentation"
    # Generic
    other = "other"


class Repository(Base):
    """Stores repository metadata for folder uploads or GitHub imports."""
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), default=RepositorySource.folder_upload.value)
    github_url = Column(String(500), nullable=True)
    github_repo_full_name = Column(String(255), nullable=True)
    local_path = Column(String(500), nullable=False)
    # When using Supabase: links to public.users (Google Auth). UUID for Postgres.
    owner_user_id = Column(PG_UUID(as_uuid=True), nullable=True)

    # Relationships
    discovered_files = relationship(
        "DiscoveredFile",
        back_populates="repository",
        cascade="all, delete-orphan"
    )
    erd_analyses = relationship(
        "ERDAnalysis",
        back_populates="repository",
        cascade="all, delete-orphan"
    )
    integrity_analyses = relationship(
        "IntegrityAnalysis",
        back_populates="repository",
        cascade="all, delete-orphan"
    )


class DiscoveredFile(Base):
    """Files discovered by the AI agent in a repository.

    Supports dual selection for both ERD and Integrity analysis workflows.
    """
    __tablename__ = "discovered_files"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # File metadata
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), default=FileType.other.value)
    language = Column(String(50), nullable=True)  # For code files: python, javascript, etc.

    # Scoring
    confidence_score = Column(Integer, default=50)  # For ERD files: how confident AI is this is an ERD/user story
    relevance_score = Column(Integer, default=50)  # For Integrity files: security relevance 0-100

    # Content preview
    content_preview = Column(Text, nullable=True)  # First ~500 chars

    # Dual selection columns - files can be selected for either or both analysis types
    is_selected_erd = Column(Boolean, default=False)
    is_selected_integrity = Column(Boolean, default=False)

    # Relationship
    repository = relationship("Repository", back_populates="discovered_files")
