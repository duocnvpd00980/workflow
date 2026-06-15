import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse

from app.marketing.models import WorkflowSession
from .schemas import (
    StartRequest, ResumeRequest, WorkflowResponse, SessionResponse,
    ChatEditRequest, ChatInlineRequest, ChatEditResponse, ChatInlineResponse,
    VersionHistoryResponse,
    SessionListResponse, StartQueuedResponse
)
from .service import WorkflowService
from typing import Optional
from app.chat.models import Conversation
from sqlalchemy import select
from app.db import get_db


router = APIRouter(prefix="/marketing", tags=["marketing"])
service = WorkflowService()



# ── Helpers ───────────────────────────────────────────────

def _sse(gen) -> StreamingResponse:
    return StreamingResponse(
        gen,
        media_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

def _sse_error(msg: str) -> str:
    return (
        f"event: error\ndata: {json.dumps({'message': msg})}\n\n"
        "event: done\ndata: {}\n\n"
    )

# ══════════════════════════════════════════════════════════════
# CONVERSATION LINK API
# ══════════════════════════════════════════════════════════════

@router.get("/{session_id}/conversation")
async def get_or_create_conversation(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Lấy hoặc tạo conversation cho session. Mỗi session có 1 conversation riêng."""
    # 1. Tìm session
    result = await db.execute(
        select(WorkflowSession).where(WorkflowSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 2. Nếu đã có conversation → trả về
    if session.conversation_id:
        conv_result = await db.execute(
            select(Conversation).where(Conversation.id == str(session.conversation_id))
        )
        conv = conv_result.scalar_one_or_none()
        
        if conv:
            return {
                "conversation_id": str(conv.id),
                "title": conv.title,
                "created_at": conv.created_at,
                "exists": True
            }
    
    # 3. Tạo conversation mới
    new_conv = Conversation(title=f"Chat: {session.request[:50] if session.request else 'New'}")
    db.add(new_conv)
    await db.flush()
    
    # 4. Gán vào session
    session.conversation_id = str(new_conv.id)
    await db.commit()
    
    return {
        "conversation_id": str(new_conv.id),
        "title": new_conv.title,
        "created_at": new_conv.created_at,
        "exists": False
    }


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
    offset: int = 0,
    db: AsyncSession = Depends(get_db),  # ← THÊM db
):
    """Lấy danh sách tất cả bài viết trong kho."""
    result = await service.list_sessions(status=status, limit=limit, offset=offset, db=db)
    return SessionListResponse(**result)

@router.get("/{session_id}", response_model=WorkflowResponse)
async def get_status(session_id: str):  # ← Bỏ db dependency
    result = await service.get_status(session_id)  # ← Bỏ db=db
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
    async def event_stream():
        try:
            async for chunk in service.chat_edit_stream(body.session_id, body.instruction):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception:
            yield _sse_error("Lỗi hệ thống, vui lòng thử lại.")

    return _sse(event_stream())



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