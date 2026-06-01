"""
Adapter endpoint — chuyển SSE nội bộ sang AI SDK Data Stream Protocol.
Thêm vào router.py hoặc mount riêng.

AI SDK Data Stream Protocol (text parts):
  0:"<text chunk>"\\n   — text delta
  8:[...]\\n            — metadata / error parts  (optional)
  d:{...}\\n            — finish signal

Docs: https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocols#data-stream-protocol
"""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.chat.service import ChatService
from app.chat.schemas import StreamRequest
from app.chat.models import Conversation

logger = logging.getLogger(__name__)
router_ai_sdk = APIRouter(prefix="/chat", tags=["chat-ai-sdk"])
_chat = ChatService()


# ── AI SDK format helpers ─────────────────────────────────

def _ai_text(chunk: str) -> str:
    """Part type 0 — text delta."""
    return f'0:{json.dumps(chunk, ensure_ascii=False)}\n'

def _ai_data(data: list) -> str:
    """Part type 2 — data (dùng để gửi metadata như node progress)."""
    return f'2:{json.dumps(data, ensure_ascii=False)}\n'

def _ai_error(msg: str) -> str:
    """Part type 3 — error."""
    return f'3:{json.dumps(msg, ensure_ascii=False)}\n'

def _ai_finish(reason: str = "stop") -> str:
    """Part type d — finish."""
    return f'd:{json.dumps({"finishReason": reason}, ensure_ascii=False)}\n'


def _title(text: str, limit: int = 60) -> str:
    text = " ".join(text.strip().split())
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


# ── Adapter stream ────────────────────────────────────────

async def _adapt(message: str, session_id: str, msg_id: str, conversation_id: str):
    """
    Đọc SSE nội bộ từ ChatService rồi re-emit theo AI SDK protocol.

    Internal events:
      event: heartbeat  → bỏ qua
      event: node       → gửi qua part type 2 (metadata), UI có thể dùng để show progress
      event: result     → text chính, emit qua part type 0 từng chunk (hoặc nguyên khối)
      event: done       → emit finish
      event: error      → emit error part
    """
    yield _ai_data([{"type": "heartbeat"}])          # ping ngay để browser không timeout

    async for raw in _chat.stream_graph(
        message,
        session_id,
        msg_id=msg_id,
        conversation_id=conversation_id,
        # db không truyền ở đây vì đã xử lý bên ngoài (xem endpoint bên dưới)
        # nếu muốn persist thì truyền db vào đây tương tự stream_message gốc
    ):
        # raw là chuỗi SSE: "event: xxx\ndata: {...}\n\n"
        event, data = _parse_sse(raw)

        if event is None:
            continue

        if event == "node":
            # gửi node progress như metadata — useChat sẽ nhận qua onData callback
            yield _ai_data([{"type": "node_progress", **data}])

        elif event == "result":
            status = data.get("status")
            text   = data.get("text", "")

            if status == "success" and text:
                # Emit toàn bộ text như một delta duy nhất.
                # Nếu muốn streaming từng ký tự thì split + asyncio.sleep(0) ở đây.
                yield _ai_text(text)

            elif status == "review":
                # Human-in-the-loop: gửi draft + instruction qua metadata
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

    # fallback nếu stream kết thúc mà không có done event
    yield _ai_finish("stop")


def _parse_sse(raw: str) -> tuple[str | None, dict]:
    """Parse 'event: xxx\\ndata: {...}\\n\\n' → (event_name, data_dict)."""
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


# ── Endpoint ──────────────────────────────────────────────

@router_ai_sdk.post("/stream/ai-sdk")
async def stream_ai_sdk(
    payload: StreamRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Drop-in endpoint cho AI SDK useChat / useCompletion.

    useChat config:
        api: "/chat/stream/ai-sdk"
        streamProtocol: "data"          // default, không cần ghi
        onData: (parts) => { ... }      // nhận node_progress & review events
    """
    msg_id          = payload.msg_id.strip() or str(uuid.uuid4())
    conversation_id = str(payload.conversation_id)

    conv = await db.get(Conversation, payload.conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found.")

    if not conv.title:
        conv.title = _title(payload.message)
        await db.commit()

    return StreamingResponse(
        _adapt(payload.message, payload.session_id, msg_id, conversation_id),
        media_type="text/plain; charset=utf-8",       # AI SDK yêu cầu text/plain
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            # Header bắt buộc để AI SDK nhận dạng đúng protocol
            "x-vercel-ai-data-stream": "v1",
        },
    )