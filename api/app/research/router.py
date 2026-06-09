import uuid
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc
from app.db import AsyncSessionLocal
from app.research.models import ResearchResult


from app.research.schemas import PipelineRequest, PipelineResponse
from app.research.service import (
    run_pipeline,
    pipeline_worker_task,
    load_task_from_db,
    TASK_STORE,
)

router = APIRouter(
    prefix="/hotel-research",
    tags=["Hotel Research"],
)


@router.post("/run/stream")
async def run_stream(request: PipelineRequest, background_tasks: BackgroundTasks):
    """
    Tiếp nhận yêu cầu, đẩy vào Background Task chạy ngầm,
    trả về task_id ngay lập tức.
    """
    task_id = str(uuid.uuid4())

    # Khởi tạo RAM một lần duy nhất ở đây
    # FIX: bỏ dòng set RAM trùng trong pipeline_worker_task
    TASK_STORE[task_id] = {"status": "running", "events": []}

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
    # Tìm trong RAM trước, nếu không có thì load từ DB (server restart)
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
    """Danh sách kết quả research, mới nhất trước."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ResearchResult)
            .order_by(desc(ResearchResult.created_at))
            .limit(limit)
            .offset(offset)
        )
        rows = result.scalars().all()

    return {
        "total": len(rows),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": r.id,
                "task_id": r.task_id,
                "business_name": r.business_name,
                "created_at": r.created_at,
                "competitors_count": len(r.competitors_clean or []),
                "has_analysis": bool(r.competitor_analysis),
                "has_report": bool(r.final_report),
            }
            for r in rows
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