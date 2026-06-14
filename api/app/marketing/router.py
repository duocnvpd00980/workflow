import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from .schemas import (
    StartRequest, ResumeRequest, WorkflowResponse, SessionResponse,
    ChatEditRequest, ChatInlineRequest, ChatEditResponse, ChatInlineResponse,
    VersionHistoryResponse,
    SessionListResponse, StartQueuedResponse
)
from .service import WorkflowService
from typing import Optional


router = APIRouter(prefix="/marketing", tags=["marketing"])
service = WorkflowService()

# ══════════════════════════════════════════════════════════════
# CORE WORKFLOW API
# ══════════════════════════════════════════════════════════════

@router.post("/session", response_model=SessionResponse)
async def create_session():
    return {"session_id": service.create_session()}

@router.post("/start", response_model=StartQueuedResponse, status_code=202)
async def start(body: StartRequest):
    """
    Nhận yêu cầu tạo content, trả về 202 ngay lập tức.
    Workflow chạy ngầm trong thread pool riêng biệt.
    """
    # Tạo session và queue task chạy ngầm, trả về ngay lập tức
    session_id = await service.start_queued(
        request=body.request,
        brand_id=body.brand_id,
        auto_mode=body.auto_mode,
    )
    
    return StartQueuedResponse(
        session_id=session_id,
        status="queued",
        message="Workflow đã được thêm vào hàng đợi. Kiểm tra trạng thái qua GET /marketing/{session_id}"
    )

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """Lấy danh sách tất cả bài viết trong kho."""
    result = await service.list_sessions(status=status, limit=limit, offset=offset)
    return SessionListResponse(**result)

@router.get("/{session_id}", response_model=WorkflowResponse)
async def get_status(session_id: str):
    result = await service.get_status(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return WorkflowResponse(**result)

@router.post("/{session_id}/resume", response_model=WorkflowResponse)
async def resume(session_id: str, body: ResumeRequest):
    result = await service.resume(session_id, body.action, body.content)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return WorkflowResponse(**result)

@router.post("/{session_id}/publish")
async def publish(session_id: str):
    result = await service.get_status(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "publish_status": result["publish_status"]}

@router.delete("/session/{session_id}")
async def delete(session_id: str):
    await service.delete(session_id)
    return {"ok": True}

# ══════════════════════════════════════════════════════════════
# CHAT API
# ══════════════════════════════════════════════════════════════

@router.post("/chat/edit", response_model=ChatEditResponse)
async def chat_edit(body: ChatEditRequest):
    result = await service.chat_edit(body.session_id, body.instruction)
    return ChatEditResponse(**result) 


@router.post("/chat/edit-stream")
async def chat_edit_stream(body: ChatEditRequest):
    async def event_generator():
        async for chunk in service.chat_edit_stream(body.session_id, body.instruction):
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )

@router.post("/chat/inline", response_model=ChatInlineResponse) 
async def chat_inline(body: ChatInlineRequest):
    result = await service.chat_inline(body.paragraph, body.instruction, body.context)
    return ChatInlineResponse(**result) 

# ══════════════════════════════════════════════════════════════
# VERSION HISTORY
# ══════════════════════════════════════════════════════════════

@router.get("/{session_id}/versions", response_model=VersionHistoryResponse)
async def get_versions(session_id: str):
    result = await service.get_versions(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return VersionHistoryResponse(**result)