"""
services/brand_voice_extract.py
────────────────────────────────
Extract 8 Brand Voice fields từ brand_voice_input (Signal Extraction output).
Dùng async_groq_client từ app.llm_clients — KHÔNG dùng litellm.

Flow:
    research_mapper.build_research_json()
        → signal_extractor.extract_brand_signals()
        → brand_voice_input (dict)
        → EXTRACTION_PROMPT
        → async_groq_client (json_object)
        → _sanitize_raw()
        → validate BrandEightFields
        → Dict[str, Any]  (sẵn sàng lưu vào Brand ORM)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from app.brand.extraction_prompt import SYSTEM_MSG, build_extraction_prompt
from app.llm_clients import async_groq_client, GROQ_MODEL
from .schemas import BrandEightFields

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# SANITIZE + VALIDATE  (giữ nguyên logic cũ — không đổi)
# ═══════════════════════════════════════════════════════════════════

def _sanitize_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Làm sạch output LLM, giới hạn array size trước khi Pydantic validate."""
    if vocab := raw.get("vocabulary"):
        for key in ("wordsToUse", "wordsToAvoid", "phrasesToUse", "phrasesToAvoid"):
            if isinstance(vocab.get(key), list):
                vocab[key] = [w.strip() for w in vocab[key] if str(w).strip()][:20]

    if tone := raw.get("tone"):
        if not tone.get("base"):
            tone["base"] = ["professional"]
        if isinstance(tone.get("overrides"), dict):
            tone["overrides"] = {
                ch: [t.strip() for t in vals if str(t).strip()][:5]
                for ch, vals in tone["overrides"].items()
            }

    if cta := raw.get("cta_style"):
        if isinstance(cta.get("phrases"), list):
            cta["phrases"] = [p.strip() for p in cta["phrases"] if str(p).strip()][:10]

    if isinstance(raw.get("examples"), list):
        raw["examples"] = raw["examples"][:3]

    for field in ("tone_funny_serious", "tone_formal_casual", "tone_respectful_irreverent", "tone_enthusiastic_matter_of_fact"):
        try:
            raw[field] = max(0, min(100, int(raw.get(field, 50))))
        except (ValueError, TypeError):
            raw[field] = 50

    return raw


def _validate(raw: Dict[str, Any]) -> BrandEightFields:
    try:
        return BrandEightFields(**raw)
    except Exception as exc:
        logger.error("BrandEightFields validation failed | raw=%s | err=%s", raw, exc)
        raise ValueError(f"LLM trả về JSON không đúng schema: {exc}") from exc


# ═══════════════════════════════════════════════════════════════════
# MAIN FUNCTION — signature mới: chỉ nhận brand_voice_input
# ═══════════════════════════════════════════════════════════════════

async def extract_brand_voice(
    brand_voice_input: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Gọi Groq async để extract 8 Brand Voice fields từ brand_voice_input
    (output của signal_extractor.extract_brand_signals()).

    Args:
        brand_voice_input: {
            customer_language, market_patterns, existing_brand_voice,
            customer_feedback, competitor_insights, business_context
        }
        business_context phải chứa: business_name, voice_config{name,purpose,
        channels,desired_tone,target_audience}. industry/products là optional —
        nếu thiếu, prompt sẽ ghi "—".

    Returns:
        Dict khớp BrandEightFields — sẵn sàng unpack vào Brand ORM.

    Raises:
        RuntimeError: Groq call thất bại
        ValueError:   JSON không đúng schema
    """
    prompt = build_extraction_prompt(brand_voice_input)

    business_name = brand_voice_input.get("business_context", {}).get("business_name", "")
    logger.info("extract_brand_voice | business=%s", business_name)

    # ── Gọi Groq async (dùng async_groq_client từ app.llm_clients) ──
    try:
        response = await async_groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_MSG},
                {"role": "user",   "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_completion_tokens=2000,
            timeout=60,
        )
    except Exception as exc:
        logger.error("Groq call failed: %s", exc)
        raise RuntimeError(f"Lỗi kết nối Groq: {exc}") from exc

    raw_text: str = response.choices[0].message.content or ""
    try:
        raw: Dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("Groq returned non-JSON: %s", raw_text[:500])
        raise ValueError(f"Groq không trả về JSON hợp lệ: {exc}") from exc

    raw = _sanitize_raw(raw)
    validated = _validate(raw)
    return validated.model_dump()