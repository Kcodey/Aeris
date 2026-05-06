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
    session: Optional[Any] = None

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

    async def _save_trace(
        self,
        context: AgentContext,
        provider: Any,
        request_payload: Dict[str, Any],
        response_payload: Dict[str, Any],
        latency_ms: int,
        first_token_ms: Optional[int],
        input_tokens: int,
        output_tokens: int,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
    ):
        """Save LLM trace to database if session is available."""
        if not context.session:
            return

        try:
            from aeris.models.trace import LLMTrace

            trace = LLMTrace(
                trace_id=str(uuid.uuid4()),
                user_id=context.user_id,
                conversation_id=context.conversation_id,
                message_id=context.message_id,
                provider=provider.config.get("type", "unknown"),
                model=provider.model,
                request_payload=request_payload,
                response_payload=response_payload,
                latency_ms=latency_ms,
                first_token_ms=first_token_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error_type=error_type,
                error_message=error_message,
                tool_calls=tool_calls,
                tool_results=tool_results,
                iteration_count=context.iteration_count + 1,
            )
            context.session.add(trace)
            await context.session.commit()
        except Exception:
            # Silently ignore trace save errors to not break the main flow
            pass

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

            # Build request/response payload for trace
            request_payload = {
                "model": provider.model,
                "messages": working_messages,
                "tools": tool_schemas,
            }
            response_payload = {
                "content": response.content,
                "tool_calls": [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in (response.tool_calls or [])
                ],
                "usage": {
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                },
            }

            # Save trace
            await self._save_trace(
                context=context,
                provider=provider,
                request_payload=request_payload,
                response_payload=response_payload,
                latency_ms=response.latency_ms,
                first_token_ms=response.first_token_ms,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                tool_calls=response_payload["tool_calls"] or None,
            )

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

            iteration_tool_results = []
            for tool_call in response.tool_calls:
                result = await self._execute_tool(tool_call, context)
                tool_calls_executed.append({
                    "tool": tool_call.name,
                    "arguments": tool_call.arguments,
                    "result": result,
                })
                iteration_tool_results.append({
                    "tool": tool_call.name,
                    "arguments": tool_call.arguments,
                    "result": {"success": result.success, "data": result.data, "error": result.error},
                })

                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result.data) if result.success else result.error,
                }
                working_messages.append(tool_message)

            # Update trace with tool results
            if context.session:
                try:
                    from aeris.models.trace import LLMTrace
                    from sqlmodel import select
                    stmt = (
                        select(LLMTrace)
                        .where(LLMTrace.user_id == context.user_id)
                        .where(LLMTrace.conversation_id == context.conversation_id)
                        .where(LLMTrace.message_id == context.message_id)
                        .order_by(LLMTrace.timestamp.desc())
                        .limit(1)
                    )
                    result = await context.session.execute(stmt)
                    latest_trace = result.scalar_one_or_none()
                    if latest_trace:
                        latest_trace.tool_results = iteration_tool_results
                        await context.session.commit()
                except Exception:
                    pass

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
        Supports tool calls: streaming pauses for tool execution, then resumes.
        """
        import time
        start_time = time.time()

        tool_schemas = self.tool_registry.get_schemas()
        provider = self.provider_manager.get_provider(context.provider_name)

        working_messages = messages.copy()
        tool_calls_executed = []

        while context.iteration_count < context.max_iterations:
            full_content = ""
            iteration_tool_calls = []

            stream_latency_ms = 0
            stream_first_token_ms = None
            stream_input_tokens = 0
            stream_output_tokens = 0

            async for chunk in provider.chat_completion_stream(
                messages=working_messages,
                tools=tool_schemas,
            ):
                if chunk.type == "content":
                    full_content += chunk.content
                    yield {
                        "type": "content",
                        "content": chunk.content,
                    }
                elif chunk.type == "tool_call":
                    iteration_tool_calls.append(chunk.tool_call)
                    yield {
                        "type": "tool_call",
                        "name": chunk.tool_call.name,
                        "arguments": chunk.tool_call.arguments,
                    }
                elif chunk.type == "usage":
                    context.record_usage(
                        chunk.usage["input_tokens"],
                        chunk.usage["output_tokens"],
                    )
                    stream_latency_ms = chunk.usage.get("latency_ms", 0)
                    stream_first_token_ms = chunk.usage.get("first_token_ms")
                    stream_input_tokens = chunk.usage["input_tokens"]
                    stream_output_tokens = chunk.usage["output_tokens"]

            # Save trace after stream completes
            request_payload = {
                "model": provider.model,
                "messages": working_messages,
                "tools": tool_schemas,
            }
            response_payload = {
                "content": full_content,
                "tool_calls": [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in iteration_tool_calls
                ],
                "usage": {
                    "input_tokens": stream_input_tokens,
                    "output_tokens": stream_output_tokens,
                },
            }

            await self._save_trace(
                context=context,
                provider=provider,
                request_payload=request_payload,
                response_payload=response_payload,
                latency_ms=stream_latency_ms,
                first_token_ms=stream_first_token_ms,
                input_tokens=stream_input_tokens,
                output_tokens=stream_output_tokens,
                tool_calls=response_payload["tool_calls"] or None,
            )

            if not iteration_tool_calls:
                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)
                yield {
                    "type": "done",
                    "usage": {
                        "input_tokens": context.total_input_tokens,
                        "output_tokens": context.total_output_tokens,
                    },
                    "iterations": context.iteration_count + 1,
                    "latency_ms": latency_ms,
                }
                return

            # Execute tool calls
            assistant_message = {
                "role": "assistant",
                "content": full_content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        },
                    }
                    for tc in iteration_tool_calls
                ],
            }
            working_messages.append(assistant_message)

            iteration_tool_results = []
            for tool_call in iteration_tool_calls:
                result = await self._execute_tool(tool_call, context)
                tool_calls_executed.append({
                    "tool": tool_call.name,
                    "arguments": tool_call.arguments,
                    "result": result,
                })
                iteration_tool_results.append({
                    "tool": tool_call.name,
                    "arguments": tool_call.arguments,
                    "result": {"success": result.success, "data": result.data, "error": result.error},
                })

                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result.data) if result.success else result.error,
                }
                working_messages.append(tool_message)

            # Update trace with tool results
            if context.session:
                try:
                    from aeris.models.trace import LLMTrace
                    from sqlmodel import select
                    stmt = (
                        select(LLMTrace)
                        .where(LLMTrace.user_id == context.user_id)
                        .where(LLMTrace.conversation_id == context.conversation_id)
                        .where(LLMTrace.message_id == context.message_id)
                        .order_by(LLMTrace.timestamp.desc())
                        .limit(1)
                    )
                    result = await context.session.execute(stmt)
                    latest_trace = result.scalar_one_or_none()
                    if latest_trace:
                        latest_trace.tool_results = iteration_tool_results
                        await context.session.commit()
                except Exception:
                    pass

            context.iteration_count += 1

        # Max iterations reached
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        yield {
            "type": "done",
            "usage": {
                "input_tokens": context.total_input_tokens,
                "output_tokens": context.total_output_tokens,
            },
            "iterations": context.max_iterations,
            "latency_ms": latency_ms,
            "error": "Max iterations reached",
        }


# Global engine instance
_engine: Optional[AgentEngine] = None


def get_agent_engine() -> AgentEngine:
    """Get or create agent engine singleton."""
    global _engine
    if _engine is None:
        _engine = AgentEngine()
    return _engine