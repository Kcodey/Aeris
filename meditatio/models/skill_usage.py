from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


class SkillUsage(SQLModel, table=True):
    """Record of skill usage/load events."""
    __tablename__ = "skill_usages"

    id: Optional[int] = Field(default=None, primary_key=True)

    # 关联信息
    user_id: int = Field(foreign_key="users.id", index=True)
    conversation_id: Optional[int] = Field(foreign_key="conversations.id", default=None, index=True)
    message_id: Optional[int] = Field(foreign_key="messages.id", default=None, index=True)

    # Skill 信息
    skill_name: str = Field(max_length=100, index=True, description="被加载的技能名称")

    # 调用结果
    success: bool = Field(default=True, description="是否成功加载")
    error_message: Optional[str] = Field(default=None, description="加载失败时的错误信息")

    # 性能指标
    latency_ms: Optional[int] = Field(default=None, description="加载耗时（毫秒）")
    content_length: Optional[int] = Field(default=None, description="技能文档内容长度")

    # 时间戳
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    # 额外元数据
    extra_meta: Optional[dict] = Field(default=None, sa_column=Column(JSON), description="额外元数据")
