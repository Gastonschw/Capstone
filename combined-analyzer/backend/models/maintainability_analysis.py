"""
Maintainability Analysis model (ISO 25010 Maintainability).
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class MaintainabilityAnalysis(Base):
    """Stores Maintainability analysis results.

    Analyzes codebase for 5 maintainability characteristics:
    - Modularity
    - Reusability
    - Analysability
    - Modifiability
    - Testability
    """
    __tablename__ = "maintainability_analyses"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)

    # 5 Characteristic reports (stored as JSON text)
    modularity_report = Column(Text, nullable=True)
    reusability_report = Column(Text, nullable=True)
    analysability_report = Column(Text, nullable=True)
    modifiability_report = Column(Text, nullable=True)
    testability_report = Column(Text, nullable=True)

    # Overall results
    overall_score = Column(Float, nullable=True)  # 0-100
    summary_report = Column(Text, nullable=True)  # Executive summary JSON

    # Relationship
    repository = relationship("Repository", back_populates="maintainability_analyses")
