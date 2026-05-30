from langchain_core.runnables import RunnableConfig
from agent_os.nodes_library.node_mail.mail_protocol import MailOutput
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

async def node_EMAIL(state: MainBus, config: RunnableConfig) -> dict:
    """
    NODE EMAIL WRITER: Soạn thảo nội dung email dựa trên kế hoạch marketing.
    """
    
    # --- LOGIC NGHIỆP VỤ (TẠM COMMENT) ---
    # context = state.reg_memory_context.payload if state.reg_memory_context else {}
    # writer = services["llm_factory"].get_model("email_expert")
    # email_draft = await writer.generate(context)

    # 1. Dữ liệu mẫu (Mock Data)
    mock_mail_data = {
        "subject": "🔥 Cơ hội đầu tư BĐS biển Đà Nẵng - Chỉ từ 2 tỷ đồng",
        "preview_text": "Khám phá danh sách các căn hộ tiềm năng nhất quý 2/2026 với tỷ suất sinh lời 12%.",
        "body_content": "Chào bạn,\n\nĐà Nẵng đang chứng kiến làn sóng đầu tư mạnh mẽ nhất trong 5 năm qua...",
        "call_to_action": "Xem danh sách dự án tại đây: https://example.com/da-nang-2026",
        "email_type": "sales",
        "target_audience": "Nhà đầu tư cá nhân",
        "internal_notes": "Sử dụng tone giọng khẩn cấp (Urgency)" # Sẽ bị lọc
    }

    # 2. Ép kiểu và lọc rác qua Protocol
    safe_output = MailOutput(**mock_mail_data)

    # 3. Trả về: Ghi vào reg_email (BusRegistry.EM)
    return StandardFrame.emit(
        BusRegistry.ML, 
        safe_output.model_dump()
    )