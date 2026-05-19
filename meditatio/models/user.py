from datetime import datetime
from typing import Optional, TYPE_CHECKING, List

from sqlmodel import SQLModel, Field, Relationship

from aeris.models.base import TimestampMixin

if TYPE_CHECKING:
    from aeris.models.conversation import Conversation
    from aeris.models.scheduled_task import ScheduledTask
    from aeris.models.file_record import FileRecord


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)

    # Quota for future multi-tenant expansion
    quota_tokens_daily: Optional[int] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    conversations: List["Conversation"] = Relationship(back_populates="user")
    tasks: List["ScheduledTask"] = Relationship(back_populates="user")
    files: List["FileRecord"] = Relationship(back_populates="user")
