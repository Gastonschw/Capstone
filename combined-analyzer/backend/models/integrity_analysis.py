"""
Integrity Analysis model.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class IntegrityAnalysis(Base):
    """Stores Integrity analysis results.

    Analyzes codebase for 6 security integrity characteristics:
    - Confidentiality
    - Data Integrity
    - Authenticity
    - Non-Repudiation
    - Accountability
    - Resistance
    """
    __tablename__ = "integrity_analyses"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)

    # 6 Characteristic reports (stored as JSON text)
    confidentiality_report = Column(Text, nullable=True)
    data_integrity_report = Column(Text, nullable=True)
    authenticity_report = Column(Text, nullable=True)
    non_repudiation_report = Column(Text, nullable=True)
    accountability_report = Column(Text, nullable=True)
    resistance_report = Column(Text, nullable=True)

    # Overall results
    overall_score = Column(Float, nullable=True)  # 0-100
    summary_report = Column(Text, nullable=True)  # Executive summary JSON

    # Relationship
    repository = relationship("Repository", back_populates="integrity_analyses")
