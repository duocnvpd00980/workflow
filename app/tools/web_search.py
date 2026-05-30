from langchain_core.tools import tool
import logging

log = logging.getLogger(__name__)


@tool
def web_search_tool(query: str) -> str:
    """..."""
    try:
        # Nếu chưa có Service thật, trả về kết quả giả lập
        return f"Thông tin về '{query}' đang được cập nhật..."
    except Exception as e:
        # Trả về kết quả 'fallback' thay vì để văng lỗi
        return "Hiện tại hệ thống tìm kiếm web chưa sẵn sàng, vui lòng thử lại sau."
