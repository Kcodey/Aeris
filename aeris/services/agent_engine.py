import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aeris.services.provider_manager import (
    get_provider_manager,
    CompletionResponse,
    ToolCall,
)
from aeris.services.tokenizer import get_tokenizer
from aeris.tools.base import ToolResult, get_tool_registry


@dataclass
class AgentContext:
    """Context for agent execution."""
    user_id: int
    conversation_id: int
    message_id: Optional[int] = None
    provider_name: str = "default"
    max_iterations: int = 10

    # Tracking
    iteration_count: int = field(default=0)
    total_input_tokens: int = field(default=0)
    total_output_tokens: int = field(default=0)

    def get_thinking_config(self) -> Optional[Dict[str, Any]]:
        """Get thinking config for provider."""
        provider_manager = get_provider_manager()
        provider = provider_manager.get_provider(self.provider_name)
        if provider.thinking_enabled:
            return {"type": "enabled", "budget_tokens": provider.thinking_budget}
        return None

    def record_usage(self, input_tokens: int, output_tokens: int):
        """Record token usage."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens


@dataclass
class AgentResult:
    """Result of agent execution."""
    content: Optional[str]
    tool_calls_executed: List[Dict[str, Any]]
    usage: Dict[str, int]
    iterations: int
    latency_ms: int
    error: Optional[str] = None


class AgentEngine:
    """Core agent loop implementation."""

    def __init__(self):
        self.provider_manager = get_provider_manager()
        self.tool_registry = get_tool_registry()
        self.tokenizer = get_tokenizer()

    async def run(
        self,
        messages: List[Dict[str, Any]],
        context: AgentContext,
    ) -> AgentResult:
        """
        Run the agent loop.

        1. Call LLM with messages and tools
        2. If no tool_calls, return content
        3. If tool_calls, execute tools and append results
        4. Loop until no tool_calls or max_iterations reached
        """
        import time
        start_time = time.time()

        tool_schemas = self.tool_registry.get_schemas()
        provider = self.provider_manager.get_provider(context.provider_name)

        working_messages = messages.copy()
        tool_calls_executed = []

        while context.iteration_count < context.max_iterations:
            # Call LLM
            response = await provider.chat_completion(
                messages=working_messages,
                tools=tool_schemas,
                stream=False,  # MVP: non-streaming for agent loop
            )

            # Record usage
            context.record_usage(response.input_tokens, response.output_tokens)

            # Check for tool calls
            if not response.tool_calls:
                # No tool calls, return final response
                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)

                return AgentResult(
                    content=response.content,
                    tool_calls_executed=tool_calls_executed,
                    usage={
                        "input_tokens": context.total_input_tokens,
                        "output_tokens": context.total_output_tokens,
                    },
                    iterations=context.iteration_count + 1,
                    latency_ms=latency_ms,
                )

            # Execute tool calls
            assistant_message = {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        },
                    }
                    for tc in response.tool_calls
                ],
            }
            working_messages.append(assistant_message)

            for tool_call in response.tool_calls:
                result = await self._execute_tool(tool_call, context)
                tool_calls_executed.append({
                    "tool": tool_call.name,
                    "arguments": tool_call.arguments,
                    "result": result,
                })

                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result.data) if result.success else result.error,
                }
                working_messages.append(tool_message)

            context.iteration_count += 1

        # Max iterations reached
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        return AgentResult(
            content=None,
            tool_calls_executed=tool_calls_executed,
            usage={
                "input_tokens": context.total_input_tokens,
                "output_tokens": context.total_output_tokens,
            },
            iterations=context.max_iterations,
            latency_ms=latency_ms,
            error="Max iterations reached",
        )

    async def _execute_tool(
        self,
        tool_call: ToolCall,
        context: AgentContext,
    ) -> ToolResult:
        """Execute a single tool call."""
        try:
            arguments = json.loads(tool_call.arguments)
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid JSON arguments: {e}",
            )

        # Add context to arguments if needed
        arguments["_context"] = {
            "user_id": context.user_id,
            "conversation_id": context.conversation_id,
        }

        return await self.tool_registry.execute(tool_call.name, arguments)

    async def run_stream(
        self,
        messages: List[Dict[str, Any]],
        context: AgentContext,
    ):
        """
        Run agent with streaming output.

        Yields chunks of content as they arrive.
        """
        # TODO: Implement streaming version for WebSocket
        # For now, use non-streaming and yield at once
        result = await self.run(messages, context)
        yield {
            "type": "content",
            "content": result.content,
        }
        yield {
            "type": "done",
            "usage": result.usage,
            "iterations": result.iterations,
        }


# Global engine instance
_engine: Optional[AgentEngine] = None


def get_agent_engine() -> AgentEngine:
    """Get or create agent engine singleton."""
    global _engine
    if _engine is None:
        _engine = AgentEngine()
    return _engine