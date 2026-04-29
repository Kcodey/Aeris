from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import json

import httpx
from openai import AsyncOpenAI

from aeris.config import get_settings

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
    ) -> CompletionResponse:
        """Send chat completion request."""
        pass

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Count tokens in text (for fallback estimation)."""
        pass


class SGLangProvider(Provider):
    """SGLang provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = AsyncOpenAI(
            base_url=config["base_url"],
            api_key="not-needed",  # SGLang doesn't require auth
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
    ) -> CompletionResponse:
        import time
        start_time = time.time()
        first_token_time = None

        # Prepare tools for OpenAI format
        openai_tools = None
        if tools:
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]

        # Add thinking config if enabled
        extra_body = {}
        if self.thinking_enabled and self.thinking_budget:
            extra_body["reasoning"] = True
            extra_body["reasoning_budget"] = self.thinking_budget

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=openai_tools,
            stream=stream,
            extra_body=extra_body if extra_body else None,
        )

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

    async def count_tokens(self, text: str) -> int:
        """Count tokens using SGLang /tokenize endpoint, fallback to estimation."""
        # Priority 1: Try SGLang /tokenize endpoint
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/tokenize",
                    json={"model": self.model, "text": text},
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

        # TODO: Load from providers config file
        # For now, use default SGLang provider from env
        provider_config = {
            "type": "sglang",
            "base_url": config.sglang_base_url,
            "model": config.sglang_model,
            "thinking": {"enabled": False},  # 代码内控制 thinking
        }

        if provider_config["type"] == "sglang":
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
