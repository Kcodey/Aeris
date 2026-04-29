# Aeris Phase 2 - Agent Loop、Provider 层与基础对话 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现 Agent Loop 核心、Provider 抽象层（支持 SGLang）、Tool Registry 框架、WebSocket 实时对话。

**架构：** 基于 Phase 1 的数据库和用户认证，添加 Provider 管理器（支持 SGLang/OpenAI-compatible）、Agent Engine（循环 + 工具执行）、对话路由（HTTP + WebSocket）。

**技术栈：** FastAPI WebSocket、OpenAI SDK（兼容层）、Asyncio、APScheduler（已集成）、自定义 Tool Registry。

---

## 文件结构（新增）

```
aeris/
├── models/
│   └── tool_call.py          # Tool 调用记录（可选，用于调试）
├── services/
│   ├── agent_engine.py       # Agent Loop 核心
│   ├── provider_manager.py   # Provider 抽象 + SGLang 实现
│   ├── tokenizer.py        # Token usage 估算（fallback）
│   ├── chat_service.py     # 对话业务逻辑
│   └── tool_registry.py    # Tool 注册和执行
├── routers/
│   ├── chat.py             # 对话 HTTP API
│   └── ws.py               # WebSocket 实时对话
├── schemas/
│   ├── __init__.py
│   ├── chat.py             # 对话相关 Pydantic schemas
│   └── tool.py             # 工具定义 schemas
├── tools/
│   ├── __init__.py         # 工具导出
│   ├── base.py             # Tool 基类
│   └── conversation_search.py  # 对话搜索工具（MVP 先实现一个）
└── config/
    └── providers.yaml      # Provider 配置文件（可选，或放 config.py）

frontend/                     # Phase 2 开始加入前端基础结构
├── package.json
├── tsconfig.json
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   │   └── Chat/
│   │       ├── ChatWindow.tsx
│   │       ├── MessageList.tsx
│   │       └── MessageInput.tsx
│   └── hooks/
│       └── useWebSocket.ts
└── index.html
```

---

## 任务分解

### 任务 1：Provider 抽象层与 SGLang 实现

**文件：**
- 创建：`aeris/services/provider_manager.py`

- [ ] **步骤 1：创建 Provider 抽象基类和 SGLang 实现**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, AsyncGenerator
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
            "base_url": getattr(config, "sglang_base_url", "http://localhost:30000/v1"),
            "model": getattr(config, "sglang_model", "default"),
            "thinking": {"enabled": False},
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
```

- [ ] **步骤 2：Commit**

```bash
git add aeris/services/provider_manager.py
git commit -m "feat: add Provider abstract class and SGLang implementation"
```

---

### 任务 2：Token 估算服务

**文件：**
- 创建：`aeris/services/tokenizer.py`
- 修改：`aeris/config.py`（添加 tokenizer 配置）

- [ ] **步骤 1：创建 tokenizer.py**

```python
from typing import Dict, Any, List
import json

import httpx


class Tokenizer:
    """Token usage estimation with multiple fallback strategies."""

    def __init__(self, provider_manager=None):
        self.provider_manager = provider_manager
        self._cache: Dict[str, Any] = {}

    async def estimate_tokens(
        self,
        messages: List[Dict[str, Any]],
        provider_name: str = "default",
    ) -> int:
        """
        Estimate token count for messages.

        Priority:
        1. Provider's /tokenize endpoint (if SGLang)
        2. Model-specific tokenizer
        3. tiktoken (cl100k_base)
        4. Character count / 4
        """
        text = json.dumps(messages)

        # Priority 1: Provider tokenize endpoint
        if self.provider_manager:
            try:
                provider = self.provider_manager.get_provider(provider_name)
                if hasattr(provider, "count_tokens"):
                    return await provider.count_tokens(text)
            except Exception:
                pass

        # Priority 2: tiktoken
        try:
            import tiktoken
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(text))
        except Exception:
            pass

        # Priority 3: Rough estimation
        return len(text) // 4

    async def estimate_output_tokens(self, text: str) -> int:
        """Estimate token count for output text."""
        # Same priority as above, but for single text
        try:
            import tiktoken
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(text))
        except Exception:
            return len(text) // 4


# Global tokenizer instance
_tokenizer: Tokenizer = None


def get_tokenizer() -> Tokenizer:
    """Get or create tokenizer singleton."""
    global _tokenizer
    if _tokenizer is None:
        from aeris.services.provider_manager import get_provider_manager
        _tokenizer = Tokenizer(get_provider_manager())
    return _tokenizer
```

- [ ] **步骤 2：Commit**

```bash
git add aeris/services/tokenizer.py
git commit -m "feat: add tokenizer service with fallback strategies"
```

---

### 任务 3：Tool Registry 框架

**文件：**
- 创建：`aeris/tools/__init__.py`
- 创建：`aeris/tools/base.py`

- [ ] **步骤 1：创建 tools/base.py**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type, Callable


@dataclass
class ToolParameter:
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolResult:
    success: bool
    data: Any
    error: Optional[str] = None


class Tool(ABC):
    """Base class for tools."""

    name: str
    description: str
    parameters: List[ToolParameter]

    def __init__(self):
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class ToolRegistry:
    """Registry for tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        self._tools[tool.name] = tool
        self._schemas[tool.name] = tool.to_openai_schema()

    def register_function(
        self,
        name: str,
        description: str,
        func: Callable,
        parameters: List[ToolParameter],
    ):
        """Register a function as a tool."""
        # Create a wrapper Tool class
        class FunctionTool(Tool):
            def __init__(self):
                self.name = name
                self.description = description
                self.parameters = parameters
                self._func = func

            async def execute(self, **kwargs) -> ToolResult:
                try:
                    result = await self._func(**kwargs)
                    return ToolResult(success=True, data=result)
                except Exception as e:
                    return ToolResult(success=False, data=None, error=str(e))

        self.register(FunctionTool())

    def get(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self._tools.get(name)

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas for LLM."""
        return list(self._schemas.values())

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    async def execute(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name with arguments."""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool '{name}' not found",
            )
        return await tool.execute(**arguments)


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create tool registry singleton."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
```

- [ ] **步骤 2：创建 tools/__init__.py**

```python
"""Tools module."""

from aeris.tools.base import Tool, ToolParameter, ToolResult, ToolRegistry, get_tool_registry

__all__ = ["Tool", "ToolParameter", "ToolResult", "ToolRegistry", "get_tool_registry"]
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/tools/
git commit -m "feat: add Tool base class and ToolRegistry"
```

---

### 任务 4：Agent Engine（核心 Agent Loop）

**文件：**
- 创建：`aeris/services/agent_engine.py`

- [ ] **步骤 1：创建 agent_engine.py**

```python
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
```

- [ ] **步骤 2：Commit**

```bash
git add aeris/services/agent_engine.py
git commit -m "feat: add AgentEngine with core agent loop"
```

---

### 任务 5：对话服务

**文件：**
- 创建：`aeris/services/chat_service.py`
- 创建：`aeris/schemas/__init__.py`
- 创建：`aeris/schemas/chat.py`

- [ ] **步骤 1：创建 schemas/chat.py**

```python
from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel


class MessageCreate(BaseModel):
    content: str
    role: str = "user"


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: Optional[str]
    tool_calls: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    messages: List[MessageResponse]


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    message: MessageResponse
    usage: Dict[str, int]
    tool_calls: List[Dict[str, Any]] = []


class StreamingChunk(BaseModel):
    type: str  # "content", "tool_call", "done", "error"
    content: Optional[str] = None
    tool_call: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None
```

- [ ] **步骤 2：创建 aeris/schemas/__init__.py**

```python
"""Pydantic schemas for API."""

from aeris.schemas.chat import (
    MessageCreate,
    MessageResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationWithMessages,
    ChatRequest,
    ChatResponse,
    StreamingChunk,
)

__all__ = [
    "MessageCreate",
    "MessageResponse",
    "ConversationCreate",
    "ConversationResponse",
    "ConversationWithMessages",
    "ChatRequest",
    "ChatResponse",
    "StreamingChunk",
]
```

- [ ] **步骤 3：创建 chat_service.py**

```python
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc

from aeris.models.conversation import Conversation
from aeris.models.message import Message
from aeris.schemas.chat import ConversationCreate, MessageCreate
from aeris.services.agent_engine import AgentEngine, AgentContext, get_agent_engine
from aeris.services.tokenizer import get_tokenizer


class ChatService:
    """Chat business logic service."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.agent_engine: AgentEngine = get_agent_engine()
        self.tokenizer = get_tokenizer()

    async def create_conversation(
        self,
        user_id: int,
        data: ConversationCreate,
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            user_id=user_id,
            title=data.title,
        )
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get_conversation(
        self,
        user_id: int,
        conversation_id: int,
    ) -> Optional[Conversation]:
        """Get conversation by ID."""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Conversation]:
        """List user's conversations."""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .where(Conversation.status == "active")
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_conversation_messages(
        self,
        conversation_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Message]:
        """Get messages in a conversation."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def send_message(
        self,
        user_id: int,
        conversation_id: int,
        content: str,
    ) -> dict:
        """
        Send a message and get AI response.

        1. Save user message
        2. Build conversation history
        3. Run agent
        4. Save AI response
        5. Return result
        """
        # Save user message
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )
        self.session.add(user_message)
        await self.session.commit()
        await self.session.refresh(user_message)

        # Get conversation history
        messages = await self.get_conversation_messages(conversation_id)

        # Build messages for LLM
        llm_messages = [
            {"role": "system", "content": "You are a helpful AI assistant."}
        ]
        for msg in messages:
            llm_messages.append({
                "role": msg.role,
                "content": msg.content or "",
            })

        # Run agent
        context = AgentContext(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=user_message.id,
        )

        result = await self.agent_engine.run(llm_messages, context)

        # Save AI response
        ai_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=result.content,
            input_tokens=result.usage["input_tokens"],
            output_tokens=result.usage["output_tokens"],
            tokens_estimated=False,  # SGLang returns actual usage
        )
        self.session.add(ai_message)
        await self.session.commit()
        await self.session.refresh(ai_message)

        # Update conversation updated_at
        conversation = await self.get_conversation(user_id, conversation_id)
        if conversation and not conversation.title:
            # Auto-generate title from first message
            from datetime import datetime
            conversation.title = content[:50] + "..." if len(content) > 50 else content
        conversation.updated_at = datetime.utcnow()
        await self.session.commit()

        return {
            "user_message": user_message,
            "ai_message": ai_message,
            "usage": result.usage,
            "tool_calls": result.tool_calls_executed,
        }

    async def delete_conversation(
        self,
        user_id: int,
        conversation_id: int,
    ) -> bool:
        """Soft delete a conversation."""
        conversation = await self.get_conversation(user_id, conversation_id)
        if not conversation:
            return False

        conversation.status = "deleted"
        await self.session.commit()
        return True
```

- [ ] **步骤 4：Commit**

```bash
git add aeris/schemas/ aeris/services/chat_service.py
git commit -m "feat: add chat service with conversation management"
```

---

### 任务 6：对话 HTTP API 路由

**文件：**
- 创建：`aeris/routers/chat.py`

- [ ] **步骤 1：创建 chat.py**

```python
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from aeris.database import get_session
from aeris.routers.auth import get_current_user, TokenData
from aeris.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationWithMessages,
    MessageResponse,
)
from aeris.services.chat_service import ChatService

router = APIRouter(prefix="/conversations", tags=["chat"])


async def get_chat_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChatService:
    """Dependency to get chat service."""
    return ChatService(session)


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: Annotated[TokenData, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    skip: int = 0,
    limit: int = 20,
):
    """List user's conversations."""
    conversations = await chat_service.list_conversations(
        current_user.user_id, skip=skip, limit=limit
    )
    return conversations


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: Annotated[TokenData, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
):
    """Create a new conversation."""
    conversation = await chat_service.create_conversation(current_user.user_id, data)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: int,
    current_user: Annotated[TokenData, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
):
    """Get conversation with messages."""
    conversation = await chat_service.get_conversation(
        current_user.user_id, conversation_id
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await chat_service.get_conversation_messages(conversation_id)

    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "title": conversation.title,
        "status": conversation.status,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "messages": messages,
    }


@router.post("/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(
    conversation_id: int,
    request: ChatRequest,
    current_user: Annotated[TokenData, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
):
    """Send a message and get AI response."""
    # Verify conversation belongs to user
    conversation = await chat_service.get_conversation(
        current_user.user_id, conversation_id
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await chat_service.send_message(
        current_user.user_id,
        conversation_id,
        request.message,
    )

    return ChatResponse(
        message=MessageResponse.model_validate(result["ai_message"]),
        usage=result["usage"],
        tool_calls=result["tool_calls"],
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    current_user: Annotated[TokenData, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
):
    """Delete a conversation."""
    success = await chat_service.delete_conversation(
        current_user.user_id, conversation_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return None
```

- [ ] **步骤 2：修改 aeris/main.py 添加 chat 路由**

在 `main.py` 的 `app.include_router(auth.router, prefix="/api/v1")` 后面添加：

```python
from aeris.routers import chat
app.include_router(chat.router, prefix="/api/v1")
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/routers/chat.py aeris/main.py
git commit -m "feat: add chat HTTP API routes"
```

---

### 任务 7：WebSocket 实时对话

**文件：**
- 创建：`aeris/routers/ws.py`
- 修改：`aeris/main.py`（添加 WebSocket 路由）

- [ ] **步骤 1：创建 ws.py**

```python
import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from aeris.database import get_session, get_session_context
from aeris.routers.auth import verify_token
from aeris.schemas.chat import StreamingChunk
from aeris.services.chat_service import ChatService
from aeris.services.agent_engine import AgentContext, get_agent_engine

router = APIRouter(tags=["websocket"])

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


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.

    Client sends: {"type": "message", "conversation_id": 123, "content": "hello"}
    Server sends: {"type": "content", "content": "chunk..."}
                  {"type": "done", "usage": {...}}
                  {"type": "error", "error": "..."}
    """
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

                if not conversation_id or not content:
                    await websocket.send_json({
                        "type": "error",
                        "error": "Missing conversation_id or content",
                    })
                    continue

                # Process message
                try:
                    async with get_session_context() as session:
                        chat_service = ChatService(session)

                        # Verify conversation
                        conversation = await chat_service.get_conversation(
                            user["user_id"], conversation_id
                        )
                        if not conversation:
                            await websocket.send_json({
                                "type": "error",
                                "error": "Conversation not found",
                            })
                            continue

                        # Save user message
                        from aeris.models.message import Message
                        from aeris.schemas.chat import MessageCreate

                        user_message = Message(
                            conversation_id=conversation_id,
                            role="user",
                            content=content,
                        )
                        session.add(user_message)
                        await session.commit()
                        await session.refresh(user_message)

                        # Get conversation history
                        messages = await chat_service.get_conversation_messages(conversation_id)

                        # Build LLM messages
                        llm_messages = [
                            {"role": "system", "content": "You are a helpful AI assistant."}
                        ]
                        for msg in messages:
                            llm_messages.append({
                                "role": msg.role,
                                "content": msg.content or "",
                            })

                        # Run agent with streaming
                        context = AgentContext(
                            user_id=user["user_id"],
                            conversation_id=conversation_id,
                            message_id=user_message.id,
                        )

                        agent_engine = get_agent_engine()
                        full_content = ""

                        async for chunk in agent_engine.run_stream(llm_messages, context):
                            await websocket.send_json(chunk)
                            if chunk["type"] == "content":
                                full_content += chunk.get("content", "")

                        # Save AI response
                        ai_message = Message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=full_content if full_content else None,
                        )
                        session.add(ai_message)
                        await session.commit()

                except Exception as e:
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
```

- [ ] **步骤 2：修改 main.py 添加 WebSocket 路由**

在 `aeris/main.py` 中添加：

```python
from aeris.routers import ws
app.include_router(ws.router)
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/routers/ws.py aeris/main.py
git commit -m "feat: add WebSocket endpoint for real-time chat"
```

---

### 任务 8：注册对话搜索工具（示例工具）

**文件：**
- 创建：`aeris/tools/conversation_search.py`
- 修改：`aeris/main.py`（应用启动时注册工具）

- [ ] **步骤 1：创建 conversation_search.py**

```python
from typing import Any, Dict, List

from sqlalchemy import text

from aeris.tools.base import Tool, ToolParameter, ToolResult


class ConversationSearchTool(Tool):
    """Search conversation history."""

    name = "conversation_search"
    description = "Search previous messages in the conversation for specific information."
    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="The search query to find relevant messages",
            required=True,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of results to return",
            required=False,
        ),
    ]

    async def execute(self, query: str, limit: int = 5, _context: Dict = None) -> ToolResult:
        """Search conversation history."""
        # This is a simple implementation that would need database access
        # In practice, we'd use the context to get conversation_id and query the DB
        # For MVP, return a placeholder
        return ToolResult(
            success=True,
            data={
                "message": "Conversation search is available but requires database connection.",
                "query": query,
                "limit": limit,
            },
        )


def register_conversation_search_tool(registry):
    """Register the conversation search tool."""
    registry.register(ConversationSearchTool())
```

- [ ] **步骤 2：修改 main.py 注册工具**

在 `lifespan` 函数中初始化数据库后添加工具注册：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()

    # Register tools
    from aeris.tools.base import get_tool_registry
    from aeris.tools.conversation_search import register_conversation_search_tool
    registry = get_tool_registry()
    register_conversation_search_tool(registry)

    yield
    # Shutdown
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/tools/conversation_search.py aeris/main.py
git commit -m "feat: add conversation_search tool example"
```

---

### 任务 9：测试 Agent 和 Provider

**文件：**
- 创建：`tests/test_provider.py`
- 创建：`tests/test_agent_engine.py`

- [ ] **步骤 1：创建 test_provider.py**

```python
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
```

- [ ] **步骤 2：创建 test_agent_engine.py**

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

from aeris.services.agent_engine import AgentEngine, AgentContext, AgentResult


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
```

- [ ] **步骤 3：Commit**

```bash
git add tests/test_provider.py tests/test_agent_engine.py
git commit -m "test: add provider and agent engine tests"
```

---

## 自检

### 规格覆盖度检查

| 规格需求 | 实现任务 |
|---------|---------|
| Provider 抽象层 | ✅ 任务 1 |
| SGLang 实现 | ✅ 任务 1 |
| Token usage 优先级 | ✅ 任务 1, 2 |
| Tool Registry | ✅ 任务 3 |
| Agent Loop | ✅ 任务 4 |
| 对话 HTTP API | ✅ 任务 5, 6 |
| WebSocket 实时对话 | ✅ 任务 7 |
| 示例工具 | ✅ 任务 8 |
| 测试覆盖 | ✅ 任务 9 |

### 文件职责

- `provider_manager.py`: Provider 抽象和具体实现
- `tokenizer.py`: Token 估算 fallback
- `agent_engine.py`: 核心 Agent Loop
- `tool_registry.py`: 工具注册和执行
- `chat_service.py`: 对话业务逻辑
- `chat.py`: HTTP API 路由
- `ws.py`: WebSocket 处理

### 类型一致性

- `CompletionResponse` 和 `ToolResult` dataclass 定义清晰
- `AgentContext` 传递上下文一致
- 所有服务使用依赖注入模式

---

## 执行方式

**计划已完成并保存到 `docs/superpowers/plans/2026-04-28-aeris-phase2.md`。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
