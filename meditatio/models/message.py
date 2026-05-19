from datetime import datetime
from typing import Optional, TYPE_CHECKING, List

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from meditatio.models.conversation import Conversation


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    role: str = Field(max_length=20)  # system, user, assistant, tool
    content: Optional[str] = Field(default=None)

    # Attached files (file IDs)
    file_ids: Optional[List[int]] = Field(default=None, sa_column=Column(JSON))

    # Tool calls
    tool_calls: Optional[List[dict]] = Field(default=None, sa_column=Column(JSON))
    tool_call_id: Optional[str] = Field(default=None, max_length=100)

    # Token usage for monitoring
    input_tokens: Optional[int] = Field(default=None)
    output_tokens: Optional[int] = Field(default=None)
    tokens_estimated: bool = Field(default=False)

    # Trace for debugging
    trace_id: Optional[str] = Field(default=None, index=True, max_length=100)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    conversation: Optional["Conversation"] = Relationship(back_populates="messages")
