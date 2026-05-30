from pydantic import BaseModel, ConfigDict, Field

class SharedStateOutput(BaseModel):
    """
    Contract bất biến định nghĩa kết quả lưu trữ và cập nhật trạng thái chung của đồ thị.
    """
    model_config = ConfigDict(frozen=True, extra="ignore")
    
    is_synced: bool = Field(..., description="Cờ xác nhận dữ liệu đã được đồng bộ vào kho lưu trữ chung thành công.")
    updated_keys: list[str] = Field(..., description="Danh sách các khóa trạng thái vừa được cập nhật.")
    persisted_text: str = Field(..., description="Nội dung văn bản chính thức được ghi nhận.")