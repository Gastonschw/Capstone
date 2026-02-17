"""
ERD Analysis model.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from database import Base


class AnalysisStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ERDAnalysis(Base):
    """Stores ERD analysis results.

    Analyzes ERD diagrams against user stories to find coverage issues.
    """
    __tablename__ = "erd_analyses"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String(50), default=AnalysisStatus.pending.value)
    error_message = Column(Text, nullable=True)

    # Analysis results (stored as JSON text)
    uml_structure = Column(Text, nullable=True)  # Extracted UML from ERD images
    report = Column(Text, nullable=True)  # Analysis report comparing UML to user stories

    # Coverage score
    coverage_score = Column(Float, nullable=True)  # 0-100

    # Relationship
    repository = relationship("Repository", back_populates="erd_analyses")
