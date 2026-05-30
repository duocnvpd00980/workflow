# chat/services.py
"""
ChatService — Django ASGI streaming service
────────────────────────────────────────────
Thread ID convention (production):
  conv_<conversation_id>   ← dùng conversation_id từ Django model

SSE events:
  node  → {"label": str}
  html  → {"html": str}
  done  → {}
"""

from __future__ import annotations

import json
import logging
import traceback
import uuid
from asgiref.sync import sync_to_async
from django.template.loader import render_to_string
from django.utils import timezone
from langgraph.types import Command

from agent_os.streaming import stream_guarded
from agent_os.workflows.app_state import get_main_app
from agent_os.system.main import _safe_get_snapshot
from chat.models import Conversation, Message

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Node labels
# ─────────────────────────────────────────────────────────────────────────────

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
    "final_response": "Render giao diện",
}

COMPONENT_TEMPLATES: dict[str, str] = {
    "text_response": "widgets/text_response.html",
    "source_list": "widgets/source_list.html",
    "ads_card": "widgets/ads_card.html",
    "email_template": "widgets/email_template.html",
    "blog_preview": "widgets/blog_preview.html",
    "campaign_summary": "widgets/campaign_summary.html",
    "error_card": "widgets/error_display.html",
    "empty_state": "widgets/empty_state.html",
    "human_review": "widgets/human_review.html",
}

# ─────────────────────────────────────────────────────────────────────────────
# Thread ID
# ─────────────────────────────────────────────────────────────────────────────


def _make_thread_id(conversation_id: str, session_id: str) -> str:
    """
    Production: dùng conversation_id để thread tồn tại lâu dài.
    Fallback về session_id nếu không có conversation_id (dev/test).
    """
    if conversation_id:
        return f"conv_{conversation_id}"
    return f"sess_{session_id}"


# ─────────────────────────────────────────────────────────────────────────────
# Pure helpers
# ─────────────────────────────────────────────────────────────────────────────

_render_async = sync_to_async(render_to_string, thread_sensitive=False)


def _node_label(node_key: str) -> str:
    return (
        NODE_LABELS.get(node_key)
        or NODE_LABELS.get(node_key.removeprefix("node_"))
        or node_key
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────


@sync_to_async(thread_sensitive=False)
def _get_or_create_conversation(user, conversation_id: str) -> Conversation:
    """Lấy conversation theo id hoặc tạo mới. user=None chỉ dùng khi conv đã tồn tại."""
    if user is not None:
        conv, _ = Conversation.objects.get_or_create(
            id=conversation_id,
            defaults={"user": user, "title": ""},
        )
    else:
        # resume_graph: conversation phải tồn tại sẵn
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
    html: str,
    status: str = Message.Status.COMPLETED,
    node_name: str = "",
    error_message: str = "",
) -> None:
    Message.objects.filter(id=msg_id).update(
        html=html,
        status=status,
        node_name=node_name,
        error_message=error_message,
        updated_at=timezone.now(),
    )


@sync_to_async(thread_sensitive=False)
def _update_assistant_message_interrupted(msg_id: str, html: str) -> None:
    Message.objects.filter(id=msg_id).update(
        html=html,
        status=Message.Status.INTERRUPTED,
        updated_at=timezone.now(),
    )


@sync_to_async(thread_sensitive=False)
def _touch_conversation(conversation_id: str) -> None:
    Conversation.objects.filter(id=conversation_id).update(
        last_message_at=timezone.now(),
        updated_at=timezone.now(),
    )


@sync_to_async(thread_sensitive=False)
def _set_conversation_title(conversation_id: str, title: str) -> None:
    Conversation.objects.filter(id=conversation_id, title="").update(
        title=title[:255],
    )


@sync_to_async(thread_sensitive=False)
def _get_conversation_messages(conversation_id: str, limit: int = 20) -> list[dict]:
    messages = Message.objects.filter(
        conversation_id=conversation_id,
        status=Message.Status.COMPLETED,
    ).order_by("-created_at")[:limit]

    return list(
        reversed(
            [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "status": m.status,
                    "content": m.content,
                    "html": m.html,
                }
                for m in messages
            ]
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# Core stream pipeline
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
    """
    Async generator — LUÔN kết thúc bằng SSE done.
    stream_guarded đã đảm bảo yield ("done", None) trong finally,
    nhưng _run_stream cũng bọc try/finally để chắc chắn.
    """
    try:
        pipeline_error: Exception | None = None

        async for event_type, value in stream_guarded(main_app, graph_input, thread_id):
            if event_type == "node":
                yield _sse("node", {"label": _node_label(value)})

            elif event_type == "interrupt":
                interrupt_payload = json.loads(value)
                html = await _render_human_review_from_payload(
                    interrupt_payload,
                    session_id=session_id,
                    msg_id=msg_id,
                    conversation_id=conversation_id,
                )
                if assistant_msg_id:
                    await _update_assistant_message_interrupted(
                        msg_id=assistant_msg_id,
                        html=html,
                    )
                yield _sse("html", {"html": html})
                return  # done yield ở finally

            elif event_type == "error":
                pipeline_error = Exception(value)
                # Không break — tiếp tục đọc để nhận ("done", None) từ stream_guarded

            elif event_type == "done":
                break  # Thoát vòng lặp, xuống render

        # ── Render snapshot ───────────────────────────────────────────────
        snapshot = await _safe_get_snapshot(main_app, thread_id)

        html = await ChatService._render_from_snapshot_static(
            snapshot,
            pipeline_error,
            session_id=session_id,
            msg_id=msg_id,
        )

        if assistant_msg_id:
            status = (
                Message.Status.ERROR if pipeline_error else Message.Status.COMPLETED
            )
            await _update_assistant_message(
                msg_id=assistant_msg_id,
                html=html,
                status=status,
                error_message=str(pipeline_error) if pipeline_error else "",
            )

        yield _sse("html", {"html": html})

    except Exception as e:
        logger.exception("[_run_stream] Unhandled crash thread=%s: %r", thread_id, e)
        try:
            error_html = await _render_error(e)
            if assistant_msg_id:
                await _update_assistant_message(
                    msg_id=assistant_msg_id,
                    html=error_html,
                    status=Message.Status.ERROR,
                    error_message=str(e),
                )
            yield _sse("html", {"html": error_html})
        except Exception:
            pass  # Không để lỗi render lỗi chặn finally

    finally:
        yield _sse("done", {})  # LUÔN yield done — đóng connection sạch


# ─────────────────────────────────────────────────────────────────────────────
# ChatService
# ─────────────────────────────────────────────────────────────────────────────


class ChatService:
    # ── Khởi chạy lần đầu ────────────────────────────────────────────────────

    async def stream_graph(
        self,
        message: str,
        session_id: str,
        msg_id: str = "",
        user=None,
        conversation_id: str = "",
    ):
        """
        Async generator → SSE chunks cho lần chạy đầu.
        Thread ID = conv_<conversation_id> (production)
                  = sess_<session_id>      (fallback dev)
        """
        # ── Tạo conversation_id nếu chưa có ──────────────────────────────
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        if not msg_id:
            msg_id = str(uuid.uuid4())

        # ── Lưu DB ────────────────────────────────────────────────────────
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

        # ── Chạy LangGraph ─────────────────────────────────────────────────
        thread_id = _make_thread_id(conversation_id, session_id)

        initial_input = {
            "user_input": message,
            "language": "vi",
            "budget_limit": 2.0,
            "conversation_id": conversation_id,
            "msg_id": msg_id,
            "chat_history": history[-10:],  # 10 tin gần nhất
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

    # ── Resume sau human review ───────────────────────────────────────────────

    async def resume_graph(
        self,
        session_id: str,
        action: str,
        feedback: str = "",
        msg_id: str = "",
        conversation_id: str = "",
        user=None,
    ):
        """Resume graph sau khi human review quyết định."""
        if not conversation_id:
            logger.error("[resume_graph] Thiếu conversation_id — không thể resume")
            return

        # ── Tạo placeholder assistant message mới ────────────────────────
        assistant_msg_id = ""
        try:
            conv = await _get_or_create_conversation(None, conversation_id)
            assistant_msg_id = str(uuid.uuid4())
            await _create_assistant_message_pending(conv, assistant_msg_id)
            await _touch_conversation(conversation_id)
        except Exception:
            logger.exception("[resume_graph] DB setup failed conv=%s", conversation_id)
            assistant_msg_id = ""

        thread_id = _make_thread_id(conversation_id, session_id)

        cmd = Command(
            resume={
                "action": action.strip().lower(),
                "feedback": feedback.strip(),
            }
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

    # ── Restore session từ DB ─────────────────────────────────────────────────

    async def restore_session(self, session_id: str, conversation_id: str = ""):
        """
        Ưu tiên restore từ DB (Message model).
        Fallback về LangGraph snapshot nếu không có conversation_id.
        """
        if conversation_id:
            return await _get_conversation_messages(conversation_id)

        # Fallback: restore từ LangGraph snapshot (dev/test)
        thread_id = _make_thread_id("", session_id)
        main_app = await get_main_app()
        snapshot = await _safe_get_snapshot(main_app, thread_id)
        if snapshot:
            return await ChatService._render_from_snapshot_static(snapshot, None)
        return None

    # ── Render ─────────────────────────────────────────────────────────────

    @staticmethod
    async def _render_from_snapshot_static(
        snapshot,
        error: Exception | None,
        session_id: str = "",
        msg_id: str = "",
    ) -> str:
        if snapshot is None or error:
            return await _render_error(error)

        state: dict = snapshot.values if snapshot else {}
        logger.info("[Render] Snapshot nodes: %s", list(state.keys()))

        has_interrupt = any(bool(task.interrupts) for task in (snapshot.tasks or []))

        if has_interrupt:
            return await _render_human_review_widget(
                snapshot,
                session_id=session_id,
                msg_id=msg_id,
            )

        final_node = state.get("final_response")
        if isinstance(final_node, dict):
            payload = final_node.get("payload", {})
            components = payload.get("records", [])
            text = payload.get("text")

            if components:
                return await _render_component_list(components)
            if text:
                return await _render_async(
                    COMPONENT_TEMPLATES["text_response"],
                    {"props": {"text": text, "title": "Kết quả"}},
                )

        hr_raw = state.get("human_review")
        if isinstance(hr_raw, dict):
            payload = hr_raw.get("payload", {})
            if payload.get("status") == "SUCCESS" and payload.get("text"):
                return await _render_async(
                    COMPONENT_TEMPLATES["text_response"],
                    {"props": {"title": "Kết quả", "text": payload["text"]}},
                )

        logger.info("[Render] No render path found for keys: %s", list(state.keys()))
        return await _render_async(
            COMPONENT_TEMPLATES["empty_state"],
            {"props": {"message": "Đang xử lý..."}},
        )


# ─────────────────────────────────────────────────────────────────────────────
# Render helpers
# ─────────────────────────────────────────────────────────────────────────────


async def _render_human_review_from_payload(
    payload: dict,
    session_id: str = "",
    msg_id: str = "",
    conversation_id: str = "",
) -> str:
    draft = payload.get("draft") or payload.get("text", "")
    instruction = payload.get(
        "instruction", "Review nội dung. Chọn Duyệt hoặc Từ chối kèm phản hồi."
    )

    return await _render_async(
        COMPONENT_TEMPLATES["human_review"],
        {
            "props": {
                "draft": draft,
                "instruction": instruction,
                "session_id": session_id,
                "msg_id": msg_id,
                "conversation_id": conversation_id,
            }
        },
    )


async def _render_human_review_widget(
    snapshot,
    session_id: str = "",
    msg_id: str = "",
    conversation_id: str = "",
) -> str:
    draft = ""

    if snapshot.tasks:
        for task in snapshot.tasks:
            if task.interrupts:
                val = task.interrupts[0].value
                if isinstance(val, dict):
                    draft = val.get("draft") or val.get("text", "")
                break

    if not draft:
        og_raw = (snapshot.values or {}).get("output_guard")
        if isinstance(og_raw, dict):
            draft = og_raw.get("payload", {}).get("text", "")

    return await _render_async(
        COMPONENT_TEMPLATES["human_review"],
        {
            "props": {
                "draft": draft,
                "instruction": "Review nội dung. Chọn Duyệt hoặc Từ chối kèm phản hồi.",
                "session_id": session_id,
                "msg_id": msg_id,
                "conversation_id": conversation_id,
            }
        },
    )


async def _render_component_list(components: list) -> str:
    parts: list[str] = []

    for comp in components:
        if not isinstance(comp, dict):
            continue

        cid = comp.get("component_id", "text_response")
        props = comp.get("props", {})
        template = comp.get("template_path") or COMPONENT_TEMPLATES.get(
            cid, COMPONENT_TEMPLATES["text_response"]
        )

        if not props and comp.get("text"):
            props = {"text": comp["text"], "title": comp.get("title", "Kết quả")}

        try:
            parts.append(await _render_async(template, {"props": props}))
        except Exception as exc:
            logger.error(
                "[Render] Template error cid=%s path=%s: %s", cid, template, exc
            )

    return "\n".join(parts)


async def _render_error(error: Exception | None) -> str:
    if isinstance(error, TimeoutError):
        msg, code = "Hệ thống đang tải quá lâu. Vui lòng thử lại.", "TIMEOUT_ERROR"
    elif error is not None:
        msg, code = (
            "Đã xảy ra lỗi trong quá trình xử lý. Vui lòng thử lại.",
            "PIPELINE_CRASH",
        )
    else:
        msg, code = (
            "Xin lỗi, hệ thống hiện chưa tạo được nội dung kết quả.",
            "EMPTY_STATE",
        )

    debug = (
        "".join(traceback.format_exception(type(error), error, error.__traceback__))
        if error is not None
        else "Hệ thống kích hoạt chế độ cứu hộ (Emergency Fallback)."
    )

    return await _render_async(
        COMPONENT_TEMPLATES["error_card"],
        {
            "props": {
                "title": "Hệ thống thông báo",
                "message": msg,
                "error_code": code,
                "failed_node": "System_Runtime",
                "debug_details": debug,
            }
        },
    )


# # chat/services.py — stream_graph
# from langchain_core.messages import HumanMessage, AIMessage

# # Load lịch sử từ DB
# past_messages = await _get_conversation_messages(conversation_id)

# # Convert sang LangChain format
# history = []
# for m in past_messages:
#     if m["role"] == "user":
#         history.append(HumanMessage(content=m["content"]))
#     elif m["role"] == "assistant" and m["content"]:
#         history.append(AIMessage(content=m["content"]))

# initial_input = {
#     "user_input": message,
#     "messages":   history + [HumanMessage(content=message)],
#     ...
# }
