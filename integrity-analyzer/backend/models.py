from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # 'folder_upload' or 'github'
    local_path = Column(String(500), nullable=False)
    github_url = Column(String(500), nullable=True)
    github_repo_full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    discovered_files = relationship("DiscoveredFile", back_populates="repository", cascade="all, delete-orphan")
    analyses = relationship("IntegrityAnalysis", back_populates="repository", cascade="all, delete-orphan")


class DiscoveredFile(Base):
    __tablename__ = "discovered_files"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # 'code', 'config', 'documentation'
    language = Column(String(50), nullable=True)  # 'python', 'javascript', 'java', etc.
    relevance_score = Column(Integer, default=50)  # 0-100 relevance for security analysis
    content_preview = Column(Text, nullable=True)
    is_selected = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    repository = relationship("Repository", back_populates="discovered_files")


class IntegrityAnalysis(Base):
    __tablename__ = "integrity_analyses"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)

    # Analysis results stored as JSON text
    confidentiality_report = Column(Text, nullable=True)
    data_integrity_report = Column(Text, nullable=True)
    authenticity_report = Column(Text, nullable=True)
    non_repudiation_report = Column(Text, nullable=True)
    accountability_report = Column(Text, nullable=True)
    resistance_report = Column(Text, nullable=True)

    # Overall summary
    overall_score = Column(Float, nullable=True)
    summary_report = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    repository = relationship("Repository", back_populates="analyses")


class GitHubToken(Base):
    __tablename__ = "github_tokens"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, nullable=False)
    encrypted_token = Column(Text, nullable=False)
    github_username = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
