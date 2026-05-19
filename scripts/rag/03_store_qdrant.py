"""
RAG 测试 03: 存入 Qdrant

运行方式:
    python scripts/rag/03_store_qdrant.py
"""

import sys
sys.path.insert(0, "/home/skdy/server/Aeris")

import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import torch
import uuid

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_DIR = "/home/skdy/server/Aeris/models/all-MiniLM-L6-v2/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf"

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "test_rag"
VECTOR_DIM = 384  # all-MiniLM-L6-v2 输出维度


def load_model():
    """加载模型，自动使用 GPU"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")

    model = SentenceTransformer(MODEL_DIR, device=device)
    print("✅ Model 加载成功")
    return model, device


def embed_texts(texts: list[str], model) -> list[list[float]]:
    """批量文本向量化"""
    embeddings = model.encode(texts, show_progress_bar=True)
    return embeddings.tolist()


def split_text(text: str, max_chars: int = 500, overlap: int = 50) -> list[str]:
    """按字符数分块"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


def main():
    print("连接 Qdrant...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print("✅ 连接成功\n")

    # 删除旧 collection（如果存在）
    collections = client.get_collections().collections
    if COLLECTION_NAME in [c.name for c in collections]:
        print(f"删除旧 collection: {COLLECTION_NAME}")
        client.delete_collection(COLLECTION_NAME)

    # 创建新 collection
    print(f"创建 collection: {COLLECTION_NAME}")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)
    )
    print(f"✅ Collection 创建成功，维度: {VECTOR_DIM}\n")

    # 准备测试数据
    documents = [
        {
            "title": "人工智能简介",
            "content": "人工智能（AI）是计算机科学的一个分支，致力于开发能够执行通常需要人类智能的任务的系统。这包括视觉感知、语音识别、决策制定和语言翻译等。"
        },
        {
            "title": "机器学习",
            "content": "机器学习是人工智能的一个子集，专注于开发能够从数据中学习的算法。通过使用统计方法，机器学习系统能够从经验中改进性能。"
        },
        {
            "title": "深度学习",
            "content": "深度学习是机器学习的一个分支，使用多层神经网络来处理复杂模式。卷积神经网络（CNN）和循环神经网络（RNN）是深度学习的典型架构。"
        },
        {
            "title": "大语言模型",
            "content": "大语言模型（LLM）是近年来发展迅速的技术，如 GPT、BERT、Qwen 等模型在各种自然语言处理任务中表现出色。"
        },
    ]

    # 分块
    all_chunks = []
    for doc in documents:
        chunks = split_text(doc["content"], max_chars=100, overlap=20)
        for chunk in chunks:
            all_chunks.append({
                "text": chunk,
                "title": doc["title"],
                "content": doc["content"]
            })

    print(f"文档数量: {len(documents)}")
    print(f"分块数量: {len(all_chunks)}\n")

    # 向量化
    print("加载模型并向量化...")
    model, device = load_model()
    texts = [c["text"] for c in all_chunks]
    vectors = embed_texts(texts, model)
    print(f"✅ 向量化完成，向量维度: {len(vectors[0])}\n")

    # 存入 Qdrant
    print("存入 Qdrant...")
    points = []
    for i, (chunk, vector) in enumerate(zip(all_chunks, vectors)):
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "text": chunk["text"],
                "title": chunk["title"],
                "content": chunk["content"]
            }
        )
        points.append(point)

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    print(f"✅ 成功存入 {len(points)} 条数据到 {COLLECTION_NAME}")


if __name__ == "__main__":
    main()