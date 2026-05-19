import pytest
from unittest.mock import MagicMock, patch

from meditatio.services.agent_engine import AgentEngine, AgentContext
from meditatio.services.provider_manager import StreamChunk, ToolCall


@pytest.fixture
def mock_provider():
    """Create a mock provider."""
    provider = MagicMock()
    provider.model = "test-model"
    provider.thinking_enabled = False
    provider.thinking_budget = None
    return provider


@pytest.fixture
def mock_tool_registry():
    """Create a mock tool registry."""
    registry = MagicMock()
    registry.get_schemas.return_value = []
    return registry


@pytest.mark.asyncio
async def test_run_stream_pure_text(mock_provider, mock_tool_registry):
    """Test streaming with pure text response (no tool calls)."""
    async def mock_stream(*args, **kwargs):
        yield StreamChunk(type="content", content="Hello")
        yield StreamChunk(type="content", content=" world")
        yield StreamChunk(type="usage", usage={
            "input_tokens": 10,
            "output_tokens": 5,
            "usage_from_api": True,
            "latency_ms": 100,
            "first_token_ms": 50,
        })

    mock_provider.chat_completion_stream = mock_stream

    with patch("meditatio.services.agent_engine.get_provider_manager", return_value=MagicMock(get_provider=lambda name: mock_provider)), \
         patch("meditatio.services.agent_engine.get_tool_registry", return_value=mock_tool_registry), \
         patch("meditatio.services.agent_engine.get_tokenizer", return_value=MagicMock()):

        engine = AgentEngine()
        context = AgentContext(user_id=1, conversation_id=1, message_id=1)

        chunks = []
        async for chunk in engine.run_stream([{"role": "user", "content": "hi"}], context):
            chunks.append(chunk)

        assert len(chunks) == 3  # 2 content + 1 done
        assert chunks[0] == {"type": "content", "content": "Hello"}
        assert chunks[1] == {"type": "content", "content": " world"}
        assert chunks[2]["type"] == "done"
        assert chunks[2]["usage"]["input_tokens"] == 10
        assert chunks[2]["usage"]["output_tokens"] == 5
        assert chunks[2]["iterations"] == 1


@pytest.mark.asyncio
async def test_run_stream_with_tool_call(mock_provider, mock_tool_registry):
    """Test streaming with tool call interruption and resume."""
    call_count = 0

    async def mock_stream(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            # First call: returns a tool call
            yield StreamChunk(type="content", content="Let me search")
            yield StreamChunk(
                type="tool_call",
                tool_call=ToolCall(id="call_1", name="search", arguments='{"q": "test"}')
            )
            yield StreamChunk(type="usage", usage={
                "input_tokens": 10,
                "output_tokens": 5,
                "usage_from_api": True,
                "latency_ms": 100,
                "first_token_ms": 50,
            })
        else:
            # Second call: returns final text after tool execution
            yield StreamChunk(type="content", content="Found it")
            yield StreamChunk(type="usage", usage={
                "input_tokens": 20,
                "output_tokens": 2,
                "usage_from_api": True,
                "latency_ms": 50,
                "first_token_ms": 20,
            })

    mock_provider.chat_completion_stream = mock_stream

    async def mock_execute_tool(tool_call, context):
        return MagicMock(success=True, data={"result": "found"})

    with patch("meditatio.services.agent_engine.get_provider_manager", return_value=MagicMock(get_provider=lambda name: mock_provider)), \
         patch("meditatio.services.agent_engine.get_tool_registry", return_value=mock_tool_registry), \
         patch("meditatio.services.agent_engine.get_tokenizer", return_value=MagicMock()):

        engine = AgentEngine()
        # Patch _execute_tool to avoid actual tool execution
        engine._execute_tool = mock_execute_tool

        context = AgentContext(user_id=1, conversation_id=1, message_id=1)

        chunks = []
        async for chunk in engine.run_stream([{"role": "user", "content": "search test"}], context):
            chunks.append(chunk)

        content_chunks = [c for c in chunks if c["type"] == "content"]
        tool_call_chunks = [c for c in chunks if c["type"] == "tool_call"]
        done_chunks = [c for c in chunks if c["type"] == "done"]

        assert len(content_chunks) == 2  # "Let me search" + "Found it"
        assert content_chunks[0]["content"] == "Let me search"
        assert content_chunks[1]["content"] == "Found it"
        assert len(tool_call_chunks) == 1
        assert tool_call_chunks[0]["name"] == "search"
        assert len(done_chunks) == 1
        assert done_chunks[0]["iterations"] == 2  # Two LLM calls


@pytest.mark.asyncio
async def test_run_stream_max_iterations(mock_provider, mock_tool_registry):
    """Test that max iterations limit is enforced."""
    async def mock_stream(*args, **kwargs):
        yield StreamChunk(
            type="tool_call",
            tool_call=ToolCall(id="call_1", name="loop_tool", arguments='{}')
        )
        yield StreamChunk(type="usage", usage={
            "input_tokens": 10,
            "output_tokens": 5,
            "usage_from_api": True,
            "latency_ms": 100,
            "first_token_ms": 50,
        })

    mock_provider.chat_completion_stream = mock_stream

    async def mock_execute_tool(tool_call, context):
        return MagicMock(success=True, data={})

    with patch("meditatio.services.agent_engine.get_provider_manager", return_value=MagicMock(get_provider=lambda name: mock_provider)), \
         patch("meditatio.services.agent_engine.get_tool_registry", return_value=mock_tool_registry), \
         patch("meditatio.services.agent_engine.get_tokenizer", return_value=MagicMock()):

        engine = AgentEngine()
        engine._execute_tool = mock_execute_tool
        context = AgentContext(user_id=1, conversation_id=1, message_id=1, max_iterations=2)

        chunks = []
        async for chunk in engine.run_stream([{"role": "user", "content": "hi"}], context):
            chunks.append(chunk)

        done_chunk = [c for c in chunks if c["type"] == "done"][0]
        assert done_chunk["iterations"] == 2
        assert done_chunk["error"] == "Max iterations reached"
