import pytest
from meditatio.services.embedding_service import EmbeddingService

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


def test_embed_single_returns_list_not_nested():
    service = EmbeddingService(MODEL_PATH)
    result = service.embed_query("测试")
    # embed_query should return List[float], not List[List[float]]
    assert isinstance(result[0], float)
    assert len(result) == 384