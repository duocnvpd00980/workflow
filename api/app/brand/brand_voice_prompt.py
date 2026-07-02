"""
services/brand_voice_prompt.py
────────────────────────────────
Build system prompt cho content generation từ Brand data phẳng (Flat DB Model).

Usage:
    from app.brand_voice.services.brand_voice_prompt import build_system_prompt

    prompt = await build_system_prompt(
        brand_voice=bv_flat_dict,
        content_type="blog_web",
        user_input={"topic": "Ra mắt sản phẩm mới", "keywords": ["bền vững", "đột phá"]},
    )
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
import re
from sqlalchemy import select
from typing import Any, Dict, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
from app.marketing.rag_context import fetch_rag_context

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# TEMPLATE LOADER — cache Environment (thread-safe, load once)
# ═══════════════════════════════════════════════════════════════════

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__))
_TEMPLATE_FILE = "brand_voice_prompt.j2"

ContentType = Literal["blog_web", "email_sale", "social_media", "ad", "landing_page", "other"]


@lru_cache(maxsize=1)
def _get_env() -> Environment:
    """Tạo Jinja2 Environment một lần duy nhất, cache lại."""
    return Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(disabled_extensions=("j2",)),
        trim_blocks=True,       # bỏ newline sau {% tag %}
        lstrip_blocks=True,     # bỏ indent trước {% tag %}
        keep_trailing_newline=True,
    )


def _get_template() -> Template:
    return _get_env().get_template(_TEMPLATE_FILE)


def safe_int(v, default=50):
    try:
        if v is None:
            return default
        if isinstance(v, int):
            return max(0, min(100, v))
        s = str(v).strip()
        if not s:
            return default
        m = re.search(r"\d+", s)
        if not m:
            return default
        return max(0, min(100, int(m.group())))
    except Exception:
        return default


# ═══════════════════════════════════════════════════════════════════
# HELPER — làm sạch khối raw text (K3/K4/K7) trước khi nhét vào prompt
# Không parse thành list Python nữa — gửi nguyên văn cho LLM đọc, chỉ lọc
# bỏ phần không cần thiết (EVIDENCE nội bộ, dòng END, dòng trống thừa) để
# gọn token hơn.
# ═══════════════════════════════════════════════════════════════════

def _truncate(text: str | None, max_chars: int = 800) -> str:
    """Cắt bớt text dài (giữ nguyên nếu ngắn hơn max_chars), cắt ở ranh giới từ."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip() + "..."


def _clean_raw_block(text: str | None, max_chars: int = 600) -> str:
    """Làm sạch nhẹ 1 khối raw text (label-based `LABEL:` hoặc markdown
    `# HEADER`, không quan trọng format nào) trước khi nhét thẳng vào
    prompt cho LLM đọc:
    - Bỏ section EVIDENCE (chỉ dùng nội bộ để debug/QA, không cần cho
      content generation)
    - Bỏ dòng "END" đánh dấu hết output của bước trích xuất K-doc
    - Bỏ dòng trống thừa
    - Cắt bớt nếu vượt quá max_chars

    Không parse thành list — giữ nguyên câu chữ để LLM tự đọc hiểu ngữ
    cảnh, tránh phụ thuộc cứng vào 1 format cụ thể (khác với
    _parse_markdown_list cũ, vốn vỡ ngay khi thượng nguồn đổi format).
    """
    if not text:
        return ""

    lines = text.split("\n")
    cleaned_lines: list[str] = []
    skip_section = False

    for line in lines:
        stripped = line.strip()

        # Nhận diện dòng "EVIDENCE" dạng cả "# EVIDENCE" lẫn "EVIDENCE:"
        if re.match(r'^#{0,3}\s*EVIDENCE:?\s*$', stripped, re.IGNORECASE):
            skip_section = True
            continue

        if skip_section:
            # Section EVIDENCE kết thúc khi gặp 1 label/header mới (dòng
            # toàn chữ hoa, có thể kèm dấu ':') hoặc dòng "END"
            is_new_label = bool(re.match(r'^#{0,3}\s*[A-ZĐÂÊÔƠƯ][A-ZĐÂÊÔƠƯ_ ]*:?\s*$', stripped))
            if is_new_label or stripped.upper() == "END":
                skip_section = False
            else:
                continue

        if stripped.upper() == "END":
            continue
        if not stripped:
            continue

        cleaned_lines.append(stripped)

    result = "\n".join(cleaned_lines).strip()
    return _truncate(result, max_chars)


# ═══════════════════════════════════════════════════════════════════
# DATA PIPELINE — Chuẩn hóa Flat Dict trực tiếp từ DB
# ═══════════════════════════════════════════════════════════════════
def _normalize_flat_brand_voice(bv_flat: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pipeline xử lý dữ liệu phẳng (Flat Data). No more nested JSON dict loops!
    Nhận vào flat dict từ DB Model và map mượt mà sang đầu ra cho Jinja2.

    K3/K4/K7 giờ được gửi NGUYÊN VĂN (raw text đã làm sạch nhẹ) thẳng vào
    prompt — không còn parse thành list Python (words_to_use, cta_phrases...).
    LLM đọc hiểu raw text tốt; parse chỉ tạo phụ thuộc cứng vào 1 format
    cụ thể, dễ vỡ khi tầng trích xuất K-doc đổi format.
    """
    # 0. Giới hạn độ dài + làm sạch các trường Markdown/raw tự do
    #    (nguồn tốn token chính, biến động theo brand)
    bv_flat["k1_brand_foundation"] = _truncate(bv_flat.get("k1_brand_foundation"), 800)
    bv_flat["k3_content_patterns"] = _clean_raw_block(bv_flat.get("k3_content_patterns"), 600)
    bv_flat["k4_behavior_rules"] = _clean_raw_block(bv_flat.get("k4_behavior_rules"), 500)
    bv_flat["k7_vocabulary_rules"] = _clean_raw_block(bv_flat.get("k7_vocabulary_rules"), 500)

    # 1. Chuẩn hóa desired_tone chuỗi thô từ DB thành List để Jinja2 dễ loop/join
    dt = bv_flat.get("desired_tone")
    if isinstance(dt, str) and dt:
        bv_flat["base_tones"] = [t.strip() for t in dt.split(",") if t.strip()]
    else:
        bv_flat["base_tones"] = [dt] if dt else ["Thân thiện"]

    # 2. Chuẩn hóa triệt để cấu trúc business_facts['locations'] dạng đa hình (String hoặc Dict)
    bf = bv_flat.get("business_facts") or {}
    if isinstance(bf, str):
        try:
            bf = json.loads(bf)
        except (json.JSONDecodeError, TypeError):
            bf = {}
    if not isinstance(bf, dict):
        bf = {}

    raw_locations = bf.get("locations") or []
    normalized_locs = []
    brand_phones = bf.get("phones") or []
    primary_hotline = brand_phones[0] if (isinstance(brand_phones, list) and brand_phones) else ""

    for loc in raw_locations:
        if isinstance(loc, str):
            normalized_locs.append({"address": loc.strip(), "city": "", "hotline": primary_hotline})
        elif isinstance(loc, dict):
            normalized_locs.append({
                "address": loc.get("address") or loc.get("raw_text") or "",
                "city": loc.get("city") or "",
                "hotline": loc.get("hotline") or primary_hotline
            })
    bf["locations"] = normalized_locs
    bv_flat["business_facts"] = bf

    # 3. Tự động bật/tắt định dạng theo đặc thù kênh truyền thông (channels)
    channels_str = str(bv_flat.get("channels") or []).upper()
    bv_flat["is_social_channel"] = any(x in channels_str for x in ["FACEBOOK", "SOCIAL", "INSTAGRAM", "TIKTOK"])

    # 4. TẦNG DỊCH THUẬT MANDATE — Chỉ 1 PRIMARY, còn lại là ACCENT (đã lọc xung đột)
    mandate_scores = []

    # Trục 1: Funny (0) ↔ Serious (100)
    val_fs = safe_int(bv_flat.get("tone_funny_serious"), 50)
    dev_fs = abs(val_fs - 50)
    if val_fs >= 65:
        mandate_scores.append((dev_fs, "MANDATE: Sắc thái 'Chuyên nghiệp & Nghiêm túc' (Serious). Văn phong chuẩn mực, tập trung chuyên môn, không dùng câu đùa."))
    elif val_fs <= 35:
        mandate_scores.append((dev_fs, "MANDATE: Sắc thái 'Hài hước & Dí dỏm' (Funny). Văn phong dí dỏm, bắt trend thông minh, mang tính giải trí."))

    # Trục 2: Formal (0) ↔ Casual (100)
    val_fc = safe_int(bv_flat.get("tone_formal_casual"), 50)
    dev_fc = abs(val_fc - 50)
    if val_fc >= 65:
        mandate_scores.append((dev_fc, "MANDATE: Sắc thái 'Thân thiện & Gần gũi' (Casual). Phong cách bình dân, tự nhiên như trò chuyện đời thường."))
    elif val_fc <= 35:
        mandate_scores.append((dev_fc, "MANDATE: Sắc thái 'Trang trọng & Quy chuẩn' (Formal). Phong cách chính thống, tôn nghiêm, cấu trúc câu gãy gọn."))

    # Trục 3: Respectful (0) ↔ Irreverent (100)
    val_ri = safe_int(bv_flat.get("tone_respectful_irreverent"), 50)
    dev_ri = abs(val_ri - 50)
    if val_ri >= 65:
        mandate_scores.append((dev_ri, "MANDATE: Sắc thái 'Tôn trọng & Lịch sự' (Respectful). Kính ngữ đầy đủ, mực thước, lịch sự tối đa."))
    elif val_ri <= 35:
        mandate_scores.append((dev_ri, "MANDATE: Sắc thái 'Táo bạo & Phá cách' (Irreverent). Văn phong sắc sảo, châm biếm, phá vỡ lối mòn."))

    # Trục 4: Enthusiastic (0) ↔ Matter-of-fact (100)
    val_em = safe_int(bv_flat.get("tone_enthusiastic_matter_of_fact"), 50)
    dev_em = abs(val_em - 50)
    if val_em >= 65:
        mandate_scores.append((dev_em, "MANDATE: Sắc thái 'Trực diện & Thực tế' (Fact-based). Tập trung sự thật, đặc tính sản phẩm, số liệu thực tế, không thổi phồng cảm xúc."))
    elif val_em <= 35:
        mandate_scores.append((dev_em, "MANDATE: Sắc thái 'Nhiệt huyết & Sôi nổi' (Enthusiastic). Giọng điệu tràn đầy năng lượng, truyền cảm hứng, kích thích hành động."))

    # Sắp xếp theo độ lệch giảm dần → cái lệch nhiều nhất là PRIMARY
    mandate_scores.sort(reverse=True, key=lambda x: x[0])

    primary_mandate = mandate_scores[0][1] if mandate_scores else "MANDATE: Sắc thái 'Thân thiện & Gần gũi' (Casual)."
    accent_mandates_raw = [m[1] for m in mandate_scores[1:]]

    # LỌC XUNG ĐỘT: Bỏ accent trực diện xung đột với primary
    conflict_map = {
        "Serious": ["Funny", "Irreverent", "Casual"],
        "Funny": ["Serious", "Formal", "Respectful"],
        "Formal": ["Funny", "Casual", "Irreverent"],
        "Casual": ["Formal", "Respectful", "Serious"],
        "Respectful": ["Funny", "Irreverent", "Casual", "Táo bạo"],
        "Irreverent": ["Respectful", "Formal", "Serious"],
        "Fact-based": ["Enthusiastic"],
        "Enthusiastic": ["Fact-based"],
    }

    # Xác định key của primary
    primary_key = None
    for key in conflict_map:
        if key in primary_mandate:
            primary_key = key
            break

    accent_mandates = []
    if primary_key:
        for m in accent_mandates_raw:
            if not any(conflict in m for conflict in conflict_map[primary_key]):
                accent_mandates.append(m)

    bv_flat["slider_mandates"] = [primary_mandate] + accent_mandates
    bv_flat["primary_mandate"] = primary_mandate
    bv_flat["accent_mandates"] = accent_mandates

    # 4b. Xưng hô — Ưu tiên giá trị đã cài sẵn trong DB, nếu không có mới tự động suy luận
    if not bv_flat.get("brand_pronoun") or not bv_flat.get("customer_pronoun"):
        k1 = bv_flat.get("k1_brand_foundation", "")
        k1_lower = k1.lower()

        if "thân thiện" in k1_lower or "gần gũi" in k1_lower or "bình dân" in k1_lower:
            bv_flat["brand_pronoun"] = bv_flat.get("brand_pronoun") or "Tụi mình"
            bv_flat["customer_pronoun"] = bv_flat.get("customer_pronoun") or "Bạn"
        elif "Formal" in primary_mandate or "Respectful" in primary_mandate:
            bv_flat["brand_pronoun"] = bv_flat.get("brand_pronoun") or "Chúng tôi"
            bv_flat["customer_pronoun"] = bv_flat.get("customer_pronoun") or "Quý khách"
        else:
            bv_flat["brand_pronoun"] = bv_flat.get("brand_pronoun") or ("Tụi mình" if "Casual" in primary_mandate else "Chúng tôi")
            bv_flat["customer_pronoun"] = bv_flat.get("customer_pronoun") or "Bạn"

    # 5. CTA template — Pre-render với data thật từ business_facts
    locs = bf.get("locations", [])
    hours = bf.get("hours", "")

    if locs:
        cta_lines = []
        for loc in locs:
            city = loc.get("city", "").strip()
            hotline = loc.get("hotline", "").strip()
            if city and hotline:
                cta_lines.append(f"Ghé {city} — {hotline}")
            elif city:
                cta_lines.append(f"Ghé {city}")
            elif hotline:
                cta_lines.append(f"Hotline: {hotline}")

        cta_core = " | ".join(cta_lines) if cta_lines else "Ghé chúng tôi"
        if hours:
            bv_flat["cta_template"] = f"{cta_core} | Mở cửa: {hours}"
        else:
            bv_flat["cta_template"] = cta_core
    else:
        bv_flat["cta_template"] = f"Ghé chúng tôi{' | Mở cửa: ' + hours if hours else ''}"

    # 6. Format rules — 1 nguồn duy nhất
    bv_flat["format_rules"] = {
        "emoji": bv_flat.get("is_social_channel", True),
        "hashtag": bv_flat.get("is_social_channel", True),
        "bullet": True,
        "max_sentences": 4
    }

    return bv_flat


# ═══════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════

async def build_system_prompt(
    brand_voice: Dict[str, Any],
    content_type: ContentType,
    user_input: Dict[str, Any],
    rag: Dict[str, Any] | None = None,
) -> str:
    """Render Jinja2 template → system prompt hoàn chỉnh cho content generation từ cấu trúc phẳng."""

    # ── DEBUG: log business_facts TRƯỚC khi normalize để xem type/value gốc từ DB ──
    raw_bf = brand_voice.get("business_facts")
    logger.info(
        "[build_system_prompt] RAW business_facts type=%s | is_dict=%s | preview=%r",
        type(raw_bf).__name__, isinstance(raw_bf, dict), str(raw_bf)[:300]
    )

    normalized = _normalize_flat_brand_voice(brand_voice)

    # ── DEBUG: log business_facts SAU khi normalize để xem có bị reset về {} không ──
    norm_bf = normalized.get("business_facts")
    logger.info(
        "[build_system_prompt] NORMALIZED business_facts type=%s | locations=%d | hours=%r | usp=%d | preview=%r",
        type(norm_bf).__name__,
        len(norm_bf.get("locations", [])) if isinstance(norm_bf, dict) else -1,
        norm_bf.get("hours") if isinstance(norm_bf, dict) else None,
        len(norm_bf.get("usp", [])) if isinstance(norm_bf, dict) else -1,
        str(norm_bf)[:300]
    )

    template = _get_template()

    try:
        prompt = template.render(
            bv=normalized,  # Đổi tên biến truyền vào gọn hơn thành `bv` đại diện cho Brand Voice phẳng
            content_type=content_type,
            user_input=user_input,
            rag=rag if rag and any(rag.values()) else None,
        )
    except Exception as exc:
        logger.error("Jinja2 render failed: %s", exc)
        raise RuntimeError(f"Không thể build system prompt: {exc}") from exc

    # ── DEBUG: kiểm tra khối FACTS có thực sự render ra trong prompt cuối không ──
    facts_rendered = "FACTS" in prompt
    logger.info(
        "[build_system_prompt] Khối FACTS %s trong prompt cuối. prompt_length=%d",
        "CÓ xuất hiện" if facts_rendered else "❌ KHÔNG xuất hiện",
        len(prompt)
    )

    return prompt.strip()


async def get_brand_prompt_by_id(
    brand_id: str,
    content_type: str,  # Hoặc ContentType
    user_input: dict,
    db: AsyncSession,
) -> str:
    """
    Hàm Service tích hợp cho LangGraph Workflow:
    Đọc trực tiếp cấu trúc phẳng (Flat Dict) từ SQLAlchemy DB và render ra Prompt.
    """
    from app.brand.models import Brand
    from app.marketing.rag_context import fetch_rag_context
    import logging

    logger = logging.getLogger(__name__)

    brand = (await db.execute(
        select(Brand)
        .where(Brand.id == brand_id, Brand.deleted_at.is_(None))
        .limit(1)
    )).scalars().one_or_none()

    if not brand:
        logger.warning("Brand voice ID=%s không tồn tại. Dùng fallback default.", brand_id)
        fallback_flat = {
            "name": "Mặc định",
            "purpose": "Viết nội dung chất lượng",
            "desired_tone": "Chuyên nghiệp",
            "tone_funny_serious": 50, "tone_formal_casual": 50,
            "tone_respectful_irreverent": 50, "tone_enthusiastic_matter_of_fact": 50,
        }
        return await build_system_prompt(fallback_flat, content_type, user_input, rag={})

    # Chuyển đổi bản ghi DB SQLAlchemy sang Flat Dict thuần túy
    brand_flat_dict = {
        "business_id":                      brand.business_id,
        "name":                             brand.name,
        "purpose":                          brand.purpose,
        "target_audience":                  brand.target_audience,
        "desired_tone":                     brand.desired_tone,
        "channels":                         brand.channels,
        "taglines":                         brand.taglines or [],
        "business_facts":                   brand.business_facts or {},
        "website_url":                      brand.website_url,

        # Đổ nguyên văn chuỗi Markdown/raw K1 -> K7 phẳng từ DB
        "k1_brand_foundation":              brand.k1_brand_foundation,
        "k2_customer_insights":             brand.k2_customer_insights,
        "k3_content_patterns":              brand.k3_content_patterns,
        "k4_behavior_rules":                brand.k4_behavior_rules,
        "k5_examples":                      brand.k5_examples,
        "k6_tone_analysis":                 brand.k6_tone_analysis,
        "k7_vocabulary_rules":              brand.k7_vocabulary_rules,

        # 4 trục sliders số phẳng
        "tone_funny_serious":               brand.tone_funny_serious,
        "tone_formal_casual":               brand.tone_formal_casual,
        "tone_respectful_irreverent":       brand.tone_respectful_irreverent,
        "tone_enthusiastic_matter_of_fact": brand.tone_enthusiastic_matter_of_fact,
    }

    search_query = user_input.get("topic", "")

    try:
        rag_ctx = await fetch_rag_context(business_id=brand.business_id, query=search_query, top_k=5)
    except Exception as exc:
        logger.error("Lỗi khi fetch RAG context: %s", exc)
        rag_ctx = {}

    rag_payload = {
        "keywords": rag_ctx.get("keywords") or [],
    }

    logger.info("RAG raw keys: %s | rag_payload: %s", list(rag_ctx.keys()), rag_payload)

    return await build_system_prompt(
        brand_voice=brand_flat_dict,
        content_type=content_type,
        user_input=user_input,
        rag=rag_payload,
    )