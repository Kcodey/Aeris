from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import json
import logging

import httpx
from openai import AsyncOpenAI

from aeris.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON string


@dataclass
class CompletionResponse:
    content: Optional[str]
    tool_calls: Optional[List[ToolCall]]
    input_tokens: int
    output_tokens: int
    usage_from_api: bool  # 是否来自 API 返回
    latency_ms: int
    first_token_ms: Optional[int]


@dataclass
class StreamChunk:
    type: str  # "content" | "tool_call" | "usage"
    content: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    usage: Optional[Dict[str, Any]] = None


class Provider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = config["model"]
        self.thinking_enabled = config.get("thinking", {}).get("enabled", False)
        self.thinking_budget = config.get("thinking", {}).get("budget_tokens")

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[ToolDefinition]] = None,
        stream: bool = False,
        max_tokens: Optional[int] = None,
    ) -> CompletionResponse:
        """Send chat completion request."""
        pass

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Count tokens in text (for fallback estimation)."""
        pass

    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[ToolDefinition]] = None,
    ):
        """Stream chat completion, yielding StreamChunk objects."""
        pass


class SGLangProvider(Provider):
    """SGLang/Volcano provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = AsyncOpenAI(
            base_url=config["base_url"],
            api_key=config.get("api_key", "not-needed"),
        )
        self.base_url = config["base_url"].rstrip("/")
        self.supports_tokenize_endpoint = self._check_tokenize_endpoint()

    def _check_tokenize_endpoint(self) -> bool:
        """Check if /tokenize endpoint is available."""
        # This will be checked lazily on first tokenize call
        return True

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[ToolDefinition]] = None,
        stream: bool = False,
        max_tokens: Optional[int] = None,
    ) -> CompletionResponse:
        import time
        start_time = time.time()
        first_token_time = None

        # Prepare tools for OpenAI format
        openai_tools = None
        if tools:
            # Tools can be List[ToolDefinition] or List[dict] (schemas)
            openai_tools = []
            for t in tools:
                if isinstance(t, dict):
                    # Already in OpenAI format
                    openai_tools.append(t)
                else:
                    # ToolDefinition object
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description,
                            "parameters": t.parameters,
                        },
                    })

        # Add thinking config if enabled
        extra_body = {}
        if self.thinking_enabled and self.thinking_budget:
            extra_body["reasoning"] = True
            extra_body["reasoning_budget"] = self.thinking_budget

        # Prepare API kwargs
        kwargs = {
            "model": self.model,
            "messages": messages,
            "tools": openai_tools,
            "stream": stream,
            "extra_body": extra_body if extra_body else None,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        response = await self.client.chat.completions.create(**kwargs)

        if stream:
            # Handle streaming response
            content_parts = []
            tool_calls_parts = {}
            usage = None
            reasoning_content = ""

            async for chunk in response:
                if first_token_time is None:
                    first_token_time = time.time()

                delta = chunk.choices[0].delta

                # Content
                if delta.content:
                    content_parts.append(delta.content)

                # Tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.index not in tool_calls_parts:
                            tool_calls_parts[tc.index] = {
                                "id": tc.id,
                                "name": tc.function.name or "",
                                "arguments": tc.function.arguments or "",
                            }
                        else:
                            if tc.function.arguments:
                                tool_calls_parts[tc.index]["arguments"] += tc.function.arguments

                # Usage in last chunk (some providers send this)
                if hasattr(chunk, "usage") and chunk.usage:
                    usage = chunk.usage

            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            first_token_ms = int((first_token_time - start_time) * 1000) if first_token_time else None

            content = "".join(content_parts) if content_parts else None
            tool_calls = []
            for idx in sorted(tool_calls_parts.keys()):
                tc = tool_calls_parts[idx]
                tool_calls.append(ToolCall(
                    id=tc["id"],
                    name=tc["name"],
                    arguments=tc["arguments"],
                ))

            # Get token usage
            input_tokens = 0
            output_tokens = 0
            usage_from_api = False

            if usage:
                input_tokens = usage.prompt_tokens
                output_tokens = usage.completion_tokens
                usage_from_api = True
            else:
                # Estimate tokens
                input_tokens = await self.count_tokens(json.dumps(messages))
                output_tokens = await self.count_tokens(content or "")
                usage_from_api = False

            return CompletionResponse(
                content=content,
                tool_calls=tool_calls if tool_calls else None,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                usage_from_api=usage_from_api,
                latency_ms=latency_ms,
                first_token_ms=first_token_ms,
            )
        else:
            # Non-streaming response
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)

            message = response.choices[0].message
            content = message.content

            tool_calls = None
            if message.tool_calls:
                tool_calls = [
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                    for tc in message.tool_calls
                ]

            # Get token usage
            input_tokens = 0
            output_tokens = 0
            usage_from_api = False

            if response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                usage_from_api = True
            else:
                # Estimate tokens
                input_tokens = await self.count_tokens(json.dumps(messages))
                output_tokens = await self.count_tokens(content or "")
                usage_from_api = False

            return CompletionResponse(
                content=content,
                tool_calls=tool_calls,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                usage_from_api=usage_from_api,
                latency_ms=latency_ms,
                first_token_ms=None,  # No streaming
            )

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[ToolDefinition]] = None,
        timing_callback: Optional[callable] = None,
    ):
        """Stream chat completion, yielding StreamChunk objects as they arrive.

        Args:
            messages: Chat messages
            tools: Available tools
            timing_callback: Optional callback for timing events (stage, timestamp, metadata)
        """
        import time
        start_time = time.perf_counter()
        first_token_time = None

        # Notify start
        if timing_callback:
            timing_callback("api_request_start", time.time())

        # Prepare tools for OpenAI format
        openai_tools = None
        if tools:
            openai_tools = []
            for t in tools:
                if isinstance(t, dict):
                    openai_tools.append(t)
                else:
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description,
                            "parameters": t.parameters,
                        },
                    })

        # Add thinking config if enabled
        extra_body = {}
        if self.thinking_enabled and self.thinking_budget:
            extra_body["reasoning"] = True
            extra_body["reasoning_budget"] = self.thinking_budget

        t_before_request = time.perf_counter()
        # 流式输入的 message
        logger.info(f"[input messages] {messages}")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=openai_tools,
            stream=True,
            extra_body=extra_body if extra_body else None,
        )
        logger.info(f"[output messages] {messages}")
        if timing_callback:
            timing_callback("api_request_sent", time.time(),
                          {"latency_ms": int((time.perf_counter() - t_before_request) * 1000)})

        content_parts = []
        tool_calls_parts = {}
        usage = None
        in_thinking_tag = False
        thinking_buffer = ""

        async for chunk in response:
            # DEBUG: Log raw chunk from volcano
            # logger.info(f"[VOLCANO CHUNK] {chunk.model_dump_json()}")

            if first_token_time is None:
                first_token_time = time.perf_counter()
                ttft_ms = int((first_token_time - start_time) * 1000)
                if timing_callback:
                    timing_callback("first_token", time.time(),
                                  {"ttft_ms": ttft_ms, "model": self.model})

            delta = chunk.choices[0].delta

            # Content with thinking tag filtering
            if delta.content:
                text = delta.content
                # Log raw content before filtering
                # logger.info(f"[THINK_FILTER_RAW] text={repr(text)}")

                # Handle thinking tags that may span chunks
                if in_thinking_tag:
                    thinking_buffer += text
                    if "</think>" in thinking_buffer:
                        in_thinking_tag = False
                        # Extract content after </think>
                        after_think = thinking_buffer.split("</think>", 1)[1]
                        if after_think:
                            content_parts.append(after_think)
                            # logger.info(f"[THINK_FILTER_OUT] after_think={repr(after_think)}")
                            yield StreamChunk(type="content", content=after_think)
                        thinking_buffer = ""
                elif "<think" in text:
                    in_thinking_tag = True
                    thinking_buffer = text
                    # Yield content before <think>
                    before_think = text.split("<think", 1)[0]
                    if before_think:
                        content_parts.append(before_think)
                        # logger.info(f"[THINK_FILTER_OUT] before_think={repr(before_think)}")
                        yield StreamChunk(type="content", content=before_think)
                else:
                    content_parts.append(text)
                    # logger.info(f"[THINK_FILTER_OUT] text={repr(text)}")
                    yield StreamChunk(type="content", content=text)

            # Tool calls
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.index not in tool_calls_parts:
                        tool_calls_parts[tc.index] = {
                            "id": tc.id,
                            "name": tc.function.name or "",
                            "arguments": tc.function.arguments or "",
                        }
                    else:
                        if tc.function.arguments:
                            tool_calls_parts[tc.index]["arguments"] += tc.function.arguments

            # Usage in last chunk (some providers send this)
            if hasattr(chunk, "usage") and chunk.usage:
                usage = chunk.usage

        end_time = time.perf_counter()
        latency_ms = int((end_time - start_time) * 1000)
        first_token_ms = int((first_token_time - start_time) * 1000) if first_token_time else None

        if timing_callback:
            timing_callback("stream_complete", time.time(),
                          {"latency_ms": latency_ms, "first_token_ms": first_token_ms})

        # Yield collected tool calls
        for idx in sorted(tool_calls_parts.keys()):
            tc = tool_calls_parts[idx]
            yield StreamChunk(
                type="tool_call",
                tool_call=ToolCall(
                    id=tc["id"],
                    name=tc["name"],
                    arguments=tc["arguments"],
                ),
            )

        # Yield usage
        input_tokens = 0
        output_tokens = 0
        usage_from_api = False

        if usage:
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            usage_from_api = True
        else:
            input_tokens = await self.count_tokens(json.dumps(messages))
            output_tokens = await self.count_tokens("".join(content_parts))
            usage_from_api = False

        yield StreamChunk(
            type="usage",
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "usage_from_api": usage_from_api,
                "latency_ms": latency_ms,
                "first_token_ms": first_token_ms,
            },
        )

    async def count_tokens(self, text: str) -> int:
        """Count tokens using SGLang /tokenize endpoint, fallback to estimation."""
        # Priority 1: Try SGLang /tokenize endpoint
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/tokenize",
                    json={"prompt": text},
                    timeout=5.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("count", 0)
        except Exception:
            pass

        # Priority 2: Fallback to tiktoken (import here to avoid mandatory dependency)
        try:
            import tiktoken
            # Try to get encoder for the model, fallback to cl100k_base
            try:
                encoder = tiktoken.encoding_for_model(self.model)
            except KeyError:
                encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(text))
        except Exception:
            pass

        # Priority 3: Rough estimation (1 token ~ 4 characters)
        return len(text) // 4


class ProviderManager:
    """Manage multiple providers."""

    def __init__(self):
        self.providers: Dict[str, Provider] = {}
        self._load_providers()

    def _load_providers(self):
        """Load providers from config."""
        from aeris.config import get_settings
        config = get_settings()

        # Provider type: "sglang" or "volcano"
        provider_type = config.provider_type

        if provider_type == "volcano":
            provider_config = {
                "type": "volcano",
                "base_url": config.volcano_base_url,
                "api_key": config.volcano_api_key,
                "model": config.volcano_model,
                "thinking": {"enabled": False},
            }
        else:
            # Default: SGLang
            provider_config = {
                "type": "sglang",
                "base_url": config.sglang_base_url,
                "api_key": "not-needed",
                "model": config.sglang_model,
                "thinking": {"enabled": False},
            }

        self.providers["default"] = SGLangProvider(provider_config)

    def get_provider(self, name: str = "default") -> Provider:
        """Get provider by name."""
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' not found")
        return self.providers[name]

    def list_providers(self) -> List[str]:
        """List available provider names."""
        return list(self.providers.keys())


# Global provider manager instance
_provider_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Get or create provider manager singleton."""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager
