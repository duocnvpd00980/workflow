from __future__ import annotations

import logging
import uuid

from sqlalchemy import select, update

from app.db import AsyncSessionLocal
from app.chat.models import Conversation, Message
from app.llm_clients import call_groq
logger = logging.getLogger(__name__)


def _build_prompt(state: dict) -> str:
    """Build prompt từ state — dùng chung cho cả stream và non-stream path."""
    draft = state.get("content_draft") or ""
    instruction = state.get("instruction") or ""
    brand_context = state.get("brand_context") or ""
    rag_context = state.get("rag_context") or ""
    history_context = state.get("history_context") or ""

    return f"""Bạn là một content editor chuyên nghiệp. Hãy xử lý nội dung dựa trên các thông tin dưới đây.

=== LỊCH SỬ TRAO ĐỔI GẦN ĐÂY (để hiểu ngữ cảnh, KHÔNG phải nội dung cần viết) ===
{history_context or "Không có lịch sử trao đổi trước đó."}

=== YÊU CẦU CỦA USER (LƯỢT NÀY) ===
{instruction}

=== BRAND VOICE ===
{brand_context or "Không có brand voice cụ thể."}

=== THÔNG TIN THAM KHẢO (RAG) ===
{rag_context or "Không có dữ liệu tham khảo."}

=== CONTENT DRAFT (BẢN NHÁP SẴN CÓ) ===
{draft or "Không có bản nháp - Hãy viết mới hoàn toàn dựa trên yêu cầu."}

=== YÊU CẦU THỰC HIỆN ===
1. Dựa vào lịch sử trao đổi để hiểu user đang muốn tiếp tục/chỉnh sửa nội dung nào (nếu có).
2. Nếu có bản nháp: Sửa đổi bản nháp tuân thủ theo yêu cầu của user.
3. Nếu không có bản nháp: Viết mới hoàn toàn một bài viết chất lượng dựa trên yêu cầu và dữ liệu tham khảo.
4. Tuân thủ nghiêm ngặt brand voice và thông tin RAG bổ sung.
5. Chỉ trả về bài viết hoàn chỉnh, KHÔNG thêm lời giải thích hay dẫn lời nào khác.
"""




# ── Helpers ───────────────────────────────────────────────

def _build_brand_block(brand_profile: dict) -> str:
    if not brand_profile:
        return ""
    lines = [
        f"Brand: {brand_profile.get('brand_name', '')}",
        f"Positioning: {brand_profile.get('positioning', '')}",
        f"Audience: {brand_profile.get('target_audience', '')}",
    ]
    tone = brand_profile.get("tone_patterns", [])
    if tone:
        lines.append(f"Tone: {', '.join(tone)}")
    forbidden = brand_profile.get("forbidden_words", [])
    if forbidden:
        lines.append(f"Forbidden: {', '.join(forbidden)}")
    ctas = brand_profile.get("cta_samples", [])
    if ctas:
        lines.append(f"CTAs: {', '.join(ctas)}")
    return "\n".join(lines)


def _build_rag_block(rag_items: list) -> str:
    if not rag_items:
        return ""
    blocks = []
    for item in rag_items[:3]:
        content = item.get("text_content") or str(item)
        blocks.append(content[:500])
    return "\n\n".join(blocks)


def _call_llm_rewrite(draft: str, instruction: str, brand_context: str, rag_context: str, history_context: str) -> str:
    """Xử lý gọi LLM đồng bộ bằng Groq API (non-stream path)."""
    prompt = _build_prompt({
        "content_draft": draft,
        "instruction": instruction,
        "brand_context": brand_context,
        "rag_context": rag_context,
        "history_context": history_context,
    })
    return call_groq(prompt, max_tokens=2000)


# ── Nodes ─────────────────────────────────────────────────

async def load_brand_voice(state: dict) -> dict:
    """Đọc brand voice (profile + voice rules) từ DB."""
    brand_id = state.get("brand_id")
    brand_profile: dict = {}

    if brand_id:
        try:
            async with AsyncSessionLocal() as db:
                from app.brand.models import Brand, BrandProfile, BrandVoiceRule

                brand = (
                    await db.execute(select(Brand).where(Brand.id == brand_id))
                ).scalars().one_or_none()

                if brand:
                    profile = (
                        await db.execute(
                            select(BrandProfile).where(BrandProfile.brand_id == brand_id)
                        )
                    ).scalars().one_or_none()

                    rules = (
                        await db.execute(
                            select(BrandVoiceRule).where(BrandVoiceRule.brand_id == brand_id)
                        )
                    ).scalars().all()

                    tone_patterns = [r.value for r in rules if r.rule_type == "tone"] or ["Thân thiện"]
                    forbidden_words = [r.value for r in rules if r.rule_type == "forbidden"]

                    brand_profile = {
                        "brand_name": brand.name,
                        "positioning": profile.positioning if profile else "",
                        "target_audience": profile.audience if profile else "",
                        "tone_patterns": tone_patterns,
                        "forbidden_words": forbidden_words,
                    }
        except Exception as e:
            logger.warning(f"Brand voice load failed: {e}")

    return {
        "brand_profile": brand_profile,
        "brand_context": _build_brand_block(brand_profile),
    }


async def load_rag(state: dict) -> dict:
    """Đọc tài liệu tri thức RAG (knowledge_document_source) theo business_id."""
    rag_items: list[dict] = []
    business_id = state.get("business_id")

    try:
        async with AsyncSessionLocal() as db:
            from app.rag.models import DocumentSource

            stmt = select(DocumentSource).order_by(DocumentSource.id.desc()).limit(3)

            if business_id:
                stmt = stmt.where(DocumentSource.business_id == business_id)

            if hasattr(DocumentSource, "status"):
                stmt = stmt.where(DocumentSource.status == "completed")

            rows = await db.execute(stmt)

            rag_items = [
                {
                    "rag_type": "document_source",
                    "title": x.title,
                    "text_content": f"Tên file: {x.title}. Đường dẫn: {getattr(x, 'file_path', None)}",
                }
                for x in rows.scalars()
            ]
    except Exception as e:
        logger.warning(f"RAG load failed: {e}")

    return {
        "knowledge_rag": rag_items,
        "rag_context": _build_rag_block(rag_items),
    }


async def load_contexts(state: dict) -> dict:
    """Chạy tuần tự 3 load để đảm bảo data đầy đủ trước khi rewrite."""
    # Load brand voice
    brand_result = await load_brand_voice(state)
    state.update(brand_result)
    
    # Load RAG
    rag_result = await load_rag(state)
    state.update(rag_result)
    
    # Load history
    history_result = await load_history(state)
    state.update(history_result)
    
    return {
        "brand_profile": state.get("brand_profile"),
        "brand_context": state.get("brand_context"),
        "knowledge_rag": state.get("knowledge_rag"),
        "rag_context": state.get("rag_context"),
        "conversation_history": state.get("conversation_history"),
        "history_context": state.get("history_context"),
    }


async def rewrite_content(state: dict) -> dict:
    """Node xử lý trung tâm: Gửi toàn bộ dữ liệu qua LLM."""
    draft = state.get("content_draft", "")
    instruction = state.get("instruction", "")
    brand_context = state.get("brand_context", "")
    rag_context = state.get("rag_context", "")
    history_context = state.get("history_context", "")

    if not draft and not instruction:
        return {"error": "Cả content_draft và instruction đều trống.", "rewritten_text": ""}

    rewritten = _call_llm_rewrite(draft, instruction, brand_context, rag_context, history_context)

    return {
        "rewritten_text": rewritten,
        "original_draft": draft,
    }

async def load_history(state: dict) -> dict:
    """Đọc lịch sử chat gần nhất của conversation để AI hiểu ngữ cảnh các lượt trước."""
    raw_conv_id = state.get("conversation_id")
    history_items: list[dict] = []

    if raw_conv_id:
        try:
            conversation_id = uuid.UUID(str(raw_conv_id))
            async with AsyncSessionLocal() as db:
                rows = await db.execute(
                    select(Message)
                    .where(
                        Message.conversation_id == conversation_id,
                        Message.status == "completed",
                    )
                    .order_by(Message.created_at.desc())
                    .limit(10)
                )
                # Đảo lại theo thứ tự thời gian tăng dần (cũ -> mới)
                history_items = [
                    {"role": m.role, "content": m.content}
                    for m in reversed(rows.scalars().all())
                ]
        except (ValueError, AttributeError) as e:
            logger.warning(f"History load skipped (invalid conversation_id): {e}")
        except Exception as e:
            logger.warning(f"History load failed: {e}")

    return {
        "conversation_history": history_items,
        "history_context": _build_history_block(history_items),
    }


def _build_history_block(history_items: list[dict]) -> str:
    if not history_items:
        return ""
    lines = []
    for item in history_items:
        speaker = "User" if item["role"] == "user" else "Assistant"
        content = (item.get("content") or "").strip()
        if not content:
            continue
        # Cắt ngắn mỗi tin nhắn để tránh prompt quá dài
        if len(content) > 800:
            content = content[:800] + "..."
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


async def save_result(state: dict) -> dict:
    """Cập nhật nội dung hoàn thiện vào Message."""
    raw_conv_id = state.get("conversation_id")
    raw_msg_id = state.get("msg_id")
    rewritten = state.get("rewritten_text", "")

    if not raw_conv_id or not raw_msg_id:
        return {"saved": False, "error": "Thiếu conversation_id hoặc msg_id."}

    try:
        conversation_id = uuid.UUID(str(raw_conv_id))
        msg_id = uuid.UUID(str(raw_msg_id))
    except (ValueError, AttributeError):
        return {"saved": False, "error": "conversation_id hoặc msg_id không phải UUID hợp lệ."}

    try:
        async with AsyncSessionLocal() as db:
            # Kiểm tra conversation có tồn tại không (tránh update vô nghĩa)
            conv = await db.get(Conversation, conversation_id)
            if not conv:
                return {"saved": False, "error": f"Conversation {conversation_id} không tồn tại."}

            result = await db.execute(
                update(Message)
                .where(Message.id == msg_id)
                .values(content=rewritten, status="completed")
            )
            await db.commit()

            if result.rowcount == 0:
                logger.warning(f"save_result: không tìm thấy Message id={msg_id}")
                return {"saved": False, "error": f"Message {msg_id} không tồn tại."}

            return {"saved": True}

    except Exception as e:
        logger.error(f"Save failed: {e}")
        return {"saved": False, "error": str(e)}