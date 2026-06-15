from __future__ import annotations

import uuid
from typing import Optional
from pydantic import BaseModel


# ── Schemas ───────────────────────────────────────────────


class StreamRequest(BaseModel):
    """Request gửi tin nhắn mới và kích hoạt luồng AI stream."""

    conversation_id: uuid.UUID
    message: str
    msg_id: uuid.UUID

    # Ngữ cảnh để load_brand_voice / load_rag hoạt động (đều optional)
    brand_id: Optional[str] = None
    business_id: Optional[str] = None


class ResumeRequest(BaseModel):
    """Request khi user muốn AI tiếp tục chạy hoặc chỉnh sửa (Human-in-the-loop)."""

    conversation_id: uuid.UUID
    msg_id: uuid.UUID
    action: str
    feedback: Optional[str] = None


class RestoreRequest(BaseModel):
    """Request khi cần khôi phục lại trạng thái của một tin nhắn cũ."""

    conversation_id: uuid.UUID
    msg_id: uuid.UUID