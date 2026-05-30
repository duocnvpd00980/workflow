from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict

class ValidationIssue(BaseModel):
    """Chi tiết một lỗi phát hiện được."""
    scope: str = Field(..., description="Phạm vi lỗi (e.g., 'grammar', 'policy', 'format')")
    severity: str = Field(..., description="Mức độ: 'critical' (phải sửa) hoặc 'warning' (nên sửa)")
    message: str = Field(..., description="Mô tả chi tiết lỗi")
    suggestion: Optional[str] = Field(None, description="Gợi ý cách sửa cho Agent")

class ValidatorOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho Node Validator.
    Xác định nội dung có đạt yêu cầu để đi tiếp hay không.
    """
    is_valid: bool = Field(default=True, description="Trạng thái tổng quát: True nếu đạt chuẩn")
    score: float = Field(default=1.0, description="Điểm chất lượng (0.0 - 1.0)")
    issues: List[ValidationIssue] = Field(default_factory=list)
    
    # Điều hướng
    needs_rework: bool = Field(default=False, description="Cần quay lại Node trước để sửa không")
    target_node: Optional[str] = Field(None, description="Node cần quay lại để sửa (e.g., 'BLOG_WRITER')")

    model_config = ConfigDict(
        frozen=True,
        extra="ignore"
    )