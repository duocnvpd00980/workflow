from langchain_core.runnables import RunnableConfig
from agent_os.nodes_library.node_context_clipper.clipper_protocol import ClipperOutput
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

async def node_CLIPPER(state: MainBus, config: RunnableConfig) -> dict:
    """
    NODE CLIPPER: Trích xuất các điểm tin đắt giá từ nội dung tổng hợp.
    """
    
    # --- LOGIC NGHIỆP VỤ (TẠM COMMENT) ---
    # aggregated_data = state.reg_aggregator.payload
    # engine = services["llm_factory"].get_model("gpt-4o-mini")
    # clips = await engine.extract(aggregated_data)

    # 1. Dữ liệu mẫu (Mock Data)
    mock_clipper_data = {
        "source_id": "BNDL_TEST_888",
        "clips": [
            "Đà Nẵng dẫn đầu xu hướng bất động sản biển 2026",
            "Lợi nhuận cho thuê căn hộ cao cấp đạt ngưỡng 8%/năm",
            "Chính sách hỗ trợ vay vốn 0% lãi suất trong 24 tháng"
        ],
        "summary": "Nội dung tập trung vào tiềm năng đầu tư căn hộ biển tại Đà Nẵng với các ưu đãi tài chính mạnh mẽ.",
        "tags": ["Đà Nẵng", "BĐS", "Đầu tư", "Căn hộ cao cấp"],
        "llm_reasoning": "Tôi chọn những đoạn này vì nó có số liệu cụ thể." # Sẽ bị lọc
    }

    # 2. Ép kiểu và lọc rác qua Protocol
    safe_output = ClipperOutput(**mock_clipper_data)

    # 3. Trả về: Ghi vào reg_clipper (BusRegistry.CP)
    return StandardFrame.emit(
        BusRegistry.CP, 
        safe_output.model_dump()
    )