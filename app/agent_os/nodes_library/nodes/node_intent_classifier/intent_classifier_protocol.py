# =========================================================
# FILE: intent_classifier_protocol.py
# =========================================================
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class IntentClassifierOutput(BaseModel):
    # Cấu hình default="qa" để nếu model sập, Pydantic vẫn tự điền vào -> Chống lỗi Missing Field
    mode: Literal["smalltalk", "qa", "marketing", "error"] = Field(default="qa")

    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_memory: bool = False
    requires_knowledge: bool = False

    # extra="ignore" giúp bỏ qua các field rác mà model sinh thêm (ví dụ: 'title', 'type')
    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
    )
