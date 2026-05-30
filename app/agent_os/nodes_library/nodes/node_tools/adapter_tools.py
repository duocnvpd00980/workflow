from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame
from .tools_protocol import ToolsAdapterOutput, ToolResultEntry

async def node_TOOL_EXECUTOR(state: MainBus, config: RunnableConfig) -> dict:
    """
    NODE ADAPTER TOOLS: Thực thi các công cụ ngoại vi và chuẩn hóa kết quả về MainBus.
    """
    
    # --- LOGIC NGHIỆP VỤ (TẠM COMMENT) ---
    # intent = state.reg_intent.payload if state.reg_intent else {}
    # tool_calls = intent.get("required_tools", [])
    # engine = services["tool_executor"]
    # raw_results = await engine.ainvoke(tool_calls)

    # 1. Dữ liệu mẫu (Mock Data) giả định vừa gọi Google Search và Scraper
    mock_tools_data = {
        "results": [
            {
                "tool_name": "google_search",
                "input_params": {"q": "xu hướng BĐS Đà Nẵng 2026"},
                "output_data": "Giá đất nền ven biển tăng 15% so với cùng kỳ...",
                "success": True
            },
            {
                "tool_name": "web_scraper",
                "input_params": {"url": "https://baodanang.vn/kinh-te/..."},
                "output_data": "Quy hoạch phân khu ven sông Hàn đã được phê duyệt.",
                "success": True
            }
        ],
        "summary_of_findings": "Thông tin tìm được: Giá BĐS Đà Nẵng 2026 đang tăng trưởng ổn định nhờ quy hoạch sông Hàn mới.",
        "tokens_consumed": 850
    }

    # 2. Ép kiểu và lọc rác qua Protocol
    safe_output = ToolsAdapterOutput(**mock_tools_data)

    # 3. TRẢ VỀ: Ghi vào reg_tool_results (Sử dụng Registry TR)
    # Registry code TR (Tool Results) giúp các Writer Node biết chỗ tìm dữ liệu thực tế
    return StandardFrame.emit(
        BusRegistry.TR, 
        safe_output.model_dump()
    )