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

import logging
import os
from functools import lru_cache
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


# ═══════════════════════════════════════════════════════════════════
# HELPER PARSER — Bóc tách danh sách từ Markdown thô (K4, K7)
# ═══════════════════════════════════════════════════════════════════

def _truncate(text: str | None, max_chars: int = 800) -> str:
    """Cắt bớt text dài (giữ nguyên nếu ngắn hơn max_chars), cắt ở ranh giới từ."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip() + "..."


def _parse_markdown_list(markdown_text: str | None, section_title: str) -> list[str]:
    """Tìm tiêu đề trong chuỗi Markdown và bóc các dòng dấu gạch đầu dòng (-) bên dưới."""
    if not markdown_text:
        return []
    lines = markdown_text.split("\n")
    result = []
    in_section = False

    for line in lines:
        cleaned = line.strip()
        if cleaned.startswith("#") or cleaned.startswith("##") or cleaned.startswith("**"):
            if section_title.upper() in cleaned.upper():
                in_section = True
                continue
            else:
                in_section = False
        
        if in_section and cleaned.startswith("-"):
            item = cleaned.replace("-", "", 1).strip()
            if item:
                result.append(item.strip('"').strip("'"))
    return result


# ═══════════════════════════════════════════════════════════════════
# DATA PIPELINE — Chuẩn hóa Flat Dict trực tiếp từ DB
# ═══════════════════════════════════════════════════════════════════

def _normalize_flat_brand_voice(bv_flat: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pipeline xử lý dữ liệu phẳng (Flat Data). No more nested JSON dict loops!
    Nhận vào flat dict từ DB Model và map mượt mà sang đầu ra cho Jinja2.
    """
    # 0. Giới hạn độ dài các trường Markdown tự do dài (nguồn tốn token chính, biến động theo brand)
    bv_flat["k1_brand_foundation"] = _truncate(bv_flat.get("k1_brand_foundation"), 800)
    bv_flat["k3_content_patterns"] = _truncate(bv_flat.get("k3_content_patterns"), 600)

    # 1. Bóc tách tập từ vựng từ phân hệ K7 Markdown
    k7 = bv_flat.get("k7_vocabulary_rules")
    bv_flat["words_to_use"] = _parse_markdown_list(k7, "WORDS TO USE")
    bv_flat["words_to_avoid"] = _parse_markdown_list(k7, "WORDS TO AVOID")
    bv_flat["phrases_to_use"] = _parse_markdown_list(k7, "PHRASES TO USE")
    bv_flat["phrases_to_avoid"] = _parse_markdown_list(k7, "PHRASES TO AVOID")
    bv_flat["topics_to_avoid"] = _parse_markdown_list(k7, "TOPICS TO AVOID")
    
    # 2. Bóc tách các câu kêu gọi hành động mẫu từ phân hệ K4 Markdown
    bv_flat["cta_phrases"] = _parse_markdown_list(bv_flat.get("k4_behavior_rules"), "CTA PHRASES")

    # 3. Chuẩn hóa desired_tone chuỗi thô từ DB thành List để Jinja2 dễ loop/join
    dt = bv_flat.get("desired_tone")
    if isinstance(dt, str) and dt:
        bv_flat["base_tones"] = [t.strip() for t in dt.split(",") if t.strip()]
    else:
        bv_flat["base_tones"] = [dt] if dt else ["Thân thiện"]

    # 4. Chuẩn hóa triệt để cấu trúc business_facts['locations'] dạng đa hình (String hoặc Dict)
    bf = bv_flat.get("business_facts") or {}
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

    # 5. Tự động bật/tắt định dạng theo đặc thù kênh truyền thông (channels)
    channels_str = str(bv_flat.get("channels") or []).upper()
    bv_flat["is_social_channel"] = any(x in channels_str for x in ["FACEBOOK", "SOCIAL", "INSTAGRAM", "TIKTOK"])

    # 6. TẦNG DỊCH THUẬT (TRANSLATION LAYER) — THIẾT LẬP MANDATES THEO TRỤC SẮC THÁI PHẲNG
    slider_mandates = []
    
    # Trục 1: Chuyên nghiệp vs Hài hước
    val_fs = bv_flat.get("tone_funny_serious", 50)
    if val_fs >= 65:
        slider_mandates.append("MANDATE: Sắc thái 'Chuyên nghiệp' (Serious). Văn phong nghiêm túc, chuẩn mực chuyên gia, không dùng câu đùa hay từ cảm thán.")
    elif val_fs <= 35:
        slider_mandates.append("MANDATE: Sắc thái 'Hài hước & Dí dỏm' (Funny). Văn phong dí dỏm, mang tính giải trí cao, bắt trend thông minh.")

    # Trục 2: Trang trọng vs Thân thiện & Gần gũi
    val_fc = bv_flat.get("tone_formal_casual", 50)
    if val_fc >= 65:
        slider_mandates.append("MANDATE: Sắc thái 'Thân thiện & Gần gũi' (Casual). Phong cách bình dân, tự nhiên như cuộc trò chuyện đời thường.")
    elif val_fc <= 35:
        slider_mandates.append("MANDATE: Sắc thái 'Trang trọng & Quy chuẩn' (Formal). Phong cách chính thống, tôn nghiêm, cấu trúc câu gãy gọn.")

    # Trục 3: Tôn trọng vs Táo bạo & Phá cách
    val_ri = bv_flat.get("tone_respectful_irreverent", 50)
    if val_ri >= 65:
        slider_mandates.append("MANDATE: Sắc thái 'Tôn trọng & Lịch sự' (Respectful). Thể hiện sự mực thước tối đa, lịch sự, sử dụng kính ngữ đầy đủ.")
    elif val_ri <= 35:
        slider_mandates.append("MANDATE: Sắc thái 'Táo bạo & Phá cách' (Irreverent). Văn phong sắc sảo, châm biếm hóm hỉnh, phá vỡ lối mòn tư duy.")

    # Trục 4: Thực tế vs Nhiệt huyết
    val_em = bv_flat.get("tone_enthusiastic_matter_of_fact", 50)
    if val_em >= 65:
        slider_mandates.append("MANDATE: Sắc thái 'Trực diện & Thực tế' (Fact-based). Tập trung tuyệt đối vào sự thật, đặc tính sản phẩm và số liệu thực tế, không thổi phồng cảm xúc.")
    elif val_em <= 35:
        slider_mandates.append("MANDATE: Sắc thái 'Nhiệt huyết & Sôi nổi' (Enthusiastic). Giọng điệu tràn đầy năng lượng, truyền cảm hứng mạnh mẽ, kích thích hành động.")

    bv_flat["slider_mandates"] = slider_mandates
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
    normalized = _normalize_flat_brand_voice(brand_voice)
    template = _get_template()

    try:
        prompt = template.render(
            bv=normalized, # Đổi tên biến truyền vào gọn hơn thành `bv` đại diện cho Brand Voice phẳng
            content_type=content_type,
            user_input=user_input,
            rag=rag or {},
        )
    except Exception as exc:
        logger.error("Jinja2 render failed: %s", exc)
        raise RuntimeError(f"Không thể build system prompt: {exc}") from exc

    return prompt.strip()



async def get_brand_prompt_by_id(
    brand_id: str,
    content_type: ContentType,
    user_input: Dict[str, Any],
    db: AsyncSession,
) -> str:
    """
    Hàm Service tích hợp cho LangGraph Workflow:
    Đọc trực tiếp cấu trúc phẳng (Flat Dict) từ SQLAlchemy DB và render ra Prompt.
    """
    from app.brand.models import Brand 
    
    brand = (await db.execute(
        select(Brand)
        .where( Brand.id == brand_id, Brand.deleted_at.is_(None) )
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
        return await build_system_prompt(fallback_flat, content_type, user_input)

    # Chuyển đổi bản ghi DB SQLAlchemy sang Flat Dict thuần túy, y hệt như cấu trúc `result` của bộ Crawl
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
        
        # Đổ nguyên văn chuỗi Markdown Base K1 -> K7 phẳng từ DB
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
   
    import asyncio

    search_query = user_input.get("topic", "")

    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                asyncio.run,
                fetch_rag_context(business_id=brand_id, query=search_query, top_k=5),
            )
            rag_ctx = future.result()
    except RuntimeError:
        rag_ctx = asyncio.run(
            fetch_rag_context(business_id=brand_id, query=search_query, top_k=5),
        )

    # Gộp RAG context vào additional_instructions (LLM đọc được)
    rag_payload = {
        "keywords": rag_ctx.get("keywords") or [],
        "comments": [_truncate(c, 150) for c in (rag_ctx.get("comments") or [])[:3]],
        "posts":    [_truncate(p, 150) for p in (rag_ctx.get("posts") or [])[:2]],
    }

    return await build_system_prompt(
        brand_voice=brand_flat_dict,
        content_type=content_type,
        user_input=user_input,
        rag=rag_payload,
    )