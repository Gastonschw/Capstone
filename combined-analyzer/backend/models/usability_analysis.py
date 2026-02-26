"""
Usability Analysis model (ISO 25010 Usability / Interaction Capability).
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class UsabilityAnalysis(Base):
    """Stores Usability analysis results.

    Analyzes codebase for 8 usability characteristics:
    - Appropriateness Recognizability
    - Learnability
    - Operability
    - User Error Protection
    - User Engagement
    - Self-Descriptiveness
    - Inclusivity
    - User Assistance
    """
    __tablename__ = "usability_analyses"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)

    # 8 Characteristic reports (stored as JSON text)
    appropriateness_recognizability_report = Column(Text, nullable=True)
    learnability_report = Column(Text, nullable=True)
    operability_report = Column(Text, nullable=True)
    user_error_protection_report = Column(Text, nullable=True)
    user_engagement_report = Column(Text, nullable=True)
    self_descriptiveness_report = Column(Text, nullable=True)
    inclusivity_report = Column(Text, nullable=True)
    user_assistance_report = Column(Text, nullable=True)

    # Overall results
    overall_score = Column(Float, nullable=True)  # 0-100
    summary_report = Column(Text, nullable=True)  # Executive summary JSON

    # Relationship
    repository = relationship("Repository", back_populates="usability_analyses")
