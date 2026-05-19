from datetime import datetime
from typing import List, Optional
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc, delete, func

from meditatio.models.conversation import Conversation
from meditatio.models.message import Message
from meditatio.schemas.chat import ConversationCreate, ConversationUpdate, MessageCreate
from meditatio.services.agent_engine import AgentEngine, AgentContext, get_agent_engine
from meditatio.services.tokenizer import get_tokenizer


class ChatService:
    """Chat business logic service."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.agent_engine: AgentEngine = get_agent_engine()
        self.tokenizer = get_tokenizer()

    async def create_conversation(
        self,
        user_id: int,
        data: ConversationCreate,
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            user_id=user_id,
            title=data.title,
            knowledge_base_ids=json.dumps(data.knowledge_base_ids) if data.knowledge_base_ids else None,
        )
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get_conversation(
        self,
        user_id: int,
        conversation_id: int,
    ) -> Optional[Conversation]:
        """Get conversation by ID."""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Conversation]:
        """List user's conversations with last message preview."""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .where(Conversation.status == "active")
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        conversations = result.scalars().all()

        # Get last message preview for each conversation
        for conv in conversations:
            msg_result = await self.session.execute(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(desc(Message.created_at))
                .limit(1)
            )
            last_msg = msg_result.scalar_one_or_none()
            if last_msg:
                content = last_msg.content or ""
                # 截取前60字符作为预览
                if len(content) > 60:
                    content = content[:60] + "..."
                # 使用 object.__setattr__ 绕过 Pydantic 检查
                object.__setattr__(conv, 'last_message_preview', content)
            else:
                object.__setattr__(conv, 'last_message_preview', None)

        return conversations

    async def get_conversation_messages(
        self,
        conversation_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Message]:
        """Get messages in a conversation."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def send_message(
        self,
        user_id: int,
        conversation_id: int,
        content: str,
    ) -> dict:
        """
        Send a message and get AI response.

        1. Save user message
        2. Build conversation history
        3. Add RAG context if KBs associated
        4. Run agent
        5. Save AI response
        6. Return result
        """
        # Save user message
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )
        self.session.add(user_message)
        await self.session.commit()
        await self.session.refresh(user_message)

        # Get conversation history
        messages = await self.get_conversation_messages(conversation_id)

        # Build system prompt with available skills
        from meditatio.skills.registry import get_skill_registry
        from textwrap import dedent
        try:
            skills_registry = get_skill_registry()
            available_skills = skills_registry.describe_available()
        except RuntimeError:
            available_skills = "(no skills available)"

        system_content = dedent(f"""\
            You are a helpful AI assistant with access to specialized skills and bash execution.

            Available skills:
            {available_skills}

            Use the load_skill tool when a task needs specialized instructions before you act.

            When analyzing CSV or data files, use the bash tool to execute Python for real analysis:
            bash -c "cd /home/skdy/server/Aeris && python -c 'import pandas as pd; ...'"
        """).strip()

        # Add RAG context if conversation has associated knowledge bases
        rag_context = await self._get_rag_context(conversation_id, content)
        if rag_context:
            system_content += "\n\n" + rag_context

        # Build messages for LLM
        llm_messages = [
            {"role": "system", "content": system_content}
        ]
        for msg in messages:
            llm_messages.append({
                "role": msg.role,
                "content": msg.content or "",
            })

        # Run agent
        context = AgentContext(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=user_message.id,
            session=self.session,
        )

        result = await self.agent_engine.run(llm_messages, context)

        # Save AI response
        ai_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=result.content,
            input_tokens=result.usage["input_tokens"],
            output_tokens=result.usage["output_tokens"],
            tokens_estimated=False,  # SGLang returns actual usage
        )
        self.session.add(ai_message)
        await self.session.commit()
        await self.session.refresh(ai_message)

        # Update conversation updated_at
        conversation = await self.get_conversation(user_id, conversation_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()
            await self.session.commit()

        return {
            "user_message": user_message,
            "ai_message": ai_message,
            "usage": result.usage,
            "tool_calls": result.tool_calls_executed,
        }

    async def update_conversation(
        self,
        user_id: int,
        conversation_id: int,
        data: ConversationUpdate,
    ) -> Optional[Conversation]:
        """Update conversation title."""
        conversation = await self.get_conversation(user_id, conversation_id)
        if not conversation:
            return None

        if data.title is not None:
            conversation.title = data.title
            conversation.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def delete_conversation(
        self,
        user_id: int,
        conversation_id: int,
    ) -> bool:
        """Soft delete a conversation."""
        conversation = await self.get_conversation(user_id, conversation_id)
        if not conversation:
            return False

        conversation.status = "deleted"
        await self.session.commit()

        # Trigger cleanup if deleted count exceeds threshold
        await self._cleanup_deleted_conversations()
        return True

    async def _get_rag_context(self, conversation_id: int, user_message: str) -> str:
        """获取对话关联知识库的 RAG 检索结果作为上下文"""
        try:
            conversation = await self.get_conversation(None, conversation_id)
            if not conversation or not conversation.knowledge_base_ids:
                return ""

            kb_ids = json.loads(conversation.knowledge_base_ids)
            if not kb_ids:
                return ""

            # 获取知识库信息
            from meditatio.models.knowledge_base import KnowledgeBase
            from meditatio.services.embedding_service import EmbeddingService
            from meditatio.services.knowledge_base_service import KnowledgeBaseService

            EMBEDDING_MODEL_PATH = "/home/skdy/server/Aeris/models/all-MiniLM-L6-v2/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf"

            kb_result = await self.session.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.id.in_(kb_ids),
                    KnowledgeBase.is_active == True
                )
            )
            kbs = kb_result.scalars().all()
            if not kbs:
                return ""

            kb_infos = [
                {"kb_id": kb.id, "collection_name": kb.collection_name, "name": kb.name}
                for kb in kbs
            ]

            # 执行搜索
            embedding_service = EmbeddingService(EMBEDDING_MODEL_PATH)
            kb_service = KnowledgeBaseService(embedding_service)
            results = kb_service.search_multi(kb_infos=kb_infos, query=user_message, top_k=3)

            if not results:
                return ""

            # 构建上下文
            context = "\n\n--- 知识库检索结果 ---\n"
            for r in results:
                context += f"\n【{r.kb_name}】\n{r.content}\n"
            context += "\n--- 结束 ---\n\n"
            context += "请参考以上知识库检索结果回答用户问题。"

            return context

        except Exception as e:
            print(f"[ChatService] RAG context error: {e}")
            return ""

    async def _cleanup_deleted_conversations(self, threshold: int = 100, batch_size: int = 20):
        """
        Hard delete oldest soft-deleted conversations when count exceeds threshold.
        Also cascades to delete associated messages.
        """
        # Count soft-deleted conversations
        result = await self.session.execute(
            select(func.count(Conversation.id)).where(Conversation.status == "deleted")
        )
        deleted_count = result.scalar()

        if deleted_count <= threshold:
            return

        # Find oldest soft-deleted conversations to remove
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.status == "deleted")
            .order_by(Conversation.updated_at)
            .limit(batch_size)
        )
        to_delete = result.scalars().all()

        for conv in to_delete:
            # Delete associated messages first (no cascade on FK)
            await self.session.execute(
                delete(Message).where(Message.conversation_id == conv.id)
            )
            # Then delete conversation
            await self.session.delete(conv)

        await self.session.commit()
        print(f"Cleaned up {len(to_delete)} soft-deleted conversations")
