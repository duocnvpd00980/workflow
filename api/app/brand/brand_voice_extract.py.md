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

from app.brand.service_slice import aggregate, prepare_kien_inputs, run_kiens
from app.brand.extraction_prompt import SYSTEM_MSG, build_extraction_prompt
from app.llm_clients import async_groq_client, GROQ_MODEL
from .schemas import BrandEightFields
from typing import Dict, Any



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
    research_record: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Extract Brand Voice từ FULL research aggregate.

    Input:
    {
        "task": PipelineTask | None,
        "result": ResearchResult,
        "posts": list[FbPost],
        "comments": list[FbComment],
        "events": list[PipelineEvent],
    }

    Output:
        Dict khớp BrandEightFields
    """

    result = research_record["result"]

    if not result:
        raise ValueError("ResearchResult không tồn tại")

    logger.info(
        "extract_brand_voice | business=%s | posts=%s | comments=%s",
        result.business_name,
        len(research_record["posts"]),
        len(research_record["comments"]),
    )

    # ============================================================
    # Chuẩn hóa input cho Kien pipeline
    # (KHÔNG build prompt, KHÔNG signal extractor)
    # ============================================================

    input_data = {
        "task": {
            "business_id": result.business_id,
            "business_name": result.business_name,
        },

        "research": {
            "suggestions_raw": result.suggestions_raw,
            "suggestions_tagged": result.suggestions_tagged,

            "serp_data": result.serp_data,

            "fb_brand": result.fb_brand,

            "final_report": result.final_report,
        },

        "posts": [
            {
                "id": p.id,
                "content": p.content,
                "attachments": p.attachments,
            }
            for p in research_record["posts"]
        ],

        "comments": [
            {
                "author": c.author,
                "time": c.time,
                "comment": c.comment,
                "replies": c.replies,
            }
            for c in research_record["comments"]
        ],

        "events": [
            {
                "seq": e.seq,
                "node": e.node_name,
                "payload": e.payload,
            }
            for e in research_record["events"]
        ],
    }

    # ============================================================
    # Slice dữ liệu → Kien
    # ============================================================

    kien_inputs = prepare_kien_inputs(input_data)

    logger.info(
        "extract_brand_voice | prepared"
    )

    # ============================================================
    # Multi extraction
    # ============================================================

    outputs = await run_kiens(
        kien_inputs
    )

    if not outputs:
        raise RuntimeError(
            "run_kiens() trả rỗng"
        )

    logger.info(
        "extract_brand_voice | aggregate"
    )

    # ============================================================
    # Final merge
    # ============================================================

    brand = aggregate(
        outputs["k1"],
        outputs["k2"],
        outputs["k3"],
        outputs["k4"],
        business_id=result.business_id,
        business_name=result.business_name,
    )

    if not isinstance(brand, dict):
        raise RuntimeError(
            "aggregate() phải trả dict"
        )

    logger.info(
        "extract_brand_voice | done"
    )

    return brand

