from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List
from datetime import datetime


class StartRequest(BaseModel):
    request: str = Field(..., description="Yêu cầu từ người dùng (VD: Viết bài blog về AI)")
    brand_id: str = Field(..., description="ID của thương hiệu để lấy context")
    group: Literal["blog_web", "email_sale", "social_media"] = Field(
        default="blog_web",
        description="Nhóm nội dung: blog_web, email_sale, social_media"
    )
    function: str = Field(
        default="blog_post",
        description="Chức năng cụ thể trong nhóm (VD: blog_post, product_description, website_copy)"
    )
    auto_mode: bool = Field(default=False, description="Chế độ tự động duyệt bài")
    selected_option_text: Optional[str] = Field(
        default=None,
        description="Văn bản của option mà user đã chọn sau khi bị hệ thống nhắc nhở (Lượt 2)"
    )

class ResumeRequest(BaseModel):
    action: Literal["approve", "edit", "reject"]
    content: Optional[str] = None
    group: Literal["blog_web", "email_sale", "social_media"] = Field(
        default="blog_web",
        description="Nhóm nội dung để chọn graph đúng"
    )


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
    instruction: str

class ChatInlineRequest(BaseModel):
    """Inline AI: rewrite đoạn bôi đen."""
    paragraph: str           # Đoạn văn bôi đen
    instruction: str         # Yêu cầu ngắn (ví dụ: "ngắn hơn")
    context: str             # Toàn bài viết để giữ tone

class ChatEditResponse(BaseModel):
    session_id: str
    draft: str
    usage: Dict[str, Any]

class ChatInlineResponse(BaseModel):
    session_id: str
    draft: Dict[str, Any]
    usage: Dict[str, Any]
    changes: Optional[List[dict]] = None

class VersionHistoryResponse(BaseModel):
    """Trả về list versions cho Màn 4 (Diff Review)."""
    session_id: str
    versions: List[Dict[str, Any]]
    current_version: int


class SessionListItem(BaseModel):
    session_id: str
    status: Literal["running", "paused", "completed", "error", "failed", "queued"]  # ✅
    request: Optional[str] = None
    draft: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    publish_status: Optional[str] = None
    approved: Optional[bool] = None
    usage: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class WorkflowResponse(BaseModel):
    session_id: str
    status: Literal["running", "paused", "completed", "error", "failed", "queued"]  # ✅
    draft: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    publish_status: Optional[str] = None
    approved: Optional[bool] = None
    usage: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SessionListResponse(BaseModel):
    items: List[SessionListItem]
    total: int
    limit: int
    offset: int


class ClarificationOption(BaseModel):
    id: str = Field(..., description="ID định danh cho lựa chọn (VD: opt_1)")
    title: str = Field(..., description="Tiêu đề hướng tiếp cận")
    preview: str = Field(..., description="Mô tả tóm tắt nội dung sẽ triển khai")

class ClarificationResponse(BaseModel):
    status: Literal["requires_clarification"] = "requires_clarification"
    clarification_type: Literal["options", "rewrite"]
    message: str
    options: Optional[List[ClarificationOption]] = None