from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from meditatio.models.user import User


class FileRecord(SQLModel, table=True):
    __tablename__ = "file_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    conversation_id: Optional[int] = Field(
        foreign_key="conversations.id", default=None, index=True
    )

    # File metadata
    original_name: str = Field(max_length=255)
    stored_name: str = Field(max_length=255)
    mime_type: str = Field(max_length=100)
    size_bytes: int
    storage_path: str = Field(max_length=500)

    # Processing status
    status: str = Field(default="ready")  # uploading, processing, ready, error
    extracted_text: Optional[str] = Field(default=None)

    # Access control
    is_public: bool = Field(default=False)
    expires_at: Optional[datetime] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="files")
