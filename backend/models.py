from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
from sqlalchemy.sql import func
import enum

from database import Base


class AnalysisStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    image_filename = Column(String, nullable=False)
    user_stories = Column(Text, nullable=False)
    extracted_erd = Column(Text, nullable=True)  # JSON stored as text
    report = Column(Text, nullable=True)  # JSON stored as text
    status = Column(String, default=AnalysisStatus.pending.value)
    error_message = Column(Text, nullable=True)
