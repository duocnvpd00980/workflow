"""
services/brand_voice_extract.py
────────────────────────────────
Extract 8 Brand Voice fields từ RAG content.
Dùng async_groq_client từ app.llm_clients — KHÔNG dùng litellm.

Flow:
    RAG content + voice_config + business info
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

from app.llm_clients import async_groq_client, GROQ_MODEL
from .schemas import BrandEightFields

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# PROMPT TEMPLATE
# ═══════════════════════════════════════════════════════════════════

SYSTEM_MSG = (
    "Bạn là chuyên gia phân tích Brand Voice. "
    "Chỉ trả về JSON object hợp lệ, không markdown, không giải thích."
)

EXTRACTION_PROMPT = """\
Bạn là chuyên gia phân tích Brand Voice.

THÔNG TIN THƯƠNG HIỆU:
- Tên: {business_name}
- Ngành: {industry}
- Sản phẩm/Dịch vụ: {products}

THIẾT LẬP VOICE NÀY:
- Tên voice: {voice_name}
- Mục đích: {purpose}
- Kênh triển khai: {channels}
- Tone mong muốn: {desired_tone}
- Đối tượng cụ thể: {target_audience}

TÀI LIỆU THAM KHẢO:
{rag_content}

═══════════════════════════════════════════════════
YÊU CẦU: Trích xuất Brand Voice thành JSON với đúng 7 trường sau.
Trả về JSON thuần — KHÔNG dùng markdown, KHÔNG thêm trường ngoài schema.
═══════════════════════════════════════════════════

{{
  "personality": "<1-2 câu mô tả AI đóng vai gì, phong cách ra sao>",

  "tone": {{
    "base": ["<tone_word>"],
    "overrides": {{
      "blog_web":   ["<tone_word>"],
      "email_sale":  ["<tone_word>"],
      "social_media": ["<tone_word>"]
    }}
  }},

  "style": {{
    "sentenceLength": "<short|medium|long|mixed>",
    "voice":          "<active|passive>",
    "perspective":    "<first|second|third>",
    "pronouns": {{
      "ai": "<Thương hiệu tự xưng là gì khi viết tiếng Việt? Ví dụ: Chúng tôi, Brilliant Restaurant, Shop>",
      "reader": "<Gọi khách hàng/độc giả là gì khi viết tiếng Việt? Ví dụ: Quý khách, Bạn, Anh/Chị>"
    }}
  }},

  "vocabulary": {{
    "wordsToUse":      ["..."],
    "wordsToAvoid":    ["..."],
    "phrasesToUse":    ["..."],
    "phrasesToAvoid":  ["..."]
  }},

  "format_rules": {{
    "paragraphMaxSentences": <1-20>,
    "useEmoji":              <true|false>,
    "useHashtags":           <true|false>,
    "bulletPointStyle":      "<dash|dot|number|arrow|none>"
  }},

  "cta_style": {{
    "style":   "<soft|direct|urgent|none>",
    "phrases": ["..."]
  }},

  "examples": [
    {{
      "input":       "<user yêu cầu gì>",
      "output":      "<output mẫu đúng giọng>",
      "contentType": "<blog_web|email_sale|social_media|ad|landing_page|other>"
    }}
  ]
}}

QUY TẮC BẮT BUỘC:
- Từ vựng phải phù hợp ngành: {industry}
- tone.overrides chỉ ghi kênh có trong danh sách kênh: {channels}
- examples: tối thiểu 1, tối đa 3 — phải đúng giọng, có thể trích từ tài liệu
- KHÔNG dùng từ generic: "rất", "cực kỳ", "tuyệt vời", "chất lượng cao"
- KHÔNG giải thích, KHÔNG markdown — chỉ JSON
"""


# ═══════════════════════════════════════════════════════════════════
# SANITIZE + VALIDATE
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
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════

async def extract_brand_voice(
    business: Dict[str, Any],
    voice_config: Dict[str, Any],
    rag_content: str,
    max_rag_chars: int = 8000,
) -> Dict[str, Any]:
    """
    Gọi Groq async để extract 8 Brand Voice fields từ RAG content.

    Args:
        business:      dict từ Business ORM (name, industry, products, ...)
        voice_config:  dict từ VoiceConfigIn
        rag_content:   text đã thu thập từ RAG sources
        max_rag_chars: cắt ngắn để tránh vượt context window

    Returns:
        Dict khớp BrandEightFields — sẵn sàng unpack vào Brand ORM.

    Raises:
        RuntimeError: Groq call thất bại
        ValueError:   JSON không đúng schema
    """
    channels_str = ", ".join(voice_config.get("channels", []))
    products_str = ", ".join(business.get("products", [])) or "—"

    prompt = EXTRACTION_PROMPT.format(
        business_name  = business.get("name", ""),
        industry       = business.get("industry", ""),
        products       = products_str,
        voice_name     = voice_config.get("name", ""),
        purpose        = voice_config.get("purpose", ""),
        channels       = channels_str,
        desired_tone   = voice_config.get("desired_tone", ""),
        target_audience= voice_config.get("target_audience", ""),
        rag_content    = rag_content[:max_rag_chars],
    )

    logger.info(
        "extract_brand_voice | business=%s | rag_chars=%d",
        business.get("name"), min(len(rag_content), max_rag_chars),
    )

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