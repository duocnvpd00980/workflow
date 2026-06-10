import uuid
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc, func
from app.db import AsyncSessionLocal
from app.research.models import ResearchResult, PipelineTask  # <-- IMPORT PipelineTask

from app.research.schemas import PipelineRequest, PipelineResponse
from app.research.service import (
    run_pipeline,
    pipeline_worker_task,
    load_task_from_db,
    TASK_STORE,
    _db_create_task,
)

router = APIRouter(
    prefix="/hotel-research",
    tags=["Hotel Research"],
)


@router.post("/run/stream")
async def run_stream(request: PipelineRequest, background_tasks: BackgroundTasks):
    """
    Tiếp nhận yêu cầu, lưu DB ngay, đẩy vào Background Task chạy ngầm,
    trả về task_id ngay lập tức.
    """
    task_id = str(uuid.uuid4())

    # Khởi tạo RAM
    TASK_STORE[task_id] = {"status": "running", "events": []}

    # FIX: Lưu PipelineTask DB ngay lập tức để /results có thể query được task đang chạy
    await _db_create_task(
        task_id=task_id,
        business_name=request.business_name,
        address=request.address,
        industry=request.industry,
    )

    background_tasks.add_task(
        pipeline_worker_task,
        task_id=task_id,
        business_name=request.business_name,
        address=request.address,
        industry=request.industry,
    )

    return {"task_id": task_id, "status": "queued"}


@router.get("/stream/{task_id}")
async def get_realtime_stream(task_id: str):
    """Mở SSE stream để theo dõi tiến trình pipeline theo task_id."""
    if task_id not in TASK_STORE:
        found = await load_task_from_db(task_id)
        if not found:
            raise HTTPException(status_code=404, detail="Task ID không tồn tại")

    async def event_generator():
        sent_index = 0

        while True:
            task = TASK_STORE.get(task_id)
            if not task:
                break

            # Gửi hết events chưa gửi
            while sent_index < len(task["events"]):
                yield task["events"][sent_index]
                sent_index += 1

            # Nếu pipeline xong: flush nốt rồi đóng
            if task["status"] in ["completed", "failed"]:
                await asyncio.sleep(0.2)
                while sent_index < len(task["events"]):
                    yield task["events"][sent_index]
                    sent_index += 1
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Kiểm tra trạng thái task nhanh, không cần stream."""
    if task_id not in TASK_STORE:
        found = await load_task_from_db(task_id)
        if not found:
            raise HTTPException(status_code=404, detail="Task ID không tồn tại")

    task = TASK_STORE[task_id]
    return {
        "task_id": task_id,
        "status": task["status"],
        "total_events": len(task["events"]),
    }


@router.get("/results")
async def list_results(limit: int = 10, offset: int = 0):
    """Danh sách tất cả tasks (cả đang chạy và đã hoàn thành), mới nhất trước."""
    async with AsyncSessionLocal() as session:
        # Query PipelineTask để lấy tất cả tasks kể cả đang chạy
        result = await session.execute(
            select(PipelineTask)
            .order_by(desc(PipelineTask.created_at))
            .limit(limit)
            .offset(offset)
        )
        tasks = result.scalars().all()

        # Query ResearchResult để lấy thông tin kết quả (nếu có)
        task_ids = [t.task_id for t in tasks]
        results_map = {}
        if task_ids:
            result_rows = await session.execute(
                select(ResearchResult).where(ResearchResult.task_id.in_(task_ids))
            )
            for r in result_rows.scalars().all():
                results_map[r.task_id] = r

    return {
        "total": len(tasks),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": t.task_id,
                "task_id": t.task_id,
                "business_name": t.business_name,
                "status": t.status,  # <-- THÊM status
                "created_at": t.created_at,
                "competitors_count": len(getattr(results_map.get(t.task_id), 'competitors_clean', None) or []),
                "has_analysis": bool(getattr(results_map.get(t.task_id), 'competitor_analysis', None)),
                "has_report": bool(getattr(results_map.get(t.task_id), 'final_report', None)),
            }
            for t in tasks
        ],
    }


@router.get("/result/{task_id}")
async def get_result(task_id: str):
    """Lấy kết quả cuối sau khi pipeline completed."""
    if task_id not in TASK_STORE:
        found = await load_task_from_db(task_id)
        if not found:
            raise HTTPException(status_code=404, detail="Task ID không tồn tại")

    task = TASK_STORE[task_id]
    if task["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task chưa hoàn thành (status: {task['status']})"
        )

    # Parse kết quả từ event FINISHED trong RAM
    for event_str in reversed(task["events"]):
        if '"node": "FINISHED"' in event_str:
            import json
            try:
                data = json.loads(event_str.removeprefix("data: ").strip()).get("data", {})
                return {"task_id": task_id, "status": "completed", "result": data}
            except Exception:
                break

    raise HTTPException(status_code=500, detail="Không tìm thấy kết quả FINISHED")


@router.post("/run", response_model=PipelineResponse)
async def run(request: PipelineRequest):
    """Endpoint đồng bộ, đợi pipeline chạy xong mới trả kết quả."""
    try:
        final = await run_pipeline(
            business_name=request.business_name,
            address=request.address,
            industry=request.industry,
        )
        return PipelineResponse(
            success=True,
            hotel_dir=final["hotel_dir"],
            competitors_clean=final.get("competitors_clean", []),
            competitor_analysis=final.get("competitor_analysis", ""),
            final_report=final.get("final_report", ""),
            errors=final.get("errors", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))