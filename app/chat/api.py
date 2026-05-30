# =============================================================================
# FILE: chat/api.py  —  Django Ninja Router
# =============================================================================
from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import StreamingHttpResponse
from ninja import Router, Schema
from ninja.responses import Response
from uuid import UUID
from chat.models import Conversation
from chat.services import ChatService

logger = logging.getLogger(__name__)

router = Router(tags=["chat"])
chat_service = ChatService()


# =============================================================================
# Schemas
# =============================================================================


class StreamRequest(Schema):
    message: str
    session_id: str
    conversation_id: uuid.UUID
    msg_id: Optional[str] = ""


class ResumeRequest(Schema):
    session_id: str
    action: str
    feedback: Optional[str] = ""
    msg_id: Optional[str] = ""
    conversation_id: uuid.UUID


class RestoreRequest(Schema):
    session_id: Optional[str] = ""
    conversation_id: uuid.UUID
    msg_id: Optional[str] = ""


class ConversationOut(Schema):
    id: str
    title: str


# =============================================================================
# Helpers
# =============================================================================


def _sse_headers(response: StreamingHttpResponse) -> StreamingHttpResponse:
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _get_or_create_test_user(request):
    """Lấy user thật hoặc fallback về admin/local_tester để test."""
    if request.user.is_authenticated:
        u = request.user
        _ = u.pk  # force load DB
        return u

    User = get_user_model()
    admin_user = User.objects.filter(is_superuser=True).first()
    if admin_user:
        return admin_user

    test_user, _ = User.objects.get_or_create(
        username="local_tester",
        defaults={"is_staff": True, "email": "test@local.com"},
    )
    return test_user


def _generate_title(text: str, limit: int = 60) -> str:
    text = " ".join(text.strip().split())

    if len(text) <= limit:
        return text

    return text[:limit].rstrip() + "..."


# =============================================================================
# POST /api/chat/stream   —  SSE streaming
# =============================================================================


@router.post("/stream", auth=None, url_name="stream")
async def stream_message(request, payload: StreamRequest):
    """SSE endpoint — nhận message, stream kết quả về client theo chuẩn SSE."""
    message = payload.message.strip()
    session_id = payload.session_id.strip()
    conversation_id = str(payload.conversation_id)
    msg_id = (payload.msg_id or "").strip() or str(uuid.uuid4())

    if not conversation_id:
        return Response({"detail": "Thiếu conversation_id."}, status=400)

    if not message or not session_id:
        return Response({"detail": "Thiếu message hoặc session_id."}, status=400)

    user = await sync_to_async(_get_or_create_test_user)(request)

    try:
        conversation = await sync_to_async(Conversation.objects.for_user(user).get)(
            id=conversation_id,
        )
    except Conversation.DoesNotExist:
        return Response(
            {"detail": "Conversation not found"},
            status=404,
        )

    # Auto-generate title từ first message
    if not conversation.title:
        title = _generate_title(message)

        await sync_to_async(
            Conversation.objects.filter(
                id=conversation.id,
                title="",
            ).update
        )(
            title=title,
        )

        conversation.title = title

    async def event_stream():
        yield "event: heartbeat\ndata: {}\n\n"

        try:
            async for chunk in chat_service.stream_graph(
                message,
                session_id,
                msg_id=msg_id,
                user=user,
                conversation_id=conversation_id,
            ):
                yield chunk

        except Exception:
            logger.exception("[stream_message] Generator crashed")

            yield f"event: error\ndata: {json.dumps({'message': 'Lỗi hệ thống'})}\n\n"
            yield "event: done\ndata: {}\n\n"

        finally:
            await sync_to_async(conversation.touch)()

    return _sse_headers(
        StreamingHttpResponse(
            event_stream(), content_type="text/event-stream; charset=utf-8"
        )
    )


# =============================================================================
# POST /api/chat/resume   —  Resume sau human review
# =============================================================================


@router.post("/resume", auth=None, url_name="resume")
async def resume_message(request, payload: ResumeRequest):
    """Resume graph sau khi human review quyết định approve/reject."""
    session_id = payload.session_id.strip()
    action = payload.action.strip()
    feedback = (payload.feedback or "").strip()
    msg_id = (payload.msg_id or "").strip()
    conversation_id = str(payload.conversation_id)

    if not session_id or not action:
        return Response({"detail": "Thiếu session_id hoặc action."}, status=400)

    if not conversation_id:
        return Response({"detail": "Thiếu conversation_id."}, status=400)

    async def event_stream():
        yield "event: heartbeat\ndata: {}\n\n"
        try:
            async for chunk in chat_service.resume_graph(
                session_id=session_id,
                action=action,
                feedback=feedback,
                msg_id=msg_id,
                conversation_id=conversation_id,
            ):
                yield chunk
        except Exception:
            logger.exception("[resume_message] Generator crashed")
            yield f"event: error\ndata: {json.dumps({'message': 'Lỗi hệ thống'})}\n\n"
            yield "event: done\ndata: {}\n\n"

    return _sse_headers(
        StreamingHttpResponse(
            event_stream(), content_type="text/event-stream; charset=utf-8"
        )
    )


# =============================================================================
# POST /api/chat/restore  —  Restore session
# =============================================================================


@router.post("/restore", auth=None, url_name="restore")
async def restore_chat(request, payload: RestoreRequest):
    """
    Khôi phục lịch sử chat khi F5 trang.
    - Nếu có conversation_id → trả về list messages (JSON).
    - Fallback → trả về HTML snapshot từ LangGraph.
    """
    session_id = (payload.session_id or "").strip()
    conversation_id = (payload.conversation_id or "").strip()

    if not session_id and not conversation_id:
        return Response(
            {"detail": "Thiếu session_id hoặc conversation_id."}, status=400
        )

    result = await chat_service.restore_session(
        session_id, conversation_id=conversation_id
    )

    if isinstance(result, list):
        return Response(
            {
                "type": "messages",
                "messages": result,
                "conversation_id": conversation_id,
                "session_id": session_id,
            }
        )

    return Response(
        {
            "type": "html",
            "html": result or "",
            "msg_id": payload.msg_id or "",
            "session_id": session_id,
        }
    )


# =============================================================================
# GET /api/chat/conversations  —  Danh sách hội thoại
# =============================================================================


@router.get("/conversations", auth=None, url_name="conversation_list")
def conversation_list(request):
    """Trả về danh sách conversations của user (hoặc admin khi test)."""

    user = _get_or_create_test_user(request)

    convs = (
        Conversation.objects.for_user(user)
        .active()
        .values("id", "title", "last_message_at")
    )

    return list(convs)


# =============================================================================
# GET /api/chat/conversations/{conversation_id}  —  Load messages
# =============================================================================


@router.get("/conversations/{conversation_id}", auth=None, url_name="conversation_load")
def conversation_load(request, conversation_id: uuid.UUID):
    """Trả về danh sách messages trong 1 conversation."""
    user = _get_or_create_test_user(request)

    try:
        conversation = Conversation.objects.for_user(user).get(id=conversation_id)
    except Conversation.DoesNotExist:
        return Response({"detail": "Không tìm thấy conversation."}, status=404)

    messages = list(
        conversation.messages.order_by("created_at").values(
            "id", "role", "status", "content", "html", "created_at"
        )
    )

    return {
        "conversation_id": str(conversation.id),
        "session_id": request.session.session_key or "local_test_session",
        "messages": messages,
    }


# =============================================================================
# POST /api/chat/conversations  —  Create conversation
# =============================================================================


@router.post("/conversations", auth=None, url_name="conversation_create")
def conversation_create(request):
    """Tạo conversation trước khi gửi message đầu tiên."""

    user = _get_or_create_test_user(request)

    with transaction.atomic():
        conversation = Conversation.objects.create(
            user=user,
            title="",
        )

    return {
        "id": str(conversation.id),
        "title": conversation.title,
    }
