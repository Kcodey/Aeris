"""
生成模拟数据用于 Agent 数据分析测试。
运行方式: python scripts/generate_demo_data.py
"""
import asyncio
import random
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

# 添加项目根目录到 path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from aeris.models.user import User
from aeris.models.conversation import Conversation
from aeris.models.message import Message
from aeris.models.trace import LLMTrace
from aeris.models.skill_usage import SkillUsage
from aeris.utils.security import get_password_hash


DATABASE_URL = "sqlite+aiosqlite:///./aeris.db"


async def generate_data():
    """生成演示数据"""
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 创建测试用户
        users = []
        for i in range(5):
            user = User(
                username=f"testuser{i+1}",
                hashed_password=get_password_hash("password123"),
                is_active=True,
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 90)),
            )
            session.add(user)
            users.append(user)

        await session.commit()

        # 为每个用户创建会话和消息
        providers = ["anthropic", "openai", "azure"]
        models = {
            "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
            "openai": ["gpt-4o", "gpt-4-turbo"],
            "azure": ["gpt-4o-2024-05-13", "gpt-4-turbo-2024-04-09"],
        }
        skills = ["data-analysis", "brainstorming", "sql", "writing-plans", "systematic-debugging"]
        skill_success = [True, True, True, False, True, True, True]  # 权重偏向成功

        all_traces = []
        all_skill_usages = []

        for user in users:
            # 每个用户 2-5 个会话
            num_conversations = random.randint(2, 5)
            for conv_idx in range(num_conversations):
                conv = Conversation(
                    user_id=user.id,
                    title=f"数据分析会话 {conv_idx + 1}",
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                )
                session.add(conv)
                await session.flush()

                # 每个会话 5-15 条消息
                num_messages = random.randint(5, 15)
                for msg_idx in range(num_messages):
                    role = random.choice(["user", "assistant"])
                    content = f"这是一条{role}消息，内容涉及数据分析、指标监控等主题。" if role == "user" else f"根据分析结果，建议关注以下指标：DAU、转化率、留存率等关键数据。"

                    msg = Message(
                        conversation_id=conv.id,
                        role=role,
                        content=content,
                        created_at=conv.created_at + timedelta(minutes=msg_idx * random.randint(2, 10)),
                    )
                    session.add(msg)
                    await session.flush()

                    # 约 70% 的 assistant 消息生成 trace
                    if role == "assistant" and random.random() < 0.7:
                        provider = random.choice(providers)
                        model = random.choice(models[provider])

                        trace = LLMTrace(
                            trace_id=f"trace_{user.id}_{conv.id}_{msg.id}_{random.randint(1000, 9999)}",
                            user_id=user.id,
                            conversation_id=conv.id,
                            message_id=msg.id,
                            provider=provider,
                            model=model,
                            timestamp=msg.created_at,
                            request_payload={
                                "messages": [{"role": "user", "content": "分析过去一周的用户行为数据"}],
                                "max_tokens": 4096,
                            },
                            response_payload={
                                "content": [{"type": "text", "text": "分析结果：本周活跃用户较上周增长12%，..."}],
                            },
                            latency_ms=random.randint(200, 5000),
                            first_token_ms=random.randint(100, 1500),
                            tokens_per_second=random.uniform(30, 150),
                            input_tokens=random.randint(500, 3000),
                            output_tokens=random.randint(200, 1500),
                            tokens_estimated=False,
                            iteration_count=random.randint(1, 4),
                        )
                        session.add(trace)
                        all_traces.append(trace)

                        # 50% 概率记录技能加载
                        if random.random() < 0.5:
                            skill = random.choice(skills)
                            success = random.choice(skill_success)
                            skill_usage = SkillUsage(
                                user_id=user.id,
                                conversation_id=conv.id,
                                message_id=msg.id,
                                skill_name=skill,
                                success=success,
                                error_message="Skill file not found" if not success else None,
                                latency_ms=random.randint(50, 500),
                                content_length=random.randint(5000, 20000),
                                timestamp=msg.created_at - timedelta(milliseconds=random.randint(50, 500)),
                            )
                            session.add(skill_usage)
                            all_skill_usages.append(skill_usage)

        await session.commit()

        print(f"✅ 数据生成完成!")
        print(f"   - 用户: {len(users)} 个")
        print(f"   - 会话: {len(users) * 3} 个 (平均)")
        print(f"   - 消息: ~{len(users) * 3 * 10} 条")
        print(f"   - LLM Trace: {len(all_traces)} 条")
        print(f"   - Skill Usage: {len(all_skill_usages)} 条")
        print(f"\n📊 你现在可以让 Agent 分析这些数据了!")
        print(f"   提问示例: '分析过去一周的Token使用情况'")
        print(f"   提问示例: '哪类技能的加载失败率最高?'")
        print(f"   提问示例: '帮我生成一个决策简报，总结最近的模型调用延迟分布'")


if __name__ == "__main__":
    asyncio.run(generate_data())