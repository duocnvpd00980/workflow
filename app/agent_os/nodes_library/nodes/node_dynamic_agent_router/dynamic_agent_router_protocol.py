# =========================================================
# FILE: dynamic_agent_router_protocol.py
# =========================================================
from typing import List
from pydantic import BaseModel, Field, ConfigDict


class DynamicAgentRouterOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho Bộ định tuyến Agent động (Dynamic Agent Router).
    Xác định trạng thái mạch điều hướng, chế độ đóng ngắt và danh sách các ngõ ra (Nodes) được cấp điện.
    """
    
    router_active: bool = Field(
        default=True, 
        description="Trạng thái kích hoạt của bộ định tuyến (On/Off)"
    )
    
    routing_mode: str = Field(
        default="dynamic", 
        description="Chế độ định tuyến (e.g., 'dynamic', 'parallel_all', 'bypass')"
    )
    
    activated_channels: List[str] = Field(
        ..., 
        description="Danh sách các key định danh ngõ ra (nhánh Agent) sẽ được cấp điện chạy"
    )
    
    total_channels: int = Field(
        ..., 
        description="Tổng số cổng/ngõ ra Agent được cấu hình trên bo mạch"
    )

    model_config = ConfigDict(
        frozen=True,
        extra="ignore"  # Lọc nhiễu tín hiệu để tránh làm chập mạch luồng điều hướng
    )