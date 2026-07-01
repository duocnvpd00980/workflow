"""Fetch keyword/post/comment/image context từ RAG cho blog generation."""
import logging
from typing import Optional

log = logging.getLogger("marketing.rag_context")

IMAGE_SCORE_THRESHOLD = 0.55  # dưới ngưỡng này coi như không match, fallback generate ảnh


async def fetch_rag_context(business_id: str, query: str, top_k: int = 5) -> dict:
    """Trả về keywords/posts/comments (text) + images (url+caption+score)."""
    from app.rag.services.keyword import KeywordRAG
    from app.rag.services.comment import CommentRAG
    from app.rag.services.social import SocialPostRAG
    from app.rag.services.image_rag import ImageRAG
    from app.rag.services.embedder import get_embedder

    result = {"keywords": [], "posts": [], "comments": [], "images": []}
    try:
        kw = await KeywordRAG().search(query, business_id=business_id, top_k=top_k)
        posts = await SocialPostRAG().search(query, business_id=business_id, top_k=top_k)
        cmts = await CommentRAG().search(query, business_id=business_id, top_k=top_k)

        irag = ImageRAG(get_embedder())
        imgs = await irag.search_by_store(query, k=3, business_id=business_id)

        result["keywords"] = [c.text for c in kw]
        result["posts"] = [c.text for c in posts]
        result["comments"] = [c.text for c in cmts]
        result["images"] = [
            {"url": r["meta"]["url"], "caption": r["meta"]["caption"], "score": r["score"]}
            for r in imgs
        ]
    except Exception as e:
        log.warning(f"[rag_context] fetch failed cho business_id={business_id}: {e}")

    return result


async def match_image_for_placeholder(business_id: str, description: str) -> Optional[dict]:
    """Tìm 1 ảnh thật khớp mô tả placeholder trong blog. None nếu không đủ tốt -> generate."""
    from app.rag.services.image_rag import ImageRAG
    from app.rag.services.embedder import get_embedder

    try:
        irag = ImageRAG(get_embedder())
        results = await irag.search_by_store(description, k=1, business_id=business_id)
        if results and results[0]["score"] >= IMAGE_SCORE_THRESHOLD:
            return {"url": results[0]["meta"]["url"], "score": results[0]["score"]}
    except Exception as e:
        log.warning(f"[match_image] failed: {e}")
    return None