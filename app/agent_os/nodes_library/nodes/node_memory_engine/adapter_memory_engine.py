from langchain_core.runnables import RunnableConfig
from agent_os.nodes_library.node_memory_engine.memory_engine_protocol import MemoryEngineOutput
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

async def node_MEMORY_ENGINE(state: MainBus, config: RunnableConfig) -> dict:
    """
    NODE MEMORY ENGINE: Tổng hợp các 'ký ức' quan trọng từ Bus để làm nguyên liệu cho Agent.
    """
    
    # --- LOGIC NGHIỆP VỤ (TẠM COMMENT) ---
    # memories = []
    # if state.reg_blog_plan: memories.append(MemoryEntry(node_id="BP", content=state.reg_blog_plan.payload))
    # if state.reg_tool_results: memories.append(MemoryEntry(node_id="TR", content=state.reg_tool_results.payload))

    # 1. Dữ liệu mẫu (Mock Data)
    mock_memory_data = {
        "short_term_history": [
            {"node_id": "INTENT", "content": "Người dùng muốn viết blog BĐS"},
            {"node_id": "PLANNER", "content": "Đã tạo dàn ý 4 phần"}
        ],
        "context_window": {
            "main_topic": "Bất động sản Đà Nẵng",
            "tone": "Chuyên nghiệp, tin cậy",
            "last_action": "Đã hoàn thành tìm kiếm dữ liệu thực tế"
        },
        "memory_efficiency_score": 0.95
    }

    # 2. Ép kiểu và lọc rác qua Protocol
    safe_output = MemoryEngineOutput(**mock_memory_data)

    # 3. Trả về: Ghi vào reg_memory_engine (BusRegistry.ME)
    return StandardFrame.emit(
        BusRegistry.ME, 
        safe_output.model_dump()
    )