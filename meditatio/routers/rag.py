from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
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
from aeris.routers.auth import get_current_user, TokenData

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])

# 全局配置
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
    current_user: TokenData = Depends(get_current_user),
):
    """创建新知识库（管理员）"""
    from aeris.models.user import User

    # 检查用户是否为管理员
    user_result = await session.execute(select(User).where(User.id == current_user.user_id))
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
        created_by=current_user.user_id,
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
    current_user: TokenData = Depends(get_current_user),
):
    """删除知识库（管理员）"""
    from aeris.models.user import User

    # 检查用户是否为管理员
    user_result = await session.execute(select(User).where(User.id == current_user.user_id))
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
    from aeris.models.chunk import Chunk

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

    # 处理文档
    try:
        processor = get_doc_processor()
        text = processor.extract_text_from_file(str(file_path), file_ext)
        chunks = processor.get_chunk_content(text)

        # 1. 存储 chunks 到 PG
        chunk_db_ids = []
        for i, chunk_text in enumerate(chunks):
            chunk = Chunk(
                document_id=doc.id,
                content=chunk_text,
                chunk_index=i,
            )
            session.add(chunk)
            await session.flush()  # 获取 id
            chunk_db_ids.append(chunk.id)

        # 2. 向量化并存储到 Qdrant
        vectors = processor.embedding_service.embed_texts(chunks)
        kb_service = get_kb_service()
        kb_service.upsert_vectors(
            collection_name=kb.collection_name,
            chunk_ids=chunk_db_ids,
            vectors=vectors,
            document_id=doc.id,
            metadata={
                "kb_id": kb_id,
                "kb_name": kb.name,
                "source_type": "upload",
            }
        )

        doc.status = "ready"
        doc.chunk_count = len(chunks)
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
        from aeris.models.chunk import Chunk

        processor = get_doc_processor()
        title, text = processor.extract_text_from_url(url_data.url)
        doc.title = title
        chunks = processor.get_chunk_content(text)

        # 1. 存储 chunks 到 PG
        chunk_db_ids = []
        for i, chunk_text in enumerate(chunks):
            chunk = Chunk(
                document_id=doc.id,
                content=chunk_text,
                chunk_index=i,
            )
            session.add(chunk)
            await session.flush()  # 获取 id
            chunk_db_ids.append(chunk.id)

        # 2. 向量化并存储到 Qdrant
        vectors = processor.embedding_service.embed_texts(chunks)
        kb_service = get_kb_service()
        kb_service.upsert_vectors(
            collection_name=kb.collection_name,
            chunk_ids=chunk_db_ids,
            vectors=vectors,
            document_id=doc.id,
            metadata={
                "kb_id": kb_id,
                "kb_name": kb.name,
                "source_type": "url",
            }
        )

        doc.status = "ready"
        doc.chunk_count = len(chunks)
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
    """检索知识库"""
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

    # 执行搜索（只返回 chunk_id 和 score）
    kb_service = get_kb_service()
    results = kb_service.search_multi(
        kb_infos=kb_infos,
        query=search_data.query,
        top_k=search_data.top_k
    )

    # 从 PG 获取 chunk 内容
    chunk_ids = [r.chunk_id for r in results]
    if chunk_ids:
        from aeris.models.chunk import Chunk
        chunk_result = await session.execute(
            select(Chunk).where(Chunk.id.in_(chunk_ids))
        )
        chunks_map = {c.id: c.content for c in chunk_result.scalars().all()}
    else:
        chunks_map = {}

    # 组装结果
    enriched_results = []
    for r in results:
        result_dict = r.to_dict()
        result_dict["content"] = chunks_map.get(r.chunk_id, "")
        enriched_results.append(result_dict)

    return SearchResponse(results=enriched_results)