import json
import time
import uuid
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from aeris.database import get_session, get_session_context
from aeris.routers.auth import verify_token
from aeris.schemas.chat import StreamingChunk
from aeris.services.chat_service import ChatService
from aeris.services.file_service import FileService
from aeris.services.agent_engine import AgentContext, get_agent_engine
from aeris.utils.timing_collector import get_collector, init_collector

router = APIRouter(tags=["websocket"])

# Initialize timing collector on module load
def init_timing_collector():
    from aeris.config import get_settings
    settings = get_settings()
    init_collector({
        "ENABLE_TIMING_TRACE": settings.enable_timing_trace,
        "TIMING_FULL_MODE": settings.timing_full_mode,
        "TIMING_QUEUE_SIZE": settings.timing_queue_size,
        "TIMING_SLOW_THRESHOLD_MS": settings.timing_slow_threshold_ms,
    })

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


async def build_file_content_messages(
    session: AsyncSession,
    user_id: int,
    file_ids: list,
    max_image_size: int = 2 * 1024 * 1024,
) -> tuple:
    """读取文件内容，构建适合 LLM 的 message parts。

    Returns: (content_parts, warnings)
    """
    file_service = FileService(session)
    content_parts = []
    warnings = []

    for file_id in file_ids:
        file_record = await file_service.get_file(user_id, file_id)
        if not file_record:
            warnings.append(f"文件 ID {file_id} 不存在或无权访问")
            continue

        # 图片大小检查
        if file_record.mime_type.startswith("image/") and file_record.size_bytes > max_image_size:
            warnings.append(
                f"图片 {file_record.original_name} 过大 ({file_record.size_bytes} bytes)，"
                f"已超过 {max_image_size // 1024 // 1024}MB 限制，已跳过"
            )
            continue

        try:
            file_content = await file_service.read_file_content(file_record)
        except Exception as e:
            warnings.append(f"文件 {file_record.original_name} 读取失败: {str(e)}")
            continue

        if file_record.mime_type.startswith("image/"):
            # OpenAI vision format
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": file_content},
            })
        else:
            # Text content appended as text part
            text_preview = file_content[:8000]
            if len(file_content) > 8000:
                text_preview += "\n... (内容已截断)"
            content_parts.append({
                "type": "text",
                "text": f"[文件: {file_record.original_name}]\n```\n{text_preview}\n```",
            })

    return content_parts, warnings


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat with full timing trace.

    Client sends: {"type": "message", "conversation_id": 123, "content": "hello"}
    Server sends: {"type": "content", "content": "chunk..."}
                  {"type": "done", "usage": {...}}
                  {"type": "error", "error": "..."}
    """
    t_start = time.time()
    trace_id = str(uuid.uuid4())
    collector = get_collector()
    timing_trace = None

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
                file_ids = data.get("file_ids", [])

                if not conversation_id or not content:
                    await websocket.send_json({
                        "type": "error",
                        "error": "Missing conversation_id or content",
                    })
                    continue

                # Initialize timing trace if enabled
                should_collect = collector.should_collect(conversation_id, user["user_id"])
                if should_collect:
                    timing_trace = collector.trace_scope(
                        trace_id, conversation_id, user["user_id"]
                    )
                    timing_context = await timing_trace.__aenter__()
                    timing_context.add_event("ws_received", t_start)
                else:
                    timing_context = None

                try:
                    async with get_session_context() as session:
                        chat_service = ChatService(session)

                        # Verify conversation
                        if timing_context:
                            t_verify_start = time.time()
                        conversation = await chat_service.get_conversation(
                            user["user_id"], conversation_id
                        )
                        if timing_context:
                            timing_context.add_event("verify_conv", time.time(),
                                duration_ms=int((time.time() - t_verify_start) * 1000))

                        if not conversation:
                            await websocket.send_json({
                                "type": "error",
                                "error": "Conversation not found",
                            })
                            continue

                        # Save user message
                        if timing_context:
                            t_save_start = time.time()
                        from aeris.models.message import Message
                        from aeris.schemas.chat import MessageCreate

                        user_message = Message(
                            conversation_id=conversation_id,
                            role="user",
                            content=content,
                            file_ids=file_ids if file_ids else None,
                        )
                        session.add(user_message)
                        await session.commit()
                        await session.refresh(user_message)

                        if timing_context:
                            timing_context.add_event("msg_saved", time.time(),
                                duration_ms=int((time.time() - t_save_start) * 1000),
                                metadata={"message_id": user_message.id})

                        # Get conversation history
                        if timing_context:
                            t_history_start = time.time()
                        messages = await chat_service.get_conversation_messages(conversation_id)
                        if timing_context:
                            timing_context.add_event("history_loaded", time.time(),
                                duration_ms=int((time.time() - t_history_start) * 1000),
                                metadata={"history_count": len(messages)})

                        # Build LLM messages
                        if timing_context:
                            t_build_start = time.time()

                        # Build system prompt with available skills
                        from aeris.skills.registry import get_skill_registry
                        from textwrap import dedent
                        try:
                            skills_registry = get_skill_registry()
                            available_skills = skills_registry.describe_available()
                        except RuntimeError:
                            available_skills = "(no skills available)"

                        system_content = dedent(f"""\
                            You are a helpful AI assistant with access to specialized skills.

                            Available skills:
                            {available_skills}

                            Use the load_skill tool when a task needs specialized instructions before you act.
                        """).strip()
                        llm_messages = [{"role": "system", "content": system_content}]

                        # Build user message content (may include files)
                        user_content_parts = []

                        # Add file contents if any
                        if file_ids:
                            if timing_context:
                                t_files_start = time.time()
                            file_parts, file_warnings = await build_file_content_messages(
                                session, user["user_id"], file_ids
                            )
                            user_content_parts.extend(file_parts)
                            for warning in file_warnings:
                                await websocket.send_json({"type": "warning", "message": warning})
                            if timing_context:
                                timing_context.add_event("files_loaded", time.time(),
                                    duration_ms=int((time.time() - t_files_start) * 1000),
                                    metadata={"file_count": len(file_ids)})

                        # Add text content
                        user_content_parts.append({"type": "text", "text": content})
                        current_user_message = {"role": "user", "content": user_content_parts}

                        # Add conversation history (exclude current message, limit to recent 10)
                        history_limit = 10  # 只保留最近10轮对话
                        recent_messages = messages[:-1][-history_limit:] if len(messages) > 1 else []
                        for msg in recent_messages:
                            # Merge consecutive messages with same role to avoid invalid sequences
                            if llm_messages and llm_messages[-1]["role"] == msg.role:
                                prev_content = llm_messages[-1]["content"] or ""
                                curr_content = msg.content or ""
                                llm_messages[-1]["content"] = f"{prev_content}\n\n{curr_content}".strip()
                            else:
                                llm_messages.append({
                                    "role": msg.role,
                                    "content": msg.content or "",
                                })

                        # Append current user message at the end
                        # Merge with previous user message if exists to avoid consecutive user roles
                        if llm_messages and llm_messages[-1]["role"] == "user":
                            prev_content = llm_messages[-1]["content"]
                            curr_content = current_user_message["content"]
                            # Handle different content types (string vs list)
                            if isinstance(prev_content, str) and isinstance(curr_content, str):
                                llm_messages[-1]["content"] = f"{prev_content}\n\n{curr_content}".strip()
                            elif isinstance(prev_content, list) and isinstance(curr_content, list):
                                llm_messages[-1]["content"] = prev_content + curr_content
                            elif isinstance(prev_content, str) and isinstance(curr_content, list):
                                # Convert previous string to list format and append
                                llm_messages[-1]["content"] = [{"type": "text", "text": prev_content}] + curr_content
                            elif isinstance(prev_content, list) and isinstance(curr_content, str):
                                llm_messages[-1]["content"] = prev_content + [{"type": "text", "text": curr_content}]
                        else:
                            llm_messages.append(current_user_message)

                        if timing_context:
                            timing_context.add_event("llm_ready", time.time(),
                                duration_ms=int((time.time() - t_build_start) * 1000))

                        # Run agent with streaming
                        if timing_context:
                            t_agent_start = time.time()

                        context = AgentContext(
                            user_id=user["user_id"],
                            conversation_id=conversation_id,
                            message_id=user_message.id,
                            session=session,
                            timing_trace=timing_context,  # Pass trace to AgentEngine
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

                        if timing_context:
                            timing_context.add_event("agent_done", time.time(),
                                duration_ms=int((time.time() - t_agent_start) * 1000),
                                metadata={"output_length": len(full_content)})

                        # Filter thinking tags from doubao model
                        import re
                        if full_content:
                            full_content = re.sub(r'<think[^>]*>.*?</think>', '', full_content, flags=re.DOTALL)
                            full_content = full_content.strip()

                        # Save AI response
                        if timing_context:
                            t_ai_save_start = time.time()
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

                        if timing_context:
                            timing_context.add_event("ai_msg_saved", time.time(),
                                duration_ms=int((time.time() - t_ai_save_start) * 1000))
                            # End timing trace
                            await timing_trace.__aexit__(None, None, None)
                            timing_trace = None

                        # Send final error if max iterations reached
                        if error:
                            await websocket.send_json({
                                "type": "error",
                                "error": error,
                            })

                except Exception as e:
                    if timing_trace:
                        await timing_trace.__aexit__(type(e), e, None)
                        timing_trace = None
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
