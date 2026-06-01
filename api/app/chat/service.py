from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator

from langgraph.types import Command
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func

from app.chat.models import Conversation, Message
from app.graph import main_v7

log = logging.getLogger(__name__)

_TIMEOUT          = 30.0
_RECURSION_LIMIT  = 20

NODE_LABELS: dict[str, str] = {
    "input_guard":      "Kiểm duyệt đầu vào",
    "heuristic_router": "Định tuyến",
    "cache_read":       "Đọc cache",
    "knowledgebase":    "Knowledge",
    "relevance_check":  "Đánh giá",
    "generation":       "Sinh câu trả lời",
    "fallback_search":  "Tìm kiếm dự phòng",
    "output_guard":     "Kiểm duyệt đầu ra",
    "final_response":   "Hoàn tất",
}


# ── SSE helpers ───────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

def _node_label(key: str) -> str:
    return NODE_LABELS.get(key) or key

def _thread_id(conversation_id: str, session_id: str) -> str:
    return f"conv_{conversation_id}" if conversation_id else f"sess_{session_id}"


# ── Result builder ────────────────────────────────────────

def _build_result(snapshot, pipeline_error: Exception | None) -> dict:
    """Luôn trả về {"status": "success"|"error", "text": "..."}"""
    if pipeline_error or not snapshot:
        msg = "Hệ thống quá tải, thử lại." if isinstance(pipeline_error, TimeoutError) \
              else "Lỗi xử lý, thử lại."
        return {"status": "error", "text": msg}

    state = snapshot.values or {}

    # human-in-the-loop interrupt
    for task in (snapshot.tasks or []):
        if task.interrupts:
            val = task.interrupts[0].value
            draft = val.get("draft", "") if isinstance(val, dict) else ""
            return {"status": "review", "text": draft,
                    "instruction": val.get("instruction", "Review nội dung.")}

    # đọc kết quả từ final_response node
    fr = state.get("final_response") or {}
    payload = fr.get("payload") if isinstance(fr, dict) else {}
    text = (payload or {}).get("text", "") if isinstance(payload, dict) else ""

    if text:
        return {"status": "success", "text": text}

    return {"status": "error", "text": "Chưa tạo được nội dung."}


# ── DB helpers ────────────────────────────────────────────

async def _save_user_msg(db: AsyncSession, conv_id: uuid.UUID, content: str, msg_id: str) -> None:
    db.add(Message(id=msg_id, conversation_id=conv_id,
                   role="user", status="completed", content=content))
    await db.commit()

async def _save_assistant_pending(db: AsyncSession, conv_id: uuid.UUID, msg_id: str) -> None:
    db.add(Message(id=msg_id, conversation_id=conv_id,
                   role="assistant", status="streaming", content=""))
    await db.commit()

async def _update_msg(db: AsyncSession, msg_id: str, result: dict) -> None:
    status = "completed" if result["status"] == "success" else "error"
    await db.execute(
        update(Message).where(Message.id == msg_id).values(
            content=result.get("text", ""),
            status=status,
            updated_at=func.now(),
        )
    )
    await db.commit()

async def _touch(db: AsyncSession, conv_id: uuid.UUID) -> None:
    await db.execute(
        update(Conversation).where(Conversation.id == conv_id)
        .values(last_message_at=func.now(), updated_at=func.now())
    )
    await db.commit()

async def _history(db: AsyncSession, conv_id: uuid.UUID, limit: int = 10) -> list[dict]:
    rows = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id, Message.status == "completed")
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return [{"role": m.role, "content": m.content}
            for m in reversed(rows.scalars().all()) if m.content]


# ── Core stream ───────────────────────────────────────────

async def _run_stream(
    thread_id: str,
    graph_input,
    session_id: str,
    msg_id: str = "",
    assistant_msg_id: str = "",
    conversation_id: str = "",
    db: AsyncSession | None = None,
) -> AsyncGenerator[str, None]:
    step = 0
    pipeline_error: Exception | None = None
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": _RECURSION_LIMIT}

    try:
        async with asyncio.timeout(_TIMEOUT):
            async for chunk in main_v7.astream(graph_input, config=config):
                if "__interrupt__" in chunk:
                    val = chunk["__interrupt__"][0].value
                    result = {"status": "review",
                              "text": val.get("draft", "") if isinstance(val, dict) else "",
                              "instruction": val.get("instruction", "Review nội dung.")}
                    if assistant_msg_id and db:
                        await _update_msg(db, assistant_msg_id, result)
                    yield _sse("result", result)
                    return

                for key in chunk:
                    if not key.startswith("__"):
                        step += 1
                        yield _sse("node", {"label": _node_label(key), "step": step})

    except asyncio.TimeoutError:
        log.error("[stream] timeout thread=%s", thread_id)
        pipeline_error = TimeoutError()
    except Exception as e:
        log.exception("[stream] crash thread=%s", thread_id)
        pipeline_error = e

    # lấy snapshot và build result
    try:
        snapshot = await main_v7.aget_state({"configurable": {"thread_id": thread_id}})
    except Exception:
        snapshot = None

    result = _build_result(snapshot, pipeline_error)

    if assistant_msg_id and db:
        await _update_msg(db, assistant_msg_id, result)

    yield _sse("result", result)
    yield _sse("done", {})


# ── ChatService ───────────────────────────────────────────

class ChatService:

    async def stream_graph(
        self, message: str, session_id: str,
        msg_id: str = "", conversation_id: str = "",
        db: AsyncSession | None = None,
    ) -> AsyncGenerator[str, None]:
        msg_id          = msg_id or str(uuid.uuid4())
        conversation_id = conversation_id or str(uuid.uuid4())
        assistant_msg_id, history = "", []

        if db:
            try:
                conv = await db.get(Conversation, uuid.UUID(conversation_id))
                if conv:
                    await _save_user_msg(db, conv.id, message, msg_id)
                    assistant_msg_id = str(uuid.uuid4())
                    await _save_assistant_pending(db, conv.id, assistant_msg_id)
                    await _touch(db, conv.id)
                    history = await _history(db, conv.id)
            except Exception:
                log.exception("[stream_graph] db setup failed")

        async for chunk in _run_stream(
            _thread_id(conversation_id, session_id),
            {"user_input": message, "language": "vi", "budget_limit": 2.0,
             "conversation_id": conversation_id, "msg_id": msg_id, "chat_history": history},
            session_id, msg_id=msg_id,
            assistant_msg_id=assistant_msg_id,
            conversation_id=conversation_id, db=db,
        ):
            yield chunk

    async def resume_graph(
        self, session_id: str, action: str, feedback: str = "",
        msg_id: str = "", conversation_id: str = "",
        db: AsyncSession | None = None,
    ) -> AsyncGenerator[str, None]:
        assistant_msg_id = ""
        if db and conversation_id:
            try:
                conv = await db.get(Conversation, uuid.UUID(conversation_id))
                if conv:
                    assistant_msg_id = str(uuid.uuid4())
                    await _save_assistant_pending(db, conv.id, assistant_msg_id)
                    await _touch(db, conv.id)
            except Exception:
                log.exception("[resume_graph] db setup failed")

        async for chunk in _run_stream(
            _thread_id(conversation_id, session_id),
            Command(resume={"action": action.strip().lower(), "feedback": feedback.strip()}),
            session_id, msg_id=msg_id,
            assistant_msg_id=assistant_msg_id,
            conversation_id=conversation_id, db=db,
        ):
            yield chunk

    async def restore_session(
        self, session_id: str, conversation_id: str = "",
        db: AsyncSession | None = None,
    ):
        if db and conversation_id:
            return await _history(db, uuid.UUID(conversation_id), limit=50)
        try:
            snapshot = await main_v7.aget_state(
                {"configurable": {"thread_id": _thread_id(conversation_id, session_id)}}
            )
            return _build_result(snapshot, None) if snapshot else None
        except Exception:
            return None