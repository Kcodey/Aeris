# RAG 功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Meditatio 添加 RAG 功能，支持多知识库管理、文档上传/URL 抓取、对话关联知识库检索

**Architecture:** 采用服务层架构，Embedding Service 封装向量化，KnowledgeBase Service 管理 Qdrant，Document Processor 处理文档，RAG Tool 提供 Agent 接口

**Tech Stack:** FastAPI, SQLModel, Qdrant, sentence-transformers, BeautifulSoup4, pypdf, python-docx

---

## 文件结构

```
aeris/
├── models/
│   ├── knowledge_base.py     # 新增: KnowledgeBase 模型
│   └── document.py           # 新增: Document 模型
├── schemas/
│   └── rag.py               # 新增: RAG API schemas
├── services/
│   ├── embedding_service.py      # 新增: 向量化服务
│   ├── knowledge_base_service.py # 新增: 知识库服务
│   └── document_processor.py    # 新增: 文档处理服务
├── tools/
│   └── rag_tool.py          # 新增: RAG Agent 工具
├── routers/
│   └── rag.py               # 新增: RAG API 路由
└── main.py                  # 修改: 注册 RAG Tool
```

---

## Task 1: 创建数据库模型

**Files:**
- Create: `aeris/models/knowledge_base.py`
- Create: `aeris/models/document.py`
- Modify: `aeris/models/__init__.py`
- Test: `tests/test_models.py`（后续创建）

- [ ] **Step 1: 创建 KnowledgeBase 模型**

```python
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field

if TYPE_CHECKING:
    from aeris.models.document import Document

class KnowledgeBase(SQLModel, table=True):
    __tablename__ = "knowledge_bases"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=100)
    description: str = Field(default="", max_length=500)
    collection_name: str = Field(index=True, max_length=100)  # Qdrant collection 名
    is_active: bool = Field(default=True)
    created_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    documents: List["Document"] = Field(foreign_key="documents.knowledge_base_id")
```

- [ ] **Step 2: 创建 Document 模型**

```python
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field

if TYPE_CHECKING:
    from aeris.models.knowledge_base import KnowledgeBase

class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    knowledge_base_id: int = Field(foreign_key="knowledge_bases.id", index=True)
    title: str = Field(max_length=255)
    source_type: str = Field(max_length=20)  # "upload" or "url"
    source_path: str = Field(max_length=500)  # 文件路径或 URL
    status: str = Field(default="processing", max_length=20)  # processing/ready/failed
    chunk_count: int = Field(default=0)
    error_message: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    knowledge_base: Optional[KnowledgeBase] = Field(foreign_key="knowledge_bases.id")
```

- [ ] **Step 3: 修改 aeris/models/__init__.py**

```python
"""SQLModel database models."""

from aeris.models.base import TimestampMixin
from aeris.models.user import User
from aeris.models.conversation import Conversation
from aeris.models.message import Message
from aeris.models.scheduled_task import ScheduledTask
from aeris.models.file_record import FileRecord
from aeris.models.trace import LLMTrace
from aeris.models.skill_usage import SkillUsage
from aeris.models.knowledge_base import KnowledgeBase
from aeris.models.document import Document

__all__ = [
    "TimestampMixin",
    "User",
    "Conversation",
    "Message",
    "ScheduledTask",
    "FileRecord",
    "LLMTrace",
    "SkillUsage",
    "KnowledgeBase",
    "Document",
]
```

- [ ] **Step 4: 运行数据库迁移生成表**

Run: `alembic revision --autogenerate -m "add knowledge_base and document tables"`
Expected: 生成迁移文件

Run: `alembic upgrade head`
Expected: 执行迁移成功

- [ ] **Step 5: 提交**

```bash
git add aeris/models/knowledge_base.py aeris/models/document.py aeris/models/__init__.py
git add alembic/versions/*.py
git commit -m "feat: add KnowledgeBase and Document models"
```

---

## Task 2: 创建 Embedding Service

**Files:**
- Create: `aeris/services/embedding_service.py`
- Test: `tests/test_embedding_service.py`

- [ ] **Step 1: 创建测试文件 tests/test_embedding_service.py**

```python
import pytest
from aeris.services.embedding_service import EmbeddingService

MODEL_PATH = "/home/skdy/server/Aeris/models/all-MiniLM-L6-v2/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf"

def test_embed_texts():
    service = EmbeddingService(MODEL_PATH)
    texts = ["你好", "世界"]
    result = service.embed_texts(texts)
    assert len(result) == 2
    assert len(result[0]) == 384  # all-MiniLM-L6-v2 dimension

def test_embed_query():
    service = EmbeddingService(MODEL_PATH)
    result = service.embed_query("测试查询")
    assert len(result) == 384
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_embedding_service.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: 创建 aeris/services/embedding_service.py**

```python
from sentence_transformers import SentenceTransformer
import torch
from typing import List


class EmbeddingService:
    """向量化服务，封装 all-MiniLM-L6-v2 模型"""

    def __init__(self, model_path: str):
        """加载本地模型

        Args:
            model_path: 模型本地路径
        """
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.model = SentenceTransformer(model_path, device=device)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量向量化文本

        Args:
            texts: 文本列表

        Returns:
            向量列表，每个向量是 list[float]
        """
        embeddings = self.model.encode(texts, show_progress_bar=True)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """向量化单个查询

        Args:
            query: 查询文本

        Returns:
            向量，list[float]
        """
        embedding = self.model.encode([query], show_progress_bar=False)
        return embedding[0].tolist()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_embedding_service.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add aeris/services/embedding_service.py tests/test_embedding_service.py
git commit -m "feat: add EmbeddingService for all-MiniLM-L6-v2"
```

---

## Task 3: 创建 KnowledgeBase Service

**Files:**
- Create: `aeris/services/knowledge_base_service.py`
- Test: `tests/test_kb_service.py`

- [ ] **Step 1: 创建测试文件 tests/test_kb_service.py**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aeris.services.knowledge_base_service import KnowledgeBaseService, SearchResult

# 需要 mock Qdrant client

def test_search_result_structure():
    result = SearchResult(
        kb_id=1,
        kb_name="test",
        document_id=1,
        chunk_id="abc",
        content="test content",
        score=0.9
    )
    assert result.kb_id == 1
    assert result.score == 0.9
```

- [ ] **Step 2: 创建 aeris/services/knowledge_base_service.py**

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Optional, Dict, Any
import uuid

from aeris.services.embedding_service import EmbeddingService


class SearchResult:
    """检索结果"""

    def __init__(
        self,
        kb_id: int,
        kb_name: str,
        document_id: int,
        chunk_id: str,
        content: str,
        score: float
    ):
        self.kb_id = kb_id
        self.kb_name = kb_name
        self.document_id = document_id
        self.chunk_id = chunk_id
        self.content = content
        self.score = score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kb_id": self.kb_id,
            "kb_name": self.kb_name,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "content": self.content,
            "score": self.score,
        }


class KnowledgeBaseService:
    """知识库服务，管理 Qdrant collection"""

    VECTOR_DIM = 384  # all-MiniLM-L6-v2 dimension

    def __init__(self, embedding_service: EmbeddingService, qdrant_host: str = "localhost", qdrant_port: int = 6333):
        self.embedding_service = embedding_service
        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)

    def create_collection(self, collection_name: str) -> None:
        """创建 Qdrant collection"""
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=self.VECTOR_DIM, distance=Distance.COSINE)
        )

    def delete_collection(self, collection_name: str) -> None:
        """删除 Qdrant collection"""
        self.client.delete_collection(collection_name=collection_name)

    def upsert_vectors(
        self,
        collection_name: str,
        chunks: List[str],
        document_id: int,
        metadata: Dict[str, Any]
    ) -> List[str]:
        """添加向量数据

        Returns:
            chunk_id 列表
        """
        vectors = self.embedding_service.embed_texts(chunks)
        chunk_ids = []

        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            chunk_id = str(uuid.uuid4())
            chunk_ids.append(chunk_id)
            point = PointStruct(
                id=chunk_id,
                vector=vector,
                payload={
                    "content": chunk,
                    "document_id": document_id,
                    "chunk_index": i,
                    **metadata
                }
            )
            points.append(point)

        self.client.upsert(collection_name=collection_name, points=points)
        return chunk_ids

    def search(
        self,
        collection_name: str,
        query: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """搜索向量"""
        query_vector = self.embedding_service.embed_query(query)

        results = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k
        ).points

        return [
            SearchResult(
                kb_id=results[0].payload.get("kb_id", 0) if results else 0,
                kb_name=results[0].payload.get("kb_name", "") if results else "",
                document_id=r.payload.get("document_id", 0),
                chunk_id=r.id,
                content=r.payload.get("content", ""),
                score=r.score
            )
            for r in results
        ]

    def search_multi(
        self,
        kb_infos: List[Dict[str, Any]],
        query: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """在多个知识库中搜索

        Args:
            kb_infos: 知识库信息列表 [{"kb_id": 1, "collection_name": "kb_1", "name": "KB1"}, ...]
            query: 查询文本
            top_k: 每个 KB 返回的数量

        Returns:
            合并后的检索结果，按 score 排序
        """
        all_results = []
        query_vector = self.embedding_service.embed_query(query)

        for kb_info in kb_infos:
            try:
                results = self.client.query_points(
                    collection_name=kb_info["collection_name"],
                    query=query_vector,
                    limit=top_k
                ).points

                for r in results:
                    all_results.append(SearchResult(
                        kb_id=kb_info["kb_id"],
                        kb_name=kb_info["name"],
                        document_id=r.payload.get("document_id", 0),
                        chunk_id=r.id,
                        content=r.payload.get("content", ""),
                        score=r.score
                    ))
            except Exception:
                continue

        # 按 score 排序
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:top_k]
```

- [ ] **Step 3: 运行测试**

Run: `pytest tests/test_kb_service.py -v`
Expected: PASS (或需要 mock Qdrant)

- [ ] **Step 4: 提交**

```bash
git add aeris/services/knowledge_base_service.py tests/test_kb_service.py
git commit -m "feat: add KnowledgeBaseService for Qdrant operations"
```

---

## Task 4: 创建 Document Processor

**Files:**
- Create: `aeris/services/document_processor.py`
- Modify: `aeris/services/__init__.py`

- [ ] **Step 1: 创建 aeris/services/document_processor.py**

```python
import httpx
from bs4 import BeautifulSoup
from typing import List, Tuple
from pathlib import Path

from aeris.services.embedding_service import EmbeddingService
from aeris.services.knowledge_base_service import KnowledgeBaseService


class DocumentProcessor:
    """文档处理服务：提取文本、分块、向量化、存储"""

    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50

    def __init__(
        self,
        embedding_service: EmbeddingService,
        kb_service: KnowledgeBaseService
    ):
        self.embedding_service = embedding_service
        self.kb_service = kb_service

    def extract_text_from_file(self, file_path: str, file_type: str) -> str:
        """从文件提取文本

        Args:
            file_path: 文件路径
            file_type: 文件类型 (pdf, docx, txt)
        """
        if file_type == "pdf":
            return self._extract_pdf(file_path)
        elif file_type == "docx":
            return self._extract_docx(file_path)
        elif file_type == "txt":
            return self._extract_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _extract_pdf(self, file_path: str) -> str:
        """提取 PDF 文本"""
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    def _extract_docx(self, file_path: str) -> str:
        """提取 DOCX 文本"""
        from docx import Document
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])

    def _extract_txt(self, file_path: str) -> str:
        """提取 TXT 文本"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def extract_text_from_url(self, url: str) -> Tuple[str, str]:
        """从 URL 提取文本

        Returns:
            (title, content)
        """
        headers = {"User-Agent": "Mozilla/5.0"}
        response = httpx.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # 提取 title
        title = soup.title.string if soup.title else url

        # 移除 script 和 style 标签
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        # 提取正文（简单策略：取 body 内的文本）
        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # 清理多余空行
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return title, "\n".join(lines)

    def split_text(self, text: str) -> List[str]:
        """按字符数分块"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.CHUNK_SIZE
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.CHUNK_OVERLAP
        return chunks

    async def process_document(
        self,
        text: str,
        title: str,
        kb_id: int,
        collection_name: str,
        document_id: int,
        metadata: dict
    ) -> int:
        """处理文档：分块、向量化、存储

        Returns:
            chunk_count
        """
        chunks = self.split_text(text)

        # 添加元数据
        chunk_metadata = {
            "kb_id": kb_id,
            "kb_name": metadata.get("kb_name", ""),
            "document_title": title,
            "source_type": metadata.get("source_type", "unknown"),
            "source_path": metadata.get("source_path", ""),
        }

        self.kb_service.upsert_vectors(
            collection_name=collection_name,
            chunks=chunks,
            document_id=document_id,
            metadata=chunk_metadata
        )

        return len(chunks)
```

- [ ] **Step 2: 修改 aeris/services/__init__.py**

```python
"""Services module."""

from aeris.services.embedding_service import EmbeddingService
from aeris.services.knowledge_base_service import KnowledgeBaseService
from aeris.services.document_processor import DocumentProcessor

__all__ = [
    "EmbeddingService",
    "KnowledgeBaseService",
    "DocumentProcessor",
]
```

- [ ] **Step 3: 提交**

```bash
git add aeris/services/document_processor.py aeris/services/__init__.py
git commit -m "feat: add DocumentProcessor for file/URL extraction and chunking"
```

---

## Task 5: 创建 RAG Pydantic Schemas

**Files:**
- Create: `aeris/schemas/rag.py`
- Modify: `aeris/schemas/__init__.py`

- [ ] **Step 1: 创建 aeris/schemas/rag.py**

```python
from typing import Optional, List
from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., max_length=100)
    description: str = Field(default="", max_length=500)


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    id: int
    name: str
    description: str
    collection_name: str
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    id: int
    knowledge_base_id: int
    title: str
    source_type: str
    source_path: str
    status: str
    created_at: str


class URLFetchRequest(BaseModel):
    """URL 抓取请求"""
    url: str = Field(..., max_length=500)


class URLFetchResponse(BaseModel):
    """URL 抓取响应"""
    id: int
    knowledge_base_id: int
    title: str
    source_type: str
    source_path: str
    status: str
    created_at: str


class DocumentStatusResponse(BaseModel):
    """文档状态响应"""
    id: int
    status: str
    chunk_count: int
    error_message: Optional[str] = None


class SearchRequest(BaseModel):
    """检索请求"""
    knowledge_base_ids: Optional[List[int]] = None
    query: str = Field(..., max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResultItem(BaseModel):
    """检索结果项"""
    kb_id: int
    kb_name: str
    document_id: int
    chunk_id: str
    content: str
    score: float


class SearchResponse(BaseModel):
    """检索响应"""
    results: List[SearchResultItem]
```

- [ ] **Step 2: 修改 aeris/schemas/__init__.py**

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
from aeris.schemas.rag import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    DocumentUploadResponse,
    URLFetchRequest,
    URLFetchResponse,
    DocumentStatusResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
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
    "KnowledgeBaseCreate",
    "KnowledgeBaseResponse",
    "DocumentUploadResponse",
    "URLFetchRequest",
    "URLFetchResponse",
    "DocumentStatusResponse",
    "SearchRequest",
    "SearchResponse",
    "SearchResultItem",
]
```

- [ ] **Step 3: 提交**

```bash
git add aeris/schemas/rag.py aeris/schemas/__init__.py
git commit -m "feat: add RAG Pydantic schemas"
```

---

## Task 6: 创建 RAG Router (API)

**Files:**
- Create: `aeris/routers/rag.py`
- Modify: `aeris/routers/__init__.py`

- [ ] **Step 1: 创建 aeris/routers/rag.py**

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
import aiofiles
from pathlib import Path

from aeris.database import get_session
from aeris.schemas.rag import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    DocumentUploadResponse,
    URLFetchRequest,
    URLFetchResponse,
    DocumentStatusResponse,
    SearchRequest,
    SearchResponse,
)
from aeris.models.knowledge_base import KnowledgeBase
from aeris.models.document import Document
from aeris.services.embedding_service import EmbeddingService
from aeris.services.knowledge_base_service import KnowledgeBaseService
from aeris.services.document_processor import DocumentProcessor
from aeris.utils.security import get_current_user_id

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])

# 全局服务实例（后续可改为依赖注入）
EMBEDDING_MODEL_PATH = "/home/skdy/server/Aeris/models/all-MiniLM-L6-v2/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
UPLOAD_DIR = Path("/home/skdy/server/Aeris/uploads/rag")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_embedding_service: EmbeddingService = None
_kb_service: KnowledgeBaseService = None
_doc_processor: DocumentProcessor = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(EMBEDDING_MODEL_PATH)
    return _embedding_service


def get_kb_service() -> KnowledgeBaseService:
    global _kb_service
    if _kb_service is None:
        _kb_service = KnowledgeBaseService(get_embedding_service())
    return _kb_service


def get_doc_processor() -> DocumentProcessor:
    global _doc_processor
    if _doc_processor is None:
        _doc_processor = DocumentProcessor(get_embedding_service(), get_kb_service())
    return _doc_processor


# === 知识库管理 ===

@router.get("/kb", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases(
    session: AsyncSession = Depends(get_session),
):
    """列出所有启用的知识库"""
    from sqlmodel import select
    result = await session.execute(
        select(KnowledgeBase).where(KnowledgeBase.is_active == True)
    )
    kbs = result.scalars().all()
    return kbs


@router.post("/kb", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """创建新知识库（管理员）"""
    from aeris.models.user import User

    # 检查用户是否为管理员
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    # 检查名称是否已存在
    existing = await session.execute(
        select(KnowledgeBase).where(KnowledgeBase.name == kb_data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Name already exists")

    # 创建 collection
    kb = KnowledgeBase(
        name=kb_data.name,
        description=kb_data.description,
        collection_name=f"kb_{uuid.uuid4().hex[:8]}",
        created_by=user_id,
    )
    session.add(kb)
    await session.commit()
    await session.refresh(kb)

    # 创建 Qdrant collection
    try:
        get_kb_service().create_collection(kb.collection_name)
    except Exception as e:
        await session.delete(kb)
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {e}")

    return kb


@router.delete("/kb/{kb_id}")
async def delete_knowledge_base(
    kb_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """删除知识库（管理员）"""
    from aeris.models.user import User

    # 检查用户是否为管理员
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    # 获取知识库
    result = await session.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # 删除 Qdrant collection
    try:
        get_kb_service().delete_collection(kb.collection_name)
    except Exception:
        pass

    # 软删除知识库
    kb.is_active = False
    await session.commit()

    return {"message": "Deleted"}


# === 文档管理 ===

@router.post("/kb/{kb_id}/documents", response_model=DocumentUploadResponse)
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """上传文档到知识库"""
    # 获取知识库
    result = await session.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.is_active == True)
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # 保存文件
    file_ext = file.filename.split(".")[-1].lower()
    file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}.{file_ext}"
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # 创建文档记录
    doc = Document(
        knowledge_base_id=kb_id,
        title=file.filename,
        source_type="upload",
        source_path=str(file_path),
        status="processing",
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    # 后台处理（简化：同步处理）
    try:
        processor = get_doc_processor()
        text = processor.extract_text_from_file(str(file_path), file_ext)
        chunk_count = await processor.process_document(
            text=text,
            title=file.filename,
            kb_id=kb_id,
            collection_name=kb.collection_name,
            document_id=doc.id,
            metadata={
                "kb_name": kb.name,
                "source_type": "upload",
                "source_path": str(file_path),
            }
        )
        doc.status = "ready"
        doc.chunk_count = chunk_count
    except Exception as e:
        doc.status = "failed"
        doc.error_message = str(e)

    await session.commit()
    await session.refresh(doc)

    return doc


@router.post("/kb/{kb_id}/url", response_model=URLFetchResponse)
async def fetch_url(
    kb_id: int,
    url_data: URLFetchRequest,
    session: AsyncSession = Depends(get_session),
):
    """从 URL 抓取内容到知识库"""
    # 获取知识库
    result = await session.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.is_active == True)
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # 创建文档记录
    doc = Document(
        knowledge_base_id=kb_id,
        title=url_data.url,
        source_type="url",
        source_path=url_data.url,
        status="processing",
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    # 处理 URL
    try:
        processor = get_doc_processor()
        title, text = processor.extract_text_from_url(url_data.url)
        doc.title = title
        chunk_count = await processor.process_document(
            text=text,
            title=title,
            kb_id=kb_id,
            collection_name=kb.collection_name,
            document_id=doc.id,
            metadata={
                "kb_name": kb.name,
                "source_type": "url",
                "source_path": url_data.url,
            }
        )
        doc.status = "ready"
        doc.chunk_count = chunk_count
    except Exception as e:
        doc.status = "failed"
        doc.error_message = str(e)

    await session.commit()
    await session.refresh(doc)

    return doc


@router.get("/kb/{kb_id}/documents", response_model=List[DocumentUploadResponse])
async def list_documents(
    kb_id: int,
    session: AsyncSession = Depends(get_session),
):
    """列出知识库中的文档"""
    result = await session.execute(
        select(Document).where(Document.knowledge_base_id == kb_id)
    )
    return result.scalars().all()


@router.get("/kb/{kb_id}/documents/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    kb_id: int,
    doc_id: int,
    session: AsyncSession = Depends(get_session),
):
    """获取文档处理状态"""
    result = await session.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.knowledge_base_id == kb_id
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentStatusResponse(
        id=doc.id,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
    )


# === 检索 ===

@router.post("/search", response_model=SearchResponse)
async def search_knowledge_bases(
    search_data: SearchRequest,
    session: AsyncSession = Depends(get_session),
):
    """检索知识库（Agent 调用）"""
    kb_infos = []

    if search_data.knowledge_base_ids:
        # 指定了 KB
        result = await session.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id.in_(search_data.knowledge_base_ids),
                KnowledgeBase.is_active == True
            )
        )
    else:
        # 所有 KB
        result = await session.execute(
            select(KnowledgeBase).where(KnowledgeBase.is_active == True)
        )

    kbs = result.scalars().all()
    kb_infos = [
        {"kb_id": kb.id, "collection_name": kb.collection_name, "name": kb.name}
        for kb in kbs
    ]

    if not kb_infos:
        return SearchResponse(results=[])

    # 执行搜索
    kb_service = get_kb_service()
    results = kb_service.search_multi(
        kb_infos=kb_infos,
        query=search_data.query,
        top_k=search_data.top_k
    )

    return SearchResponse(results=[r.to_dict() for r in results])
```

- [ ] **Step 2: 修改 aeris/routers/__init__.py**

```python
"""API routers."""

from aeris.routers import auth, health, chat, ws, files, tasks, monitoring, timing_admin, skill_usage, rag

__all__ = [
    "auth",
    "health",
    "chat",
    "ws",
    "files",
    "tasks",
    "monitoring",
    "timing_admin",
    "skill_usage",
    "rag",
]
```

- [ ] **Step 3: 在 main.py 中注册路由**

修改 `aeris/main.py`，在 routers 列表中添加 `rag`

```python
from aeris.routers import auth, health, chat, ws, files, tasks, monitoring, timing_admin, skill_usage, rag
```

```python
app.include_router(rag.router, prefix="/api/v1")
```

- [ ] **Step 4: 提交**

```bash
git add aeris/routers/rag.py aeris/routers/__init__.py aeris/main.py
git commit -m "feat: add RAG API router with KB and document management"
```

---

## Task 7: 创建 RAG Tool (Agent 工具)

**Files:**
- Create: `aeris/tools/rag_tool.py`
- Modify: `aeris/main.py`

- [ ] **Step 1: 创建 aeris/tools/rag_tool.py**

```python
from typing import Dict, List, Optional

from aeris.tools.base import Tool, ToolParameter, ToolResult, get_tool_registry
from aeris.services.embedding_service import EmbeddingService
from aeris.services.knowledge_base_service import KnowledgeBaseService
from aeris.database import async_session

EMBEDDING_MODEL_PATH = "/home/skdy/server/Aeris/models/all-MiniLM-L6-v2/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf"

# 全局服务实例
_embedding_service: EmbeddingService = None
_kb_service: KnowledgeBaseService = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(EMBEDDING_MODEL_PATH)
    return _embedding_service


def get_kb_service() -> KnowledgeBaseService:
    global _kb_service
    if _kb_service is None:
        _kb_service = KnowledgeBaseService(get_embedding_service())
    return _kb_service


class RAGSearchTool(Tool):
    """RAG 检索工具"""

    name = "rag_search"
    description = (
        "Search knowledge bases for relevant information. "
        "Use this when user asks about product docs, manuals, FAQs, or specific knowledge stored in knowledge bases. "
        "Returns relevant content chunks with similarity scores."
    )

    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="Search query in Chinese or English",
            required=True,
        ),
        ToolParameter(
            name="knowledge_base_ids",
            type="string",
            description="Comma-separated knowledge base IDs to search (e.g., '1,2'). If not provided, searches all knowledge bases.",
            required=False,
        ),
        ToolParameter(
            name="top_k",
            type="integer",
            description="Number of results to return (default: 3)",
            required=False,
        ),
    ]

    async def execute(
        self,
        query: str,
        knowledge_base_ids: Optional[str] = None,
        top_k: int = 3,
        _context: Dict = None,
    ) -> ToolResult:
        """执行知识库检索"""
        try:
            from sqlmodel import select
            from aeris.models.knowledge_base import KnowledgeBase

            # 解析 KB IDs
            kb_ids = None
            if knowledge_base_ids:
                try:
                    kb_ids = [int(kbid.strip()) for kbid in knowledge_base_ids.split(",")]
                except ValueError:
                    return ToolResult(
                        success=False,
                        data=None,
                        error="Invalid knowledge_base_ids format. Use comma-separated integers."
                    )

            # 获取知识库信息
            async with async_session() as session:
                if kb_ids:
                    result = await session.execute(
                        select(KnowledgeBase).where(
                            KnowledgeBase.id.in_(kb_ids),
                            KnowledgeBase.is_active == True
                        )
                    )
                else:
                    result = await session.execute(
                        select(KnowledgeBase).where(KnowledgeBase.is_active == True)
                    )
                kbs = result.scalars().all()

            if not kbs:
                return ToolResult(
                    success=True,
                    data={"results": [], "message": "No knowledge bases available"},
                )

            kb_infos = [
                {"kb_id": kb.id, "collection_name": kb.collection_name, "name": kb.name}
                for kb in kbs
            ]

            # 执行搜索
            kb_service = get_kb_service()
            results = kb_service.search_multi(
                kb_infos=kb_infos,
                query=query,
                top_k=top_k
            )

            # 格式化结果
            formatted_results = []
            for r in results:
                formatted_results.append({
                    "kb_name": r.kb_name,
                    "content": r.content,
                    "score": round(r.score, 4),
                })

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": formatted_results,
                    "total": len(formatted_results),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"RAG search failed: {str(e)}"
            )


def register_rag_tool(registry):
    """注册 RAG 工具"""
    registry.register(RAGSearchTool())
```

- [ ] **Step 2: 在 main.py 中注册工具**

修改 `aeris/main.py`:
```python
from aeris.tools.rag_tool import register_rag_tool
```

在工具注册部分添加:
```python
register_rag_tool(registry)
```

- [ ] **Step 3: 提交**

```bash
git add aeris/tools/rag_tool.py aeris/main.py
git commit -m "feat: add RAG search tool for agent"
```

---

## Task 8: 修改 Conversation 模型支持知识库关联

**Files:**
- Modify: `aeris/models/conversation.py`
- Modify: `aeris/routers/chat.py`（处理创建对话时的 KB 关联）

- [ ] **Step 1: 修改 aeris/models/conversation.py**

在 Conversation 模型中添加 `knowledge_base_ids` 字段

```python
from typing import Optional, List
from sqlmodel import Field

class Conversation(SQLModel, table=True):
    # ... 现有字段 ...

    # 新增字段
    knowledge_base_ids: Optional[str] = Field(default=None, max_length=500)  # JSON 格式，如 "[1, 2]"
```

- [ ] **Step 2: 生成数据库迁移**

Run: `alembic revision --autogenerate -m "add knowledge_base_ids to conversation"`
Run: `alembic upgrade head`

- [ ] **Step 3: 修改 aeris/schemas/chat.py 的 ConversationCreate**

```python
class ConversationCreate(BaseModel):
    name: str = Field(default="New Chat", max_length=100)
    provider_name: Optional[str] = Field(default="default")
    knowledge_base_ids: Optional[List[int]] = Field(default=None)  # 新增
```

- [ ] **Step 4: 修改创建对话逻辑**

在 `aeris/routers/chat.py` 的 `create_conversation` 函数中，处理 `knowledge_base_ids`:
```python
import json

# conversation 创建时
if conversation_data.knowledge_base_ids:
    conversation.knowledge_base_ids = json.dumps(conversation_data.knowledge_base_ids)
```

- [ ] **Step 5: 提交**

```bash
git add aeris/models/conversation.py aeris/schemas/chat.py aeris/routers/chat.py
git add alembic/versions/*.py
git commit -m "feat: add knowledge_base_ids to conversation model"
```

---

## Task 9: 在 Agent 调用链中加载对话关联的知识库

**Files:**
- Modify: `aeris/services/chat_service.py`
- Modify: `aeris/tools/rag_tool.py`

- [ ] **Step 1: 修改 chat_service.py 的 get_conversation_context 方法**

在构建 LLM 消息时，如果对话关联了知识库，先执行 RAG 检索并添加上下文:

```python
async def _add_rag_context(self, conversation_id: int, user_message: str) -> str:
    """添加 RAG 检索结果到上下文"""
    from aeris.models.conversation import Conversation
    from sqlmodel import select
    import json

    async with self.session() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation or not conversation.knowledge_base_ids:
            return ""

        kb_ids = json.loads(conversation.knowledge_base_ids)

        if not kb_ids:
            return ""

        # 调用 RAG 搜索
        kb_service = get_kb_service()
        from aeris.models.knowledge_base import KnowledgeBase

        kb_infos = []
        for kb_id in kb_ids:
            result = await session.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.id == kb_id,
                    KnowledgeBase.is_active == True
                )
            )
            kb = result.scalar_one_or_none()
            if kb:
                kb_infos.append({
                    "kb_id": kb.id,
                    "collection_name": kb.collection_name,
                    "name": kb.name
                })

        if not kb_infos:
            return ""

        results = kb_service.search_multi(
            kb_infos=kb_infos,
            query=user_message,
            top_k=3
        )

        if not results:
            return ""

        context = "\n\n--- 知识库检索结果 ---\n"
        for r in results:
            context += f"\n[{r.kb_name}]\n{r.content}\n"
        context += "\n--- 结束 ---\n\n"

        return context
```

- [ ] **Step 2: 在 chat_service.py 中使用 RAG 上下文**

在 `chat` 方法中，对话消息进入 Agent 前调用 `_add_rag_context`:

```python
# 在构建 messages 之前添加 RAG 上下文
rag_context = await self._add_rag_context(conversation_id, request.message)
if rag_context:
    # 在 user message 前插入系统上下文
    messages.insert(0, {
        "role": "system",
        "content": f"以下是知识库中检索到的相关信息，请参考回答：\n{rag_context}"
    })
```

- [ ] **Step 3: 提交**

```bash
git add aeris/services/chat_service.py
git commit -m "feat: integrate RAG context into chat service"
```

---

## Task 10: 前端知识库管理界面（可选，后端已完成）

**Files:**
- Create: `frontend/src/pages/Rag.tsx`
- Modify: `frontend/src/App.tsx`（添加路由）

此任务为可选的 UI 工作，后端 API 已完整。如需要前端界面，再单独处理。

---

## 依赖更新

如果 beautifulsoup4 未在 pyproject.toml 中，添加：

```toml
beautifulsoup4>=4.12.0
```

Run: `pip install beautifulsoup4`

---

## 验证方式

### 1. 启动 Qdrant
```bash
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### 2. 启动应用
```bash
conda activate meditatio
python run.py
```

### 3. 创建知识库（管理员）
```bash
curl -X POST http://localhost:8000/api/v1/rag/kb \
  -H "Content-Type: application/json" \
  -d '{"name": "产品文档", "description": "产品相关文档"}'
```

### 4. 上传文档
```bash
curl -X POST http://localhost:8000/api/v1/rag/kb/1/documents \
  -F "file=@/path/to/document.pdf"
```

### 5. 抓取 URL
```bash
curl -X POST http://localhost:8000/api/v1/rag/kb/1/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/doc"}'
```

### 6. 测试检索
```bash
curl -X POST http://localhost:8000/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "你的问题", "top_k": 3}'
```

### 7. 对话中测试
在对话创建时指定 `knowledge_base_ids: [1]`，然后问一个 KB 中有的问题，看 Agent 是否能正确引用知识库内容。