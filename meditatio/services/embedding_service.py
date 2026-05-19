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
        print(f"[EmbeddingService] Using device: {device}")
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