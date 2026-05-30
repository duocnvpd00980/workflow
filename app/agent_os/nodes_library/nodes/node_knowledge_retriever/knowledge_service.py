# =========================================================
# FILE:
# agent_os/nodes_library/node_knowledge_retriever/knowledge_service.py
# =========================================================

import logging
from typing import Any

from agent_os.nodes_library.node_knowledge_retriever.knowledge_protocol import (
    RetrievedChunk,
    KnowledgeRetrieverOutput
)

logger = logging.getLogger(__name__)


class KnowledgeRetrieverService:
    """
    CORE DOMAIN SERVICE: Chỉ chứa logic nghiệp vụ trích xuất tri thức.
    Được thiết kế theo khuôn khổ độc lập, nhận Engine từ lớp Adapter truyền vào.
    """

    def __init__(self, knowledge_engine: Any):
        # KHUÔN KHỔ CHUẨN: Nhận engine đã được khởi tạo sẵn từ bên ngoài (Dependency Injection)
        # Triệt tiêu hoàn toàn lỗi tự tạo Engine bậy bạ làm sập nguồn hệ thống
        self.engine = knowledge_engine

    async def run(
        self,
        query: str,
        user_id: str,
        doc_type: str,
        top_k: int = 5,
        score_threshold: float = 0.7
    ) -> KnowledgeRetrieverOutput:

        try:
            logger.info(
                f"KNOWLEDGE SEARCH | user={user_id} | type={doc_type}"
            )

            # Gọi Engine tìm kiếm (Lúc này engine đã được Adapter đảm bảo nạp đủ tham số)
            results = self.engine.search(
                query=query,
                user_id=user_id,
                doc_type=doc_type,
                top_k=top_k,
                score_threshold=score_threshold
            )

            chunks = []
            for r in results:
                chunks.append(
                    RetrievedChunk(
                        text=r.text,
                        score=float(r.score or 0.0),
                        metadata=r.metadata or {}
                    )
                )

            return KnowledgeRetrieverOutput(
                success=True,
                query=query,
                retrieved_chunks=chunks,
                total_chunks=len(chunks),
                doc_type=doc_type
            )

        except Exception as e:
            logger.exception("KNOWLEDGE RETRIEVAL FAILED")
            return KnowledgeRetrieverOutput(
                success=False,
                query=query,
                retrieved_chunks=[],
                total_chunks=0,
                doc_type=doc_type,
                error=str(e)
            )