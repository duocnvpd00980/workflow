from langchain_core.runnables import RunnableConfig
from agent_os.nodes_library.node_blog_planner.planner_protocol import BlogPlanOutput
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame


async def node_BLOG_PLANNER(state: MainBus, config: RunnableConfig) -> dict:
    """
    NODE BLOG PLANNER: Lập kế hoạch nội dung bài viết.
    Tạm thời comment nghiệp vụ, trả về dữ liệu mẫu để thông luồng.
    """

    # --- LOGIC NGHIỆP VỤ (TẠM COMMENT) ---
    # services = config["configurable"].get("services")
    # engine = services["llm_factory"].get_model("qwen2.5")
    # module = PlannerService(llm_engine=engine)
    # raw = await module.run(topic=state.user_input, language=getattr(state, "language", "vi"))
    # parsed = PlannerParser.parse(raw)

    # 1. Dữ liệu mẫu (Mock Data) khớp với BlogPlan Protocol
    mock_plan = {
        "title_suggestion": "Giải pháp đầu tư bất động sản bền vững 2026",
        "target_keywords": ["đầu tư 2026", "bất động sản", "chiến lược tài chính"],
        "outline": [
            "Mở đầu: Xu hướng thị trường",
            "Nội dung 1: Các phân khúc tiềm năng",
            "Nội dung 2: Rủi ro và cách phòng tránh",
            "Kết luận",
        ],
        "estimated_word_count": 1500,
        "research_required": False,
    }

    # 2. Ép kiểu và lọc rác tự động bằng Pydantic
    safe_output = BlogPlanOutput(**mock_plan)

    # 3. PHÁT TÍN HIỆU (Emit): Ghi vào reg_blog_plan
    # Sử dụng .model_dump() để LangGraph có thể serialize dữ liệu
    return StandardFrame.emit(BusRegistry.BP, safe_output.model_dump())
