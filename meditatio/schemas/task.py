from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel


class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str  # cron, once, interval
    trigger_config: Dict[str, Any]
    task_payload: Dict[str, Any]


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    trigger_config: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    trigger_type: str
    trigger_config: Dict[str, Any]
    task_payload: Dict[str, Any]
    status: str
    last_run_at: Optional[datetime]
    last_result: Optional[str]
    next_run_at: Optional[datetime]
    run_count: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    id: int
    name: str
    trigger_type: str
    status: str
    next_run_at: Optional[datetime]
    run_count: int
    is_active: bool
