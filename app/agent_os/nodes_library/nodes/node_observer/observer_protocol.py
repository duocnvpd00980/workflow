from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any

class ObservationMetric(BaseModel):
    """Chi tiết một chỉ số giám sát."""
    metric_name: str
    value: Any
    unit: str = "count"  # e.g., "tokens", "ms", "usd"

class ObserverOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho Node Observer.
    Dùng để ghi lại dấu vết hệ thống (Tracing) và đánh giá sức khỏe workflow.
    """
    model_config = ConfigDict(frozen=True, extra="ignore")

    # 1. Giám sát tài nguyên
    usage_stats: Dict[str, ObservationMetric] = Field(
        default_factory=dict, 
        description="Thống kê tài nguyên tiêu thụ (Token, Latency)"
    )

    # 2. Đánh giá chất lượng
    quality_check: Dict[str, bool] = Field(
        default_factory=dict,
        description="Kết quả kiểm tra nhanh (e.g., 'no_hallucination': True)"
    )

    # 3. Trạng thái luồng
    current_step: str = Field(..., description="Node cuối cùng vừa thực thi xong")
    system_health: str = Field(default="healthy", description="Trạng thái hệ thống: healthy, warning, critical")