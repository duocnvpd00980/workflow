# agent_os/nodes_library/node_final_response/final_response_service.py
"""
FinalResponseService  (graph mới)
──────────────────────────────────
Hợp nhất select_components + resolve_ui cũ → build_components() duy nhất.
Giữ nguyên:
  • Logic keyword detection (empty signal)
  • Props mapping có giá trị fallback thực tế
  • Schema validation qua PROPS_SCHEMA_MAP
  • Thứ tự component cho campaign đầy đủ

Thêm mới:
  • Flow routing rõ ràng theo graph: chat | knowledge | marketing | default
  • Dispatch table → thêm flow mới không cần sửa class
  • Không bao giờ raise — luôn fallback về text_response
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from app.core.protocol  import BodyFrame
from .final_response_protocol import (
    ComponentId,
    COMPONENT_REGISTRY,
    PROPS_SCHEMA_MAP,
    RenderedComponent,
)

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Hằng số
# ─────────────────────────────────────────────────────────────────────────────

_EMPTY_KEYWORDS = frozenset(
    [
        "chưa tìm thấy",
        "không tìm thấy",
        "không có dữ liệu",
        "xin lỗi",
    ]
)

# Thứ tự hiển thị khi campaign đầy đủ (ads + email + blog)
_FULL_CAMPAIGN_ORDER: list[ComponentId] = [
    "campaign_summary",
    "ads_card",
    "email_template",
    "blog_preview",
]


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────


class FinalResponseService:
    """Stateless — dùng như singleton."""

    def build_components(
        self,
        payload: BodyFrame,
        flow_type: str,
    ) -> list[RenderedComponent]:
        """
        Entry point duy nhất cho adapter.
        Không bao giờ raise — fallback về text_response nếu mọi thứ thất bại.
        """
        # Guard: pipeline thượng nguồn đã báo lỗi
        if payload.status == "FAILED":
            return [self._render_one("error_card", payload)]

        # Guard: tín hiệu rỗng / không có nội dung
        if self._is_empty(payload):
            return [self._render_one("empty_state", payload)]

        try:
            handler = _FLOW_HANDLERS.get(flow_type, _handle_default)
            result = handler(self, payload)
            if result:
                return result
        except Exception as exc:
            log.exception(
                "[FinalResponseService] handler crash flow=%s: %s", flow_type, exc
            )

        # Fallback an toàn
        return [self._render_one("text_response", payload)]

    # ── Kiểm tra tín hiệu rỗng ───────────────────────────────────────────────

    @staticmethod
    def _is_empty(payload: BodyFrame) -> bool:
        # 1. Kiểm tra text trước: Nếu có text thì không bao giờ là empty
        if payload.text and len(payload.text.strip()) > 0:
            return False

        # 2. Kiểm tra records
        records = payload.records or []
        if len(records) > 0:
            return False

        # 3. Chỉ khi không có cả text lẫn records mới xét đến logic từ khóa rỗng
        text_lower = (payload.text or "").lower()
        has_empty_kw = any(kw in text_lower for kw in _EMPTY_KEYWORDS)

        return has_empty_kw

    # ── Phân tích records theo loại content ──────────────────────────────────

    @staticmethod
    def _detect(records: list) -> tuple[dict, dict, dict]:
        """Trả về (raw_ads, raw_email, raw_blog) — dict rỗng nếu không có."""
        raw_ads = next(
            (r for r in records if isinstance(r, dict) and "headline" in r), {}
        )
        raw_email = next(
            (r for r in records if isinstance(r, dict) and "subject" in r), {}
        )
        raw_blog = next(
            (r for r in records if isinstance(r, dict) and "title" in r), {}
        )
        return raw_ads, raw_email, raw_blog

    # ── Build props map đầy đủ ───────────────────────────────────────────────

    def _props_map(self, payload: BodyFrame) -> dict[ComponentId, dict[str, Any]]:
        """
        Toàn bộ props mặc định cho từng component.
        Adapter gọi _render_one() sẽ tra cứu dict này.
        """
        text = payload.text or ""
        records = payload.records or []
        context_data = payload.context or {}

        raw_ads, raw_email, raw_blog = self._detect(records)

        components_ready = [
            k
            for k, v in [
                ("ads_card", raw_ads),
                ("email_template", raw_email),
                ("blog_preview", raw_blog),
            ]
            if v
        ]

        return {
            "error_card": {
                "title": "Sự cố xử lý dữ liệu",
                "message": text or "Hệ thống trục trặc, vui lòng thử lại.",
                "error_code": payload.error or "PIPELINE_ERROR",
                "failed_node": context_data.get("failed_node", "node_final_response"),
                "debug_details": payload.error,
            },
            "empty_state": {
                "title": "Không tìm thấy nội dung kết quả",
                "description": text,
                "user_input": context_data.get("user_prompt"),
            },
            "text_response": {
                "title": "Kết quả xử lý",
                "text": text,
            },
            "source_list": {
                "sources": [
                    r
                    for r in records
                    if isinstance(r, dict) and r.get("component_id") == "source_list"
                ],
            },
            "ads_card": raw_ads
            or {
                "headline": "Chiến dịch quảng cáo",
                "body": text,
            },
            "email_template": raw_email
            or {
                "subject": "Thông tin gửi tới bạn",
                "body": text,
            },
            "blog_preview": raw_blog
            or {
                "title": "Bài viết mới",
                "content": text,
            },
            "campaign_summary": {
                "status": "completed" if payload.status == "SUCCESS" else "pending",
                "components_ready": components_ready,
                "message": "Chiến dịch marketing hoàn tất.",
                "total_words": len(text.split()),
            },
        }

    # ── Schema-validated render ───────────────────────────────────────────────

    def _render_one(
        self,
        cid: ComponentId,
        payload: BodyFrame,
    ) -> RenderedComponent:
        """
        Render 1 component với schema validation.
        Nếu validation thất bại → fallback text_response, không raise.
        """
        props_data = self._props_map(payload).get(cid, {})

        try:
            schema_model = PROPS_SCHEMA_MAP.get(cid)
            if not schema_model:
                raise ValueError(f"Missing props schema for component: {cid!r}")

            validated_props = schema_model.model_validate(props_data).model_dump()
            template_path = COMPONENT_REGISTRY[cid]["template_path"]

            return RenderedComponent(
                component_id=cid,
                props=validated_props,
                template_path=template_path,
            )

        except (ValidationError, Exception) as exc:
            log.warning(
                "[FinalResponseService] validation failed cid=%s: %s — using text_response fallback",
                cid,
                exc,
            )
            return RenderedComponent(
                component_id="text_response",
                props={"text": payload.text or "", "title": "Phản hồi dự phòng"},
                template_path=COMPONENT_REGISTRY["text_response"]["template_path"],
            )

    def _render_many(
        self,
        cids: list[ComponentId],
        payload: BodyFrame,
    ) -> list[RenderedComponent]:
        return [self._render_one(cid, payload) for cid in cids]


# ─────────────────────────────────────────────────────────────────────────────
# Flow handlers  (bound methods thông qua dispatch table)
# ─────────────────────────────────────────────────────────────────────────────


def _handle_chat(
    self: FinalResponseService,
    payload: BodyFrame,
) -> list[RenderedComponent]:
    """flow=chat → 1 card text_response."""
    return [self._render_one("text_response", payload)]


def _handle_knowledge(
    self: FinalResponseService,
    payload: BodyFrame,
) -> list[RenderedComponent]:
    """flow=knowledge → text_response + source_list nếu có."""
    result = [self._render_one("text_response", payload)]

    sources = [
        r
        for r in (payload.records or [])
        if isinstance(r, dict) and r.get("component_id") == "source_list"
    ]
    if sources:
        result.append(self._render_one("source_list", payload))

    return result


def _handle_marketing(
    self: FinalResponseService,
    payload: BodyFrame,
) -> list[RenderedComponent]:
    """
    flow=marketing → chọn component theo content có trong records.
    Campaign đầy đủ (ads + email + blog) → thêm campaign_summary dẫn đầu.
    """
    records = payload.records or []
    raw_ads, raw_email, raw_blog = FinalResponseService._detect(records)

    has_ads = bool(raw_ads)
    has_email = bool(raw_email)
    has_blog = bool(raw_blog)

    # Campaign đầy đủ
    if has_ads and has_email and has_blog:
        return self._render_many(_FULL_CAMPAIGN_ORDER, payload)

    # Từng loại đơn lẻ
    selected: list[ComponentId] = []
    if has_ads:
        selected.append("ads_card")
    if has_email:
        selected.append("email_template")
    if has_blog:
        selected.append("blog_preview")

    return (
        self._render_many(selected, payload)
        if selected
        else [self._render_one("text_response", payload)]
    )


def _handle_default(
    self: FinalResponseService,
    payload: BodyFrame,
) -> list[RenderedComponent]:
    """flow=default hoặc không nhận dạng → empty_state."""
    return [self._render_one("empty_state", payload)]


# ─────────────────────────────────────────────────────────────────────────────
# Dispatch table — thêm flow mới ở đây, không sửa class
# ─────────────────────────────────────────────────────────────────────────────

_FLOW_HANDLERS: dict[str, Any] = {
    "chat": _handle_chat,
    "knowledge": _handle_knowledge,
    "marketing": _handle_marketing,
    "cache": _handle_knowledge,
    "default": _handle_default,
}
