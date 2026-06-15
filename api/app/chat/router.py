from __future__ import annotations

import json
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db, AsyncSessionLocal
from app.chat.service import ChatService
from app.chat.schemas import RestoreRequest, ResumeRequest, StreamRequest
from .models import Conversation, Message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])
_chat = ChatService()


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


@router.post("/stream")
async def stream_message(
    payload: StreamRequest,
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, payload.conversation_id)
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")

    # ✅ TỰ SINH msg_id Ở SERVER — tránh trùng từ client
    msg_id = uuid.uuid4()

    # Tạo placeholder
    try:
        placeholder_msg = Message(
            id=msg_id,
            conversation_id=payload.conversation_id,
            role="assistant",
            content="",
            status="pending"
        )
        db.add(placeholder_msg)
        await db.commit()
    except Exception as e:
        logger.error(f"Placeholder failed: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Khởi tạo tin nhắn thất bại")

    await _chat.clear_stop_flag(payload.conversation_id)

    if not conv.title or conv.title == "New Chat":
        conv.title = _title(payload.message)
        await db.commit()

    # Trả msg_id về client qua header hoặc event đầu tiên
    async def event_stream():
        # Gửi msg_id cho client biết
        yield f"event: msg_id\ndata: {json.dumps({'msg_id': str(msg_id)})}\n\n"
        
        try:
            async for chunk in _chat.stream_graph(
                message=payload.message,
                msg_id=msg_id,  # ← Dùng msg_id server sinh
                conversation_id=payload.conversation_id,
                db=db,
                brand_id=payload.brand_id,
                business_id=payload.business_id,
            ):
                if await _chat.check_if_stopped(payload.conversation_id):
                    yield "event: Interrupted\ndata: {\"status\": \"stopped_by_user\"}\n\n"
                    break
                yield chunk
        except Exception:
            logger.exception("[stream] crashed")
            yield _sse_error("Lỗi hệ thống")
        finally:
            await _chat.clear_stop_flag(payload.conversation_id)

    return _sse(event_stream())


@router.post("/stop")
async def stop_stream(conversation_id: uuid.UUID):
    await _chat.mark_as_stopped(conversation_id)
    return {"status": "success", "message": "Signal to stop stream has been sent."}


@router.post("/resume")
async def resume_message(
    payload: ResumeRequest,
):
    await _chat.clear_stop_flag(payload.conversation_id)

    async def event_stream():
        yield "event: heartbeat\ndata: {}\n\n"
        async with AsyncSessionLocal() as stream_db:
            try:
                async for chunk in _chat.resume_graph(
                    action=payload.action,
                    feedback=payload.feedback,
                    msg_id=payload.msg_id,
                    conversation_id=payload.conversation_id,
                    db=stream_db,
                ):
                    if await _chat.check_if_stopped(payload.conversation_id):
                        yield "event: Interrupted\ndata: {\"status\": \"stopped_by_user\"}\n\n"
                        break
                    yield chunk
            except Exception:
                logger.exception("[resume] crashed — conv_id=%s", payload.conversation_id)
                yield _sse_error("Lỗi hệ thống khi tiếp tục xử lý.")
            finally:
                await _chat.clear_stop_flag(payload.conversation_id)

    return _sse(event_stream())


@router.post("/restore")
async def restore_chat(
    payload: RestoreRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await _chat.restore_session(
        conversation_id=payload.conversation_id,
        db=db,
    )

    if isinstance(result, list):
        return {
            "type": "messages", 
            "messages": result, 
            "conversation_id": payload.conversation_id
        }

    return {
        "type": "html", 
        "html": result or "", 
        "msg_id": payload.msg_id
    }


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def conversation_create(db: AsyncSession = Depends(get_db)):
    conv = Conversation()
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return {"id": conv.id, "title": conv.title}


@router.get("/conversations")
async def conversation_list(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(Conversation)
        .where(Conversation.title != "")
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at}
        for c in rows.scalars()
    ]


@router.get("/conversations/{conversation_id}")
async def conversation_load(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy conversation.")

    rows = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.status == "completed",
        )
        .order_by(Message.created_at)
    )
    return {
        "conversation_id": conv.id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in rows.scalars()
        ],
    }


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def conversation_delete(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy conversation.")
    await db.delete(conv)
    await db.commit()