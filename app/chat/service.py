from __future__ import annotations

import asyncio
import json
import logging
import traceback
import uuid
from typing import AsyncGenerator

from langgraph.types import Command
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func

from app.chat.models import Conversation, Message
from app.graph import main_v7

logger = logging.getLogger(__name__)

_MAX_SECONDS     = 30.0
_RECURSION_LIMIT = 20

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


# ── Stream ────────────────────────────────────────────────

async def _stream_guarded(app, graph_input, thread_id: str):
    pipeline_error: str | None = None
    try:
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": _RECURSION_LIMIT}
        async with asyncio.timeout(_MAX_SECONDS):
            async for chunk in app.astream(graph_input, config=config):
                if "__interrupt__" in chunk:
                    payload = chunk["__interrupt__"][0].value
                    yield "interrupt", json.dumps(payload, ensure_ascii=False)
                    return
                for node_key in chunk:
                    if not node_key.startswith("__"):
                        yield "node", node_key
    except asyncio.TimeoutError:
        logger.error("[stream] timeout thread=%s", thread_id)
        pipeline_error = "timeout"
    except Exception as e:
        logger.error("[stream] CRASH (%s): %s thread=%s", type(e).__name__, e, thread_id)
        pipeline_error = repr(e)
    finally:
        if pipeline_error:
            yield "error", pipeline_error
        yield "done", None


async def _get_snapshot(app, thread_id: str):
    try:
        return await app.aget_state({"configurable": {"thread_id": thread_id}})
    except Exception as e:
        logger.error("[snapshot] failed thread=%s: %s", thread_id, e)
        return None


# ── Helpers ───────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

def _thread_id(conversation_id: str, session_id: str) -> str:
    return f"conv_{conversation_id}" if conversation_id else f"sess_{session_id}"

def _node_label(key: str) -> str:
    return NODE_LABELS.get(key) or NODE_LABELS.get(key.removeprefix("node_")) or key


# ── Builders ──────────────────────────────────────────────

def _text(text: str)          -> dict: return {"type": "text_response", "text": text}
def _empty()                  -> dict: return {"type": "empty_state", "message": "Đang xử lý..."}
def _result(components: list) -> dict: return {"components": components}

def _error(e: Exception | None) -> dict:
    if isinstance(e, TimeoutError):
        msg, code = "Hệ thống quá tải, thử lại.", "TIMEOUT_ERROR"
    elif e:
        msg, code = "Lỗi xử lý, thử lại.", "PIPELINE_CRASH"
    else:
        msg, code = "Chưa tạo được nội dung.", "EMPTY_STATE"
    debug = "".join(traceback.format_exception(type(e), e, e.__traceback__)) if e else ""
    return {"type": "error", "message": msg, "code": code, "debug": debug}

def _human_review(draft: str, instruction: str, **ctx) -> dict:
    return {"type": "human_review", "draft": draft, "instruction": instruction, **ctx}

def _snapshot_to_result(snapshot, error: Exception | None, **ctx) -> dict:
    if not snapshot or error:
        return _result([_error(error)])

    state = snapshot.values or {}

    if any(bool(t.interrupts) for t in (snapshot.tasks or [])):
        for task in (snapshot.tasks or []):
            if task.interrupts:
                val = task.interrupts[0].value
                draft = (val.get("draft") or val.get("text", "")) if isinstance(val, dict) else ""
                return _result([_human_review(draft=draft,
                    instruction="Review nội dung. Chọn Duyệt hoặc Từ chối.", **ctx)])

    if isinstance(final := state.get("final_response"), dict):
        if text := final.get("payload", {}).get("text"):
            return _result([_text(text)])

    return _result([_empty()])


# ── DB helpers ────────────────────────────────────────────

async def _save_user_msg(db: AsyncSession, conv_id: uuid.UUID, content: str, msg_id: str) -> None:
    db.add(Message(id=msg_id, conversation_id=conv_id,
                   role="user", status="completed", content=content))
    await db.commit()

async def _save_assistant_pending(db: AsyncSession, conv_id: uuid.UUID, msg_id: str) -> None:
    db.add(Message(id=msg_id, conversation_id=conv_id,
                   role="assistant", status="streaming", content="", html=""))
    await db.commit()

async def _update_msg(db: AsyncSession, msg_id: str, payload: dict,
                      status: str = "completed", error: str = "") -> None:
    content = next((c.get("text", "") for c in payload.get("components", [])
                    if c.get("type") == "text_response"), "")
    await db.execute(update(Message).where(Message.id == msg_id).values(
        content=content, html=json.dumps(payload, ensure_ascii=False),
        status=status, error_message=error, updated_at=func.now(),
    ))
    await db.commit()

async def _touch(db: AsyncSession, conv_id: uuid.UUID) -> None:
    await db.execute(update(Conversation).where(Conversation.id == conv_id)
                     .values(last_message_at=func.now(), updated_at=func.now()))
    await db.commit()

async def _history(db: AsyncSession, conv_id: uuid.UUID, limit: int = 10) -> list[dict]:
    rows = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id, Message.status == "completed")
        .order_by(Message.created_at.desc()).limit(limit)
    )
    return [{"role": m.role, "content": m.content}
            for m in reversed(rows.scalars().all()) if m.content]


# ── Core stream ───────────────────────────────────────────

async def _run_stream(
    thread_id: str, graph_input,
    session_id: str, msg_id: str = "",
    assistant_msg_id: str = "", conversation_id: str = "",
    db: AsyncSession | None = None,
) -> AsyncGenerator[str, None]:
    step, pipeline_error = 0, None

    try:
        async for event_type, value in _stream_guarded(main_v7, graph_input, thread_id):
            if event_type == "node":
                step += 1
                yield _sse("node", {"label": _node_label(value), "step": step})
            elif event_type == "interrupt":
                val = json.loads(value) if isinstance(value, str) else value
                result = _result([_human_review(
                    draft=val.get("draft", ""),
                    instruction=val.get("instruction", "Review nội dung."),
                    session_id=session_id, msg_id=msg_id, conversation_id=conversation_id,
                )])
                if assistant_msg_id and db:
                    await _update_msg(db, assistant_msg_id, result, status="interrupted")
                yield _sse("result", result)
                return
            elif event_type == "error":
                pipeline_error = Exception(value)
            elif event_type == "done":
                break

        snapshot = await _get_snapshot(main_v7, thread_id)
        result   = _snapshot_to_result(snapshot, pipeline_error,
                                       session_id=session_id, msg_id=msg_id,
                                       conversation_id=conversation_id)
        if assistant_msg_id and db:
            await _update_msg(db, assistant_msg_id, result,
                              status="error" if pipeline_error else "completed",
                              error=str(pipeline_error) if pipeline_error else "")
        yield _sse("result", result)

    except Exception as e:
        logger.exception("[run_stream] crash thread=%s", thread_id)
        err = _result([_error(e)])
        if assistant_msg_id and db:
            await _update_msg(db, assistant_msg_id, err, status="error", error=str(e))
        yield _sse("result", err)
    finally:
        yield _sse("done", {})


# ── ChatService ───────────────────────────────────────────

class ChatService:

    async def stream_graph(self, message: str, session_id: str,
                           msg_id: str = "", conversation_id: str = "",
                           db: AsyncSession | None = None) -> AsyncGenerator[str, None]:
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
                logger.exception("[stream_graph] DB setup failed")

        async for chunk in _run_stream(
            _thread_id(conversation_id, session_id),
            {"user_input": message, "language": "vi", "budget_limit": 2.0,
             "conversation_id": conversation_id, "msg_id": msg_id, "chat_history": history},
            session_id, msg_id=msg_id,
            assistant_msg_id=assistant_msg_id,
            conversation_id=conversation_id, db=db,
        ):
            yield chunk

    async def resume_graph(self, session_id: str, action: str, feedback: str = "",
                           msg_id: str = "", conversation_id: str = "",
                           db: AsyncSession | None = None) -> AsyncGenerator[str, None]:
        assistant_msg_id = ""
        if db and conversation_id:
            try:
                conv = await db.get(Conversation, uuid.UUID(conversation_id))
                if conv:
                    assistant_msg_id = str(uuid.uuid4())
                    await _save_assistant_pending(db, conv.id, assistant_msg_id)
                    await _touch(db, conv.id)
            except Exception:
                logger.exception("[resume_graph] DB setup failed")

        async for chunk in _run_stream(
            _thread_id(conversation_id, session_id),
            Command(resume={"action": action.strip().lower(), "feedback": feedback.strip()}),
            session_id, msg_id=msg_id,
            assistant_msg_id=assistant_msg_id,
            conversation_id=conversation_id, db=db,
        ):
            yield chunk

    async def restore_session(self, session_id: str, conversation_id: str = "",
                               db: AsyncSession | None = None):
        if db and conversation_id:
            return await _history(db, uuid.UUID(conversation_id), limit=50)
        snapshot = await _get_snapshot(main_v7, _thread_id(conversation_id, session_id))
        return _snapshot_to_result(snapshot, None) if snapshot else None