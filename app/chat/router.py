# chat/router.py
from __future__ import annotations

import json
import logging
import uuid

from app.chat.schemas import RestoreRequest, ResumeRequest, StreamRequest
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.container import get_ctx, Services
from app.db import get_db
from .models import Conversation, Message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])




# ── Helpers ───────────────────────────────────────────────
def _sse(gen) -> StreamingResponse:
    return StreamingResponse(
        gen,
        media_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

def _title(text: str, limit: int = 60) -> str:
    text = " ".join(text.strip().split())
    return text if len(text) <= limit else text[:limit].rstrip() + "..."

def _sse_error(msg: str) -> str:
    return (
        f"event: error\ndata: {json.dumps({'message': msg})}\n\n"
        "event: done\ndata: {}\n\n"
    )


# ── Endpoints ─────────────────────────────────────────────
@router.post("/stream")
async def stream_message(
    payload: StreamRequest,
    db: AsyncSession = Depends(get_db),
    svc: Services = Depends(get_ctx),
):
    msg_id = payload.msg_id.strip() or str(uuid.uuid4())
    conversation_id = str(payload.conversation_id)

    conv = await db.get(Conversation, payload.conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found.")

    # Đặt title lần đầu (không block stream)
    if not conv.title:
        conv.title = _title(payload.message)
        await db.commit()

    async def event_stream():
        yield "event: heartbeat\ndata: {}\n\n"
        try:
            async for chunk in svc.chat.stream_graph(
                payload.message,
                payload.session_id,
                msg_id=msg_id,
                conversation_id=conversation_id,
            ):
                yield chunk
        except Exception:
            logger.exception("[stream] crashed — session=%s", payload.session_id)
            yield _sse_error("Lỗi hệ thống, vui lòng thử lại.")

    return _sse(event_stream())


@router.post("/resume")
async def resume_message(
    payload: ResumeRequest,
    svc: Services = Depends(get_ctx),
):
    async def event_stream():
        yield "event: heartbeat\ndata: {}\n\n"
        try:
            async for chunk in svc.chat.resume_graph(
                session_id=payload.session_id,
                action=payload.action,
                feedback=payload.feedback,
                msg_id=payload.msg_id,
                conversation_id=str(payload.conversation_id),
            ):
                yield chunk
        except Exception:
            logger.exception("[resume] crashed — session=%s", payload.session_id)
            yield _sse_error("Lỗi hệ thống khi tiếp tục xử lý.")

    return _sse(event_stream())


@router.post("/restore")
async def restore_chat(
    payload: RestoreRequest,
    svc: Services = Depends(get_ctx),
):
    session_id = payload.session_id.strip()
    conversation_id = str(payload.conversation_id)

    result = await svc.chat.restore_session(session_id, conversation_id=conversation_id)

    if isinstance(result, list):
        return {
            "type": "messages",
            "messages": result,
            "conversation_id": conversation_id,
            "session_id": session_id,
        }

    return {
        "type": "html",
        "html": result or "",
        "msg_id": payload.msg_id,
        "session_id": session_id,
    }


# ── Conversations CRUD ────────────────────────────────────
@router.post("/conversations", status_code=201)
async def conversation_create(db: AsyncSession = Depends(get_db)):
    conv = Conversation(title="")
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return {"id": str(conv.id), "title": conv.title}


@router.get("/conversations")
async def conversation_list(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Conversation).order_by(Conversation.last_message_at.desc())
    )
    return [
        {"id": str(c.id), "title": c.title, "last_message_at": c.last_message_at}
        for c in rows.scalars()
    ]


@router.get("/conversations/{conversation_id}")
async def conversation_load(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(404, "Không tìm thấy conversation.")

    rows = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return {
        "conversation_id": str(conv.id),
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "html": m.html,
                "created_at": m.created_at,
            }
            for m in rows.scalars()
        ],
    }


@router.delete("/conversations/{conversation_id}", status_code=204)
async def conversation_delete(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(404, "Không tìm thấy conversation.")
    await db.delete(conv)
    await db.commit()