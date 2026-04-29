# Aeris Phase 4 - 定时任务系统 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现定时任务系统（Agent 自主创建、Web 管理面板查看管理）、schedule_create/list/delete 工具。

**架构：** APScheduler 集成 PostgreSQLJobStore，同进程异步执行，Agent 通过工具创建任务，任务执行时调用 Agent Loop 完成对话。

**技术栈：** APScheduler（PostgreSQL 持久化），croniter（cron 表达式解析），FastAPI 后台任务。

---

## 文件结构（新增）

```
aeris/
├── services/
│   ├── task_scheduler.py     # APScheduler 封装、任务执行器
│   └── task_service.py       # 定时任务业务逻辑
├── routers/
│   └── tasks.py              # 定时任务管理 API
├── tools/
│   └── schedule_tools.py     # schedule_create/list/delete 工具
└── schemas/
    └── task.py               # 定时任务 schemas

frontend/src/
├── components/
│   └── TaskManager/
│       ├── TaskList.tsx
│       ├── TaskDetail.tsx
│       └── TaskCreateModal.tsx
└── services/
    └── taskApi.ts
```

---

## 任务分解

### 任务 1：APScheduler 集成与配置

**文件：**
- 创建：`aeris/services/task_scheduler.py`
- 修改：`pyproject.toml`（添加依赖）

- [ ] **步骤 1：修改 pyproject.toml 添加依赖**

```toml
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sqlmodel>=0.0.14",
    "psycopg[binary]>=3.1.18",
    "pydantic-settings>=2.1.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "alembic>=1.13.0",
    "python-multipart>=0.0.9",
    "openai>=1.12.0",  # OpenAI SDK for SGLang
    "httpx>=0.26.0",
    "aiofiles>=23.2.0",  # Async file I/O
    "Pillow>=10.2.0",   # Image processing
    "python-magic>=0.4.27",  # MIME type detection
    "apscheduler>=3.10.4",  # Task scheduling
    "croniter>=2.0.1",  # Cron expression parsing
    # Optional: tiktoken for token estimation
    "tiktoken>=0.6.0",
]
```

- [ ] **步骤 2：创建 task_scheduler.py**

```python
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Callable, Any

from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import select

from aeris.config import get_settings
from aeris.database import get_session_context
from aeris.models.scheduled_task import ScheduledTask
from aeris.models.message import Message
from aeris.services.agent_engine import AgentEngine, AgentContext, get_agent_engine
from aeris.services.chat_service import ChatService

settings = get_settings()


class TaskScheduler:
    """APScheduler wrapper for Aeris."""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.agent_engine: Optional[AgentEngine] = None

    def initialize(self, agent_engine: AgentEngine):
        """Initialize the scheduler."""
        self.agent_engine = agent_engine

        # Create scheduler with PostgreSQL job store
        self.scheduler = AsyncIOScheduler(
            jobstores={
                "default": {
                    "type": "sqlalchemy",
                    "url": settings.database_url,
                    "tablename": "apscheduler_jobs",
                }
            },
            executors={
                "default": {
                    "type": "asyncio",
                    "max_workers": 10,
                }
            },
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 3600,  # 1 hour
            },
            timezone="UTC",
        )

        # Add event listeners
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED,
        )
        self.scheduler.add_listener(
            self._on_job_error,
            EVENT_JOB_ERROR,
        )

    def start(self):
        """Start the scheduler."""
        if self.scheduler:
            self.scheduler.start()

    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown()

    def _on_job_executed(self, event):
        """Handle successful job execution."""
        print(f"Job {event.job_id} executed successfully at {event.scheduled_run_time}")

    def _on_job_error(self, event):
        """Handle job execution error."""
        print(f"Job {event.job_id} failed: {event.exception}")

    def add_job(
        self,
        task_id: int,
        trigger_type: str,
        trigger_config: dict,
        task_payload: dict,
        user_id: int,
    ) -> str:
        """
        Add a job to the scheduler.

        Args:
            task_id: Database task ID
            trigger_type: 'cron', 'once', or 'interval'
            trigger_config: Trigger configuration
            task_payload: Task execution payload
            user_id: User ID

        Returns:
            Job ID (APScheduler job ID)
        """
        job_id = f"task_{task_id}"

        if trigger_type == "cron":
            trigger = CronTrigger.from_crontab(
                trigger_config["cron"],
                timezone="UTC",
            )
        elif trigger_type == "once":
            run_date = datetime.fromisoformat(trigger_config["run_date"])
            trigger = DateTrigger(run_date=run_date, timezone="UTC")
        elif trigger_type == "interval":
            trigger = IntervalTrigger(
                **trigger_config["interval"],
                timezone="UTC",
            )
        else:
            raise ValueError(f"Unknown trigger type: {trigger_type}")

        self.scheduler.add_job(
            func=self._execute_task,
            trigger=trigger,
            id=job_id,
            args=[task_id, task_payload, user_id],
            replace_existing=True,
            jobstore="default",
        )

        return job_id

    def remove_job(self, task_id: int):
        """Remove a job from the scheduler."""
        job_id = f"task_{task_id}"
        try:
            self.scheduler.remove_job(job_id, jobstore="default")
        except Exception:
            pass  # Job might not exist

    def pause_job(self, task_id: int):
        """Pause a job."""
        job_id = f"task_{task_id}"
        try:
            self.scheduler.pause_job(job_id, jobstore="default")
        except Exception:
            pass

    def resume_job(self, task_id: int):
        """Resume a paused job."""
        job_id = f"task_{task_id}"
        try:
            self.scheduler.resume_job(job_id, jobstore="default")
        except Exception:
            pass

    async def _execute_task(self, task_id: int, task_payload: dict, user_id: int):
        """
        Execute a scheduled task.

        This is the actual job that runs when triggered.
        """
        from datetime import datetime

        async with get_session_context() as session:
            # Update task status
            result = await session.execute(
                select(ScheduledTask).where(ScheduledTask.id == task_id)
            )
            task = result.scalar_one_or_none()

            if not task or not task.is_active:
                return

            task.status = "running"
            task.run_count += 1
            task.last_run_at = datetime.utcnow()
            await session.commit()

            try:
                # Execute the task based on payload type
                task_type = task_payload.get("type", "chat_completion")

                if task_type == "chat_completion":
                    await self._execute_chat_task(session, task, task_payload, user_id)
                elif task_type == "code_execution":
                    await self._execute_code_task(session, task, task_payload)
                else:
                    raise ValueError(f"Unknown task type: {task_type}")

                task.status = "pending"  # Back to pending for next run
                task.last_result = "Success"

                # Update next_run_at
                job = self.scheduler.get_job(f"task_{task_id}")
                if job and job.next_run_time:
                    task.next_run_at = job.next_run_time

            except Exception as e:
                task.status = "failed"
                task.last_result = str(e)
                print(f"Task {task_id} failed: {e}")

            await session.commit()

    async def _execute_chat_task(
        self,
        session,
        task: ScheduledTask,
        task_payload: dict,
        user_id: int,
    ):
        """Execute a chat completion task."""
        conversation_id = task_payload.get("conversation_id")
        message_content = task_payload.get("message", "")

        if not conversation_id:
            # Create a new conversation for this task
            from aeris.models.conversation import Conversation
            conversation = Conversation(
                user_id=user_id,
                title=f"Scheduled task: {task.name}",
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            conversation_id = conversation.id

        # Get conversation history
        from aeris.services.chat_service import ChatService
        chat_service = ChatService(session)
        messages = await chat_service.get_conversation_messages(conversation_id)

        # Add system message for scheduled task
        system_message = f"This is a scheduled task: {task.name}. {task.description or ''}"

        llm_messages = [
            {"role": "system", "content": system_message},
        ]
        for msg in messages:
            llm_messages.append({
                "role": msg.role,
                "content": msg.content or "",
            })

        # Add the task message
        llm_messages.append({"role": "user", "content": message_content})

        # Save user message
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=message_content,
            created_at=datetime.utcnow(),
        )
        session.add(user_message)
        await session.commit()
        await session.refresh(user_message)

        # Run agent
        context = AgentContext(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=user_message.id,
        )

        result = await self.agent_engine.run(llm_messages, context)

        # Save AI response
        ai_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=result.content,
            input_tokens=result.usage["input_tokens"],
            output_tokens=result.usage["output_tokens"],
            created_at=datetime.utcnow(),
        )
        session.add(ai_message)
        await session.commit()

    async def _execute_code_task(self, session, task: ScheduledTask, task_payload: dict):
        """Execute a code execution task (placeholder for future)."""
        # For MVP, just log that code execution is not yet implemented
        print(f"Code execution task not yet implemented for task {task.id}")


# Global scheduler instance
_scheduler: Optional[TaskScheduler] = None


def get_task_scheduler() -> TaskScheduler:
    """Get or create task scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler
```

- [ ] **步骤 3：Commit**

```bash
git add pyproject.toml aeris/services/task_scheduler.py
git commit -m "feat: add APScheduler integration with PostgreSQL job store"
```

---

### 任务 2：定时任务服务

**文件：**
- 创建：`aeris/services/task_service.py`
- 创建：`aeris/schemas/task.py`

- [ ] **步骤 1：创建 schemas/task.py**

```python
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
```

- [ ] **步骤 2：创建 task_service.py**

```python
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc

from aeris.models.scheduled_task import ScheduledTask
from aeris.schemas.task import TaskCreate, TaskUpdate
from aeris.services.task_scheduler import get_task_scheduler


class TaskService:
    """Scheduled task business logic service."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.scheduler = get_task_scheduler()

    async def create_task(self, user_id: int, data: TaskCreate) -> ScheduledTask:
        """Create a new scheduled task."""
        task = ScheduledTask(
            user_id=user_id,
            name=data.name,
            description=data.description,
            trigger_type=data.trigger_type,
            trigger_config=data.trigger_config,
            task_payload=data.task_payload,
            status="pending",
        )

        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)

        # Add to scheduler
        self.scheduler.add_job(
            task_id=task.id,
            trigger_type=task.trigger_type,
            trigger_config=task.trigger_config,
            task_payload=task.task_payload,
            user_id=user_id,
        )

        # Get next run time from scheduler
        job = self.scheduler.scheduler.get_job(f"task_{task.id}")
        if job and job.next_run_time:
            task.next_run_at = job.next_run_time
            await self.session.commit()

        return task

    async def get_task(self, user_id: int, task_id: int) -> Optional[ScheduledTask]:
        """Get task by ID."""
        result = await self.session.execute(
            select(ScheduledTask)
            .where(ScheduledTask.id == task_id)
            .where(ScheduledTask.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        active_only: bool = False,
    ) -> List[ScheduledTask]:
        """List user's tasks."""
        query = select(ScheduledTask).where(ScheduledTask.user_id == user_id)

        if active_only:
            query = query.where(ScheduledTask.is_active == True)

        query = query.order_by(desc(ScheduledTask.created_at)).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_task(
        self,
        user_id: int,
        task_id: int,
        data: TaskUpdate,
    ) -> Optional[ScheduledTask]:
        """Update a task."""
        task = await self.get_task(user_id, task_id)
        if not task:
            return None

        # Update fields
        if data.name is not None:
            task.name = data.name
        if data.description is not None:
            task.description = data.description
        if data.is_active is not None:
            task.is_active = data.is_active
            if task.is_active:
                self.scheduler.resume_job(task_id)
            else:
                self.scheduler.pause_job(task_id)

        if data.trigger_config is not None:
            task.trigger_config = data.trigger_config
            # Remove and re-add job with new trigger
            self.scheduler.remove_job(task_id)
            self.scheduler.add_job(
                task_id=task.id,
                trigger_type=task.trigger_type,
                trigger_config=task.trigger_config,
                task_payload=task.task_payload,
                user_id=user_id,
            )

        task.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(task)

        return task

    async def delete_task(self, user_id: int, task_id: int) -> bool:
        """Delete a task."""
        task = await self.get_task(user_id, task_id)
        if not task:
            return False

        # Remove from scheduler
        self.scheduler.remove_job(task_id)

        # Soft delete
        task.is_active = False
        task.status = "cancelled"
        await self.session.commit()

        return True

    async def run_task_now(self, user_id: int, task_id: int) -> bool:
        """Trigger a task to run immediately."""
        task = await self.get_task(user_id, task_id)
        if not task:
            return False

        # Modify the job to run immediately
        self.scheduler.scheduler.modify_job(
            f"task_{task_id}",
            next_run_time=datetime.utcnow(),
        )

        return True
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/schemas/task.py aeris/services/task_service.py
git commit -m "feat: add task service with CRUD operations"
```

---

### 任务 3：定时任务 API 路由

**文件：**
- 创建：`aeris/routers/tasks.py`
- 修改：`aeris/main.py`（添加路由和初始化）

- [ ] **步骤 1：创建 tasks.py**

```python
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from aeris.database import get_session
from aeris.routers.auth import get_current_user, TokenData
from aeris.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
)
from aeris.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def get_task_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TaskService:
    return TaskService(session)


@router.get("", response_model=List[TaskListResponse])
async def list_tasks(
    active_only: bool = False,
    skip: int = 0,
    limit: int = 20,
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    task_service: Annotated[TaskService, Depends(get_task_service)] = None,
):
    """List user's scheduled tasks."""
    tasks = await task_service.list_tasks(
        current_user.user_id,
        skip=skip,
        limit=limit,
        active_only=active_only,
    )
    return tasks


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    task_service: Annotated[TaskService, Depends(get_task_service)] = None,
):
    """Create a new scheduled task."""
    task = await task_service.create_task(current_user.user_id, data)
    return task


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    task_service: Annotated[TaskService, Depends(get_task_service)] = None,
):
    """Get task details."""
    task = await task_service.get_task(current_user.user_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    task_service: Annotated[TaskService, Depends(get_task_service)] = None,
):
    """Update a task."""
    task = await task_service.update_task(current_user.user_id, task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    task_service: Annotated[TaskService, Depends(get_task_service)] = None,
):
    """Delete a task."""
    success = await task_service.delete_task(current_user.user_id, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return None


@router.post("/{task_id}/run-now")
async def run_task_now(
    task_id: int,
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    task_service: Annotated[TaskService, Depends(get_task_service)] = None,
):
    """Trigger a task to run immediately."""
    success = await task_service.run_task_now(current_user.user_id, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task triggered to run now"}
```

- [ ] **步骤 2：修改 main.py 添加路由和初始化**

在 `lifespan` 函数中添加任务调度器初始化：

```python
from aeris.services.task_scheduler import get_task_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()

    # Initialize task scheduler
    from aeris.services.agent_engine import get_agent_engine
    scheduler = get_task_scheduler()
    scheduler.initialize(get_agent_engine())
    scheduler.start()

    # Register tools
    from aeris.tools.base import get_tool_registry
    from aeris.tools.conversation_search import register_conversation_search_tool
    from aeris.tools.file_tools import register_file_tools
    from aeris.tools.schedule_tools import register_schedule_tools

    registry = get_tool_registry()
    register_conversation_search_tool(registry)
    register_file_tools(registry)
    register_schedule_tools(registry)

    yield

    # Shutdown
    scheduler.shutdown()

    # Register routers
from aeris.routers import auth, chat, files, tasks

app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/routers/tasks.py aeris/main.py
git commit -m "feat: add task management API routes"
```

---

### 任务 4：定时任务工具

**文件：**
- 创建：`aeris/tools/schedule_tools.py`

- [ ] **步骤 1：创建 schedule_tools.py**

```python
from datetime import datetime
from typing import Any, Dict, Optional

from croniter import croniter

from aeris.tools.base import Tool, ToolParameter, ToolResult
from aeris.schemas.task import TaskCreate
from aeris.services.task_service import TaskService
from aeris.database import get_session_context


class ScheduleCreateTool(Tool):
    """Create a scheduled task that runs automatically."""

    name = "schedule_create"
    description = "Create a scheduled task that will run automatically at specified times. Supports cron expressions, one-time runs, and intervals."
    parameters = [
        ToolParameter(
            name="name",
            type="string",
            description="Name of the scheduled task",
            required=True,
        ),
        ToolParameter(
            name="description",
            type="string",
            description="Description of what this task does",
            required=False,
        ),
        ToolParameter(
            name="trigger_type",
            type="string",
            description="Type of trigger: 'cron' (repeating), 'once' (one-time), or 'interval' (fixed interval)",
            required=True,
        ),
        ToolParameter(
            name="trigger_config",
            type="object",
            description="Configuration for the trigger. For 'cron': {'cron': '0 9 * * *'} (daily at 9am). For 'once': {'run_date': '2024-01-01T09:00:00'}. For 'interval': {'minutes': 30}.",
            required=True,
        ),
        ToolParameter(
            name="task_type",
            type="string",
            description="Type of task to run: 'chat_completion' (send a message to AI)",
            required=True,
        ),
        ToolParameter(
            name="task_config",
            type="object",
            description="Configuration for the task. For 'chat_completion': {'message': 'What is the weather today?'}",
            required=True,
        ),
    ]

    async def execute(
        self,
        name: str,
        description: Optional[str] = None,
        trigger_type: str = "cron",
        trigger_config: Dict = None,
        task_type: str = "chat_completion",
        task_config: Dict = None,
        _context: Dict = None,
    ) -> ToolResult:
        try:
            user_id = _context.get("user_id") if _context else None

            if not user_id:
                return ToolResult(success=False, error="User context not available")

            # Validate trigger type
            if trigger_type not in ["cron", "once", "interval"]:
                return ToolResult(
                    success=False,
                    error=f"Invalid trigger_type. Must be 'cron', 'once', or 'interval'",
                )

            # Validate trigger config
            if trigger_type == "cron":
                cron_expr = trigger_config.get("cron")
                if not cron_expr:
                    return ToolResult(success=False, error="Missing 'cron' in trigger_config")
                if not croniter.is_valid(cron_expr):
                    return ToolResult(success=False, error=f"Invalid cron expression: {cron_expr}")

            elif trigger_type == "once":
                run_date = trigger_config.get("run_date")
                if not run_date:
                    return ToolResult(success=False, error="Missing 'run_date' in trigger_config")
                try:
                    datetime.fromisoformat(run_date)
                except ValueError:
                    return ToolResult(success=False, error=f"Invalid run_date format: {run_date}")

            elif trigger_type == "interval":
                if not any(k in trigger_config for k in ["weeks", "days", "hours", "minutes", "seconds"]):
                    return ToolResult(
                        success=False,
                        error="Interval trigger_config must include at least one of: weeks, days, hours, minutes, seconds",
                    )

            # Build task payload
            conversation_id = _context.get("conversation_id") if _context else None
            task_payload = {
                "type": task_type,
                "message": task_config.get("message", ""),
                "conversation_id": conversation_id,
            }

            # Create task
            async with get_session_context() as session:
                task_service = TaskService(session)
                task = await task_service.create_task(
                    user_id=user_id,
                    data=TaskCreate(
                        name=name,
                        description=description,
                        trigger_type=trigger_type,
                        trigger_config=trigger_config,
                        task_payload=task_payload,
                    ),
                )

            return ToolResult(
                success=True,
                data={
                    "task_id": task.id,
                    "name": task.name,
                    "trigger_type": task.trigger_type,
                    "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ScheduleListTool(Tool):
    """List scheduled tasks."""

    name = "schedule_list"
    description = "List all scheduled tasks for the current user. Shows task status, next run time, and execution count."
    parameters = [
        ToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of tasks to return (default 20)",
            required=False,
        ),
        ToolParameter(
            name="active_only",
            type="boolean",
            description="Show only active tasks (default False)",
            required=False,
        ),
    ]

    async def execute(
        self,
        limit: int = 20,
        active_only: bool = False,
        _context: Dict = None,
    ) -> ToolResult:
        try:
            user_id = _context.get("user_id") if _context else None

            if not user_id:
                return ToolResult(success=False, error="User context not available")

            async with get_session_context() as session:
                task_service = TaskService(session)
                tasks = await task_service.list_tasks(
                    user_id=user_id,
                    limit=limit,
                    active_only=active_only,
                )

            return ToolResult(
                success=True,
                data={
                    "tasks": [
                        {
                            "id": t.id,
                            "name": t.name,
                            "trigger_type": t.trigger_type,
                            "status": t.status,
                            "next_run_at": t.next_run_at.isoformat() if t.next_run_at else None,
                            "run_count": t.run_count,
                            "is_active": t.is_active,
                        }
                        for t in tasks
                    ],
                    "count": len(tasks),
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ScheduleDeleteTool(Tool):
    """Delete a scheduled task."""

    name = "schedule_delete"
    description = "Delete (cancel) a scheduled task. The task will no longer run."
    parameters = [
        ToolParameter(
            name="task_id",
            type="integer",
            description="ID of the task to delete",
            required=True,
        ),
    ]

    async def execute(
        self,
        task_id: int,
        _context: Dict = None,
    ) -> ToolResult:
        try:
            user_id = _context.get("user_id") if _context else None

            if not user_id:
                return ToolResult(success=False, error="User context not available")

            async with get_session_context() as session:
                task_service = TaskService(session)
                success = await task_service.delete_task(user_id, task_id)

                if not success:
                    return ToolResult(success=False, error=f"Task {task_id} not found")

            return ToolResult(
                success=True,
                data={"message": f"Task {task_id} deleted successfully"},
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


def register_schedule_tools(registry):
    """Register all schedule tools."""
    registry.register(ScheduleCreateTool())
    registry.register(ScheduleListTool())
    registry.register(ScheduleDeleteTool())
```

- [ ] **步骤 2：Commit**

```bash
git add aeris/tools/schedule_tools.py
git commit -m "feat: add schedule tools (create, list, delete)"
```

---

### 任务 5：测试定时任务

**文件：**
- 创建：`tests/test_task_service.py`

- [ ] **步骤 1：创建 test_task_service.py**

```python
import pytest
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_create_cron_task(client, db_session):
    """Test creating a cron task."""
    from aeris.services.auth_service import AuthService
    from aeris.schemas.task import TaskCreate

    auth_service = AuthService(db_session)
    user = await auth_service.create_user("taskuser", "password123")
    token = auth_service.create_access_token_for_user(user)

    response = await client.post(
        "/api/v1/tasks",
        json={
            "name": "Daily Summary",
            "description": "Send daily summary at 9am",
            "trigger_type": "cron",
            "trigger_config": {"cron": "0 9 * * *"},
            "task_payload": {
                "type": "chat_completion",
                "message": "Give me a summary of today's activities",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Daily Summary"
    assert data["trigger_type"] == "cron"
    assert data["trigger_config"]["cron"] == "0 9 * * *"


@pytest.mark.asyncio
async def test_list_tasks(client, db_session):
    """Test listing tasks."""
    from aeris.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    user = await auth_service.create_user("taskuser2", "password123")
    token = auth_service.create_access_token_for_user(user)

    response = await client.get(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **步骤 2：Commit**

```bash
git add tests/test_task_service.py
git commit -m "test: add task service tests"
```

---

## 自检

### 规格覆盖度检查

| 规格需求 | 实现任务 |
|---------|---------|
| APScheduler 集成 | ✅ 任务 1 |
| PostgreSQL JobStore | ✅ 任务 1 |
| 任务执行器 | ✅ 任务 1 |
| 任务 CRUD API | ✅ 任务 2, 3 |
| schedule_create 工具 | ✅ 任务 4 |
| schedule_list 工具 | ✅ 任务 4 |
| schedule_delete 工具 | ✅ 任务 4 |
| Web 管理面板 API | ✅ 任务 3 |
| 测试覆盖 | ✅ 任务 5 |

### 文件职责

- `task_scheduler.py`: APScheduler 封装，任务执行逻辑
- `task_service.py`: 定时任务业务逻辑（CRUD）
- `tasks.py`: HTTP API 路由（管理面板）
- `schedule_tools.py`: Agent 可调用的工具
- `task.py` (schemas): Pydantic schemas

---

## 执行方式

**计划已完成并保存到 `docs/superpowers/plans/2026-04-28-aeris-phase4.md`。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理

**2. 内联执行** - 在当前会话中使用 executing-plans 技能

**选哪种方式？**
