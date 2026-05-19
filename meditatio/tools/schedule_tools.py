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
