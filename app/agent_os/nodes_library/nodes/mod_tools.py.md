import asyncio
from typing import Any, Tuple
from agent_os.system import (
    ShieldInput, ShieldOutput, safe_node, StateBus, 
    _emit, sanitise, validate_tool_call, ToolCallRecord, 
    ToolForbiddenException
)
from agent_os.tools.web_search import _tool_web_search

# =============================================================================
# §22.1  THƯ VIỆN CÔNG CỤ (Tool Library & Permissions)
# =============================================================================

# Đăng ký tất cả Tools vào hệ thống
_TOOL_REGISTRY: dict[str, Any] = {
    "web_search": _tool_web_search,
    # "seo_checker": _tool_seo,  <-- Giả sử thêm 20 cái nữa ở đây
}

# BẢNG PHÂN QUYỀN (ACL): Ngăn chặn việc gọi lộn xộn
# Chỉ những Agent có tên trong danh sách này mới được dùng tool tương ứng
_TOOL_PERMISSIONS = {
    "BLOG_WRITER": ["web_search", "seo_checker"],
    "AGENT_ADS": ["ads_competitor_analysis"],
    "AGENT_EMAIL": ["email_validator"],
}

# =============================================================================
# §22.2  TOOL SHIELD (Linh kiện thực thi Sandbox)
# =============================================================================

class ToolExecutorShield:
    def __init__(self, registry: dict, permissions: dict):
        self.registry = registry
        self.permissions = permissions

    async def process(self, packet: ShieldInput) -> ShieldOutput:
        state = packet.metadata.get("state")
        tool_name = packet.payload.get("tool_name")
        tool_input = sanitise(packet.payload.get("tool_input", ""))
        
        # Lấy ID của thằng đang gọi (Caller Identification)
        # Trong LangGraph, chúng ta có thể xác định Node trước đó
        caller = state.last_active_node or "BLOG_WRITER" 

        # --- TẦNG BẢO VỆ 1: PHÂN QUYỀN THEO AGENT ---
        allowed_tools = self.permissions.get(caller, [])
        if tool_name not in allowed_tools:
            _emit("error", event="tool_unauthorized", agent=caller, tool=tool_name)
            raise ToolForbiddenException(f"Agent '{caller}' KHÔNG có quyền sử dụng tool '{tool_name}'!")

        # --- TẦNG BẢO VỆ 2: KIỂM TRA HÀNH VI (Safety Validation) ---
        try:
            validate_tool_call(
                caller, 
                tool_name, 
                tool_input, 
                state.tool_call_history
            )
        except ToolForbiddenException as exc:
            # Ghi lại lịch sử vi phạm để Kill Switch xử lý nếu cần
            record = ToolCallRecord(agent_id=caller, tool_name=tool_name, query=tool_input, success=False)
            return ShieldOutput(data={
                "pending_tool": "", 
                "pending_tool_input": "",
                "tool_call_history": [record],
                "error": str(exc)
            })

        # 2. Tìm "Driver" trong Registry
        fn = self.registry.get(tool_name)
        if not fn:
            return ShieldOutput(data={"pending_tool": "", "pending_tool_input": "", "error": f"Unknown tool: {tool_name}"})

        # 3. Thực thi
        _emit("info", event="tool_start", tool=tool_name, caller=caller)
        success, result_text = await fn(tool_input)
        clean_result = sanitise(result_text)
        _emit("info", event="tool_done", tool=tool_name, success=success)

        # 4. Ghi nhật ký
        record = ToolCallRecord(
            agent_id=caller, tool_name=tool_name, query=tool_input, 
            result=clean_result, success=success
        )

        return ShieldOutput(data={
            "tool_result": clean_result,
            "pending_tool": "",
            "pending_tool_input": "",
            "tool_call_history": [record]
        })

# =============================================================================
# ADAPTER
# =============================================================================

async def node_TOOL_EXECUTOR(s: StateBus) -> dict:
    if not s.pending_tool:
        return {"pending_tool": "", "pending_tool_input": ""}

    # Truyền cả Registry và Bảng phân quyền vào Shield
    shield = ToolExecutorShield(_TOOL_REGISTRY, _TOOL_PERMISSIONS)
    
    packet = ShieldInput(
        payload={"tool_name": s.pending_tool, "tool_input": s.pending_tool_input},
        metadata={"state": s}
    )

    output: ShieldOutput = await safe_node(
        "TOOL_EXECUTOR", 
        shield.process(packet),
        fallback_delta={"pending_tool": "", "pending_tool_input": ""}
    )
    
    return output.data