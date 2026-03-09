"""
Pydantic schemas for Compliance Analysis.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ComplianceAnalysisResponse(BaseModel):
    """Response schema for a Compliance analysis."""
    id: int
    repository_id: int
    status: str
    error_message: Optional[str] = None

    # 3 Characteristic reports
    functional_completeness_report: Optional[Dict[str, Any]] = None
    functional_correctness_report: Optional[Dict[str, Any]] = None
    functional_appropriateness_report: Optional[Dict[str, Any]] = None

    # Overall results
    overall_score: Optional[float] = None
    summary_report: Optional[Dict[str, Any]] = None

    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ComplianceAnalysisListItem(BaseModel):
    """Summary response for Compliance analysis listing."""
    id: int
    repository_id: int
    status: str
    overall_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
