from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Dict


class ToolResultEntry(BaseModel):
    """Một kết quả đơn lẻ từ Tool."""

    tool_name: str
    input_params: Dict[str, Any]
    output_data: Any
    success: bool = True


class ToolsAdapterOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho Node Adapter Tools.
    Tổng hợp kết quả từ nhiều Tool khác nhau.
    """

    results: List[ToolResultEntry] = Field(default_factory=list)
    summary_of_findings: str = Field(
        ..., description="Tóm tắt ngắn gọn các thông tin tìm thấy được"
    )
    tokens_consumed: int = Field(
        default=0, description="Lượng token tiêu tốn để xử lý kết quả"
    )

    model_config = ConfigDict(frozen=True, extra="ignore")
