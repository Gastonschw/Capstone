"""
Compliance Analysis model (ISO 25010 Functional Suitability).
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class ComplianceAnalysis(Base):
    """Stores Compliance analysis results.

    Analyzes codebase for 3 functional suitability characteristics:
    - Functional Completeness
    - Functional Correctness
    - Functional Appropriateness
    """
    __tablename__ = "compliance_analyses"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)

    # 3 Characteristic reports (stored as JSON text)
    functional_completeness_report = Column(Text, nullable=True)
    functional_correctness_report = Column(Text, nullable=True)
    functional_appropriateness_report = Column(Text, nullable=True)

    # Overall results
    overall_score = Column(Float, nullable=True)  # 0-100
    summary_report = Column(Text, nullable=True)  # Executive summary JSON

    # Relationship
    repository = relationship("Repository", back_populates="compliance_analyses")
