from fastapi import APIRouter, HTTPException
from .schemas import (
    StartRequest, ResumeRequest, WorkflowResponse, SessionResponse,
    ChatEditRequest, ChatInlineRequest, ChatResponse, VersionHistoryResponse,
    SessionListResponse
)
from .service import WorkflowService
from typing import Optional


router = APIRouter(prefix="/marketing", tags=["marketing"])
service = WorkflowService()

# ══════════════════════════════════════════════════════════════
# CORE WORKFLOW API (6 endpoints cũ — giữ nguyên)
# ══════════════════════════════════════════════════════════════

@router.post("/session", response_model=SessionResponse)
async def create_session():
    return {"session_id": service.create_session()}

@router.post("/start", response_model=WorkflowResponse)
async def start(body: StartRequest):
    result = await service.start(
        request=body.request, 
        brand_id=body.brand_id, 
        auto_mode=body.auto_mode
    )
    return WorkflowResponse(**result)

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
# CHAT API (Mới — Phương án C: Inline AI + Chat Sidebar)
# ══════════════════════════════════════════════════════════════

@router.post("/chat/edit", response_model=ChatResponse)
async def chat_edit(body: ChatEditRequest):
    """
    Chat sidebar: rewrite toàn bộ draft.
    Dùng cho yêu cầu phức tạp: "đổi tone", "thêm CTA", "viết lại toàn bài".
    """
    result = await service.chat_edit(body.draft, body.instruction)
    return ChatResponse(**result)

@router.post("/chat/inline", response_model=ChatResponse)
async def chat_inline(body: ChatInlineRequest):
    """
    Inline AI: rewrite đoạn bôi đen.
    Dùng cho sửa nhanh: "ngắn hơn", "thêm emoji", "viết hay hơn".
    Trả về diff để UI highlight changes.
    """
    result = await service.chat_inline(body.paragraph, body.instruction, body.context)
    return ChatResponse(**result)

# ══════════════════════════════════════════════════════════════
# VERSION HISTORY (Mới — Màn 4 Diff Review)
# ══════════════════════════════════════════════════════════════

@router.get("/{session_id}/versions", response_model=VersionHistoryResponse)
async def get_versions(session_id: str):
    """
    Lấy version history để so sánh diff (Màn 4 Review Mode).
    """
    result = await service.get_versions(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return VersionHistoryResponse(**result)


