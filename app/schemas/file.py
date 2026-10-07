from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.file import FileProcessingStatus


class FileUploadResponse(BaseModel):
    id: str
    filename: str
    feature_count: int
    crs: Optional[str] = None
    status: FileProcessingStatus

    model_config = ConfigDict(from_attributes=True)


class FileDetailResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    feature_count: int
    crs: Optional[str] = None
    status: FileProcessingStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
