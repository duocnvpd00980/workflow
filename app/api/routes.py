from fastapi import APIRouter
from app.api.schemas import ChatRequest, ChatResponse
from app.agents.workflow import run_agent

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    history = [m.model_dump() for m in req.history]
    reply = await run_agent(req.message, history, req.session_id)
    return ChatResponse(reply=reply, session_id=req.session_id)
