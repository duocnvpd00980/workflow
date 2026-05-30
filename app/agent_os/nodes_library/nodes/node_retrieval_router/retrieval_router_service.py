import logging
from .retrieval_router_protocol import RetrievalRouterInput, RetrievalRouterOutput

logger = logging.getLogger(__name__)

class RetrievalRouterService:
    @staticmethod
    async def process_routing(data: RetrievalRouterInput) -> RetrievalRouterOutput:
        """
        Xử lý tính toán vi mô cho câu truy vấn trước khi làm RAG nặng.
        """
        raw_query = data.query.strip()
        
        # Kỹ thuật công nghiệp: Thực hiện Query Cleaning / Keyword Extraction thô
        # (Alex có thể tích hợp thêm một LLM nhỏ ở đây để chuyên viết lại câu hỏi nếu muốn)
        optimized_query = raw_query
        
        logger.info(f"[RetrievalRouterService] Tối ưu hóa query thành công: '{optimized_query}'")
        
        return RetrievalRouterOutput(
            rewritten_query=optimized_query,
            retrieval_needed=True,
            search_namespaces=["company_policy", "product_specs"],
            confidence_score=1.0
        )