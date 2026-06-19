import uuid
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc
from app.research.research_service import pipeline
from app.db import AsyncSessionLocal
from app.research.models import PipelineEvent, ResearchResult, PipelineTask
from app.research.schemas import PipelineRequest, PipelineResponse
# from app.research.service import (
#     run_pipeline,
#     pipeline_worker_task,
#     load_task_from_db,
#     TASK_STORE,
#     _db_create_task,
# )
from app.business.models import Business
from app.business.schemas import BusinessCreate
from app.business import service as business_service

router = APIRouter(
    prefix="/hotel-research",
    tags=["Hotel Research"],
)


# async def _get_or_create_business(
#     business_name: str,
#     owner_id: str,
#     industry: str | None,
#     address: str | None,
# ) -> Business:
#     """
#     Tìm Business theo name + owner_id.
#     Nếu chưa có → tạo mới.
#     Đảm bảo research nhiều lần cùng 1 tên → dùng chung 1 business_id.
#     """
#     async with AsyncSessionLocal() as db:
#         existing = (await db.execute(
#             select(Business).where(
#                 Business.name == business_name,
#                 Business.owner_id == owner_id,
#                 Business.deleted_at.is_(None),
#             )
#         )).scalars().one_or_none()

#         if existing:
#             return existing

#         return await business_service.create_business(
#             db,
#             BusinessCreate(
#                 name=business_name,
#                 owner_id=owner_id,
#                 industry=industry,
#                 address=address,
#             ),
#         )


# @router.post("/run/stream")
# async def run_stream(request: PipelineRequest, background_tasks: BackgroundTasks):
#     """
#     Tiếp nhận yêu cầu, lưu DB ngay, đẩy vào Background Task chạy ngầm,
#     trả về task_id ngay lập tức.
#     """
#     # ── 1. Get or create Business ────────────────────────────────
#     business = await _get_or_create_business(
#         business_name=request.business_name,
#         owner_id=request.owner_id,
#         industry=request.industry,
#         address=request.address,
#     )

#     # ── 2. Khởi tạo task ─────────────────────────────────────────
#     task_id = str(uuid.uuid4())
#     TASK_STORE[task_id] = {"status": "running", "events": []}

#     await _db_create_task(
#         task_id=task_id,
#         business_id=business.id,        # ← anchor trung tâm
#         business_name=request.business_name,
#         address=request.address,
#         industry=request.industry,
#     )

#     background_tasks.add_task(
#         pipeline_worker_task,
#         task_id=task_id,
#         business_id=business.id,        # ← truyền xuống worker
#         business_name=request.business_name,
#         address=request.address,
#         industry=request.industry,
#     )

#     return {
#         "task_id":     task_id,
#         "business_id": business.id,     # ← trả về để frontend lưu
#         "status":      "queued",
#     }


# @router.get("/stream/{task_id}")
# async def get_realtime_stream(task_id: str):
#     """Mở SSE stream để theo dõi tiến trình pipeline theo task_id."""
#     if task_id not in TASK_STORE:
#         found = await load_task_from_db(task_id)
#         if not found:
#             raise HTTPException(status_code=404, detail="Task ID không tồn tại")

#     async def event_generator():
#         sent_index = 0
#         while True:
#             task = TASK_STORE.get(task_id)
#             if not task:
#                 break

#             while sent_index < len(task["events"]):
#                 yield task["events"][sent_index]
#                 sent_index += 1

#             if task["status"] in ["completed", "failed"]:
#                 await asyncio.sleep(0.2)
#                 while sent_index < len(task["events"]):
#                     yield task["events"][sent_index]
#                     sent_index += 1
#                 break

#             await asyncio.sleep(0.5)

#     return StreamingResponse(
#         event_generator(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection":    "keep-alive",
#             "X-Accel-Buffering": "no",
#         },
#     )


# @router.get("/status/{task_id}")
# async def get_task_status(task_id: str):
#     """Kiểm tra trạng thái task nhanh, không cần stream."""
#     if task_id not in TASK_STORE:
#         found = await load_task_from_db(task_id)
#         if not found:
#             raise HTTPException(status_code=404, detail="Task ID không tồn tại")

#     task = TASK_STORE[task_id]
#     return {
#         "task_id":      task_id,
#         "status":       task["status"],
#         "total_events": len(task["events"]),
#     }


# @router.get("/results")
# async def list_results(
#     business_id: str | None = None,   # ← filter theo business
#     limit: int = 10,
#     offset: int = 0,
# ):
#     """Danh sách tất cả tasks, mới nhất trước. Filter theo business_id nếu có."""
#     async with AsyncSessionLocal() as session:
#         q = select(PipelineTask).order_by(desc(PipelineTask.created_at))
#         if business_id:
#             q = q.where(PipelineTask.business_id == business_id)

#         tasks = (await session.execute(q.limit(limit).offset(offset))).scalars().all()

#         task_ids = [t.task_id for t in tasks]
#         results_map = {}
#         if task_ids:
#             for r in (await session.execute(
#                 select(ResearchResult).where(ResearchResult.task_id.in_(task_ids))
#             )).scalars().all():
#                 results_map[r.task_id] = r

#     return {
#         "total":  len(tasks),
#         "limit":  limit,
#         "offset": offset,
#         "items": [
#             {
#                 "id":                t.task_id,
#                 "task_id":           t.task_id,
#                 "business_id":       t.business_id,
#                 "business_name":     t.business_name,
#                 "status":            t.status,
#                 "created_at":        t.created_at,
#                 "competitors_count": len(getattr(results_map.get(t.task_id), "competitors_clean", None) or []),
#                 "has_analysis":      bool(getattr(results_map.get(t.task_id), "competitor_analysis", None)),
#                 "has_report":        bool(getattr(results_map.get(t.task_id), "final_report", None)),
#             }
#             for t in tasks
#         ],
#     }


# @router.get("/result/{task_id}")
# async def get_result(task_id: str):
#     """Lấy kết quả cuối sau khi pipeline completed."""
#     if task_id not in TASK_STORE:
#         found = await load_task_from_db(task_id)
#         if not found:
#             raise HTTPException(status_code=404, detail="Task ID không tồn tại")

#     task = TASK_STORE[task_id]
#     if task["status"] != "completed":
#         raise HTTPException(
#             status_code=400,
#             detail=f"Task chưa hoàn thành (status: {task['status']})",
#         )

#     for event_str in reversed(task["events"]):
#         if '"node": "FINISHED"' in event_str:
#             import json
#             try:
#                 data = json.loads(event_str.removeprefix("data: ").strip()).get("data", {})
#                 return {"task_id": task_id, "status": "completed", "result": data}
#             except Exception:
#                 break

#     raise HTTPException(status_code=500, detail="Không tìm thấy kết quả FINISHED")


# @router.post("/run", response_model=PipelineResponse)
# async def run(request: PipelineRequest):
#     """Endpoint đồng bộ. run_pipeline tự lo toàn bộ DB."""
#     try:
#         final = await run_pipeline(
#             business_name=request.business_name,
#             address=request.address,
#             industry=request.industry,
#             owner_id=request.owner_id,  
#         )
#         return PipelineResponse(
#             success=True,
#             hotel_dir=final["hotel_dir"],
#             competitors_clean=final.get("competitors_clean", []),
#             competitor_analysis=final.get("competitor_analysis", ""),
#             final_report=final.get("final_report", ""),
#             errors=final.get("errors", []),
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    


@router.post("/test")
async def test_pipeline(
    query: str = Query(..., description="Query nghiên cứu"),
    fb_url: str = Query("popup_only.html", description="Path file HTML Facebook"),
    business_id: str | None = Query(None, description="Business ID (optional)"),
    business_name: str | None = Query(None, description="Tên business hiển thị"),
):
    """Test endpoint — chạy đồng bộ, trả kết quả ngay."""

    result = await pipeline(
        query=query,
        fb_url=fb_url,
        business_id=business_id,
        business_name=business_name or query[:50],
    )

    return {
        "success": True,
        "task_id": result.get("task_id"),
        "business_id": business_id,
        "business_name": business_name or query[:50],
        "suggestions_count": result.get("suggestions_count", 0),
        "serp_urls_count": result.get("serp_urls_count", 0),
        "fb_posts_count": result.get("fb_posts_count", 0),
        "fb_comments_count": result.get("fb_comments_count", 0),
        "status": result.get("status", "done"),
    }


@router.get("/test/status/{task_id}")
async def test_status(task_id: str):
    """Kiểm tra nhanh status + event count."""
    async with AsyncSessionLocal() as session:
        task = (await session.execute(
            select(PipelineTask).where(PipelineTask.task_id == task_id)
        )).scalars().one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        events = (await session.execute(
            select(PipelineEvent).where(PipelineEvent.task_id == task_id)
        )).scalars().all()

        return {
            "task_id": task_id,
            "status": task.status,
            "business_id": task.business_id,
            "business_name": task.business_name,
            "query": task.query,
            "events": len(events),
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }