from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


class LLMTrace(SQLModel, table=True):
    __tablename__ = "llm_traces"

    trace_id: str = Field(primary_key=True, max_length=100)
    user_id: int = Field(foreign_key="users.id", index=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    message_id: Optional[int] = Field(foreign_key="messages.id", default=None)

    # Provider and model info
    provider: str = Field(max_length=50)
    model: str = Field(max_length=100)

    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Request/Response payloads
    request_payload: dict = Field(sa_column=Column(JSON))
    response_payload: dict = Field(sa_column=Column(JSON))

    # Performance metrics
    latency_ms: int
    first_token_ms: Optional[int] = Field(default=None)
    tokens_per_second: Optional[float] = Field(default=None)

    # Token usage
    input_tokens: int
    output_tokens: int
    tokens_estimated: bool = Field(default=False)

    # Tool calls
    tool_calls: Optional[List[dict]] = Field(default=None, sa_column=Column(JSON))
    tool_results: Optional[List[dict]] = Field(default=None, sa_column=Column(JSON))
    iteration_count: int = Field(default=1)

    # Errors
    error_type: Optional[str] = Field(default=None, max_length=50)
    error_message: Optional[str] = Field(default=None)
