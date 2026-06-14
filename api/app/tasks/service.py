from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import BackgroundTask, TaskStep


# ══════════════════════════════════════════════════════════════
# WRITE — dùng trong từng module khi bắt đầu / cập nhật task
# ══════════════════════════════════════════════════════════════

async def create_task(
    db: AsyncSession,
    *,
    source: str,
    source_id: str,
    title: str,
    content_type: Optional[str] = None,
    triggered_by: Optional[str] = None,
    steps_total: int = 0,
    model: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
) -> BackgroundTask:
    """
    Gọi khi bắt đầu chạy nền.

    Ví dụ:
        task = await create_task(
            db,
            source="marketing",
            source_id=session_id,
            title="Gen blog AI Trends",
            content_type="blog",
            triggered_by="user",
            steps_total=7,
            model="gpt-4o",
            meta={
                "brand": "Acme Corp",
                "template": "Blog Post",
                "prompt": "Viết blog về xu hướng AI...",
                "tone": "Chuyên nghiệp",
                "framework": "Tự do",
                "length": "Vừa (~1000 từ)",
                "rag_docs": ["Brand Guidelines"],
            },
        )
    """
    task = BackgroundTask(
        source=source,
        source_id=str(source_id),
        title=title[:512],
        content_type=content_type,
        status="running",
        triggered_by=triggered_by,
        steps_total=steps_total,
        model=model,
        meta=meta,
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
    meta_update: Optional[dict[str, Any]] = None,
) -> Optional[BackgroundTask]:
    """
    Cập nhật tiến độ hoặc trạng thái.
    meta_update sẽ merge vào meta hiện tại (không replace toàn bộ).

    Ví dụ cập nhật progress:
        await update_task(db, task_id, steps_done=3)

    Ví dụ khi hoàn thành, lưu output:
        await update_task(
            db, task_id,
            status="completed",
            steps_done=7,
            meta_update={"output_preview": "Trí tuệ nhân tạo...", "content_id": "abc"},
        )
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

    if meta_update:
        existing = task.meta or {}
        task.meta = {**existing, **meta_update}

    await db.commit()
    await db.refresh(task)
    return task


async def finish_task(
    db: AsyncSession,
    task_id: int,
    *,
    steps_done: Optional[int] = None,
    output_preview: Optional[str] = None,
    content_id: Optional[str] = None,
) -> Optional[BackgroundTask]:
    """Shorthand cho completed — có thể kèm output."""
    meta_update: dict[str, Any] = {}
    if output_preview:
        meta_update["output_preview"] = output_preview
    if content_id:
        meta_update["content_id"] = content_id

    return await update_task(
        db, task_id,
        status="completed",
        steps_done=steps_done,
        meta_update=meta_update or None,
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


async def stop_task(
    db: AsyncSession,
    task_id: int,
    reason: Optional[str] = None,
) -> Optional[BackgroundTask]:
    """
    Dừng task đang chạy → status = 'stopped'.
    Chỉ áp dụng với task đang running.
    """
    task = await db.get(BackgroundTask, task_id)
    if not task:
        return None
    if task.status != "running":
        return task  # Không làm gì nếu không phải đang chạy

    task.status = "stopped"
    task.finished_at = datetime.now()
    if reason:
        task.error_message = reason

    await db.commit()
    await db.refresh(task)
    return task


async def retry_task(
    db: AsyncSession,
    task_id: int,
    meta_override: Optional[dict[str, Any]] = None,
) -> Optional[BackgroundTask]:
    """
    Clone task cũ (failed/stopped) thành task mới với status=running.
    meta_override cho phép ghi đè một số field nếu cần.
    Trả về task mới.
    """
    original = await db.get(BackgroundTask, task_id)
    if not original:
        return None
    if original.status not in ("failed", "stopped"):
        return None  # Chỉ retry task thất bại / đã dừng

    merged_meta = {**(original.meta or {}), **(meta_override or {})}

    new_task = BackgroundTask(
        source=original.source,
        source_id=original.source_id,
        title=original.title,
        content_type=original.content_type,
        status="running",
        triggered_by=original.triggered_by,
        steps_total=original.steps_total,
        model=original.model,
        meta=merged_meta or None,
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task


# ══════════════════════════════════════════════════════════════
# STEP LOG — gọi trong từng bước của pipeline
# ══════════════════════════════════════════════════════════════

async def add_step(
    db: AsyncSession,
    task_id: int,
    *,
    step_index: int,
    message: str,
    status: str = "completed",
) -> TaskStep:
    """
    Thêm 1 bước vào log của task.

    Ví dụ dùng trong pipeline:
        await add_step(db, task.id, step_index=1, message="Research từ khóa")
        await add_step(db, task.id, step_index=2, message="Tạo outline")
        await add_step(db, task.id, step_index=3,
                       message="Viết nội dung chính", status="running")
    """
    step = TaskStep(
        task_id=task_id,
        step_index=step_index,
        message=message,
        status=status,
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


async def update_step(
    db: AsyncSession,
    step_id: int,
    *,
    status: str,
    message: Optional[str] = None,
) -> Optional[TaskStep]:
    """Cập nhật trạng thái bước — vd từ running → completed/failed."""
    step = await db.get(TaskStep, step_id)
    if not step:
        return None
    step.status = status
    if message:
        step.message = message
    await db.commit()
    await db.refresh(step)
    return step


# ══════════════════════════════════════════════════════════════
# READ — dùng cho trang History
# ══════════════════════════════════════════════════════════════

async def list_tasks(
    db: AsyncSession,
    *,
    status: Optional[str] = None,
    source: Optional[str] = None,
    content_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    List background tasks — filter + search + phân trang.
    Không load steps (tránh N+1), chỉ load trong get_task.
    """
    query = select(BackgroundTask)

    if status:
        query = query.where(BackgroundTask.status == status)

    if source:
        query = query.where(BackgroundTask.source == source)

    if content_type:
        query = query.where(BackgroundTask.content_type == content_type)

    if search:
        pattern = f"%{search}%"
        query = query.where(
            BackgroundTask.title.ilike(pattern)
            | BackgroundTask.source_id.ilike(pattern)
        )

    # Đếm tổng trước khi phân trang
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Lấy trang
    query = (
        query
        .order_by(desc(BackgroundTask.created_at))
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(query)).scalars().all()

    return {
        "items": rows,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def get_task(
    db: AsyncSession,
    task_id: int,
) -> Optional[BackgroundTask]:
    """Lấy task kèm steps (eager load)."""
    result = await db.execute(
        select(BackgroundTask)
        .where(BackgroundTask.id == task_id)
        .options(selectinload(BackgroundTask.steps))
    )
    return result.scalar_one_or_none()


async def delete_task(db: AsyncSession, task_id: int) -> bool:
    task = await db.get(BackgroundTask, task_id)
    if not task:
        return False
    await db.delete(task)
    await db.commit()
    return True