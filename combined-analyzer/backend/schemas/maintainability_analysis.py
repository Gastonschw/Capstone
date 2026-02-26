"""
Pydantic schemas for Maintainability Analysis.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class MaintainabilityAnalysisResponse(BaseModel):
    """Response schema for a Maintainability analysis."""
    id: int
    repository_id: int
    status: str
    error_message: Optional[str] = None

    # 5 Characteristic reports
    modularity_report: Optional[Dict[str, Any]] = None
    reusability_report: Optional[Dict[str, Any]] = None
    analysability_report: Optional[Dict[str, Any]] = None
    modifiability_report: Optional[Dict[str, Any]] = None
    testability_report: Optional[Dict[str, Any]] = None

    # Overall results
    overall_score: Optional[float] = None
    summary_report: Optional[Dict[str, Any]] = None

    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MaintainabilityAnalysisListItem(BaseModel):
    """Summary response for Maintainability analysis listing."""
    id: int
    repository_id: int
    status: str
    overall_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
