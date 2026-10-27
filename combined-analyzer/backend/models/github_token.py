"""
GitHub OAuth token model.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
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
    # When using Supabase: links to public.users (Google Auth). UUID for Postgres.
    user_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)


class GitHubOAuthState(Base):
    """Short-lived, browser-bound, single-use OAuth authorization."""
    __tablename__ = "github_oauth_states"

    state_hash = Column(String(64), primary_key=True)
    cookie_hash = Column(String(64), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)


class GitHubOAuthTicket(Base):
    """One-use handoff from authenticated fetch to top-level browser navigation."""
    __tablename__ = "github_oauth_tickets"

    ticket_hash = Column(String(64), primary_key=True)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
