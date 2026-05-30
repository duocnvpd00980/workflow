"""
SYSTEM INFRASTRUCTURE (The Motherboard BIOS)
============================================
Định nghĩa các tiêu chuẩn dữ liệu, giao thức giao tiếp và hệ thống bảo vệ cấp thấp.

Đây là tầng "Cứng", đảm bảo tính ổn định và an toàn tài chính cho toàn bộ hệ thống Multi-Agent.
"""

from .core_protocol import (
    AgentState, 
    StateBus, 
    ContentItem, 
    CFG,
    _emit, 
    detect_language,
    sanitise,
    ShieldInput, 
    ShieldOutput,
    _PLACEHOLDER,
    InjectionDetectedException,
    SeedStrategy,
    ToolCallRecord,
)
from .core_power import (
    AGENT_REGISTRY, 
    KILL_SWITCH, 
    AgentConfig,
    validate_tool_call, 
)
from .core_guard import (
    FinancialFirewall,
    safe_node, 
    POLICY, 
    _FIREWALL,
    _RATE_LIMITER,
    _SAFETY,
   
)

__all__ = [
    "AgentState", "StateBus", "ContentItem", "CFG",
    "FinancialFirewall", "POLICY", "AGENT_REGISTRY", "KILL_SWITCH", "_FIREWALL",
    "AgentConfig", "ShieldInput", "ShieldOutput", "safe_node", 
    "validate_tool_call", "_PLACEHOLDER", "_emit", "detect_language", "sanitise", "_RATE_LIMITER",
    "_SAFETY", "InjectionDetectedException", "ToolCallRecord",
]

# =============================================================================
# INFRASTRUCTURE SPECIFICATIONS (Hệ thống điều khiển trung tâm)
# =============================================================================

# --- [1. DATA & BUS PROTOCOLS] ---

# AgentState / StateBus
#   CHỨC NĂNG: Đường truyền dữ liệu tổng (PCIe Bus). 
#   VAI TRÒ: Chứa toàn bộ trạng thái hệ thống, lịch sử chat, chi phí và kết quả đầu ra. 
#   LƯU Ý: Phải đảm bảo 100% JSON Serialisable để LangGraph Checkpointer có thể lưu trữ.

# ContentItem
#   CHỨC NĂNG: Đơn vị thành phẩm (Product Unit).
#   VAI TRÒ: Cấu trúc chuẩn cho mọi nội dung do Agent tạo ra (content, agent_id, language).

# --- [2. POWER & BUDGET MANAGEMENT] ---

# FinancialFirewall (POLICY / _FIREWALL)
#   CHỨC NĂNG: Bộ quản lý nguồn (Power Supply Unit - PSU).
#   VAI TRÒ: Kiểm soát hạn mức USD (Budget). Thực thi "ngắt mạch" (FuseBlown) nếu chi phí vượt ngưỡng.

# KILL_SWITCH
#   CHỨC NĂNG: Công tắc khẩn cấp (Emergency Stop).
#   VAI TRÒ: Dừng toàn bộ Pipeline ngay lập tức nếu phát hiện lỗi hệ thống nghiêm trọng hoặc lệnh từ Admin.

# AGENT_REGISTRY
#   CHỨC NĂNG: Danh mục thiết bị. Định nghĩa vai trò (Role), mục tiêu (Goal) và mô hình LLM cho từng Agent.

# --- [3. GUARD RAILS & SANDBOXING] ---

# safe_node
#   CHỨC NĂNG: Bộ ổn áp (Voltage Regulator).
#   VAI TRÒ: Bao bọc mọi Node trong một khối try-except toàn diện. Đảm bảo lỗi ở một Node không làm cháy cả mạch.

# validate_tool_call (TOOL_PERMISSIONS)
#   CHỨC NĂNG: Phân quyền thiết bị ngoại vi (ACL).
#   VAI TRÒ: Kiểm tra xem Agent có quyền gọi một Tool cụ thể hay không. Chặn đứng các hành vi "vượt cấp".

# ShieldInput / ShieldOutput
#   CHỨC NĂNG: Giao tiếp chuẩn (Standard Interface).
#   VAI TRÒ: Định dạng dữ liệu vào/ra cho các lớp bảo vệ (Shields).

# --- [4. UTILITIES] ---

# _emit
#   CHỨC NĂNG: Cổng Serial Monitor. Phát tín hiệu Telemetry về luồng xử lý, chi phí và lỗi.

# sanitise / detect_language
#   CHỨC NĂNG: Bộ lọc nhiễu (Signal Filter). Làm sạch dữ liệu đầu vào và nhận diện ngôn ngữ đồng bộ.

