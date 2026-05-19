"""Pydantic schemas for API."""

from meditatio.schemas.chat import (
    MessageCreate,
    MessageResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationWithMessages,
    ChatRequest,
    ChatResponse,
    StreamingChunk,
)
from meditatio.schemas.rag import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    DocumentUploadResponse,
    URLFetchRequest,
    URLFetchResponse,
    DocumentStatusResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

__all__ = [
    "MessageCreate",
    "MessageResponse",
    "ConversationCreate",
    "ConversationResponse",
    "ConversationWithMessages",
    "ChatRequest",
    "ChatResponse",
    "StreamingChunk",
    "KnowledgeBaseCreate",
    "KnowledgeBaseResponse",
    "DocumentUploadResponse",
    "URLFetchRequest",
    "URLFetchResponse",
    "DocumentStatusResponse",
    "SearchRequest",
    "SearchResponse",
    "SearchResultItem",
]
