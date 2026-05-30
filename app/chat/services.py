# =============================================================================
# FILE: chat/services.py (Bản sửa đổi tối ưu hóa Real-time Stream)
# =============================================================================
from __future__ import annotations

import json
import logging
import traceback
import uuid
import asyncio  # <-- Thêm asyncio để xử lý mượt luồng dữ liệu
from asgiref.sync import sync_to_async
from django.utils import timezone
from langgraph.types import Command

from agent_os.streaming import stream_guarded
from agent_os.workflows.app_state import get_main_app
from agent_os.system.main import _safe_get_snapshot
from chat.models import Conversation, Message

logger = logging.getLogger(__name__)

# [Giữ nguyên cấu trúc NODE_LABELS, _make_thread_id, _node_label, _sse]
NODE_LABELS: dict[str, str] = {
    "input_guard": "Kiểm duyệt đầu vào",
    "supervisor": "Supervisor",
    "knowledge": "Knowledge Agent",
    "marketing": "Marketing Agent",
    "lightweight_chat": "Chat nhanh",
    "evaluator": "Đánh giá kết quả",
    "aggregator": "Tổng hợp",
    "output_guard": "Kiểm duyệt đầu ra",
    "human_review": "Human Review",
    "final_response": "Hoàn tất",
}


def _make_thread_id(conversation_id: str, session_id: str) -> str:
    if conversation_id:
        return f"conv_{conversation_id}"
    return f"sess_{session_id}"


def _node_label(node_key: str) -> str:
    return (
        NODE_LABELS.get(node_key)
        or NODE_LABELS.get(node_key.removeprefix("node_"))
        or node_key
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# [Giữ nguyên các hàm DB helpers từ bản cũ của bạn sang...]
@sync_to_async(thread_sensitive=False)
def _get_or_create_conversation(user, conversation_id: str) -> Conversation:
    if user is not None:
        conv, _ = Conversation.objects.get_or_create(
            id=conversation_id, defaults={"user": user, "title": ""}
        )
    else:
        conv = Conversation.objects.get(id=conversation_id)
    return conv


@sync_to_async(thread_sensitive=False)
def _create_user_message(
    conversation: Conversation, content: str, msg_id: str
) -> Message:
    return Message.objects.create(
        id=msg_id,
        conversation=conversation,
        role=Message.Role.USER,
        status=Message.Status.COMPLETED,
        content=content,
    )


@sync_to_async(thread_sensitive=False)
def _create_assistant_message_pending(
    conversation: Conversation, msg_id: str
) -> Message:
    return Message.objects.create(
        id=msg_id,
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        status=Message.Status.STREAMING,
        content="",
        html="",
    )


@sync_to_async(thread_sensitive=False)
def _update_assistant_message(
    msg_id: str,
    payload: dict,
    status: str = Message.Status.COMPLETED,
    error_message: str = "",
) -> None:
    Message.objects.filter(id=msg_id).update(
        content=next(
            (
                c.get("text", "")
                for c in payload.get("components", [])
                if c.get("type") == "text_response"
            ),
            "",
        ),
        html=json.dumps(payload, ensure_ascii=False),
        status=status,
        error_message=error_message,
        updated_at=timezone.now(),
    )


@sync_to_async(thread_sensitive=False)
def _update_assistant_message_interrupted(msg_id: str, payload: dict) -> None:
    Message.objects.filter(id=msg_id).update(
        html=json.dumps(payload, ensure_ascii=False),
        status=Message.Status.INTERRUPTED,
        updated_at=timezone.now(),
    )


@sync_to_async(thread_sensitive=False)
def _touch_conversation(conversation_id: str) -> None:
    Conversation.objects.filter(id=conversation_id).update(
        last_message_at=timezone.now(), updated_at=timezone.now()
    )


@sync_to_async(thread_sensitive=False)
def _set_conversation_title(conversation_id: str, title: str) -> None:
    Conversation.objects.filter(id=conversation_id, title="").update(title=title[:255])


@sync_to_async(thread_sensitive=False)
def _get_conversation_messages(conversation_id: str, limit: int = 20) -> list[dict]:
    messages = Message.objects.filter(
        conversation_id=conversation_id, status=Message.Status.COMPLETED
    ).order_by("-created_at")[:limit]
    return list(
        reversed(
            [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "status": m.status,
                    "content": m.content,
                    "payload": _safe_parse_json(m.html),
                }
                for m in messages
            ]
        )
    )


def _safe_parse_json(s: str) -> dict | None:
    try:
        return json.loads(s) if s else None
    except Exception:
        return None


# [JSON Builders của bạn...]
def _build_result(components: list[dict]) -> dict:
    return {"components": components}


def _build_text_response(text: str, title: str = "Kết quả") -> dict:
    return {"type": "text_response", "title": title, "text": text}


def _build_empty_state(message: str = "Đang xử lý...") -> dict:
    return {"type": "empty_state", "message": message}


def _build_error(error: Exception | None, code: str = "PIPELINE_CRASH") -> dict:
    if isinstance(error, TimeoutError):
        msg, code = "Hệ thống đang tải quá lâu. Vui lòng thử lại.", "TIMEOUT_ERROR"
    elif error is not None:
        msg = "Đã xảy ra lỗi trong quá trình xử lý. Vui lòng thử lại."
    else:
        msg, code = "Hệ thống chưa tạo được nội dung kết quả.", "EMPTY_STATE"
    debug = (
        "".join(traceback.format_exception(type(error), error, error.__traceback__))
        if error is not None
        else "Emergency Fallback."
    )
    return {"type": "error", "message": msg, "code": code, "debug": debug}


def _build_human_review(
    draft: str,
    instruction: str,
    session_id: str = "",
    msg_id: str = "",
    conversation_id: str = "",
) -> dict:
    return {
        "type": "human_review",
        "draft": draft,
        "instruction": instruction,
        "session_id": session_id,
        "msg_id": msg_id,
        "conversation_id": conversation_id,
    }


def _build_component(comp: dict) -> dict | None:
    if not isinstance(comp, dict):
        return None
    cid = comp.get("component_id", "text_response")
    props = comp.get("props", {})
    if not props and comp.get("text"):
        props = {"text": comp["text"], "title": comp.get("title", "Kết quả")}
    return {"type": cid, **props}


def _snapshot_to_json(
    snapshot,
    error: Exception | None,
    session_id: str = "",
    msg_id: str = "",
    conversation_id: str = "",
) -> dict:
    if snapshot is None or error:
        return _build_result([_build_error(error)])
    state: dict = snapshot.values if snapshot else {}
    has_interrupt = any(bool(task.interrupts) for task in (snapshot.tasks or []))
    if has_interrupt:
        draft = ""
        if snapshot.tasks:
            for task in snapshot.tasks:
                if task.interrupts:
                    val = task.interrupts[0].value
                    if isinstance(val, dict):
                        draft = val.get("draft") or val.get("text", "")
                    break
        if not draft:
            og_raw = state.get("output_guard")
            if isinstance(og_raw, dict):
                draft = og_raw.get("payload", {}).get("text", "")
        return _build_result(
            [
                _build_human_review(
                    draft=draft,
                    instruction="Review nội dung. Chọn Duyệt hoặc Từ chối kèm phản hồi.",
                    session_id=session_id,
                    msg_id=msg_id,
                    conversation_id=conversation_id,
                )
            ]
        )

    final_node = state.get("final_response")
    if isinstance(final_node, dict):
        payload = final_node.get("payload", {})
        components = payload.get("records", [])
        text = payload.get("text")
        if components:
            built = [c for comp in components if (c := _build_component(comp))]
            if built:
                return _build_result(built)
        if text:
            return _build_result([_build_text_response(text)])

    hr_raw = state.get("human_review")
    if isinstance(hr_raw, dict):
        payload = hr_raw.get("payload", {})
        if payload.get("status") == "SUCCESS" and payload.get("text"):
            return _build_result([_build_text_response(payload["text"])])
    return _build_result([_build_empty_state()])


# ─────────────────────────────────────────────────────────────────────────────
# TỐI ƯU HÓA TIẾN TRÌNH STREAM CORE
# ─────────────────────────────────────────────────────────────────────────────


async def _run_stream(
    main_app,
    thread_id: str,
    graph_input,
    session_id: str,
    msg_id: str = "",
    assistant_msg_id: str = "",
    conversation_id: str = "",
):
    step = 0
    try:
        pipeline_error: Exception | None = None

        async for event_type, value in stream_guarded(main_app, graph_input, thread_id):
            # 1. BẮN TRẠNG THÁI NODE NGAY LẬP TỨC
            if event_type == "node":
                step += 1
                yield _sse("node", {"label": _node_label(value), "step": step})

            # 2. HỖ TRỢ STREAM TOKEN THỜI GIAN THỰC (Nếu stream_guarded có trả về từ LLM)
            elif event_type in ("token", "on_chat_model_stream", "message_chunk"):
                token_text = ""
                if isinstance(value, str):
                    token_text = value
                elif isinstance(value, dict):
                    token_text = value.get("token") or value.get("content") or ""

                if token_text:
                    yield _sse("token", {"token": token_text})

            elif event_type == "interrupt":
                interrupt_payload = (
                    json.loads(value) if isinstance(value, str) else value
                )
                draft = interrupt_payload.get("draft") or interrupt_payload.get(
                    "text", ""
                )
                instruction = interrupt_payload.get("instruction", "Review nội dung.")
                result = _build_result(
                    [
                        _build_human_review(
                            draft=draft,
                            instruction=instruction,
                            session_id=session_id,
                            msg_id=msg_id,
                            conversation_id=conversation_id,
                        )
                    ]
                )
                if assistant_msg_id:
                    await _update_assistant_message_interrupted(
                        assistant_msg_id, result
                    )
                yield _sse("result", result)
                return

            elif event_type == "error":
                pipeline_error = Exception(value)

            elif event_type == "done":
                break

        # ── LẤY SNAPSHOT CUỐI CÙNG ──────────────────────────────────────────
        snapshot = await _safe_get_snapshot(main_app, thread_id)
        result = _snapshot_to_json(
            snapshot,
            pipeline_error,
            session_id=session_id,
            msg_id=msg_id,
            conversation_id=conversation_id,
        )

        # 3. MẸO GIẢI QUYẾT TRIỆT ĐỂ: Nếu hệ thống không hỗ trợ stream token thô,
        # Ta tiến hành phân rã chuỗi text thu được và stream giả lập tốc độ cao (Typewriter) về phía UI.
        components = result.get("components", [])
        text_response = next(
            (c for c in components if c.get("type") == "text_response"), None
        )

        if text_response and not pipeline_error:
            full_text = text_response.get("text", "")
            # Cắt nhỏ chuỗi văn bản thành từng cụm 2 ký tự và nhả dần ra môi trường mạng
            chunk_size = 2
            for i in range(0, len(full_text), chunk_size):
                await asyncio.sleep(0.01)  # Giãn cách siêu ngắn 10ms
                yield _sse("token", {"token": full_text[i : i + chunk_size]})

        # Cập nhật trạng thái lưu trữ tin nhắn vào Database bền vững
        if assistant_msg_id:
            status = (
                Message.Status.ERROR if pipeline_error else Message.Status.COMPLETED
            )
            await _update_assistant_message(
                assistant_msg_id,
                result,
                status=status,
                error_message=str(pipeline_error) if pipeline_error else "",
            )

        # Trả về gói kết quả cấu trúc tổng kết (Để UI render Markdown / Component nâng cao ổn định)
        yield _sse("result", result)

    except Exception as e:
        logger.exception("[_run_stream] Crash thread=%s: %r", thread_id, e)
        try:
            error_result = _build_result([_build_error(e)])
            if assistant_msg_id:
                await _update_assistant_message(
                    assistant_msg_id,
                    error_result,
                    status=Message.Status.ERROR,
                    error_message=str(e),
                )
            yield _sse("result", error_result)
        except Exception:
            pass
    finally:
        yield _sse("done", {})


# [Giữ nguyên cấu trúc Class ChatService bên dưới...]
class ChatService:
    async def stream_graph(
        self,
        message: str,
        session_id: str,
        msg_id: str = "",
        user=None,
        conversation_id: str = "",
    ):
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        if not msg_id:
            msg_id = str(uuid.uuid4())
        assistant_msg_id = ""
        history = []
        if user:
            try:
                conv = await _get_or_create_conversation(user, conversation_id)
                await _set_conversation_title(conversation_id, message)
                await _create_user_message(conv, message, msg_id)
                assistant_msg_id = str(uuid.uuid4())
                await _create_assistant_message_pending(conv, assistant_msg_id)
                await _touch_conversation(conversation_id)
                past = await _get_conversation_messages(conversation_id)
                history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in past
                    if m["content"]
                ]
            except Exception:
                logger.exception(
                    "[stream_graph] DB setup failed conv=%s", conversation_id
                )
                assistant_msg_id = ""
                history = []

        thread_id = _make_thread_id(conversation_id, session_id)
        initial_input = {
            "user_input": message,
            "language": "vi",
            "budget_limit": 2.0,
            "conversation_id": conversation_id,
            "msg_id": msg_id,
            "chat_history": history[-10:],
        }
        main_app = await get_main_app()
        async for chunk in _run_stream(
            main_app,
            thread_id,
            initial_input,
            session_id,
            msg_id=msg_id,
            assistant_msg_id=assistant_msg_id,
            conversation_id=conversation_id,
        ):
            yield chunk

    async def resume_graph(
        self,
        session_id: str,
        action: str,
        feedback: str = "",
        msg_id: str = "",
        conversation_id: str = "",
        user=None,
    ):
        if not conversation_id:
            return
        assistant_msg_id = ""
        try:
            conv = await _get_or_create_conversation(None, conversation_id)
            assistant_msg_id = str(uuid.uuid4())
            await _create_assistant_message_pending(conv, assistant_msg_id)
            await _touch_conversation(conversation_id)
        except Exception:
            logger.exception("[resume_graph] DB setup failed conv=%s", conversation_id)
        thread_id = _make_thread_id(conversation_id, session_id)
        cmd = Command(
            resume={"action": action.strip().lower(), "feedback": feedback.strip()}
        )
        main_app = await get_main_app()
        async for chunk in _run_stream(
            main_app,
            thread_id,
            cmd,
            session_id,
            msg_id=msg_id,
            assistant_msg_id=assistant_msg_id,
            conversation_id=conversation_id,
        ):
            yield chunk

    async def restore_session(self, session_id: str, conversation_id: str = ""):
        if conversation_id:
            return await _get_conversation_messages(conversation_id)
        thread_id = _make_thread_id("", session_id)
        main_app = await get_main_app()
        snapshot = await _safe_get_snapshot(main_app, thread_id)
        if snapshot:
            return _snapshot_to_json(snapshot, None)
        return None
