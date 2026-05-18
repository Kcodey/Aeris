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