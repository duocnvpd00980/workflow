from __future__ import annotations
import logging
from langchain_core.runnables import RunnableConfig

from app.core.main_bus import MainBus
from app.core.registry import BusRegistry
from app.core.protocol import StandardFrame, BodyFrame
from app.tools.tools_registry import google_search

log = logging.getLogger(__name__)


async def node_fallback_search(state: MainBus, config: RunnableConfig | None = None) -> dict:
    """
    Fallback Search Node - Tìm kiếm Google khi agent không tìm được câu trả lời.
    
    Ngắt vòng lặp bằng cách:
    1. Kiểm tra query hợp lệ
    2. Giới hạn số lần retry
    3. Luôn đánh dấu process_completed=True
    4. Route về 'end' thay vì 'error' để không quay lại agent
    """
    # Lấy query từ state
    query = getattr(state.relevance_check.payload, "text", "") if state.relevance_check else ""
    
    if not query:
        log.warning("[FALLBACK] Thiếu query, dừng tìm kiếm.")
        return StandardFrame.emit(
            registry_key=BusRegistry.FB,
            payload=BodyFrame(
                status="STOPPED",
                text="Không có query để tìm kiếm.",
                route="end",  # Route về end, không quay lại agent
                state={"process_completed": True},
            ),
        )

    # Kiểm tra đã thử tìm kiếm chưa (tránh lặp)
    search_attempts = getattr(state.relevance_check.payload, "state", {}).get("search_attempts", 0)
    if search_attempts >= 2:
        log.warning(f"[FALLBACK] Đã thử {search_attempts} lần, dừng để tránh lặp.")
        return StandardFrame.emit(
            registry_key=BusRegistry.FB,
            payload=BodyFrame(
                status="STOPPED",
                text="Đã thử tìm kiếm nhiều lần không thành công.",
                route="end",
                state={"process_completed": True, "max_retries_reached": True},
            ),
        )

    try:
        log.info(f"[FALLBACK] Tìm kiếm: {query}")
        
        # Gọi tool - google_search là @tool, dùng .ainvoke cho async
        result = await google_search.ainvoke({"query": query})
        
        # Tăng counter search attempts
        new_state = {
            "process_completed": True,
            "search_attempts": search_attempts + 1,
        }

        return StandardFrame.emit(
            registry_key=BusRegistry.FB,
            payload=BodyFrame(
                status="SUCCESS",
                text=result,
                route="end",  # Route về end, không quay lại agent
                state=new_state,
            ),
        )

    except Exception as e:
        log.error(f"[FALLBACK] Lỗi tìm kiếm: {e}", exc_info=True)
        
        return StandardFrame.emit(
            registry_key=BusRegistry.FB,
            payload=BodyFrame(
                status="FAILED",
                text=f"Không thể tìm kiếm: {str(e)[:100]}",
                route="end",  # Route về end, KHÔNG phải 'error'
                state={
                    "process_completed": True,
                    "search_attempts": search_attempts + 1,
                    "error": str(e)[:100],
                },
            ),
        )