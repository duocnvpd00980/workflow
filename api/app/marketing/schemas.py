from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List

class StartRequest(BaseModel):
    request: str = Field(..., description="Yêu cầu từ người dùng (VD: Viết bài blog về AI)")
    brand_id: str = Field(..., description="ID của thương hiệu để lấy context") 
    auto_mode: bool = Field(default=False, description="Chế độ tự động duyệt bài")

class ResumeRequest(BaseModel):
    action: Literal["approve", "edit", "reject"]
    content: Optional[str] = None

class WorkflowResponse(BaseModel):
    session_id: str
    status: Literal["running", "paused", "completed", "error"]
    draft: Optional[Dict[str, Any]] = None
    publish_status: Optional[str] = None
    approved: Optional[bool] = None
    usage: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str

# ══════════════════════════════════════════════════════════════
# CHAT API (Mới — Phương án C: Inline AI + Chat Sidebar)
# ══════════════════════════════════════════════════════════════

class ChatEditRequest(BaseModel):
    """Chat sidebar: rewrite toàn bộ draft."""
    draft: str
    instruction: str

class ChatInlineRequest(BaseModel):
    """Inline AI: rewrite đoạn bôi đen."""
    paragraph: str           # Đoạn văn bôi đen
    instruction: str         # Yêu cầu ngắn (ví dụ: "ngắn hơn")
    context: str             # Toàn bài viết để giữ tone
    draft_id: Optional[str] = None  # Track version

class ChatResponse(BaseModel):
    """Response cho cả 2 loại chat."""
    draft: str               # Toàn bài mới (edit) hoặc đoạn mới (inline)
    usage: Dict[str, Any]
    changes: Optional[List[dict]] = None  # Diff cho inline (optional)

class VersionHistoryResponse(BaseModel):
    """Trả về list versions cho Màn 4 (Diff Review)."""
    session_id: str
    versions: List[Dict[str, Any]]
    current_version: int