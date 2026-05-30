from __future__ import annotations
import logging
from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame
from agent_os.tools.tools_registry import web_search_tool

log = logging.getLogger(__name__)


async def node_fallback_search(state: MainBus, config: RunnableConfig = None) -> dict:
    """
    Fallback Search Node đã được tối ưu hóa để ngắt vòng lặp.
    """
    query = getattr(state.relevance_check.payload, "text", "")

    # 1. Kiểm tra an toàn: Nếu không có query, dừng ngay lập tức
    if not query:
        log.warning("[FALLBACK] Thiếu query, dừng tìm kiếm để tránh lặp.")
        return StandardFrame.emit(
            registry_key=BusRegistry.FB,
            payload=BodyFrame(
                status="STOPPED", text="No query provided", route="error"
            ),
        )

    try:
        log.info(f"[FALLBACK] Đang gọi trực tiếp công cụ tìm kiếm cho: {query}")
        result_text = web_search_tool.invoke({"query": query})

        return StandardFrame.emit(
            registry_key=BusRegistry.FB,
            payload=BodyFrame(
                status="SUCCESS",
                text=result_text,
                route="error",
                state={"process_completed": True},  # <--- Quan trọng: Đánh dấu hoàn tất
            ),
        )

    except Exception as e:
        log.error(f"[FALLBACK] Search Error: {e}")

        # 2. NGẮT VÒNG LẶP: Đừng bao giờ trả về route="error" nếu nó quay lại Agent
        # Hãy trả về một thông báo "Thất bại" để Agent nhận biết và dừng lại
        return StandardFrame.emit(
            registry_key=BusRegistry.FB,
            payload=BodyFrame(
                status="FAILED",
                text=f"Công cụ tìm kiếm không phản hồi: {str(e)[:50]}",
                route="error",  # <--- Chuyển route sang 'end' để ngắt luồng Agent
                state={"process_completed": True, "error_handled": True},
            ),
        )
