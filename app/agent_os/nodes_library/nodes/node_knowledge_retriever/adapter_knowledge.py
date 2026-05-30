# =============================================================================
# FILE: agent_os/nodes_library/node_knowledge_retriever/adapter_knowledge.py
# =============================================================================

from langchain_core.runnables import RunnableConfig
from django.conf import settings  # Import cài đặt Django để lấy Engine từ RAM tĩnh

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

from agent_os.nodes_library.node_knowledge_retriever.knowledge_service import (
    KnowledgeRetrieverService
)

from agent_os.nodes_library.node_knowledge_retriever.knowledge_protocol import (
    KnowledgeRetrieverOutput
)

# CHỐT CHẶN AN TOÀN: Tuyệt đối KHÔNG khởi tạo 'module = KnowledgeRetrieverService()' tại đây nữa.


async def node_KNOWLEDGE_RETRIEVER(
    state: MainBus,
    config: RunnableConfig
) -> dict:

    conf = config.get("configurable", {}) \
        if isinstance(config, dict) else {}

    thread_id = conf.get("thread_id")
    tenant_id = conf.get("tenant_id")

    # =====================================================
    # INPUTS
    # =====================================================

    user_input = getattr(state, "user_input", "")

    user_id = getattr(
        state,
        "user_id",
        tenant_id or "anonymous"
    )

    # ==========================================
    # DOC TYPE
    # ==========================================

    # Có thể thay dynamic routing sau
    doc_type = getattr(
        state,
        "doc_type",
        "general"
    )

    # =====================================================
    # SERVICE (LAZY INITIALIZATION & DEPENDENCY INJECTION)
    # =====================================================
    
    # 1. Bốc engine xịn đã được build_runtime() nạp sẵn trên RAM tĩnh Django
    knowledge_engine = getattr(settings, "KNOWLEDGE_ENGINE", None)
    if not knowledge_engine:
        raise ValueError("[NODE_KNOWLEDGE_RETRIEVER] KNOWLEDGE_ENGINE chưa được nạp lên RAM tĩnh!")

    # 2. Khởi tạo Service ngay tại local scope và tiêm Engine vào gánh vác hạ tầng DB
    module = KnowledgeRetrieverService(knowledge_engine=knowledge_engine)

    # 3. Chạy nghiệp vụ trích xuất tri thức
    res = await module.run(
        query=user_input,
        user_id=user_id,
        doc_type=doc_type,
        top_k=5,
        score_threshold=0.7
    )

    # =====================================================
    # OUTPUT FRAME
    # =====================================================

    output = KnowledgeRetrieverOutput(
        success=res.success,
        query=res.query,
        retrieved_chunks=res.retrieved_chunks,
        total_chunks=res.total_chunks,
        doc_type=res.doc_type,
        error=res.error
    )

    # Phát chuẩn lên xe Bus hệ thống
    return StandardFrame.emit(
        BusRegistry.KE,
        output.model_dump()
    )