"""
services/brand_voice_prompt.py
────────────────────────────────
Build system prompt cho content generation từ Brand data.

Usage:
    from app.brand_voice.services.brand_voice_prompt import build_system_prompt

    prompt = await build_system_prompt(
        brand_voice=bv_dict,
        content_type="blog",
        user_input={"topic": "Ra mắt sản phẩm mới", "keywords": ["bền vững", "đột phá"]},
    )
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any, Dict, Literal

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# TEMPLATE LOADER — cache Environment (thread-safe, load once)
# ═══════════════════════════════════════════════════════════════════

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
_TEMPLATE_FILE = "brand_voice_prompt.j2"

ContentType = Literal["blog", "email", "social", "ad", "landing_page", "other"]


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
# HELPER — normalize brand_voice dict
# ═══════════════════════════════════════════════════════════════════

def _normalize_brand_voice(brand_voice: Dict[str, Any]) -> Dict[str, Any]:
    """
    Đảm bảo brand_voice dict có đúng shape mà template cần.
    Hỗ trợ cả Pydantic model (.model_dump()) lẫn raw dict từ DB (JSON columns).
    """
    bv = dict(brand_voice)

    # tone.overrides phải là dict, không phải None
    tone = bv.get("tone") or {}
    if not isinstance(tone.get("overrides"), dict):
        tone["overrides"] = {}
    bv["tone"] = tone

    # style defaults
    style = bv.get("style") or {}
    style.setdefault("sentenceLength", "medium")
    style.setdefault("voice", "active")
    style.setdefault("perspective", "second")
    bv["style"] = style

    # vocabulary defaults
    vocab = bv.get("vocabulary") or {}
    for key in ("wordsToUse", "wordsToAvoid", "phrasesToUse", "phrasesToAvoid"):
        vocab.setdefault(key, [])
    bv["vocabulary"] = vocab

    # format_rules defaults
    fmt = bv.get("format_rules") or {}
    fmt.setdefault("paragraphMaxSentences", 4)
    fmt.setdefault("useEmoji", False)
    fmt.setdefault("useHashtags", False)
    fmt.setdefault("bulletPointStyle", "none")
    bv["format_rules"] = fmt

    # cta_style defaults
    cta = bv.get("cta_style") or {}
    cta.setdefault("style", "none")
    cta.setdefault("phrases", [])
    bv["cta_style"] = cta

    # examples: list of dicts with contentType
    bv.setdefault("examples", [])
    bv.setdefault("personality", "")

    # ═══════════════════════════════════════════════════════════════════
    # TẦNG DỊCH THUẬT (TRANSLATION LAYER) — Trả ra mảng string cho Jinja2
    # ═══════════════════════════════════════════════════════════════════
    slider_directives = []

    # 1. Trục Hài hước vs Nghiêm túc
    funny_serious_val = bv.get("tone_funny_serious", 50)
    if funny_serious_val <= 35:
        slider_directives.append("Hành văn hài hước, dí dỏm, sử dụng câu đùa và từ lóng bắt trend để tạo không khí vui vẻ.")
    elif funny_serious_val >= 65:
        slider_directives.append("Hành văn cực kỳ nghiêm túc, trang trọng, chuẩn mực chuyên gia. Tuyệt đối không dùng câu đùa hay từ cảm thán.")

    # 2. Trục Trang trọng vs Bình dân
    formal_casual_val = bv.get("tone_formal_casual", 50)
    if formal_casual_val <= 35:
        slider_directives.append("Phong cách diễn đạt trang trọng, chính thống, sử dụng thuật ngữ chuyên môn chính xác.")
    elif formal_casual_val >= 65:
        slider_directives.append("Phong cách diễn đạt bình dân, giản dị, tự nhiên như cuộc trò chuyện đời thường.")

    # 3. Trục Tôn trọng vs Phá cách
    respectful_irreverent_val = bv.get("tone_respectful_irreverent", 50)
    if respectful_irreverent_val <= 35:
        slider_directives.append("Thể hiện sự tôn trọng tối đa đối với người đọc, lịch sự, sử dụng kính ngữ đầy đủ.")
    elif respectful_irreverent_val >= 65:
        slider_directives.append("Phong cách phá cách, táo bạo, nổi loạn nhẹ hoặc hóm hỉnh châm biếm để gây ấn tượng mạnh.")

    # 4. Trục Nhiệt huyết vs Thực tế
    enthusiastic_matter_val = bv.get("tone_enthusiastic_matter_of_fact", 50)
    if enthusiastic_matter_val <= 35:
        slider_directives.append("Giọng điệu tràn đầy năng lượng, nhiệt huyết, sử dụng văn phong sôi nổi kích thích hành động.")
    elif enthusiastic_matter_val >= 65:
        slider_directives.append("Giọng điệu khách quan tuyệt đối, chỉ tập trung vào sự thật và số liệu (matter-of-fact), không thổi phồng cảm xúc.")

    # Gán mảng này vào dictionary để Jinja2 bốc dỡ ra render
    bv["slider_directives"] = slider_directives

    return bv


# ═══════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════

async def build_system_prompt(
    brand_voice: Dict[str, Any],
    content_type: ContentType,
    user_input: Dict[str, Any],
) -> str:
    """
    Render Jinja2 template → system prompt hoàn chỉnh cho content generation.

    Args:
        brand_voice:  dict từ Brand ORM hoặc BrandOut.model_dump()
        content_type: loại nội dung — "blog" | "email" | "social" | "ad" | ...
        user_input:   {
                        topic?: str,
                        keywords?: List[str],
                        length?: str,           # "500 từ", "short", ...
                        additional_instructions?: str,
                      }

    Returns:
        System prompt string sẵn sàng truyền vào LLM.
    """
    normalized = _normalize_brand_voice(brand_voice)
    template = _get_template()

    try:
        prompt = template.render(
            brand_voice=normalized,
            content_type=content_type,
            user_input=user_input,
        )
    except Exception as exc:
        logger.error("Jinja2 render failed: %s", exc)
        raise RuntimeError(f"Không thể build system prompt: {exc}") from exc

    logger.debug(
        "build_system_prompt | content_type=%s | prompt_chars=%d",
        content_type, len(prompt),
    )
    return prompt.strip()
