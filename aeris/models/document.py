from datetime import datetime
from typing import Optional, TYPE_CHECKING, List

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from aeris.models.knowledge_base import KnowledgeBase
    from aeris.models.chunk import Chunk


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    knowledge_base_id: int = Field(foreign_key="knowledge_bases.id", index=True)
    title: str = Field(max_length=255)
    source_type: str = Field(max_length=20)  # "upload" or "url"
    source_path: str = Field(max_length=500)
    status: str = Field(default="processing", max_length=20)
    chunk_count: int = Field(default=0)
    error_message: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    knowledge_base: Optional["KnowledgeBase"] = Relationship(back_populates="documents")
    chunks: List["Chunk"] = Relationship(back_populates="document")