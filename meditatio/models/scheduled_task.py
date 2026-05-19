from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from meditatio.models.user import User


class ScheduledTask(SQLModel, table=True):
    __tablename__ = "scheduled_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None)

    # Trigger configuration
    trigger_type: str = Field(max_length=20)  # cron, once, interval
    trigger_config: dict = Field(sa_column=Column(JSON))

    # Task payload (what to execute)
    task_payload: dict = Field(sa_column=Column(JSON))

    # Status
    status: str = Field(default="pending")  # pending, running, completed, failed, cancelled

    # Execution tracking
    last_run_at: Optional[datetime] = Field(default=None)
    last_result: Optional[str] = Field(default=None)
    next_run_at: Optional[datetime] = Field(default=None, index=True)
    run_count: int = Field(default=0)

    is_active: bool = Field(default=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="tasks")
