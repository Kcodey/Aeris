import pytest
from unittest.mock import Mock, AsyncMock, patch

from meditatio.services.agent_engine import AgentEngine, AgentContext, AgentResult


@pytest.mark.asyncio
async def test_agent_context():
    """Test AgentContext."""
    context = AgentContext(
        user_id=1,
        conversation_id=1,
        message_id=1,
        max_iterations=5,
    )

    assert context.user_id == 1
    assert context.max_iterations == 5
    assert context.iteration_count == 0

    context.record_usage(100, 50)
    assert context.total_input_tokens == 100
    assert context.total_output_tokens == 50
