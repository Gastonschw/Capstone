"""
Pydantic schemas for classes and membership.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ClassSummary(BaseModel):
    """Summary information about a class."""

    id: str
    name: str
    description: Optional[str] = None
    join_code: Optional[str] = None  # Only returned for owners
    created_at: Optional[datetime] = None


class MyClassesResponse(BaseModel):
    """Classes for the current user."""

    role: Optional[str] = None  # 'admin' or 'general'
    teaching: List[ClassSummary] = []
    enrolled: List[ClassSummary] = []


class ClassMemberItem(BaseModel):
    """A student enrolled in a class (roster row)."""

    user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    joined_at: Optional[datetime] = None


class ClassMembersResponse(BaseModel):
    members: List[ClassMemberItem] = []

