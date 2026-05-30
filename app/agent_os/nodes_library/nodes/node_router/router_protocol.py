from pydantic import BaseModel, Field
from typing import Literal, List

class RouterOutput(BaseModel):

    intent: Literal[
        "ads_only",
        "blog_only",    
        "email_only",
        "full_campaign",
        "invalid",
    ] = Field(
        default="invalid", 
        description="Phân loại ý định của khách hàng dựa trên yêu cầu marketing"
    )

    active_branches: List[str] = Field(
        default_factory=list,
        description="Danh sách các nhánh cần kích hoạt (ads, blog, email)"
    )

    reasoning: str = Field(
        default="auto",
        description="Lý do chi tiết tại sao router lại chọn hướng đi này"
    )

    next_steps: List[str] = Field(
        default_factory=list,
        description="Các bước thực thi tiếp theo dành cho các Agent phía sau"
    )

    confidence_score: float = Field(
        default=0.0, 
        ge=0, 
        le=1,
        description="Độ tự tin của mô hình đối với quyết định này (từ 0.0 đến 1.0)"
    )