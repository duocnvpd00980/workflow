"""
brand/extraction_prompt.py
────────────────────────────────
EXTRACTION_PROMPT — build prompt từ brand_voice_input (Signal Extraction output).
KHÔNG truyền final_report, KHÔNG truyền raw research — chỉ truyền 6 nhóm signal đã lọc.
"""

from __future__ import annotations

import json
from typing import Any, Dict

SYSTEM_MSG = (
    "Bạn là chuyên gia phân tích Brand Voice. "
    "Chỉ trả về JSON object hợp lệ, không markdown, không giải thích."
)

_TEMPLATE = """\
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

═══════════════════════════════════════════════════
TÍN HIỆU ĐÃ ĐƯỢC TRÍCH XUẤT TỪ NGHIÊN CỨU THỰC TẾ
(Đây là dữ liệu thật từ ngôn ngữ khách hàng, hành vi khách hàng,
giọng điệu hiện tại của thương hiệu, thị trường và đối thủ —
hãy HỌC TỪ ĐÂY, không tự bịa đặt)
═══════════════════════════════════════════════════

1. NGÔN NGỮ KHÁCH HÀNG (customer_language):
{customer_language}

2. HÀNH VI / XU HƯỚNG THỊ TRƯỜNG (market_patterns):
{market_patterns}

3. GIỌNG ĐIỆU THƯƠNG HIỆU HIỆN TẠI (existing_brand_voice):
{existing_brand_voice}

4. PHẢN HỒI KHÁCH HÀNG (customer_feedback):
{customer_feedback}

5. THÔNG TIN ĐỐI THỦ (competitor_insights — có thể còn hạn chế):
{competitor_insights}

═══════════════════════════════════════════════════
YÊU CẦU: Trích xuất Brand Voice thành JSON với đúng 8 trường sau.
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
  ],

  "tone_funny_serious": <0-100>,
  "tone_formal_casual": <0-100>,
  "tone_respectful_irreverent": <0-100>,
  "tone_enthusiastic_matter_of_fact": <0-100>
}}

QUY TẮC BẮT BUỘC:
- Ưu tiên bám sát "existing_brand_voice.representative_posts" và "voice_signals"
  (emoji, độ dài câu, formality, cta_frequency) để suy ra style/format_rules/cta_style
  cho ĐÚNG với cách thương hiệu đang viết — không tự sáng tác phong cách mới.
- Lấy "wordsToUse"/"phrasesToUse" ưu tiên từ "customer_language.top_phrases" và
  "customer_feedback.positive_themes" — đây là ngôn ngữ khách hàng thật đang dùng.
- 4 trục tone_* (0-100) phải phản ánh đúng dữ liệu thật quan sát được, không mặc định 50
  trừ khi dữ liệu không đủ rõ.
- Từ vựng phải phù hợp ngành: {industry}
- tone.overrides chỉ ghi kênh có trong danh sách kênh: {channels}
- examples: tối thiểu 1, tối đa 3 — phải đúng giọng, có thể dựa trên representative_posts
- KHÔNG dùng từ generic: "rất", "cực kỳ", "tuyệt vời", "chất lượng cao"
- KHÔNG giải thích, KHÔNG markdown — chỉ JSON
"""


def _json_block(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_extraction_prompt(brand_voice_input: Dict[str, Any]) -> str:
    """
    Render EXTRACTION_PROMPT từ brand_voice_input (output extract_brand_signals()).
    """
    ctx = brand_voice_input.get("business_context", {})
    voice_config = ctx.get("voice_config", {}) or {}

    return _TEMPLATE.format(
        business_name   = ctx.get("business_name") or "",
        industry        = ctx.get("industry") or "—",
        products        = ctx.get("products") or "—",
        voice_name      = voice_config.get("name", ""),
        purpose         = voice_config.get("purpose", ""),
        channels        = ", ".join(voice_config.get("channels", [])),
        desired_tone    = voice_config.get("desired_tone", ""),
        target_audience = voice_config.get("target_audience", ""),
        customer_language    = _json_block(brand_voice_input.get("customer_language", {})),
        market_patterns      = _json_block(brand_voice_input.get("market_patterns", {})),
        existing_brand_voice = _json_block(brand_voice_input.get("existing_brand_voice", {})),
        customer_feedback    = _json_block(brand_voice_input.get("customer_feedback", {})),
        competitor_insights  = _json_block(brand_voice_input.get("competitor_insights", {})),
    )