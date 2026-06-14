from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from .schemas import TaskOut, TaskDetailOut, TaskListOut, TaskStepOut, TaskStopRequest, TaskRetryRequest
from . import service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=TaskListOut)
async def list_tasks(
    status: Optional[str] = None,
    source: Optional[str] = None,
    content_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    result = await service.list_tasks(
        db,
        status=status,
        source=source,
        content_type=content_type,
        search=search,
        limit=min(limit, 100),
        offset=offset,
    )
    return TaskListOut(
        items=result["items"],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get("/{task_id}", response_model=TaskDetailOut)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task không tồn tại")
    return task


@router.post("/{task_id}/stop", response_model=TaskDetailOut)
async def stop_task(
    task_id: int,
    body: TaskStopRequest = TaskStopRequest(),
    db: AsyncSession = Depends(get_db),
):
    task = await service.stop_task(db, task_id, reason=body.reason)
    if not task:
        raise HTTPException(status_code=404, detail="Task không tồn tại")
    return task


@router.post("/{task_id}/retry", response_model=TaskDetailOut, status_code=status.HTTP_201_CREATED)
async def retry_task(
    task_id: int,
    body: TaskRetryRequest = TaskRetryRequest(),
    db: AsyncSession = Depends(get_db),
):
    new_task = await service.retry_task(db, task_id, meta_override=body.meta_override)
    if not new_task:
        raise HTTPException(
            status_code=400,
            detail="Chỉ retry được task có status: failed hoặc stopped",
        )
    return new_task


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    ok = await service.delete_task(db, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task không tồn tại")
    return {"ok": True}


@router.get("/{task_id}/steps", response_model=list[TaskStepOut])
async def list_steps(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task không tồn tại")
    return task.steps