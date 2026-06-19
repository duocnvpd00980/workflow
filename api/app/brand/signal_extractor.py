"""
brand/signal_extractor.py
────────────────────────────────
Signal Extraction Layer — lọc raw research_json thành brand_voice_input gọn,
KHÔNG gửi toàn bộ suggestions/comments/posts vào LLM.

Input:  output của research_mapper.build_research_json()
Output: brand_voice_input dict — input thật cho EXTRACTION_PROMPT (FILE 7)
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List

# Stopword tiếng Việt rất tối giản — chỉ để loại từ nối khi đếm vocabulary
_STOPWORDS = {
    "là", "và", "của", "có", "ở", "tại", "cho", "với", "này", "đó",
    "các", "những", "một", "trong", "ra", "đến", "được", "khi", "nào",
}

_CTA_KEYWORDS = ["inbox", "đặt bàn", "gọi", "hotline", "liên hệ", "đặt món", "gọi ngay"]
_POSITIVE_KEYWORDS = ["ngon", "tuyệt", "ấn tượng", "xứng đáng", "thích", "đẹp"]
_QUESTION_KEYWORDS = ["?", "xin menu", "đặt bàn", "giá", "ở đâu"]
_OBJECTION_KEYWORDS = ["không liên lạc được", "k đặt được", "k gọi được", "thuê bao", "không đặt được"]


# ═══════════════════════════════════════════════════════════════════
# CUSTOMER LANGUAGE
# ═══════════════════════════════════════════════════════════════════

def _extract_customer_language(data: Dict[str, Any]) -> Dict[str, Any]:
    raw = data.get("suggestions_raw", [])
    tagged = data.get("suggestions_tagged", {})

    # top recurring phrases — đếm cụm 2-3 từ xuất hiện nhiều nhất
    words = []
    for s in raw:
        words.extend(w for w in re.findall(r"[\wÀ-ỹ]+", s.lower()) if w not in _STOPWORDS)
    top_words = [w for w, _ in Counter(words).most_common(15)]

    # dominant intents — tag nào có nhiều suggestion nhất (bỏ tag rỗng)
    intent_counts = {k: len(v) for k, v in tagged.items() if v}
    dominant_intents = sorted(intent_counts, key=intent_counts.get, reverse=True)

    return {
        "top_phrases": top_words,
        "dominant_intents": dominant_intents,
        "intent_breakdown": intent_counts,
    }


# ═══════════════════════════════════════════════════════════════════
# MARKET PATTERNS — chỉ truyền lại, đã lọc sẵn ở mapper
# ═══════════════════════════════════════════════════════════════════

def _extract_market_patterns(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "keyword_cluster": data.get("keyword_cluster", []),
        "content_angle": data.get("content_angle", []),
        "intent": data.get("intent", []),
        "competitor_pattern": data.get("competitor_pattern", []),
    }


# ═══════════════════════════════════════════════════════════════════
# EXISTING BRAND VOICE — chọn 3 post đại diện, rút đặc điểm văn phong
# ═══════════════════════════════════════════════════════════════════

_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F1E6-\U0001F1FF]"
)


def _pick_representative_posts(posts: List[str], n: int = 3) -> List[str]:
    """Ưu tiên post độ dài trung bình (không quá ngắn/dài), trải đều thứ tự gốc."""
    if not posts:
        return []
    scored = sorted(posts, key=lambda p: abs(len(p) - 800))  # gần 800 ký tự = "chuẩn"
    picked, seen = [], set()
    for p in scored:
        if p not in seen:
            picked.append(p)
            seen.add(p)
        if len(picked) >= n:
            break
    return picked


def _extract_existing_brand_voice(data: Dict[str, Any]) -> Dict[str, Any]:
    fb_brand = data.get("fb_brand", {})
    posts = data.get("posts_raw", [])

    total_emoji = sum(len(_EMOJI_RE.findall(p)) for p in posts)
    avg_emoji = round(total_emoji / len(posts), 1) if posts else 0

    sentences = []
    for p in posts:
        sentences.extend(re.split(r"[.!?\n]+", p))
    sentences = [s.strip() for s in sentences if s.strip()]
    avg_sentence_len = (
        round(sum(len(s.split()) for s in sentences) / len(sentences), 1)
        if sentences else 0
    )

    cta_count = sum(
        1 for p in posts if any(kw in p.lower() for kw in _CTA_KEYWORDS)
    )
    cta_frequency = f"{cta_count}/{len(posts)}" if posts else "0/0"

    # formality: heuristic dựa trên xưng hô — có "anh/chị", "quý khách" => formal hơn
    formal_signals = sum(p.lower().count("quý khách") + p.lower().count("anh/chị") for p in posts)
    formality = "formal" if formal_signals >= 2 else "casual"

    return {
        "page_intro": fb_brand.get("intro", "")[:500],
        "voice_signals": {
            "avg_emoji_per_post": avg_emoji,
            "avg_sentence_length_words": avg_sentence_len,
            "formality": formality,
            "cta_frequency": cta_frequency,
        },
        "representative_posts": _pick_representative_posts(posts, n=3),
    }


# ═══════════════════════════════════════════════════════════════════
# CUSTOMER FEEDBACK — rút theme, KHÔNG gửi toàn bộ comment
# ═══════════════════════════════════════════════════════════════════

def _extract_customer_feedback(data: Dict[str, Any]) -> Dict[str, Any]:
    comments = data.get("comments_raw", [])
    texts = [c.get("comment", "") or "" for c in comments]

    positive = [t for t in texts if any(kw in t.lower() for kw in _POSITIVE_KEYWORDS)]
    questions = [t for t in texts if any(kw in t.lower() for kw in _QUESTION_KEYWORDS)]
    objections = [t for t in texts if any(kw in t.lower() for kw in _OBJECTION_KEYWORDS)]

    return {
        "positive_themes": positive[:5],
        "common_questions": list(dict.fromkeys(questions))[:5],
        "objections": objections[:5],
        "total_comments_analyzed": len(comments),
    }


# ═══════════════════════════════════════════════════════════════════
# COMPETITOR INSIGHTS — yếu (chỉ có competitor_pattern), giữ schema cho FILE 7
# ═══════════════════════════════════════════════════════════════════

def _extract_competitor_insights(data: Dict[str, Any]) -> Dict[str, Any]:
    patterns = data.get("competitor_pattern", [])
    return {
        "common_positioning": patterns,  # placeholder — chưa có data đối thủ thật
        "messaging_patterns": [],
        "differentiation_opportunities": [],
    }


# ═══════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════

def extract_brand_signals(research_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Input: output của build_research_json()
    Output: brand_voice_input — JSON gọn, đã lọc, sẵn sàng đưa vào EXTRACTION_PROMPT.
    """
    return {
        "customer_language": _extract_customer_language(
            research_json.get("customer_language", {})
        ),
        "market_patterns": _extract_market_patterns(
            research_json.get("market_patterns", {})
        ),
        "existing_brand_voice": _extract_existing_brand_voice(
            research_json.get("existing_brand_voice", {})
        ),
        "customer_feedback": _extract_customer_feedback(
            research_json.get("customer_feedback", {})
        ),
        "competitor_insights": _extract_competitor_insights(
            research_json.get("competitor_insights", {})
        ),
        "business_context": research_json.get("business_context", {}),
    }