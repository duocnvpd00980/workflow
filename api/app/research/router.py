import uuid
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.research.schemas import PipelineRequest, PipelineResponse
from app.research.service import run_pipeline, pipeline_worker_task, TASK_STORE

router = APIRouter(
    prefix="/hotel-research",
    tags=["Hotel Research"],
)


@router.post("/run/stream")
async def run_stream(request: PipelineRequest, background_tasks: BackgroundTasks):
    """
    Endpoint tiếp nhận yêu cầu, đẩy vào Background Task chạy ngầm
    và trả về task_id ngay lập tức cho Frontend.
    """
    task_id = str(uuid.uuid4())
    
    # Khởi tạo TASK_STORE trước để tránh race condition
    TASK_STORE[task_id] = {
        "status": "running",
        "events": []
    }
    
    # Kích hoạt chạy ngầm
    background_tasks.add_task(
        pipeline_worker_task,
        task_id=task_id,
        business_name=request.business_name,
        address=request.address,
        industry=request.industry
    )
    
    return {"task_id": task_id, "status": "queued"}


@router.get("/stream/{task_id}")
async def get_realtime_stream(task_id: str):
    if task_id not in TASK_STORE:
        raise HTTPException(status_code=404, detail="Task ID không tồn tại")

    async def event_generator():
        # Mỗi lần client kết nối (kể cả F5), sent_index reset về 0
        # để bắn lại toàn bộ lịch sử event cũ từ RAM lên UI
        sent_index = 0
        
        while True:
            task = TASK_STORE.get(task_id)
            if not task:
                break
            
            # Gửi tất cả event chưa gửi
            while sent_index < len(task["events"]):
                yield task["events"][sent_index]
                sent_index += 1
                
            # Thoát nếu task đã xong hoặc lỗi
            if task["status"] in ["completed", "failed"]:
                # Đợi thêm 1 giây để đảm bảo client nhận hết dữ liệu cuối
                await asyncio.sleep(1)
                # Gửi lại lần cuối nếu có event mới trong lúc đợi
                while sent_index < len(task["events"]):
                    yield task["events"][sent_index]
                    sent_index += 1
                break
                
            # Polling mỗi 500ms
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Tắt buffering của nginx nếu có
        }
    )


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Endpoint phụ để kiểm tra trạng thái task nhanh không cần stream"""
    if task_id not in TASK_STORE:
        raise HTTPException(status_code=404, detail="Task ID không tồn tại")
    
    task = TASK_STORE[task_id]
    return {
        "task_id": task_id,
        "status": task["status"],
        "total_events": len(task["events"]),
    }


@router.post("/run", response_model=PipelineResponse)
async def run(request: PipelineRequest):
    """
    Endpoint đồng bộ, đợi pipeline chạy xong mới trả kết quả.
    """
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
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )