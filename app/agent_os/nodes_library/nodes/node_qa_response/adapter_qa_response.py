# ruff: noqa: E501
from __future__ import annotations

import logging
from typing import Any, List

from agent_os.container import AgentServices, get_ctx
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.protocol import BodyFrame, StandardFrame
from agent_os.system.bus.registry import BusRegistry

from .qa_response_protocol import QaResponseOutput
from .qa_response_service import QaResponseService

logger = logging.getLogger(__name__)


async def node_QA_RESPONSE(state: MainBus) -> dict:
    """
    ======================================================================
    INDUSTRIAL PROTOCOL WORKFLOW: [NODE_QA_RESPONSE]
    ======================================================================
    [VAI TRÒ]: Nhặt câu hỏi gốc và mảng tri thức sạch từ mạng Bus.
    Kích hoạt LLM sinh câu trả lời chuyên gia. Phòng vệ tuyệt đối nếu
    tầng tri thức thô (QAR) phía trước bị sập hoặc trống.
    ======================================================================
    """
    logger.info("[NodeQAResponse] Khởi chạy tiến trình Control Plane.")

    # 1. SAFE DATA INSURANCE (Bảo hiểm kiểu dữ liệu mạng Bus)
    if isinstance(state, dict):
        state = MainBus.model_validate(state)

    # 2. DIALECTIC CONTAINER RESOLUTION (Khai thác hạ tầng dịch vụ)
    ctx: AgentServices = await get_ctx()
    llm_engine = ctx.llm_factory.get_model("default")

    # 3. MULTI-LAYER DEFENSIVE POST-GUARD (Phòng vệ dữ liệu thượng nguồn)
    # Tìm kiếm an toàn câu hỏi của User từ Retrieval Router (RR)
    upstream_router = getattr(state, "reg_retrieval_router", None)
    user_input = (
        upstream_router.payload.text
        if upstream_router
        else (getattr(state, "user_input", "") or "Hi")
    )

    # Tìm kiếm an toàn mảng tri thức từ QA Retriever (QAR)
    upstream_retriever = getattr(state, "reg_qa_retriever", None)

    clean_contexts: List[Any] = []
    is_rag_valid = False

    if upstream_retriever and upstream_retriever.payload.status == "SUCCESS":
        raw_records = upstream_retriever.payload.records
        # 🛡️ BẪY CHẶN BẨN: Loại bỏ trường hợp chuỗi báo lỗi, báo rỗng bị nhầm là tài liệu tri thức
        if (
            raw_records
            and len(raw_records) > 0
            and "aborted" not in str(raw_records[0]).lower()
        ):
            clean_contexts = raw_records
            is_rag_valid = True
            logger.info(
                f"[NodeQAResponse] Tiếp nhận thành công {len(clean_contexts)} tài liệu tri thức sạch."
            )

    if not is_rag_valid:
        logger.warning(
            "[NodeQAResponse] Phát hiện luồng tri thức thượng nguồn trống hoặc gãy. Kích hoạt cơ chế Fallback sang LLM Base Knowledge."
        )

    # 4. PURE DOMAIN EXECUTION (Gọi nghiệp vụ lõi)
    module = QaResponseService(llm_engine=llm_engine)

    try:
        # Nếu RAG gãy, ta vẫn truyền user_input xuống, Service hoặc Prompt bên trong
        # sẽ tự biết cách ép LLM dùng kiến thức nền dựa trên mảng contexts rỗng.
        decision = await module.generate_response(
            user_input=user_input,
            contexts=clean_contexts,
        )

        answer_text = getattr(decision, "answer", "").strip()
        tone = getattr(decision, "tone", "neutral")
        citations = getattr(decision, "citations", [])

    except Exception as service_err:
        logger.error(f"[NodeQAResponse] Nghiệp vụ LLM sập: {str(service_err)}")
        answer_text = f"Hệ thống gặp sự cố khi xử lý câu hỏi: '{user_input}'. Vui lòng thử lại sau."
        tone = "neutral"
        citations = []

    # 5. FLAT BUS EMIT (Đóng gói phẳng đúng 8 trường BodyFrame)
    # Xác định trạng thái phản hồi dựa trên nội dung thực tế của câu trả lời
    final_status = "SUCCESS" if answer_text else "EMPTY"

    return StandardFrame.emit(
        registry_key=BusRegistry.QA,  # 🎯 GHI CHÍNH XÁC VÀO Ô: reg_qa_response
        payload=BodyFrame(
            status=final_status,
            text=answer_text,
            records=clean_contexts,  # Giữ lại vết tài liệu đã dùng để đối chiếu UI nếu cần
            entities=[],
            state={"source_used": is_rag_valid, "tone": tone, "flow_type": "qa"},
            metrics={
                "context_quality": 1.0 if is_rag_valid else 0.0,
                "latency_optimized": True,
            },
            context={"citations": citations, "source_node": "node_qa_response"},
            error=None
            if final_status == "SUCCESS"
            else "LLM generated an empty answer.",
        ),
    )
