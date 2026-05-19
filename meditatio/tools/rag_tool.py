from typing import Dict, Optional

from meditatio.tools.base import Tool, ToolParameter, ToolResult, get_tool_registry
from meditatio.services.embedding_service import EmbeddingService
from meditatio.services.knowledge_base_service import KnowledgeBaseService
from meditatio.database import async_session

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
            from meditatio.models.knowledge_base import KnowledgeBase

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

            # 从 PG 获取 chunk 内容
            chunk_ids = [r.chunk_id for r in results]
            chunks_map = {}
            if chunk_ids:
                async with async_session() as session:
                    from meditatio.models.chunk import Chunk
                    chunk_result = await session.execute(
                        select(Chunk).where(Chunk.id.in_(chunk_ids))
                    )
                    chunks_map = {c.id: c.content for c in chunk_result.scalars().all()}

            # 格式化结果为纯文本
            lines = [f"查询: {query}\n结果 ({len(results)} 条):\n"]
            for i, r in enumerate(results, 1):
                content = chunks_map.get(r.chunk_id, "").strip()
                lines.append(f"{i}. 【{r.kb_name}】(相关度: {round(r.score, 4)})\n{content}\n")

            return ToolResult(
                success=True,
                data={"text": "\n".join(lines)},
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