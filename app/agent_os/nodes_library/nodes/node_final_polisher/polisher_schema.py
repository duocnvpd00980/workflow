from pydantic import BaseModel, Field
from typing import Any

class FinalProduct(BaseModel):
    final_output: str = Field(..., description="Toàn bộ nội dung đã được làm đẹp và tổng hợp")
    meta_summary: str = Field(..., description="Tóm tắt ngắn gọn những gì đã thực hiện")

class PolisherParser:
    @staticmethod
    def parse(raw: Any) -> FinalProduct:
        try:
            if isinstance(raw, FinalProduct): return raw
            return FinalProduct.model_validate(raw)
        except Exception:
            return FinalProduct(
                final_output=str(raw),
                meta_summary="Hoàn tất xử lý nội dung."
            )