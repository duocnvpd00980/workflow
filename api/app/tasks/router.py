from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from .schemas import TaskOut, TaskListOut
from . import service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=TaskListOut)
async def list_tasks(
    status: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    result = await service.list_tasks(
        db,
        status=status,
        source=source,
        search=search,
        limit=limit,
        offset=offset,
    )
    return TaskListOut(
        items=result["items"],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task không tồn tại")
    return task


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    ok = await service.delete_task(db, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task không tồn tại")
    return {"ok": True}
