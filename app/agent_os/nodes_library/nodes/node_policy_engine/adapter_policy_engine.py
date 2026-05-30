# =========================================================
# FILE: adapter_policy_engine.py
# =========================================================
from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import (
    StandardFrame,
    BodyFrame,
)

from .policy_engine_service import PolicyEngineService

# Khởi tạo instance service dùng chung toàn cục cho Node
service_module = PolicyEngineService()


async def node_POLICY_ENGINE(
    state: MainBus,
    config: RunnableConfig,
) -> dict:
    
    # 1. KIỂM TRA CHẶN LỖI (Fail-fast): Yêu cầu bắt buộc phải có dữ liệu sạch từ Intent Classifier (IC)
    if not state.reg_intent_classifier or state.reg_intent_classifier.payload.status != "SUCCESS":
        raise RuntimeError(
            "[NODE_POLICY_ENGINE] Security Violation: Chưa có kết quả phân loại Intent hoặc IC thất bại!"
        )

    # 2. BÓC TÁCH (Pydantic Native): Lấy trực tiếp intent từ payload của thanh ghi IC

    mode = state.reg_intent_classifier.payload.state.get("intent")

    print(f"🛡️ [ADAPTER_POE] Driver extracted incoming Intent Mode: '{mode}'")

    # 3. THỰC THI NGHIỆP VỤ (Service): Nhận về một Pydantic Object đóng băng xịn sò
    result = await service_module.enforce_policy(mode=str(mode))

    # 4. CHUẨN HÓA TRẠNG THÁI (Status Normalization)
    policy_passed = (result.route != "error")
    status = "SUCCESS" if policy_passed else "FAILED"


    # 5. EMIT: Phát tín hiệu chuyển mạch chính thức lên thanh ghi POL của MainBus
    return StandardFrame.emit(
        registry_key=BusRegistry.POL,
        payload=BodyFrame(
            status=status,
            text=f"Policy enforcement completed for mode: {mode}",
            state={
                "intent_mode": mode,
                "route_to": result.route,
                "policy_passed": policy_passed,
                "allow_heavy_execution": result.allow_heavy_execution,
                "allow_memory": result.allow_memory,
                "allow_knowledge": result.allow_knowledge,
                "allow_tools": result.allow_tools,
            },
            metrics={
                "priority": 1 if result.allow_heavy_execution else 0,
            },
            context=state.reg_intent_classifier.payload.context, 
            error=None if policy_passed else "Policy rejected: Undefined or error traffic detected.",
        ),
    )