import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from meditatio.utils.security import create_access_token


@pytest.fixture(scope="module")
def test_client():
    """Create TestClient with init_db patched to avoid real DB connections."""
    with patch("meditatio.main.init_db", new_callable=AsyncMock):
        from meditatio.main import app
        client = TestClient(app)
        yield client


@pytest.fixture
def auth_token():
    """Create a valid JWT token for WebSocket auth."""
    return create_access_token(data={"sub": "1", "username": "testuser"})


class MockSession:
    """Mock async session for WebSocket tests."""
    async def commit(self):
        pass

    async def refresh(self, obj):
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = 1

    def add(self, obj):
        pass


async def mock_session_context():
    yield MockSession()


def test_websocket_chat_streaming(test_client, auth_token):
    """Test WebSocket chat with streaming response."""

    async def mock_run_stream(messages, context):
        yield {"type": "content", "content": "Hello"}
        yield {"type": "content", "content": " world"}
        yield {"type": "done", "usage": {"input_tokens": 10, "output_tokens": 5}, "iterations": 1}

    mock_engine = MagicMock()
    mock_engine.run_stream = mock_run_stream

    mock_conversation = MagicMock()
    mock_conversation.id = 1

    with patch("meditatio.routers.ws.get_agent_engine", return_value=mock_engine), \
         patch("meditatio.routers.ws.get_session_context", mock_session_context), \
         patch("meditatio.routers.ws.ChatService") as MockChatService:

        mock_service = MagicMock()
        mock_service.get_conversation = AsyncMock(return_value=mock_conversation)
        mock_service.get_conversation_messages = AsyncMock(return_value=[])
        MockChatService.return_value = mock_service

        with test_client.websocket_connect(f"/ws/chat?token={auth_token}") as websocket:
            websocket.send_json({
                "type": "message",
                "conversation_id": 1,
                "content": "hi",
            })

            chunks = []
            for _ in range(3):
                chunks.append(websocket.receive_json())

            assert chunks[0] == {"type": "content", "content": "Hello"}
            assert chunks[1] == {"type": "content", "content": " world"}
            assert chunks[2]["type"] == "done"
            assert chunks[2]["usage"]["input_tokens"] == 10
            assert chunks[2]["usage"]["output_tokens"] == 5


def test_websocket_chat_tool_call(test_client, auth_token):
    """Test WebSocket chat with tool call in stream."""

    async def mock_run_stream(messages, context):
        yield {"type": "content", "content": "Let me search"}
        yield {"type": "tool_call", "name": "search", "arguments": '{"q": "test"}'}
        yield {"type": "done", "usage": {"input_tokens": 15, "output_tokens": 3}, "iterations": 1}

    mock_engine = MagicMock()
    mock_engine.run_stream = mock_run_stream

    mock_conversation = MagicMock()
    mock_conversation.id = 1

    with patch("meditatio.routers.ws.get_agent_engine", return_value=mock_engine), \
         patch("meditatio.routers.ws.get_session_context", mock_session_context), \
         patch("meditatio.routers.ws.ChatService") as MockChatService:

        mock_service = MagicMock()
        mock_service.get_conversation = AsyncMock(return_value=mock_conversation)
        mock_service.get_conversation_messages = AsyncMock(return_value=[])
        MockChatService.return_value = mock_service

        with test_client.websocket_connect(f"/ws/chat?token={auth_token}") as websocket:
            websocket.send_json({
                "type": "message",
                "conversation_id": 1,
                "content": "search test",
            })

            chunks = []
            for _ in range(3):
                chunks.append(websocket.receive_json())

            assert chunks[0] == {"type": "content", "content": "Let me search"}
            assert chunks[1] == {"type": "tool_call", "name": "search", "arguments": '{"q": "test"}'}
            assert chunks[2]["type"] == "done"


def test_websocket_invalid_token(test_client):
    """Test WebSocket connection with invalid token is rejected."""
    with pytest.raises(Exception):
        with test_client.websocket_connect("/ws/chat?token=invalid_token") as websocket:
            pass


def test_websocket_conversation_not_found(test_client, auth_token):
    """Test WebSocket returns error when conversation not found."""

    async def mock_run_stream(messages, context):
        yield {"type": "content", "content": "test"}
        yield {"type": "done", "usage": {}, "iterations": 1}

    mock_engine = MagicMock()
    mock_engine.run_stream = mock_run_stream

    with patch("meditatio.routers.ws.get_agent_engine", return_value=mock_engine), \
         patch("meditatio.routers.ws.get_session_context", mock_session_context), \
         patch("meditatio.routers.ws.ChatService") as MockChatService:

        mock_service = MagicMock()
        mock_service.get_conversation = AsyncMock(return_value=None)
        MockChatService.return_value = mock_service

        with test_client.websocket_connect(f"/ws/chat?token={auth_token}") as websocket:
            websocket.send_json({
                "type": "message",
                "conversation_id": 999,
                "content": "hi",
            })

            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Conversation not found" in response["error"]


def test_websocket_ping_pong(test_client, auth_token):
    """Test WebSocket ping/pong."""
    with test_client.websocket_connect(f"/ws/chat?token={auth_token}") as websocket:
        websocket.send_json({"type": "ping"})
        response = websocket.receive_json()
        assert response == {"type": "pong"}
