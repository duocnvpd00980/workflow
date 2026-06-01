
from typing import Optional
from pydantic import BaseModel
import uuid

# ── Schemas ───────────────────────────────────────────────
class StreamRequest(BaseModel):
    message: str
    session_id: str
    conversation_id: uuid.UUID
    msg_id: Optional[str] = ""

class ResumeRequest(BaseModel):
    session_id: str
    action: str
    feedback: Optional[str] = ""
    msg_id: Optional[str] = ""
    conversation_id: uuid.UUID

class RestoreRequest(BaseModel):
    session_id: Optional[str] = ""
    conversation_id: uuid.UUID
    msg_id: Optional[str] = ""

