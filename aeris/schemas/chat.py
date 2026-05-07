from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel


class MessageCreate(BaseModel):
    content: str
    role: str = "user"


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: Optional[str]
    tool_calls: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    last_message_preview: Optional[str] = None  # 最后一条消息预览

    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    messages: List[MessageResponse]


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    message: MessageResponse
    usage: Dict[str, int]
    tool_calls: List[Dict[str, Any]] = []


class StreamingChunk(BaseModel):
    type: str  # "content", "tool_call", "done", "error"
    content: Optional[str] = None
    tool_call: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None
