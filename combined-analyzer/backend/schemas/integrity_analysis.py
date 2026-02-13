"""
Pydantic schemas for Integrity Analysis.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class Finding(BaseModel):
    """Schema for a security finding."""
    type: str  # 'positive', 'negative', 'warning'
    file_path: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    explanation: str


class CharacteristicReport(BaseModel):
    """Schema for a single characteristic analysis report."""
    characteristic: str
    score: float  # 0-100
    status: str  # 'fulfilled', 'partially_fulfilled', 'not_fulfilled', 'not_applicable'
    description: str
    findings: List[Dict[str, Any]] = []
    recommendations: List[str] = []


class SummaryReport(BaseModel):
    """Schema for the overall summary report."""
    overall_score: float
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    executive_summary: str
    strengths: List[str] = []
    areas_for_improvement: List[str] = []
    priority_recommendations: List[str] = []


class IntegrityAnalysisResponse(BaseModel):
    """Response schema for an Integrity analysis."""
    id: int
    repository_id: int
    status: str
    error_message: Optional[str] = None

    # 6 Characteristic reports
    confidentiality_report: Optional[Dict[str, Any]] = None
    data_integrity_report: Optional[Dict[str, Any]] = None
    authenticity_report: Optional[Dict[str, Any]] = None
    non_repudiation_report: Optional[Dict[str, Any]] = None
    accountability_report: Optional[Dict[str, Any]] = None
    resistance_report: Optional[Dict[str, Any]] = None

    # Overall results
    overall_score: Optional[float] = None
    summary_report: Optional[Dict[str, Any]] = None

    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IntegrityAnalysisListItem(BaseModel):
    """Summary response for Integrity analysis listing."""
    id: int
    repository_id: int
    status: str
    overall_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
