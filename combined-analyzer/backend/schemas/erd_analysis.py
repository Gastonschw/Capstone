"""
Pydantic schemas for ERD Analysis.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class UMLAttribute(BaseModel):
    """Schema for a UML class attribute."""
    name: str
    type: Optional[str] = None
    visibility: Optional[str] = "public"
    is_primary_key: bool = False
    is_foreign_key: bool = False
    is_nullable: Optional[bool] = True
    default_value: Optional[str] = None


class UMLClass(BaseModel):
    """Schema for a UML class."""
    name: str
    attributes: List[UMLAttribute] = []
    methods: List[str] = []


class UMLAssociation(BaseModel):
    """Schema for a UML association/relationship."""
    source: str
    target: str
    association_type: Optional[str] = "association"
    source_multiplicity: Optional[str] = None
    target_multiplicity: Optional[str] = None
    label: Optional[str] = None
    source_role: Optional[str] = None
    target_role: Optional[str] = None


class UMLGeneralization(BaseModel):
    """Schema for a UML generalization (inheritance)."""
    parent: str
    child: str


class UMLStructure(BaseModel):
    """Complete UML structure extracted from ERD."""
    classes: List[UMLClass] = []
    associations: List[UMLAssociation] = []
    generalizations: List[UMLGeneralization] = []
    notes: List[str] = []


class ERDAnalysisResponse(BaseModel):
    """Response schema for an ERD analysis."""
    id: int
    repository_id: int
    status: str
    error_message: Optional[str] = None
    uml_structure: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
    coverage_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ERDAnalysisListItem(BaseModel):
    """Summary response for ERD analysis listing."""
    id: int
    repository_id: int
    status: str
    coverage_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
