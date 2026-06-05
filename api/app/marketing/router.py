from fastapi import APIRouter, HTTPException
from .schemas import StartRequest, ResumeRequest, WorkflowResponse, SessionResponse
from .service import WorkflowService

router = APIRouter(prefix="/marketing", tags=["marketing"])
service = WorkflowService()

@router.post("/session", response_model=SessionResponse)
async def create_session():
    return {"session_id": service.create_session()}

@router.post("/start", response_model=WorkflowResponse)
async def start(body: StartRequest):
    result = await service.start(body.request)
    return WorkflowResponse(**result)

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