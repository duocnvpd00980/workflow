from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .models import BackgroundTask


# ══════════════════════════════════════════════════════════════
# WRITE — dùng trong từng module khi bắt đầu / kết thúc task
# ══════════════════════════════════════════════════════════════

async def create_task(
    db: AsyncSession,
    *,
    source: str,
    source_id: str,
    title: str,
    triggered_by: Optional[str] = None,
    steps_total: int = 0,
    model: Optional[str] = None,
) -> BackgroundTask:
    """
    Gọi ngay khi bắt đầu chạy nền.
    
    Ví dụ trong marketing:
        task = await create_task(db, source="marketing", source_id=session_id,
                                 title=request_text, triggered_by="user")
    """
    task = BackgroundTask(
        source=source,
        source_id=str(source_id),
        title=title[:512],
        status="running",
        triggered_by=triggered_by,
        steps_total=steps_total,
        model=model,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(
    db: AsyncSession,
    task_id: int,
    *,
    status: Optional[str] = None,
    steps_done: Optional[int] = None,
    steps_total: Optional[int] = None,
    error_message: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[BackgroundTask]:
    """
    Cập nhật tiến độ hoặc trạng thái.
    
    Ví dụ khi pipeline xong:
        await update_task(db, task_id, status="completed", steps_done=5)
    
    Ví dụ khi lỗi:
        await update_task(db, task_id, status="failed", error_message=str(e))
    """
    task = await db.get(BackgroundTask, task_id)
    if not task:
        return None

    if status is not None:
        task.status = status
        if status in ("completed", "failed", "stopped"):
            task.finished_at = datetime.now()

    if steps_done is not None:
        task.steps_done = steps_done

    if steps_total is not None:
        task.steps_total = steps_total

    if error_message is not None:
        task.error_message = error_message

    if model is not None:
        task.model = model

    await db.commit()
    await db.refresh(task)
    return task


async def finish_task(
    db: AsyncSession,
    task_id: int,
    *,
    steps_done: Optional[int] = None,
) -> Optional[BackgroundTask]:
    """Shorthand cho completed."""
    return await update_task(
        db, task_id,
        status="completed",
        steps_done=steps_done,
    )


async def fail_task(
    db: AsyncSession,
    task_id: int,
    error_message: str,
) -> Optional[BackgroundTask]:
    """Shorthand cho failed."""
    return await update_task(
        db, task_id,
        status="failed",
        error_message=error_message,
    )


# ══════════════════════════════════════════════════════════════
# READ — dùng cho trang History
# ══════════════════════════════════════════════════════════════

async def list_tasks(
    db: AsyncSession,
    *,
    status: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    List tất cả background tasks, hỗ trợ filter + search + phân trang.
    Dùng cho GET /tasks trong router.
    """
    query = select(BackgroundTask)

    if status:
        query = query.where(BackgroundTask.status == status)

    if source:
        query = query.where(BackgroundTask.source == source)

    if search:
        pattern = f"%{search}%"
        query = query.where(
            BackgroundTask.title.ilike(pattern)
            | BackgroundTask.source_id.ilike(pattern)
        )

    # Đếm tổng
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Lấy trang
    query = query.order_by(desc(BackgroundTask.created_at)).limit(limit).offset(offset)
    rows = (await db.execute(query)).scalars().all()

    return {
        "items": rows,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def get_task(db: AsyncSession, task_id: int) -> Optional[BackgroundTask]:
    return await db.get(BackgroundTask, task_id)


async def delete_task(db: AsyncSession, task_id: int) -> bool:
    task = await db.get(BackgroundTask, task_id)
    if not task:
        return False
    await db.delete(task)
    await db.commit()
    return True
