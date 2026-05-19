from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc

from meditatio.models.scheduled_task import ScheduledTask
from meditatio.schemas.task import TaskCreate, TaskUpdate
from meditatio.services.task_scheduler import get_task_scheduler


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
