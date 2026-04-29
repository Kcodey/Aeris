import pytest
from unittest.mock import Mock, AsyncMock

from aeris.services.provider_manager import SGLangProvider, CompletionResponse


@pytest.mark.asyncio
async def test_sglang_provider_init():
    """Test SGLang provider initialization."""
    config = {
        "base_url": "http://localhost:30000/v1",
        "model": "test-model",
        "thinking": {"enabled": True, "budget_tokens": 1000},
    }
    provider = SGLangProvider(config)

    assert provider.model == "test-model"
    assert provider.thinking_enabled is True
    assert provider.thinking_budget == 1000
