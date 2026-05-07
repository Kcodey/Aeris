from datetime import datetime
from typing import Optional, TYPE_CHECKING, List

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from aeris.models.user import User
    from aeris.models.message import Message


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: Optional[str] = Field(default=None, max_length=200)
    status: str = Field(default="active")  # active, archived, deleted

    # Model config snapshot for this conversation
    model_config_snapshot: Optional[dict] = Field(
        default=None, sa_column=Column(JSON)
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="conversations")
    messages: List["Message"] = Relationship(back_populates="conversation")

    # 非数据库字段：最后一条消息预览
    class Config:
        # 这些字段不会被映射到数据库
        arbitrary_types_allowed = True
