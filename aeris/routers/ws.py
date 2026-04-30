import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from aeris.database import get_session, get_session_context
from aeris.routers.auth import verify_token
from aeris.schemas.chat import StreamingChunk
from aeris.services.chat_service import ChatService
from aeris.services.agent_engine import AgentContext, get_agent_engine

router = APIRouter(tags=["websocket"])

# Store active connections: user_id -> Set[WebSocket]
active_connections: Dict[int, Set[WebSocket]] = {}


class ConnectionManager:
    """Manage WebSocket connections."""

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        if user_id not in active_connections:
            active_connections[user_id] = set()
        active_connections[user_id].add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in active_connections:
            active_connections[user_id].discard(websocket)
            if not active_connections[user_id]:
                del active_connections[user_id]

    async def send_message(self, user_id: int, message: dict):
        """Send message to all connections of a user."""
        if user_id in active_connections:
            disconnected = []
            for connection in active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)

            # Clean up disconnected
            for conn in disconnected:
                self.disconnect(user_id, conn)


manager = ConnectionManager()


async def get_current_user_ws(websocket: WebSocket) -> dict:
    """Authenticate WebSocket connection via token in query param."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=401, detail="Token required")

    payload = verify_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=401, detail="Invalid token")

    return {
        "user_id": int(payload["sub"]),
        "username": payload["username"],
    }


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.

    Client sends: {"type": "message", "conversation_id": 123, "content": "hello"}
    Server sends: {"type": "content", "content": "chunk..."}
                  {"type": "done", "usage": {...}}
                  {"type": "error", "error": "..."}
    """
    try:
        user = await get_current_user_ws(websocket)
    except HTTPException:
        return

    await manager.connect(user["user_id"], websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                conversation_id = data.get("conversation_id")
                content = data.get("content")

                if not conversation_id or not content:
                    await websocket.send_json({
                        "type": "error",
                        "error": "Missing conversation_id or content",
                    })
                    continue

                # Process message
                try:
                    async with get_session_context() as session:
                        chat_service = ChatService(session)

                        # Verify conversation
                        conversation = await chat_service.get_conversation(
                            user["user_id"], conversation_id
                        )
                        if not conversation:
                            await websocket.send_json({
                                "type": "error",
                                "error": "Conversation not found",
                            })
                            continue

                        # Save user message
                        from aeris.models.message import Message
                        from aeris.schemas.chat import MessageCreate

                        user_message = Message(
                            conversation_id=conversation_id,
                            role="user",
                            content=content,
                        )
                        session.add(user_message)
                        await session.commit()
                        await session.refresh(user_message)

                        # Get conversation history
                        messages = await chat_service.get_conversation_messages(conversation_id)

                        # Build LLM messages
                        llm_messages = [
                            {"role": "system", "content": "You are a helpful AI assistant."}
                        ]
                        for msg in messages:
                            llm_messages.append({
                                "role": msg.role,
                                "content": msg.content or "",
                            })

                        # Run agent with streaming
                        context = AgentContext(
                            user_id=user["user_id"],
                            conversation_id=conversation_id,
                            message_id=user_message.id,
                        )

                        agent_engine = get_agent_engine()
                        full_content = ""
                        usage = None
                        error = None

                        async for chunk in agent_engine.run_stream(llm_messages, context):
                            await websocket.send_json(chunk)
                            if chunk["type"] == "content":
                                full_content += chunk.get("content", "")
                            elif chunk["type"] == "done":
                                usage = chunk.get("usage")
                                error = chunk.get("error")

                        # Save AI response
                        ai_message = Message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=full_content if full_content else None,
                            input_tokens=usage.get("input_tokens") if usage else None,
                            output_tokens=usage.get("output_tokens") if usage else None,
                            tokens_estimated=False,
                        )
                        session.add(ai_message)
                        await session.commit()

                        # Send final error if max iterations reached
                        if error:
                            await websocket.send_json({
                                "type": "error",
                                "error": error,
                            })

                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "error": str(e),
                    })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(user["user_id"], websocket)
    except Exception:
        manager.disconnect(user["user_id"], websocket)
