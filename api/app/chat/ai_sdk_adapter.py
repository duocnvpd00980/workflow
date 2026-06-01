from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.chat.service import ChatService
from app.chat.models import Conversation

logger = logging.getLogger(__name__)
router_ai_sdk = APIRouter(prefix="/chat", tags=["chat-ai-sdk"])
_chat = ChatService()


def _ai_text(chunk: str) -> str:
    return f'0:{json.dumps(chunk, ensure_ascii=False)}\n'

def _ai_data(data: list) -> str:
    return f'2:{json.dumps(data, ensure_ascii=False)}\n'

def _ai_error(msg: str) -> str:
    return f'3:{json.dumps(msg, ensure_ascii=False)}\n'

def _ai_finish(reason: str = "stop") -> str:
    return f'd:{json.dumps({"finishReason": reason}, ensure_ascii=False)}\n'

def _title(text: str, limit: int = 60) -> str:
    text = " ".join(text.strip().split())
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


class MessagePart(BaseModel):
    type: str
    text: str | None = None

class UIMessage(BaseModel):
    id: str
    role: str
    parts: list[MessagePart]

class AIChatRequest(BaseModel):
    id: str | None = None
    messages: list[UIMessage] = Field(default_factory=list)
    trigger: str | None = None
    session_id: str
    conversation_id: str | None = None
    msg_id: str | None = ""


async def _adapt(
    message: str,
    session_id: str,
    msg_id: str,
    conversation_id: str,
    db: AsyncSession | None,
):
    async for raw in _chat.stream_graph(
        message,
        session_id,
        msg_id=msg_id,
        conversation_id=conversation_id,
    ):
        event, data = _parse_sse(raw)
        if event is None:
            continue

        if event == "node":
            yield _ai_data([{"type": "node_progress", **data}])

        elif event == "result":
            status = data.get("status")
            text = data.get("text", "")

            if status == "success" and text:
                yield _ai_text(text)
            elif status == "review":
                yield _ai_data([{
                    "type": "review",
                    "draft": text,
                    "instruction": data.get("instruction", ""),
                }])
            else:
                yield _ai_error(text or "Lỗi xử lý, thử lại.")

        elif event == "done":
            yield _ai_finish("stop")
            return

        elif event == "error":
            yield _ai_error(data.get("message", "Lỗi hệ thống."))
            yield _ai_finish("error")
            return

    yield _ai_finish("stop")


def _parse_sse(raw: str) -> tuple[str | None, dict]:
    event, data = None, {}
    for line in raw.strip().splitlines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            try:
                data = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                data = {}
    return event, data


@router_ai_sdk.post("/stream/ai-sdk")
async def stream_ai_sdk(
    payload: AIChatRequest,
    db: AsyncSession = Depends(get_db),
):
    # Extract message từ messages array
    message = ""
    if payload.messages and len(payload.messages) > 0:
        last_msg = payload.messages[-1]
        if last_msg.role == "user" and last_msg.parts:
            for part in last_msg.parts:
                if part.type == "text" and part.text:
                    message = part.text
                    break

    if not message:
        raise HTTPException(400, "No message found in request.")

    msg_id = payload.msg_id.strip() or str(uuid.uuid4())

    # === TỰ TẠO CONVERSATION MỚI NẾU KHÔNG TÌM THẤY ===
    conversation_id = payload.conversation_id
    conv = None

    if conversation_id:
        try:
            conv = await db.get(Conversation, uuid.UUID(conversation_id))
        except Exception:
            conv = None

    if not conv:
        # Tạo conversation mới
        conversation_id = str(uuid.uuid4())
        conv = Conversation(
            id=uuid.UUID(conversation_id),
            title=_title(message),
            session_id=payload.session_id,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

    elif not conv.title:
        conv.title = _title(message)
        await db.commit()

    return StreamingResponse(
        _adapt(message, payload.session_id, msg_id, conversation_id, db),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "x-vercel-ai-data-stream": "v1",
        },
    )