from langchain_core.runnables import RunnableConfig
from agent_os.nodes_library.node_aggregator.aggregator_protocol import (
    AggregatedOutput,
)  # Giả định đường dẫn
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame


async def node_AGGREGATOR(state: MainBus, config: RunnableConfig) -> dict:
    """
    NODE AGGREGATOR: Tổng hợp kết quả từ các nhánh thành một bundle duy nhất.
    """

    # --- LOGIC NGHIỆP VỤ (TẠM COMMENT) ---
    # services = config["configurable"].get("services")
    # logic tổng hợp dữ liệu từ reg_ads, reg_blog, reg_email...
    # bundle_id = f"BNDL_{uuid.uuid4().hex[:6]}"

    # 1. Dữ liệu mẫu (Mock Data)
    # Lưu ý: bundle_id là trường bắt buộc (required) trong AggregatedOutput
    mock_aggregator_content = {
        "full_content_ready": True,
        "bundle_id": "BNDL_TEST_888",
        "extra_info_trash": "Dữ liệu rác này sẽ bị lọc bỏ",
    }

    # 2. Ép kiểu và lọc rác (Validation & Extra Ignore)
    # Pydantic sẽ tự động bỏ 'extra_info_trash'
    safe_output = AggregatedOutput(**mock_aggregator_content)

    # 3. PHÁT TÍN HIỆU (Emit): Đóng gói vào StandardFrame
    # Sử dụng .model_dump() để chuyển thành dict chuẩn JSON
    return StandardFrame.emit(BusRegistry.AG, safe_output.model_dump())
