# Aeris - 轻量 AI Agent 平台设计文档

**日期**: 2026-04-28  
**版本**: MVP v1.0  
**状态**: 待审阅

---

## 1. 项目概述

### 1.1 目标

Aeris 是一个面向个人和小团队的**轻量级 AI Agent 平台**，支持：

- **网页端对话**: 实时流式聊天，支持工具调用
- **文件上传下载**: 双向文件交互，PDF/图片解析
- **定时任务**: Agent 自主创建，Web 面板管理
- **全链路监控**: LLM Trace + 业务指标，优化有据

### 1.2 定位

| 维度 | 决策 |
|------|------|
| 产品形态 | 个人 AI 助手平台 |
| 用户规模 | 小范围多人（MVP B 模式），数据按多租户隔离预留 |
| 技术栈 | Python (FastAPI) + React + PostgreSQL |
| 架构 | 单体轻量型，所有模块同进程部署 |
| LLM 接入 | OpenAI-compatible API，本地推理引擎为主 (SGLang/vLLM) |

### 1.3 参考项目

- **learn-claude-code**: Harness 工程教学，极简 Agent Loop 设计
- **nanobot**: 超轻量级 AI Agent 产品，同进程架构，多 IM 通道

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                          前端层                                   │
│  [React SPA] ←──HTTP/WebSocket──→ [FastAPI 后端服务]           │
└─────────────────────────────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
        [PostgreSQL]            [本地磁盘]              [可选: S3]
        (数据持久化)            (文件存储)              (文件备份)
```

### 2.2 模块划分

```
aeris_backend/
├── main.py                 # FastAPI 入口，挂载路由
├── config.py               # Pydantic Settings，YAML/ENV 配置
├── models/                 # SQLModel 模型定义
│   ├── user.py
│   ├── conversation.py
│   ├── message.py
│   ├── scheduled_task.py
│   ├── file_record.py
│   └── trace.py
├── routers/                # API 路由
│   ├── auth.py
│   ├── chat.py
│   ├── files.py
│   ├── tasks.py
│   └── metrics.py
├── services/               # 业务逻辑
│   ├── agent_engine.py     # Agent Loop 核心
│   ├── provider_manager.py # Provider 适配层
│   ├── tokenizer.py        # Usage 估算
│   ├── file_service.py     # 文件存储
│   ├── task_scheduler.py   # APScheduler 封装
│   └── trace_collector.py  # Trace 采集
└── utils/                  # 工具函数
```

### 2.3 技术栈

| 层级 | 选型 | 理由 |
|------|------|------|
| 后端框架 | FastAPI | Python 生态成熟，原生 async/WebSocket，自动 API 文档 |
| 数据库 | PostgreSQL | 支持多租户扩展预留，比 SQLite 可靠，支持 APScheduler 持久化 |
| ORM | SQLModel | SQLAlchemy + Pydantic 结合，类型安全，FastAPI 原生支持 |
| 定时任务 | APScheduler | 纯 Python，无需 Redis，支持 PostgreSQL 持久化存储 |
| LLM 调用 | `openai` SDK | 兼容所有 OpenAI-compatible API |
| 文件存储 | 本地磁盘 + 路径隔离 | MVP 足够，后期可平滑替换为 S3/MinIO |
| 前端 | React + TypeScript | 组件化强，生态成熟，聊天界面库丰富 |
| 实时通信 | WebSocket (FastAPI native) | 流式 LLM 输出、推送通知 |

---

## 3. 数据模型

### 3.1 实体关系

```
User (1) ───< (N) Conversation
                │
                ├──< (N) Message
                │
                └──< (N) ScheduledTask

User (1) ───< (N) FileRecord

Message (1) ─── (1) LLMTrace (可选，Agent 消息才有)
```

### 3.2 核心模型

#### User
```python
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)

    # 预留多租户字段
    quota_tokens_daily: Optional[int] = Field(default=None)

    conversations: List["Conversation"] = Relationship(back_populates="user")
    tasks: List["ScheduledTask"] = Relationship(back_populates="user")
    files: List["FileRecord"] = Relationship(back_populates="user")
```

#### Conversation & Message
```python
class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: Optional[str] = Field(default=None)
    status: str = Field(default="active")
    model_config_snapshot: Optional[dict] = Field(default=None, sa_column_kwargs={"type": "JSON"})

    user: Optional["User"] = Relationship(back_populates="conversations")
    messages: List["Message"] = Relationship(back_populates="conversation")


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: int = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    role: str  # system, user, assistant, tool
    content: Optional[str] = Field(default=None)

    tool_calls: Optional[List[dict]] = Field(default=None, sa_column_kwargs={"type": "JSON"})
    tool_call_id: Optional[str] = Field(default=None)

    # Token 使用（用于监控）
    input_tokens: Optional[int] = Field(default=None)
    output_tokens: Optional[int] = Field(default=None)
    tokens_estimated: bool = Field(default=False)

    trace_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    conversation: Optional["Conversation"] = Relationship(back_populates="messages")
```

#### ScheduledTask
```python
class ScheduledTask(SQLModel, table=True):
    __tablename__ = "scheduled_tasks"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    name: str
    description: Optional[str] = Field(default=None)

    trigger_type: str  # cron, once, interval
    trigger_config: dict = Field(sa_column_kwargs={"type": "JSON"})
    task_payload: dict = Field(sa_column_kwargs={"type": "JSON"})

    status: str = Field(default="pending")

    last_run_at: Optional[datetime] = Field(default=None)
    last_result: Optional[str] = Field(default=None)
    next_run_at: Optional[datetime] = Field(default=None, index=True)
    run_count: int = Field(default=0)

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship(back_populates="tasks")
```

#### FileRecord
```python
class FileRecord(SQLModel, table=True):
    __tablename__ = "file_records"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    conversation_id: Optional[int] = Field(foreign_key="conversations.id", default=None)

    original_name: str
    stored_name: str
    mime_type: str
    size_bytes: int
    storage_path: str

    status: str = Field(default="ready")
    extracted_text: Optional[str] = Field(default=None)

    is_public: bool = Field(default=False)
    expires_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship(back_populates="files")
```

---

## 4. Agent Loop 与工具设计

### 4.1 核心 Agent Loop

```python
async def agent_loop(
    messages: list[dict],
    tools: list[Tool],
    provider: Provider,
    context: AgentContext,
    max_iterations: int = 10,
) -> AgentResult:
    iteration = 0
    final_response = None

    while iteration < max_iterations:
        response = await provider.chat_completion(
            messages=messages,
            tools=tools if tools else None,
            stream=False,
            thinking=context.get_thinking_config(),
        )

        message = response.choices[0].message
        context.record_usage(
            input_tokens=response.usage.prompt_tokens if response.usage else None,
            output_tokens=response.usage.completion_tokens if response.usage else None,
            model=context.model,
        )

        if not message.tool_calls:
            final_response = message.content
            break

        # 处理 tool calls
        messages.append({...})  # assistant message with tool_calls
        
        for tool_call in message.tool_calls:
            result = await execute_tool(...)
            messages.append({...})  # tool result

        iteration += 1

    return AgentResult(...)
```

### 4.2 工具设计

| 工具类别 | 工具名 | 功能 |
|---------|-------|------|
| **文件** | `file_upload` | 处理用户上传文件 |
| | `file_read` | 读取文件内容（文本/PDF/图片 OCR） |
| | `file_write` | 生成文件到用户目录 |
| | `file_list` | 列出用户文件目录 |
| **定时任务** | `schedule_create` | 创建定时任务（cron/once/interval） |
| | `schedule_list` | 列出用户的定时任务 |
| | `schedule_delete` | 删除指定任务 |
| | `schedule_update` | 修改任务 |
| **上下文** | `conversation_search` | 搜索历史对话 |

### 4.3 Provider 层

```python
# 配置示例
providers:
  sglang-qwen-thinking:
    type: sglang
    base_url: "http://localhost:30000/v1"
    model: "Qwen/QwQ-32B-Preview"
    thinking:
      enabled: true
      budget_tokens: 8192
    capabilities: ["tool_calling", "streaming", "reasoning_content"]
    
  sglang-qwen-normal:
    type: sglang
    base_url: "http://localhost:30001/v1"
    model: "Qwen/Qwen2.5-72B-Instruct"
    thinking:
      enabled: false
    capabilities: ["tool_calling", "streaming"]
```

**Usage 获取优先级**（按你指定）：
1. 非流式：读 SGLang 返回的 `response.usage`
2. 流式：如果最后有 `usage`，就读取
3. 无 usage：用模型 tokenizer 或 SGLang `/tokenize` 估算
4. 最后才用 tiktoken 兜底

---

## 5. 监控与可观测性

### 5.1 数据存储

**所有监控数据存 PostgreSQL**，无额外时序数据库。

| 数据类型 | 存储表 |
|---------|-------|
| LLM Trace | `llm_traces` |
| Token 使用 | `messages.input_tokens/output_tokens` |
| 对话数据 | `conversations` + `messages` |
| 定时任务 | `scheduled_tasks` |
| 文件存储 | `file_records` |

### 5.2 Trace 模型

```python
class LLMTrace(SQLModel, table=True):
    __tablename__ = "llm_traces"

    trace_id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    message_id: Optional[int] = Field(foreign_key="messages.id")

    provider: str
    model: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    request_payload: dict = Field(sa_column_kwargs={"type": "JSON"})
    response_payload: dict = Field(sa_column_kwargs={"type": "JSON"})

    latency_ms: int
    first_token_ms: Optional[int] = Field(default=None)
    tokens_per_second: Optional[float] = Field(default=None)

    input_tokens: int
    output_tokens: int
    tokens_estimated: bool = Field(default=False)

    tool_calls: Optional[List[dict]] = Field(default=None, sa_column_kwargs={"type": "JSON"})
    tool_results: Optional[List[dict]] = Field(default=None, sa_column_kwargs={"type": "JSON"})
    iteration_count: int = Field(default=1)

    error_type: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
```

### 5.3 监控面板

| 页面 | 功能 |
|------|------|
| **Overview** | 今日对话数、Token 消耗、平均延迟、错误率趋势（基于 PG 聚合） |
| **Traces** | LLM Trace 列表，支持按 provider/模型/错误筛选，点击查看完整请求/响应 |
| **Usage** | 模型使用分布、Token 消耗趋势 |

**去掉系统级监控**（CPU/内存/磁盘），后续如需可单独部署 node_exporter。

---

## 6. 部署与配置

### 6.1 部署架构

```
docker-compose.yml
├── aeris-web      # React 静态文件构建
├── aeris-api      # FastAPI 服务（托管静态文件）
└── aeris-db       # PostgreSQL 16
```

### 6.2 配置结构

```yaml
# config.yaml
app:
  name: "Aeris"
  version: "0.1.0"
  debug: false
  
database:
  url: "postgresql://user:pass@localhost:5432/aeris"
  
server:
  host: "0.0.0.0"
  port: 8000
  workers: 1  # 单体架构，单 worker

security:
  secret_key: "your-secret-key"
  access_token_expire_minutes: 1440  # 24h

providers:
  sglang-qwen-thinking:
    type: sglang
    base_url: "http://localhost:30000/v1"
    model: "Qwen/QwQ-32B-Preview"
    thinking:
      enabled: true
      budget_tokens: 8192
    capabilities: ["tool_calling", "streaming", "reasoning_content"]
    
  sglang-qwen-normal:
    type: sglang
    base_url: "http://localhost:30001/v1"
    model: "Qwen/Qwen2.5-72B-Instruct"
    thinking:
      enabled: false
    capabilities: ["tool_calling", "streaming"]

storage:
  type: "local"
  base_path: "/data/aeris/files"
  max_file_size: 104857600  # 100MB
  allowed_types: ["*/*"]  # 或者限制具体类型

scheduler:
  job_store: "postgresql"
  max_instances: 10
  misfire_grace_time: 3600
```

### 6.3 启动命令

```bash
# 开发环境
pip install -e .
aeris dev

# 生产环境（Docker）
docker-compose up -d
```

---

## 7. UI 设计决策

| 决策项 | 选择 | 说明 |
|--------|------|------|
| **前端框架** | React + TypeScript | 类型安全，组件化强 |
| **UI 组件库** | Ant Design (antd) | 企业级组件库，聊天场景组件丰富 |
| **对话界面** | 现成 React Chat 组件库 | 使用 Ant Design Chat / react-chat-elements 等，快速实现 |
| **文件预览** | 仅图片预览 | 使用 `react-image-gallery` 或 Ant Design Image 组件，PDF 预览不做 |

### 7.1 图片预览实现

- 预览库：`react-image-gallery` 或 Ant Design `Image.PreviewGroup`
- 支持的格式：`image/*`（JPEG, PNG, WebP, GIF 等）
- 交互：点击缩略图放大查看，支持轮播

### 7.2 文件列表展示

- 上传文件以卡片/列表形式展示在对话中
- 图片：直接显示缩略图，点击查看大图
- 其他文件：显示文件名 + 大小 + 下载按钮

---

## 8. 附录

### 8.1 缩写与术语

| 缩写 | 含义 |
|------|------|
| APScheduler | Advanced Python Scheduler |
| FastAPI | 现代 Python Web 框架 |
| SQLModel | SQLAlchemy + Pydantic 结合 |
| SGLang | 高效 LLM 推理引擎 |
| Trace | 分布式追踪，此处指 LLM 调用链追踪 |

### 8.2 版本历史

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-04-28 | 0.1.0 | 初始版本 |
