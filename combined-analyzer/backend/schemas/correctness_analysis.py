"""
Pydantic schemas for Correctness Analysis.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class CorrectnessAnalysisResponse(BaseModel):
    """Response schema for a Correctness analysis."""
    id: int
    repository_id: int
    status: str
    error_message: Optional[str] = None

    # 3 Characteristic reports
    functional_completeness_correctness_report: Optional[Dict[str, Any]] = None
    functional_correctness_accuracy_report: Optional[Dict[str, Any]] = None
    functional_appropriateness_correctness_report: Optional[Dict[str, Any]] = None

    # Overall results
    overall_score: Optional[float] = None
    summary_report: Optional[Dict[str, Any]] = None

    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CorrectnessAnalysisListItem(BaseModel):
    """Summary response for Correctness analysis listing."""
    id: int
    repository_id: int
    status: str
    overall_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
