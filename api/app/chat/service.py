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

_TIMEOUT         = 30.0
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


# ── Helpers ───────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

def _node_label(key: str) -> str:
    return NODE_LABELS.get(key) or key

def _thread_id(conversation_id: str, session_id: str) -> str:
    return f"conv_{conversation_id}" if conversation_id else f"sess_{session_id}"

def _read(obj: object | dict, key: str, default=None):
    """Đọc field từ Pydantic object hoặc dict — an toàn cả hai dạng."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# ── Result builder ────────────────────────────────────────

def _build_result(snapshot, pipeline_error: Exception | None) -> dict:
    """
    Đọc StandardFrame[BodyFrame] từ MainBus.final_response và serialize
    thành SSE result dict.

    MainBus.final_response kiểu BusFrame = StandardFrame[BodyFrame] | None.
    LangGraph có thể trả về object hoặc dict — _read() xử lý cả hai.

    Contract đầu ra:
        status        : "success" | "fallback" | "review" | "error"
        text          : câu trả lời (BodyFrame.text)
        answer_source : "cache"|"rag"|"llm"|"search"  (BodyFrame.state)
        confidence    : float                          (BodyFrame.state)
        sources       : list[{...}]                   (BodyFrame.records)
        metrics       : {latency_ms, model, ...}      (BodyFrame.metrics)
        error         : {code, message, retryable} | None
    """

    # ── Pipeline crash / timeout trước khi graph emit ─────────────────────
    if pipeline_error or not snapshot:
        code = "TIMEOUT" if isinstance(pipeline_error, TimeoutError) else "PIPELINE_CRASH"
        msg  = "Hệ thống quá tải, thử lại." if isinstance(pipeline_error, TimeoutError) \
               else "Lỗi xử lý, thử lại."
        return {
            "status":        "error",
            "text":          "",
            "answer_source": "llm",
            "confidence":    0.0,
            "sources":       [],
            "metrics":       {},
            "error":         {"code": code, "message": msg, "retryable": True},
        }

    state = snapshot.values or {}

    # ── Human-in-the-loop interrupt ───────────────────────────────────────
    for task in (snapshot.tasks or []):
        if task.interrupts:
            val = task.interrupts[0].value if task.interrupts else {}
            return {
                "status":        "review",
                "text":          val.get("draft", "") if isinstance(val, dict) else "",
                "answer_source": "llm",
                "confidence":    0.0,
                "sources":       [],
                "metrics":       {},
                "error":         None,
                "review": {
                    "instruction": val.get("instruction", "Review nội dung."),
                },
            }

    # ── Đọc StandardFrame từ MainBus.final_response ───────────────────────
    # snapshot.values["final_response"] = StandardFrame object hoặc dict
    # tuỳ theo LangGraph version và cách Pydantic validate BusFrame field
    fr = state.get("final_response")

    log.debug("[_build_result] state keys=%s", list(state.keys()))
    log.debug("[_build_result] final_response type=%s", type(fr))

    if fr is None:
        return {
            "status":        "error",
            "text":          "",
            "answer_source": "llm",
            "confidence":    0.0,
            "sources":       [],
            "metrics":       {},
            "error":         {
                "code":      "NO_FRAME",
                "message":   "final_response chưa được emit lên Bus.",
                "retryable": False,
            },
        }

    # ── Lấy payload từ StandardFrame (object hoặc dict) ───────────────────
    payload = _read(fr, "payload")

    log.debug("[_build_result] payload type=%s", type(payload))

    if payload is None:
        return {
            "status":        "error",
            "text":          "",
            "answer_source": "llm",
            "confidence":    0.0,
            "sources":       [],
            "metrics":       {},
            "error":         {
                "code":      "NO_PAYLOAD",
                "message":   "StandardFrame.payload là None.",
                "retryable": False,
            },
        }

    # ── Đọc BodyFrame fields ──────────────────────────────────────────────
    bf_status  = _read(payload, "status",  "FAILED")
    bf_text    = _read(payload, "text",    "")
    bf_records = _read(payload, "records", [])
    bf_state   = _read(payload, "state",   {})
    bf_metrics = _read(payload, "metrics", {})
    bf_error   = _read(payload, "error",   None)

    log.debug(
        "[_build_result] bf_status=%s text_len=%d source=%s confidence=%s",
        bf_status, len(bf_text),
        bf_state.get("answer_source", "?"),
        bf_state.get("confidence", "?"),
    )

    # ── Map BodyFrame → SSE status ────────────────────────────────────────
    finish_reason = bf_state.get("finish_reason", "")
    if bf_status == "SUCCESS":
        sse_status = "fallback" if finish_reason == "fallback" else "success"
    else:
        sse_status = "error"

    return {
        "status":        sse_status,
        "text":          bf_text,
        "answer_source": bf_state.get("answer_source", "llm"),
        "confidence":    bf_state.get("confidence", 0.0),
        "sources":       bf_records,
        "metrics": {
            "latency_ms":    bf_metrics.get("latency_ms", 0.0),
            "model":         bf_metrics.get("model", ""),
            "input_tokens":  bf_metrics.get("input_tokens", 0),
            "output_tokens": bf_metrics.get("output_tokens", 0),
            "node_path":     bf_metrics.get("node_path", []),
        },
        "error": {
            "code":      "UPSTREAM_FAILED",
            "message":   bf_error,
            "retryable": False,
        } if bf_error else None,
    }


# ── DB helpers ────────────────────────────────────────────

async def _save_user_msg(
    db: AsyncSession, conv_id: uuid.UUID, content: str, msg_id: str,
) -> None:
    db.add(Message(
        id=msg_id, conversation_id=conv_id,
        role="user", status="completed", content=content,
    ))
    await db.commit()

async def _save_assistant_pending(
    db: AsyncSession, conv_id: uuid.UUID, msg_id: str,
) -> None:
    db.add(Message(
        id=msg_id, conversation_id=conv_id,
        role="assistant", status="streaming", content="",
    ))
    await db.commit()

async def _update_msg(db: AsyncSession, msg_id: str, result: dict) -> None:
    # "success" | "fallback" | "review" → completed
    # "error"                           → error
    db_status = "completed" if result["status"] in ("success", "fallback", "review") else "error"
    await db.execute(
        update(Message).where(Message.id == msg_id).values(
            content    = result.get("text", ""),
            status     = db_status,
            updated_at = func.now(),
        )
    )
    await db.commit()

async def _touch(db: AsyncSession, conv_id: uuid.UUID) -> None:
    await db.execute(
        update(Conversation).where(Conversation.id == conv_id)
        .values(last_message_at=func.now(), updated_at=func.now())
    )
    await db.commit()

async def _history(
    db: AsyncSession, conv_id: uuid.UUID, limit: int = 10,
) -> list[dict]:
    rows = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id, Message.status == "completed")
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return [
        {"role": m.role, "content": m.content}
        for m in reversed(rows.scalars().all()) if m.content
    ]


# ── Core stream ───────────────────────────────────────────

async def _run_stream(
    thread_id:        str,
    graph_input,
    session_id:       str,
    msg_id:           str = "",
    assistant_msg_id: str = "",
    conversation_id:  str = "",
    db:               AsyncSession | None = None,
) -> AsyncGenerator[str, None]:
    step           = 0
    pipeline_error: Exception | None = None
    config = {
        "configurable":   {"thread_id": thread_id},
        "recursion_limit": _RECURSION_LIMIT,
    }

    try:
        async with asyncio.timeout(_TIMEOUT):
            async for chunk in main_v7.astream(graph_input, config=config):

                # interrupt — xử lý ngay, không đợi snapshot
                if "__interrupt__" in chunk:
                    val = chunk["__interrupt__"][0].value
                    result = {
                        "status":        "review",
                        "text":          val.get("draft", "") if isinstance(val, dict) else "",
                        "answer_source": "llm",
                        "confidence":    0.0,
                        "sources":       [],
                        "metrics":       {},
                        "error":         None,
                        "review": {
                            "instruction": val.get("instruction", "Review nội dung."),
                        },
                    }
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

    # ── Lấy snapshot sau khi stream kết thúc hoặc crash ──────────────────
    try:
        snapshot = await main_v7.aget_state({"configurable": {"thread_id": thread_id}})
    except Exception:
        log.exception("[stream] aget_state failed thread=%s", thread_id)
        snapshot = None

    result = _build_result(snapshot, pipeline_error)

    if assistant_msg_id and db:
        await _update_msg(db, assistant_msg_id, result)

    yield _sse("result", result)
    yield _sse("done", {})


# ── ChatService ───────────────────────────────────────────

class ChatService:

    async def stream_graph(
        self,
        message:         str,
        session_id:      str,
        msg_id:          str = "",
        conversation_id: str = "",
        db:              AsyncSession | None = None,
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
            {
                "user_input":      message,
                "language":        "vi",
                "budget_limit":    2.0,
                "conversation_id": conversation_id,
                "msg_id":          msg_id,
                "chat_history":    history,
            },
            session_id,
            msg_id           = msg_id,
            assistant_msg_id = assistant_msg_id,
            conversation_id  = conversation_id,
            db               = db,
        ):
            yield chunk

    async def resume_graph(
        self,
        session_id:      str,
        action:          str,
        feedback:        str = "",
        msg_id:          str = "",
        conversation_id: str = "",
        db:              AsyncSession | None = None,
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
            session_id,
            msg_id           = msg_id,
            assistant_msg_id = assistant_msg_id,
            conversation_id  = conversation_id,
            db               = db,
        ):
            yield chunk

    async def restore_session(
        self,
        session_id:      str,
        conversation_id: str = "",
        db:              AsyncSession | None = None,
    ):
        # Ưu tiên DB — đầy đủ, không phụ thuộc LangGraph memory
        if db and conversation_id:
            return await _history(db, uuid.UUID(conversation_id), limit=50)

        # Fallback: đọc snapshot từ LangGraph checkpointer
        try:
            snapshot = await main_v7.aget_state(
                {"configurable": {"thread_id": _thread_id(conversation_id, session_id)}}
            )
            return _build_result(snapshot, None) if snapshot else None
        except Exception:
            log.exception("[restore_session] aget_state failed")
            return None