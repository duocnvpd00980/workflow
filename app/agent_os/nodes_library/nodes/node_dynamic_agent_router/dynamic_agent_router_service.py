# =========================================================
# FILE: dynamic_agent_router_service.py
# =========================================================
from typing import Any, Dict


class DynamicAgentRouterService:
    """
    DYNAMIC AGENT ROUTER DOMAIN SERVICE (PURE LOGIC)

    Thuật toán xử lý lõi của Rơ-le định tuyến.
    Nhận các tham số đóng ngắt mạch điện từ bộ cấu hình (Planner)
    để tính toán ra các kênh ngõ ra được cấp điện thực tế.
    """

    async def compute_routing_channels(
        self, run_ads: bool, run_email: bool, run_blog: bool
    ) -> Dict[str, Any]:
        """
        Tính toán toán học và logic để xuất ra trạng thái các kênh của bộ định tuyến.
        """
        activated_channels = []

        # Đóng ngắt các cổng vật lý dựa trên tín hiệu của Planner gửi xuống
        if run_ads:
            activated_channels.append("reg_ads")
        if run_email:
            activated_channels.append("reg_email")
        if run_blog:
            activated_channels.append("reg_blog_plan")

        # Xác định chế độ định tuyến dựa trên số lượng kênh được mở
        total = len(activated_channels)
        if total == 3:
            routing_mode = "parallel_all"
        elif total > 0:
            routing_mode = "dynamic"
        else:
            routing_mode = (
                "bypass"  # Toàn bộ hệ thống marketing bị ngắt, đi thẳng về sync
            )

        return {
            "router_active": True,
            "routing_mode": routing_mode,
            "activated_channels": activated_channels,
            "total_channels": total,
        }
