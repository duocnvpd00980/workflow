from langchain_core.runnables import RunnableConfig
from agent_os.nodes_library.node_validator.validator_protocol import ValidatorOutput, ValidationIssue
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

async def node_VALIDATOR(state: MainBus, config: RunnableConfig) -> dict:
    """
    NODE VALIDATOR: Kiểm định chất lượng đầu ra của các Agent.
    """
    
    # --- LOGIC NGHIỆP VỤ (TẠM COMMENT) ---
    # content_to_check = state.reg_blog_writer.payload if state.reg_blog_writer else ""
    # checker = services["quality_assurance"]
    # report = await checker.analyze(content_to_check)

    # 1. Dữ liệu mẫu (Mock Data) - Giả định phát hiện một lỗi nhỏ
    mock_validator_data = {
        "is_valid": True, 
        "score": 0.85,
        "issues": [
            {
                "scope": "policy",
                "severity": "warning",
                "message": "Nội dung thiếu phần miễn trừ trách nhiệm đầu tư.",
                "suggestion": "Thêm câu: 'Thông tin chỉ mang tính chất tham khảo' vào cuối bài."
            }
        ],
        "needs_rework": False,
        "target_node": None
    }

    # 2. Ép kiểu và lọc rác
    safe_output = ValidatorOutput(**mock_validator_data)

    # 3. Trả về: Ghi vào reg_validator (BusRegistry.VA)
    return StandardFrame.emit(
        BusRegistry.VA, 
        safe_output.model_dump()
    )