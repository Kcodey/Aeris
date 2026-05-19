from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Optional, Dict, Any
import uuid

from meditatio.services.embedding_service import EmbeddingService


class SearchResult:
    """检索结果"""

    def __init__(
        self,
        kb_id: int,
        kb_name: str,
        document_id: int,
        chunk_id: int,
        score: float
    ):
        self.kb_id = kb_id
        self.kb_name = kb_name
        self.document_id = document_id
        self.chunk_id = chunk_id
        self.score = score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kb_id": self.kb_id,
            "kb_name": self.kb_name,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "score": self.score,
        }


class KnowledgeBaseService:
    """知识库服务，管理 Qdrant collection"""

    VECTOR_DIM = 384  # all-MiniLM-L6-v2 dimension

    def __init__(
        self,
        embedding_service: EmbeddingService,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333
    ):
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
        try:
            self.client.delete_collection(collection_name=collection_name)
        except Exception:
            pass  # Ignore if collection doesn't exist

    def upsert_vectors(
        self,
        collection_name: str,
        chunk_ids: List[int],  # DB chunk ids as Qdrant point ids
        vectors: List[List[float]],
        document_id: int,
        metadata: Dict[str, Any]
    ) -> None:
        """添加向量数据到 Qdrant

        Args:
            collection_name: Qdrant collection name
            chunk_ids: 数据库 chunk id 列表（作为 Qdrant point id）
            vectors: 向量列表
            document_id: 文档 id
            metadata: 包含 kb_id, kb_name 等
        """
        points = []
        for chunk_id, vector in zip(chunk_ids, vectors):
            point = PointStruct(
                id=chunk_id,  # 使用 DB chunk id 作为 Qdrant point id
                vector=vector,
                payload={
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    **metadata
                }
            )
            points.append(point)

        self.client.upsert(collection_name=collection_name, points=points)

    def search(
        self,
        collection_name: str,
        query: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """搜索单个 collection"""
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
                chunk_id=r.payload.get("chunk_id", 0),
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
                        chunk_id=r.payload.get("chunk_id", 0),
                        score=r.score
                    ))
            except Exception:
                continue

        # 按 score 排序
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:top_k]