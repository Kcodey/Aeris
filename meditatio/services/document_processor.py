import httpx
from bs4 import BeautifulSoup
from typing import List, Tuple
from pathlib import Path

from meditatio.services.embedding_service import EmbeddingService
from meditatio.services.knowledge_base_service import KnowledgeBaseService


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
        """处理文档：分块、向量化、存储chunk到PG，向量存Qdrant

        Returns:
            chunk_count
        """
        chunks = self.split_text(text)

        # 向量化
        vectors = self.embedding_service.embed_texts(chunks)

        # 构建元数据（不含content）
        qdrant_metadata = {
            "kb_id": kb_id,
            "kb_name": metadata.get("kb_name", ""),
            "source_type": metadata.get("source_type", "unknown"),
        }

        # 返回 chunks 和 vectors，后续由调用方存储到 PG 并插入 Qdrant
        return len(chunks)

    def get_chunk_content(self, text: str) -> List[str]:
        """获取文本分块结果（用于外部存储到 PG）"""
        return self.split_text(text)