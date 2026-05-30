from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict

class BudgetManagerOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho Quản lý ngân sách (Budget & Token Management).
    Kiểm soát hạn mức chi tiêu và đề xuất hạ cấp model nếu cần thiết.
    """
    total_budget_limit: float = Field(..., description="Ngân sách tối đa cho phép (USD)")
    current_spend: float = Field(default=0.0, description="Số tiền đã chi tiêu thực tế")
    is_budget_exceeded: bool = Field(default=False, description="Đã vượt quá hạn mức chưa")
    
    # Chiến lược tiết kiệm
    suggested_model_tier: str = Field(
        default="premium", 
        description="Gợi ý phân khúc model (e.g., 'premium', 'economy') để tối ưu chi phí"
    )
    remaining_percentage: float = Field(..., description="Phần trăm ngân sách còn lại")

    model_config = ConfigDict(
        frozen=True,
        extra="ignore"
    )