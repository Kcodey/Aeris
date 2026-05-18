from datetime import datetime
from typing import Optional, TYPE_CHECKING, List

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from aeris.models.document import Document


class KnowledgeBase(SQLModel, table=True):
    __tablename__ = "knowledge_bases"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=100)
    description: str = Field(default="", max_length=500)
    collection_name: str = Field(index=True, max_length=100)
    is_active: bool = Field(default=True)
    created_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    documents: List["Document"] = Relationship(back_populates="knowledge_base")