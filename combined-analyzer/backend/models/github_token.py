"""
GitHub OAuth token model.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from database import Base


class GitHubToken(Base):
    """Stores encrypted GitHub OAuth tokens for user sessions."""
    __tablename__ = "github_tokens"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    session_id = Column(String(255), unique=True, index=True, nullable=False)
    access_token_encrypted = Column(Text, nullable=False)
    github_user_id = Column(String(100), nullable=True)
    github_username = Column(String(255), nullable=True)
