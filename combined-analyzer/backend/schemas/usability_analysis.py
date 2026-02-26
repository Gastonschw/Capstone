"""
Pydantic schemas for Usability Analysis.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class UsabilityAnalysisResponse(BaseModel):
    """Response schema for a Usability analysis."""
    id: int
    repository_id: int
    status: str
    error_message: Optional[str] = None

    # 8 Characteristic reports
    appropriateness_recognizability_report: Optional[Dict[str, Any]] = None
    learnability_report: Optional[Dict[str, Any]] = None
    operability_report: Optional[Dict[str, Any]] = None
    user_error_protection_report: Optional[Dict[str, Any]] = None
    user_engagement_report: Optional[Dict[str, Any]] = None
    self_descriptiveness_report: Optional[Dict[str, Any]] = None
    inclusivity_report: Optional[Dict[str, Any]] = None
    user_assistance_report: Optional[Dict[str, Any]] = None

    # Overall results
    overall_score: Optional[float] = None
    summary_report: Optional[Dict[str, Any]] = None

    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UsabilityAnalysisListItem(BaseModel):
    """Summary response for Usability analysis listing."""
    id: int
    repository_id: int
    status: str
    overall_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
