from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, field_validator
import uuid


class StreamRequest(BaseModel):
    conversation_id: str
    message: str
    msg_id: str
    brand_id: Optional[str] = None
    business_id: Optional[str] = None

    @field_validator("conversation_id", "msg_id", mode="before")
    @classmethod
    def ensure_str(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class ResumeRequest(BaseModel):
    conversation_id: str
    msg_id: str
    action: str
    feedback: Optional[str] = None

    @field_validator("conversation_id", "msg_id", mode="before")
    @classmethod
    def ensure_str(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class RestoreRequest(BaseModel):
    conversation_id: str
    msg_id: str

    @field_validator("conversation_id", "msg_id", mode="before")
    @classmethod
    def ensure_str(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v