from pydantic import BaseModel, Field, ConfigDict

class AggregatedOutput(BaseModel):
    """
    Hợp đồng dữ liệu cho Node Aggregator.
    Dùng để xác nhận toàn bộ nội dung từ các nhánh đã được gom cụm thành công.
    """
    full_content_ready: bool = Field(
        default=True, 
        description="Đánh dấu trạng thái tất cả nội dung đã sẵn sàng"
    )
    bundle_id: str = Field(
        ..., 
        description="ID định danh gói nội dung (UUID hoặc mã phiên làm việc)"
    )

    model_config = ConfigDict(
        frozen=True,   # Chống sửa đổi sau khi tạo
        extra="ignore" # Tự động loại bỏ các trường thừa khi parse dữ liệu từ LLM/Logic
    )