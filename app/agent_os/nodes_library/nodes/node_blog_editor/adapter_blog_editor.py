from agent_os.nodes_library.node_blog_editor.blog_editor_protocol import WriterOutput

# WriterParser tạm thời không dùng vì ta dùng khởi tạo trực tiếp để lọc rác nhanh
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame
from langchain_core.runnables import RunnableConfig


async def node_BLOG_EDITOR(state: MainBus, config: RunnableConfig) -> dict:
    """
    NODE BLOG EDITOR: Biên tập nội dung bài viết Blog.
    """
    # --- LOGIC NGHIỆP VỤ (TẠM COMMENT) ---
    # services = config["configurable"].get("services")
    # engine = services["llm_factory"].get_model("deepseek-v3")
    # plan_data = state.reg_blog_plan.payload if state.reg_blog_plan else ""
    # tool_data = state.reg_tool_results.payload if state.reg_tool_results else "None"
    # context = f"Plan: {plan_data}. Search Results: {tool_data}"
    # raw = await engine.generate(system="Professional Blogger Mode", user=context, schema=WriterOutput)
    # res = WriterParser.parse(raw)

    # 1. Dữ liệu mẫu (Mock Data) chuẩn theo WriterOutput
    mock_blog_data = {
        "draft_content": "Đây là nội dung bài blog chuẩn SEO về bất động sản Đà Nẵng...",
        "pending_tool": False,
        "tool_query": None,
        "garbage_data": "Thông tin thừa này sẽ bị loại bỏ bởi ConfigDict",
    }

    # 2. Ép kiểu và lọc rác qua WriterOutput
    # Sử dụng tính năng extra="ignore" đã định nghĩa trong protocol
    safe_output = WriterOutput(**mock_blog_data)

    # 3. Trả về: Đóng gói vào StandardFrame và dump dictionary
    # BusRegistry.BW tương ứng với reg_blog_writer/editor
    return StandardFrame.emit(BusRegistry.BW, safe_output.model_dump())
