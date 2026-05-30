# =========================================================
# FILE: adapter_dynamic_agent_router.py
# =========================================================
from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

from .dynamic_agent_router_protocol import DynamicAgentRouterOutput


async def node_DYNAMIC_AGENT_ROUTER(state: MainBus, config: RunnableConfig) -> dict:
    """
    ADAPTER NODE: DYNAMIC AGENT ROUTER (DRIVER LAYER)

    Nhiệm vụ:
    - Đọc các switch cấu hình cấp phép từ bộ nhớ của Policy Engine (Planner).
    - Tổng hợp các kênh/ngõ ra (nhánh Agent) được phép kích hoạt.
    - Ép kiểu dữ liệu sạch theo đúng khung Protocol và phát tín hiệu lên BusRegistry.DAR.
    """

    # ── 1. ĐỌC CẤU HÌNH ĐÓNG NGẮT TỪ THANH GHI POLICY ENGINE ─────────────────────
    poe_reg = None
    if isinstance(state, dict):
        poe_reg = state.get(BusRegistry.POE)
    elif hasattr(state, BusRegistry.POE):
        poe_reg = getattr(state, BusRegistry.POE)

    # Khởi tạo các cờ switch mặc định (Mạch hở - Khóa an toàn)
    run_ads = False
    run_email = False
    run_blog = False

    if poe_reg:
        payload = (
            poe_reg.get("payload", {})
            if isinstance(poe_reg, dict)
            else getattr(poe_reg, "payload", {})
        )

        # Đồng bộ hóa kiểu dữ liệu Object/Dict an toàn
        if hasattr(payload, "model_dump"):
            payload_dict = payload.model_dump()
        elif hasattr(payload, "__dict__"):
            payload_dict = payload.__dict__
        else:
            payload_dict = payload if isinstance(payload, dict) else {}

        # Trích xuất trạng thái đóng ngắt của từng Agent từ Planner
        run_ads = payload_dict.get("run_ads", False)
        run_email = payload_dict.get("run_email", False)
        run_blog = payload_dict.get("run_blog", False)

    # ── 2. ĐỊNH TUYẾN KÊNH DỰA TRÊN THÔNG SỐ TRÍCH XUẤT ──────────────────────────
    activated_channels = []

    # Map các switch True/False thành danh sách các Registry Key đích thực tế
    if run_ads:
        activated_channels.append(BusRegistry.AD)  # "reg_ads"
    if run_email:
        activated_channels.append(BusRegistry.EM)  # "reg_email"
    if run_blog:
        activated_channels.append(BusRegistry.BP)  # "reg_blog_plan"

    print(f"🎛️ [ADAPTER_DAR] Router Activated Channels: {activated_channels}")

    # ── 3. ĐÓNG GÓI DỮ LIỆU ĐẦU RA MẪU (OR REALTIME OUTPUT) ─────────────────────
    router_data = {
        "router_active": True,
        "routing_mode": "dynamic",
        "activated_channels": activated_channels,
        "total_channels": len(activated_channels),
    }

    # Ép kiểu qua khung bảo vệ Protocol chống tràn/nhiễu tín hiệu
    safe_output = DynamicAgentRouterOutput(**router_data)

    # ── 4. PHÁT TÍN HIỆU LÊN TRỤC BUS HỆ THỐNG ─────────────────────────────────
    # Đăng ký lên trục chính thông qua khóa BusRegistry.DAR (Đã đổi tên từ BS)
    return StandardFrame.emit(BusRegistry.BS, safe_output.model_dump())
