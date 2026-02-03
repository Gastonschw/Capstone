from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any


class AnalysisCreate(BaseModel):
    user_stories: str


class AnalysisResponse(BaseModel):
    id: int
    created_at: datetime
    image_filename: str
    user_stories: str
    extracted_erd: Optional[Any] = None
    report: Optional[Any] = None
    status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class AnalysisListItem(BaseModel):
    id: int
    created_at: datetime
    status: str

    class Config:
        from_attributes = True
