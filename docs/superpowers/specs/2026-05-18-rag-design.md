# RAG 功能设计方案

## 概述

为 Meditatio 项目添加 RAG（Retrieval Augmented Generation）功能，支持用户通过上传文档或抓取网页内容构建知识库，并在对话中检索使用。

## 需求总结

| 项目 | 方案 |
|------|------|
| 知识库管理 | 管理员统一管理，多个独立 Knowledge Base |
| 文档来源 | 用户上传（PDF/DOCX/TXT）+ 管理员输入单 URL 抓取 |
| 分块策略 | 固定字符数分块（500 字符，50 重叠） |
| Embedding 模型 | all-MiniLM-L6-v2（本地） |
| 对话关联 | 对话创建时选择关联的知识库 |

## 架构设计

```
用户上传文档 / 管理员输入URL
         ↓
   ┌─────┴─────┐
   ↓           ↓
文档处理    URL抓取
   ↓           ↓
分块 + 向量化
         ↓
   Qdrant 存储（一个 KB = 一个 Collection）
         ↓
   知识库 API 管理
         ↓
   对话关联 KB → Agent 检索回答
```

## 数据模型

### KnowledgeBase（知识库）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| name | str | 知识库名称（唯一） |
| description | str | 描述 |
| collection_name | str | 对应 Qdrant collection 名称 |
| is_active | bool | 是否启用 |
| created_by | int | 创建者用户 ID |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### Document（文档）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| knowledge_base_id | int | 关联知识库 ID |
| title | str | 文档标题 |
| source_type | str | upload / url |
| source_path | str | 文件路径或 URL |
| status | str | processing / ready / failed |
| chunk_count | int | 分块数量 |
| error_message | str | 失败原因（如果有） |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### Conversation（修改现有表）

新增 `knowledge_base_ids` 字段，JSON 格式存储关联的知识库 ID 列表。

## API 设计

### 基础路径

所有 RAG 相关接口前缀：`/api/v1/rag`

### 接口列表

#### 1. 知识库管理

| 接口 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/kb` | GET | 所有用户 | 列出所有启用的知识库 |
| `/kb` | POST | 管理员 | 创建新知识库 |
| `/kb/{id}` | DELETE | 管理员 | 删除知识库及其所有文档 |
| `/kb/{id}` | PATCH | 管理员 | 更新知识库信息 |

#### 2. 文档管理

| 接口 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/kb/{id}/documents` | GET | 所有用户 | 列出知识库中的文档 |
| `/kb/{id}/documents` | POST | 所有用户 | 上传文档到知识库 |
| `/kb/{id}/url` | POST | 所有用户 | 从 URL 抓取内容 |
| `/kb/{id}/documents/{doc_id}` | DELETE | 所有用户 | 删除文档 |
| `/kb/{id}/documents/{doc_id}/status` | GET | 所有用户 | 获取文档处理状态 |

#### 3. 检索

| 接口 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/search` | POST | Agent | 检索知识库内容（内部接口） |

#### 请求/响应示例

**POST /api/v1/rag/kb**
```json
// Request
{
  "name": "产品文档",
  "description": "公司产品相关文档"
}

// Response
{
  "id": 1,
  "name": "产品文档",
  "description": "公司产品相关文档",
  "collection_name": "kb_1",
  "is_active": true,
  "created_at": "2026-05-18T10:00:00Z"
}
```

**POST /api/v1/rag/kb/{id}/documents**
```json
// Request (multipart/form-data)
file: <binary>

// Response
{
  "id": 1,
  "knowledge_base_id": 1,
  "title": "用户手册.pdf",
  "source_type": "upload",
  "source_path": "/uploads/rag/docs/1_user_manual.pdf",
  "status": "processing",
  "created_at": "2026-05-18T10:00:00Z"
}
```

**POST /api/v1/rag/kb/{id}/url**
```json
// Request
{
  "url": "https://example.com/doc/article1"
}

// Response
{
  "id": 2,
  "knowledge_base_id": 1,
  "title": "example.com/doc/article1",
  "source_type": "url",
  "source_path": "https://example.com/doc/article1",
  "status": "processing",
  "created_at": "2026-05-18T10:00:00Z"
}
```

**POST /api/v1/rag/search**
```json
// Request
{
  "knowledge_base_ids": [1, 2],
  "query": "如何重置密码？",
  "top_k": 5
}

// Response
{
  "results": [
    {
      "kb_id": 1,
      "kb_name": "产品文档",
      "document_id": 1,
      "chunk_id": "abc123",
      "content": "要重置密码，请访问...",
      "score": 0.85
    }
  ]
}
```

## 服务组件

### 1. Embedding Service

**位置**: `aeris/services/embedding_service.py`

**职责**:
- 加载 all-MiniLM-L6-v2 模型（本地路径）
- 提供 `embed_texts(texts)` 方法
- 提供 `embed_query(query)` 方法

**接口**:
```python
class EmbeddingService:
    def __init__(self, model_path: str):
        """加载本地模型"""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量向量化文本"""

    def embed_query(self, query: str) -> list[float]:
        """向量化单个查询"""
```

### 2. Knowledge Base Service

**位置**: `aeris/services/knowledge_base_service.py`

**职责**:
- 创建/删除 Qdrant collection
- Upsert/Delete 向量数据
- 相似度搜索

**接口**:
```python
class KnowledgeBaseService:
    def __init__(self, embedding_service: EmbeddingService):
        """初始化"""

    async def create_kb(self, name: str, description: str) -> KnowledgeBase:
        """创建知识库和对应 collection"""

    async def delete_kb(self, kb_id: int) -> None:
        """删除知识库和对应 collection"""

    async def add_document(self, kb_id: int, title: str, chunks: list[str]) -> None:
        """添加文档 chunks 到知识库"""

    async def search(self, kb_ids: list[int], query: str, top_k: int) -> list[SearchResult]:
        """多知识库检索"""

    async def get_kb_info(self, kb_id: int) -> dict:
        """获取知识库统计信息"""
```

### 3. Document Processor

**位置**: `aeris/services/document_processor.py`

**职责**:
- 提取 PDF/DOCX/TXT 文件文本
- 按固定字符数分块
- 调用 EmbeddingService 向量化
- 调用 KnowledgeBaseService 存储

**接口**:
```python
class DocumentProcessor:
    def __init__(self, embedding_service: EmbeddingService, kb_service: KnowledgeBaseService):
        """初始化"""

    async def process_upload(self, file_path: str, kb_id: int, title: str) -> Document:
        """处理上传文件"""

    async def process_url(self, url: str, kb_id: int) -> Document:
        """处理 URL 抓取"""
```

**分块参数**:
- `chunk_size`: 500 字符
- `chunk_overlap`: 50 字符

### 4. RAG Tool

**位置**: `aeris/tools/rag_tool.py`

**职责**:
- Agent 调用接口
- 从对话上下文获取关联的 knowledge_base_ids
- 执行检索并返回结果

**Tool 定义**:
```python
class RAGSearchTool(Tool):
    name = "rag_search"
    description = "Search knowledge base for relevant information. Use this when user asks about product docs, manuals, or specific knowledge stored in knowledge bases."

    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True,
        ),
        ToolParameter(
            name="knowledge_base_ids",
            type="string",
            description="Comma-separated knowledge base IDs to search (optional, searches all if not specified)",
            required=False,
        ),
    ]
```

## 对话关联知识库

### 修改 Conversation 模型

在数据库 `conversation` 表新增 `knowledge_base_ids` 列（JSON 格式）。

### 检索流程

1. 对话消息进入 Agent 前，从数据库加载对话关联的 `knowledge_base_ids`
2. Agent 调用 `rag_search` 工具时传入 `knowledge_base_ids`
3. 如果未指定，则使用对话关联的所有 KB
4. 检索结果作为上下文注入 LLM 消息

### System Prompt 增强

在 Agent system prompt 中添加：
```
当用户询问与产品文档、知识库相关的问题时，使用 rag_search 工具检索相关知识。
检索结果会作为上下文提供给你。
```

## 文件结构

```
aeris/
├── services/
│   ├── embedding_service.py      # 向量化服务
│   ├── knowledge_base_service.py # 知识库服务
│   ├── document_processor.py     # 文档处理
│   └── rag_service.py            # RAG 流程编排
├── tools/
│   └── rag_tool.py               # Agent RAG 工具
├── routers/
│   └── rag.py                    # RAG API 路由
├── models/
│   ├── knowledge_base.py         # KnowledgeBase 模型
│   └── document.py               # Document 模型
└── schemas/
    └── rag.py                    # Pydantic schemas
```

## 实现顺序

### 阶段 1：基础设施
1. 创建数据库模型（KnowledgeBase, Document）
2. 创建 Embedding Service
3. 创建 KnowledgeBase Service

### 阶段 2：文档处理
4. 创建 Document Processor
5. 实现 PDF/DOCX/TXT 文本提取
6. 实现 URL 抓取（使用 httpx + BeautifulSoup）

### 阶段 3：API 和工具
7. 创建 RAG Router（API 接口）
8. 创建 RAG Tool（Agent 工具）
9. 在 main.py 注册 RAG Tool

### 阶段 4：集成
10. 修改 Conversation 模型，添加 knowledge_base_ids
11. 在 Agent 调用链中加载对话关联的 KB
12. 前端知识库管理界面

## 依赖

已在 pyproject.toml 中：
- `qdrant-client>=1.12.0`
- `sentence-transformers>=2.7.0`

需要额外添加：
- `beautifulsoup4>=4.12.0`（网页抓取）
- `pypdf>=4.0.0`（已有）
- `python-docx>=1.1.0`（已有）

## 注意事项

1. **模型路径**: 使用本地缓存路径 `/home/skdy/server/Aeris/models/all-MiniLM-L6-v2/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf`

2. **异步处理**: 文档处理可能是异步的（文件大、URL 抓取慢），需要使用任务队列或后台任务

3. **Qdrant Collection 命名**: 使用 `kb_{id}` 格式，如 `kb_1`、`kb_2`

4. **安全**: URL 抓取需要限制域名，防止 SSRF 攻击