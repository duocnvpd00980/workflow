"""
aggregator_protocol.py
======================
Core Contract Layer — node_aggregator
Định nghĩa giao ước dữ liệu đầu ra bất biến cho tầng tổng hợp chặng cuối.
Sẵn sàng bàn giao cho các Gateway bên ngoài hệ thống.
"""

from pydantic import BaseModel, ConfigDict, Field


class AggregationResult(BaseModel):
    """
    Object đầu ra bất biến (Immutable Output Contract) của AggregatorService.

    Fields:
        final_response      : Nội dung câu trả lời hoàn chỉnh cuối cùng,
                              đã được tối ưu định dạng Markdown — đây là
                              Single Source of Truth cho trường `text` trên Bus.
        summary_of_changes  : Tóm tắt ngắn gọn các bước xử lý / điều chỉnh
                              nội dung mà Chief Editor đã thực hiện.
        metadata            : Thông tin bổ sung phục vụ tầng hiển thị UI
                              hoặc Tracking Analytics (ui_format, language…).
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    final_response: str = Field(
        ...,
        description="Câu trả lời hoàn chỉnh đã được làm mượt và định dạng Markdown.",
    )
    summary_of_changes: str = Field(
        default="",
        description="Ghi chú tóm tắt về những thay đổi / tinh chỉnh đã áp dụng.",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Siêu dữ liệu bổ sung phục vụ UI rendering hoặc analytics.",
    )
