from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    id: int
    original_name: str
    mime_type: str
    size_bytes: int
    size_display: str
    created_at: datetime


class FileListResponse(BaseModel):
    id: int
    original_name: str
    mime_type: str
    size_bytes: int
    size_display: str
    is_image: bool
    created_at: datetime
