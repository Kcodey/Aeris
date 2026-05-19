from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from meditatio.database import get_session
from meditatio.routers.auth import get_current_user, TokenData
from meditatio.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationWithMessages,
    MessageResponse,
)
from meditatio.services.chat_service import ChatService

router = APIRouter(prefix="/conversations", tags=["chat"])


async def get_chat_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChatService:
    """Dependency to get chat service."""
    return ChatService(session)


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: Annotated[TokenData, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    skip: int = 0,
    limit: int = 20,
):
    """List user's conversations."""
    conversations = await chat_service.list_conversations(
        current_user.user_id, skip=skip, limit=limit
    )
    return conversations


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: Annotated[TokenData, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
):
    """Create a new conversation."""
    conversation = await chat_service.create_conversation(current_user.user_id, data)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: int,
    current_user: Annotated[TokenData, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
):
    """Get conversation with messages."""
    conversation = await chat_service.get_conversation(
        current_user.user_id, conversation_id
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await chat_service.get_conversation_messages(conversation_id)

    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "title": conversation.title,
        "status": conversation.status,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "messages": messages,
    }


@router.post("/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(
    conversation_id: int,
    request: ChatRequest,
    current_user: Annotated[TokenData, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
):
    """Send a message and get AI response."""
    # Verify conversation belongs to user
    conversation = await chat_service.get_conversation(
        current_user.user_id, conversation_id
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await chat_service.send_message(
        current_user.user_id,
        conversation_id,
        request.message,
    )

    return ChatResponse(
        message=MessageResponse.model_validate(result["ai_message"]),
        usage=result["usage"],
        tool_calls=result["tool_calls"],
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    current_user: Annotated[TokenData, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
):
    """Delete a conversation."""
    success = await chat_service.delete_conversation(
        current_user.user_id, conversation_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return None


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    current_user: Annotated[TokenData, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
):
    """Update conversation (title only for now)."""
    conversation = await chat_service.update_conversation(
        current_user.user_id, conversation_id, data
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation