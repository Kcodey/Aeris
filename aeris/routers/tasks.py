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
