from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

# Sử dụng WriterOutput từ protocol đã thống nhất
from .blog_writer_protocol import WriterOutput


async def node_BLOG_WRITER(state: MainBus, config: RunnableConfig) -> dict:
    """
    NODE BLOG WRITER: Thực thi viết bài dựa trên kế hoạch (Plan) và dữ liệu bổ trợ (Tool results).
    """
    # --- LOGIC NGHIỆP VỤ (TẠM COMMENT) ---
    # services = config["configurable"].get("services")
    # engine = services["llm_factory"].get_model("qwen2.5-max")
    # module = WriterService(llm_engine=engine)
    # plan_data = state.reg_blog_plan.payload if state.reg_blog_plan else ""
    # tool_data = state.reg_tool_results.payload if state.reg_tool_results else ""
    # raw = await module.run(plan=plan_data, tool_data=tool_data, lang=getattr(state, "language", "vi"))
    # parsed = WriterParser.parse(raw)

    # 1. Dữ liệu mẫu (Mock Data) chuẩn theo WriterOutput
    mock_blog_content = {
        "draft_content": "Đây là nội dung chi tiết bài Blog được triển khai từ dàn ý...",
        "pending_tool": False,
        "tool_query": None,
    }

    # 2. Ép kiểu và lọc rác tự động bằng Pydantic
    # (Đã có ConfigDict extra='ignore' trong WriterOutput)
    safe_output = WriterOutput(**mock_blog_content)

    # 3. PHÁT TÍN HIỆU (Emit): Ghi vào reg_blog_writer
    # Sử dụng .model_dump() để chuyển đổi thành dict thuần cho MainBus
    return StandardFrame.emit(BusRegistry.BW, safe_output.model_dump())
