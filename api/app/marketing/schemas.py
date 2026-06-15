from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List
from datetime import datetime


class StartRequest(BaseModel):
    request: str = Field(..., description="Yêu cầu từ người dùng (VD: Viết bài blog về AI)")
    brand_id: str = Field(..., description="ID của thương hiệu để lấy context") 
    auto_mode: bool = Field(default=False, description="Chế độ tự động duyệt bài")

class ResumeRequest(BaseModel):
    action: Literal["approve", "edit", "reject"]
    content: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str

class StartQueuedResponse(BaseModel):
    session_id: str
    status: Literal["queued", "running"]
    message: str

# ══════════════════════════════════════════════════════════════
# CHAT API (Mới — Phương án C: Inline AI + Chat Sidebar)
# ══════════════════════════════════════════════════════════════

class ChatEditRequest(BaseModel):
    """Chat sidebar: rewrite toàn bộ draft."""
    session_id: str 
    draft: str
    instruction: str

class ChatInlineRequest(BaseModel):
    """Inline AI: rewrite đoạn bôi đen."""
    paragraph: str           # Đoạn văn bôi đen
    instruction: str         # Yêu cầu ngắn (ví dụ: "ngắn hơn")
    context: str             # Toàn bài viết để giữ tone
    draft_id: Optional[str] = None  # Track version

class ChatEditResponse(BaseModel):
    draft: str
    usage: Dict[str, Any]

class ChatInlineResponse(BaseModel):
    draft: str  # String content mới
    usage: Dict[str, Any]
    changes: Optional[List[dict]] = None

class VersionHistoryResponse(BaseModel):
    """Trả về list versions cho Màn 4 (Diff Review)."""
    session_id: str
    versions: List[Dict[str, Any]]
    current_version: int



class SessionListItem(BaseModel):
    session_id: str
    status: Literal["running", "paused", "completed", "error", "queued"]
    request: Optional[str] = None
    draft: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None  # ← THÊM
    publish_status: Optional[str] = None
    approved: Optional[bool] = None
    usage: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class WorkflowResponse(BaseModel):
    session_id: str
    status: Literal["running", "paused", "completed", "error", "queued"]
    draft: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None  # ← THÊM
    publish_status: Optional[str] = None
    approved: Optional[bool] = None
    usage: Optional[Dict[str, Any]] = None
    error: Optional[str] = None



class SessionListResponse(BaseModel):
    items: List[SessionListItem]
    total: int
    limit: int
    offset: int