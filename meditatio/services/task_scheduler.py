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

from meditatio.config import get_settings
from meditatio.database import get_session_context
from meditatio.models.scheduled_task import ScheduledTask
from meditatio.models.message import Message
from meditatio.services.agent_engine import AgentEngine, AgentContext, get_agent_engine
from meditatio.services.chat_service import ChatService

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
            from meditatio.models.conversation import Conversation
            conversation = Conversation(
                user_id=user_id,
                title=f"Scheduled task: {task.name}",
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            conversation_id = conversation.id

        # Get conversation history
        from meditatio.services.chat_service import ChatService
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
