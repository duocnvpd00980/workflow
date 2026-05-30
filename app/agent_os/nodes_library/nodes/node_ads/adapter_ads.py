from langchain_core.runnables import RunnableConfig
from agent_os.nodes_library.node_ads.ads_protocol import AdOutput
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

async def node_AGENT_ADS(state: MainBus, config: RunnableConfig) -> dict:
    """
    NODE TEST THÔNG LUỒNG:
    Tạm thời comment logic nghiệp vụ, trả về dữ liệu mẫu chuẩn StandardFrame.
    """
    
    # --- LOGIC NGHIỆP VỤ (TẠM COMMENT) ---
    # services = config["configurable"].get("services")
    # llm_factory = services.get("llm_factory")
    # selected_engine = llm_factory.get_model("qwen2.5")
    # module = AdsService(llm_engine=selected_engine)
    # raw_output = await module.run(...)
    # parsed_output = AdsParser.parse(raw_output)

    # 1. Dữ liệu mẫu (Mock Data)
    mock_ad_content = {
        "content": """
        🏢 CĂN HỘ CAO CẤP ĐÀ NẴNG
        Sống sang trọng giữa trung tâm thành phố biển.
        - View biển
        - Nội thất 5 sao
        - An ninh 24/7
        📞 Liên hệ ngay để nhận ưu đãi!
        """,
        "has_cta": True,
        "language_detected": "vi"
    }
    safe_output = AdOutput(**mock_ad_content)
    return StandardFrame.emit(
        BusRegistry.AD,
        safe_output.model_dump()
    )