# =========================================================
# FILE: policy_engine_service.py
# =========================================================
from agent_os.nodes_library.node_policy_engine.policy_engine_protocol import (
    PolicyEngineOutput,
)


class PolicyEngineService:
    """
    POLICY ENGINE DOMAIN SERVICE (PURE LOGIC)

    Chỉ tập trung vào business logic đóng ngắt thiết bị bảo vệ.
    Trả về dữ liệu chuẩn hóa theo đúng Hợp đồng Protocol (Pydantic Native).
    """

    async def enforce_policy(self, mode: str) -> PolicyEngineOutput:
        """
        Căn cứ vào chế độ (mode) trần để kích hoạt các switch bảo vệ tương ứng.
        """
        cleaned_mode = str(mode or "").lower().strip()

        # Chế độ: MARKETING (Kích hoạt toàn bộ công suất)
        if cleaned_mode == "marketing":
            return PolicyEngineOutput(
                allow_heavy_execution=True,
                allow_memory=True,
                allow_knowledge=True,
                allow_tools=True,
                route="marketing",
            )

        # Chế độ: QA (Chỉ mở cổng tri thức RAG)
        if cleaned_mode == "qa":
            return PolicyEngineOutput(
                allow_heavy_execution=False,
                allow_memory=False,
                allow_knowledge=True,
                allow_tools=False,
                route="qa",
            )

        # Chế độ: SMALLTALK (Hạn chế tối đa tài nguyên)
        if cleaned_mode == "smalltalk":
            return PolicyEngineOutput(
                allow_heavy_execution=False,
                allow_memory=False,
                allow_knowledge=False,
                allow_tools=False,
                route="smalltalk",
            )

        # Chế độ mặc định bảo vệ: ERROR / UNDEFINED
        return PolicyEngineOutput(
            allow_heavy_execution=False,
            allow_memory=False,
            allow_knowledge=False,
            allow_tools=False,
            route="error",
        )
