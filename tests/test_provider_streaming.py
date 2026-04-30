import pytest
from unittest.mock import AsyncMock, MagicMock

from aeris.services.provider_manager import SGLangProvider, StreamChunk


@pytest.fixture
def provider_config():
    return {
        "base_url": "http://localhost:30000/v1",
        "model": "test-model",
        "thinking": {"enabled": False},
    }


@pytest.mark.asyncio
async def test_sglang_provider_stream_content(provider_config):
    """Test streaming content chunks."""
    provider = SGLangProvider(provider_config)

    # Mock the OpenAI client response chunks
    mock_chunk1 = MagicMock()
    mock_chunk1.choices = [MagicMock()]
    mock_chunk1.choices[0].delta = MagicMock(content="Hello", tool_calls=None)
    mock_chunk1.usage = None

    mock_chunk2 = MagicMock()
    mock_chunk2.choices = [MagicMock()]
    mock_chunk2.choices[0].delta = MagicMock(content=" world", tool_calls=None)
    mock_chunk2.usage = None

    mock_chunk3 = MagicMock()
    mock_chunk3.choices = [MagicMock()]
    mock_chunk3.choices[0].delta = MagicMock(content=None, tool_calls=None)
    mock_chunk3.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

    mock_response = AsyncMock()
    mock_response.__aiter__.return_value = [mock_chunk1, mock_chunk2, mock_chunk3]

    provider.client = MagicMock()
    provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

    chunks = []
    async for chunk in provider.chat_completion_stream([{"role": "user", "content": "hi"}]):
        chunks.append(chunk)

    content_chunks = [c for c in chunks if c.type == "content"]
    usage_chunks = [c for c in chunks if c.type == "usage"]

    assert len(content_chunks) == 2
    assert content_chunks[0].content == "Hello"
    assert content_chunks[1].content == " world"
    assert len(usage_chunks) == 1
    assert usage_chunks[0].usage["input_tokens"] == 10
    assert usage_chunks[0].usage["output_tokens"] == 5
    assert usage_chunks[0].usage["usage_from_api"] is True


@pytest.mark.asyncio
async def test_sglang_provider_stream_with_tool_calls(provider_config):
    """Test streaming with tool calls."""
    provider = SGLangProvider(provider_config)

    mock_chunk1 = MagicMock()
    mock_chunk1.choices = [MagicMock()]
    mock_chunk1.choices[0].delta = MagicMock(content="Let me", tool_calls=None)
    mock_chunk1.usage = None

    mock_func = MagicMock()
    mock_func.name = "search"
    mock_func.arguments = '{"q": "test"}'

    mock_chunk2 = MagicMock()
    mock_chunk2.choices = [MagicMock()]
    mock_chunk2.choices[0].delta = MagicMock(
        content=" help",
        tool_calls=[
            MagicMock(
                index=0,
                id="call_1",
                function=mock_func
            )
        ]
    )
    mock_chunk2.usage = None

    mock_response = AsyncMock()
    mock_response.__aiter__.return_value = [mock_chunk1, mock_chunk2]

    provider.client = MagicMock()
    provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

    chunks = []
    async for chunk in provider.chat_completion_stream([{"role": "user", "content": "search"}]):
        chunks.append(chunk)

    content_chunks = [c for c in chunks if c.type == "content"]
    tool_call_chunks = [c for c in chunks if c.type == "tool_call"]

    assert len(content_chunks) == 2
    assert len(tool_call_chunks) == 1
    assert tool_call_chunks[0].tool_call.name == "search"
    assert tool_call_chunks[0].tool_call.arguments == '{"q": "test"}'


@pytest.mark.asyncio
async def test_sglang_provider_stream_token_fallback(provider_config):
    """Test token estimation when usage is not provided."""
    provider = SGLangProvider(provider_config)

    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta = MagicMock(content="Hello", tool_calls=None)
    mock_chunk.usage = None

    mock_response = AsyncMock()
    mock_response.__aiter__.return_value = [mock_chunk]

    provider.client = MagicMock()
    provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Mock count_tokens to return fixed value
    provider.count_tokens = AsyncMock(return_value=42)

    chunks = []
    async for chunk in provider.chat_completion_stream([{"role": "user", "content": "hi"}]):
        chunks.append(chunk)

    usage_chunks = [c for c in chunks if c.type == "usage"]
    assert len(usage_chunks) == 1
    assert usage_chunks[0].usage["usage_from_api"] is False
    assert usage_chunks[0].usage["input_tokens"] == 42
    assert usage_chunks[0].usage["output_tokens"] == 42
