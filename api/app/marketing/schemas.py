from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any

class StartRequest(BaseModel):
    request: str

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