"""
RAG 测试 04: 查询 Qdrant + PostgreSQL

新的检索架构:
1. Qdrant 存储: id(=chunk_db_id), vector, payload(kb_id, kb_name, document_id, chunk_id)
2. PostgreSQL chunks 表存储: id, document_id, content, chunk_index

运行方式:
    python scripts/rag/04_search_qdrant.py
"""
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import sys
sys.path.insert(0, "/home/skdy/server/Aeris")

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
import torch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

from aeris.models.chunk import Chunk

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_DIR = "/home/skdy/server/Aeris/models/all-MiniLM-L6-v2/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf"

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "kb_011eeff2"

# PostgreSQL 连接
POSTGRES_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/aeris"


def load_model():
    """加载模型，自动使用 GPU"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")

    model = SentenceTransformer(MODEL_DIR, device=device)
    print("✅ Model 加载成功")
    return model, device


def embed_query(query: str, model, device: str = "cpu") -> list[float]:
    """查询向量化"""
    embedding = model.encode([query], show_progress_bar=False)
    return embedding[0].tolist()


# 同步 PostgreSQL 连接（用于测试脚本）
SYNC_POSTGRES_URL = "postgresql://skdy:skdy@localhost:5432/meditatio"
sync_engine = create_engine(SYNC_POSTGRES_URL, echo=False)
SyncSessionLocal = sessionmaker(bind=sync_engine)


def get_chunk_contents(chunk_ids: list[int]) -> dict[int, str]:
    """从 PostgreSQL 获取 chunk 内容（同步版本）"""
    with SyncSessionLocal() as session:
        result = session.execute(
            select(Chunk).where(Chunk.id.in_(chunk_ids))
        )
        chunks = result.scalars().all()
        return {c.id: c.content for c in chunks}


def main():
    print("连接 Qdrant...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print("✅ 连接成功\n")

    # 检查 collection 是否存在
    collections = client.get_collections().collections
    if COLLECTION_NAME not in [c.name for c in collections]:
        print(f"❌ Collection '{COLLECTION_NAME}' 不存在，请先运行 03_store_qdrant.py")
        return

    # 加载模型
    print("加载 embedding 模型...")
    model, device = load_model()
    print("✅ 模型加载完成\n")

    # 查询
    queries = [
        "什么是人工智能？",
        "时空道宇公司",
    ]

    for query in queries:
        print(f"\n{'='*50}")
        print(f"查询: {query}")
        print(f"{'='*50}")

        # 向量化查询
        query_vector = embed_query(query, model, device)

        # 搜索 Qdrant
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=3
        ).points

        if not results:
            print("未找到相关结果")
            continue

        # 获取 chunk_ids
        chunk_ids = [r.payload.get("chunk_id", 0) for r in results]
        print(f"\n从 Qdrant 获取到 {len(results)} 条结果")
        print(f"Chunk IDs: {chunk_ids}")

        # 从 PostgreSQL 获取内容
        chunks_map = get_chunk_contents(chunk_ids)
        print(f"从 PG 获取到 {len(chunks_map)} 条内容\n")

        # 输出结果
        print(f"找到 {len(results)} 条相关结果:\n")
        for i, result in enumerate(results, 1):
            chunk_id = result.payload.get("chunk_id", 0)
            content = chunks_map.get(chunk_id, "N/A")
            print(f"结果 {i}:")
            print(f"  相似度分数: {result.score:.4f}")
            print(f"  KB ID: {result.payload.get('kb_id', 'N/A')}")
            print(f"  KB Name: {result.payload.get('kb_name', 'N/A')}")
            print(f"  Document ID: {result.payload.get('document_id', 'N/A')}")
            print(f"  Chunk ID: {chunk_id}")
            print(f"  内容: {content[:200]}..." if len(content) > 200 else f"  内容: {content}")
            print()


if __name__ == "__main__":
    main()