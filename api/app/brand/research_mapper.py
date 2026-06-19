"""
brand/research_mapper.py
────────────────────────────────
Gom dữ liệu thô từ Research Pipeline (ResearchResult + FbPost[] + FbComment[])
thành 1 JSON thống nhất, CHƯA lọc tín hiệu — chỉ tập hợp đúng nguồn.

Output dùng làm input cho signal_extractor.extract_brand_signals().
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.research.models import ResearchResult, FbPost, FbComment


def build_research_json(
    research: Optional[ResearchResult],
    fb_posts: Optional[List[FbPost]] = None,
    fb_comments: Optional[List[FbComment]] = None,
    voice_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Gom raw data theo 6 nhóm cố định. KHÔNG lọc, KHÔNG rút gọn —
    signal_extractor sẽ xử lý ở bước sau.

    Args:
        research:     ResearchResult ORM instance (có thể None nếu chưa research)
        fb_posts:     list FbPost ORM rows
        fb_comments:  list FbComment ORM rows
        voice_config: dict từ VoiceConfigIn.model_dump()

    Returns:
        {
          customer_language: {suggestions_raw, suggestions_tagged},
          market_patterns: {keyword_cluster, content_angle, intent, competitor_pattern},
          existing_brand_voice: {fb_brand, posts_raw},
          customer_feedback: {comments_raw},
          competitor_insights: {competitor_pattern},  # tạm — chưa có node competitor riêng
          business_context: {business_id, business_name, query, voice_config}
        }
    """
    fb_posts = fb_posts or []
    fb_comments = fb_comments or []

    if research is None:
        return {
            "customer_language": {"suggestions_raw": [], "suggestions_tagged": {}},
            "market_patterns": {
                "keyword_cluster": [], "content_angle": [], "intent": [], "competitor_pattern": [],
            },
            "existing_brand_voice": {"fb_brand": {}, "posts_raw": []},
            "customer_feedback": {"comments_raw": []},
            "competitor_insights": {"competitor_pattern": []},
            "business_context": {
                "business_id": None, "business_name": None, "query": None,
                "voice_config": voice_config or {},
            },
        }

    serp = research.serp_data or {}

    return {
        "customer_language": {
            "suggestions_raw": list(research.suggestions_raw or []),
            "suggestions_tagged": dict(research.suggestions_tagged or {}),
        },
        "market_patterns": {
            "keyword_cluster": serp.get("keyword_cluster", []),
            "content_angle": serp.get("content_angle", []),
            "intent": serp.get("intent", []),
            "competitor_pattern": serp.get("competitor_pattern", []),
        },
        "existing_brand_voice": {
            "fb_brand": dict(research.fb_brand or {}),
            "posts_raw": [p.content for p in fb_posts if p.content],
        },
        "customer_feedback": {
            "comments_raw": [
                {
                    "author": c.author,
                    "comment": c.comment,
                    "replies": list(c.replies or []),
                }
                for c in fb_comments
            ],
        },
        "competitor_insights": {
            "competitor_pattern": serp.get("competitor_pattern", []),
        },
        "business_context": {
            "business_id": research.business_id,
            "business_name": research.business_name,
            "query": None, 
            "voice_config": voice_config or {},
        },
    }