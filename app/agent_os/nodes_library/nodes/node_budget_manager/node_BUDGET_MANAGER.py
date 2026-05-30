from langchain_core.runnables import RunnableConfig
from agent_os.nodes_library.node_budget_manager.budget_manager_protocol import (
    BudgetManagerOutput,
)
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame


async def node_BUDGET_MANAGER(state: MainBus, config: RunnableConfig) -> dict:
    """
    NODE BUDGET MANAGER: Kiểm soát ví tiền và tối ưu hóa chi phí LLM.
    """

    # --- LOGIC NGHIỆP VỤ (TẠM COMMENT) ---
    # usage = state.reg_observer.payload.get("usage_stats") if state.reg_observer else {}
    # current_cost = calculate_cost(usage)
    # limit = config.get("budget_limit", 1.0) # Mặc định 1 USD

    # 1. Dữ liệu mẫu (Mock Data)
    mock_budget_data = {
        "total_budget_limit": 5.0,
        "current_spend": 0.45,
        "is_budget_exceeded": False,
        "suggested_model_tier": "premium",  # Vẫn còn tiền nên dùng model xịn (gpt-4o, qwen-max)
        "remaining_percentage": 91.0,
    }

    # 2. Ép kiểu và lọc rác
    safe_output = BudgetManagerOutput(**mock_budget_data)

    # 3. Trả về: Ghi vào reg_budget (BusRegistry.BM)
    return StandardFrame.emit(BusRegistry.BM, safe_output.model_dump())
