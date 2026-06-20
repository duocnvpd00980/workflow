"""rag_core — Knowledge RAG cho content generation (không phải QA chatbot).

3 loại RAG độc lập, mỗi loại 1 storage riêng:
    - KeywordRAG  -> rag_storage/keyword/
    - CommentRAG  -> rag_storage/comment/
    - SocialPostRAG -> rag_storage/social/

Dùng:
    from rag_core import KeywordRAG, CommentRAG, SocialPostRAG

    kw = KeywordRAG()
    await kw.add("seo nhà hàng view pháo hoa đà nẵng", business_id="b1", source_id="kw-001")
    chunks = await kw.search("nhà hàng view đẹp đà nẵng", business_id="b1")
"""

from .comment import CommentRAG
from .keyword import KeywordRAG
from .schemas import Chunk, SearchResult
from .social import SocialPostRAG

__all__ = ["KeywordRAG", "CommentRAG", "SocialPostRAG", "Chunk", "SearchResult"]
