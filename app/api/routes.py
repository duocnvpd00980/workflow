from fastapi import APIRouter
from app.api.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    reply = "hello"
    return ChatResponse(reply=reply, session_id=req.session_id)
