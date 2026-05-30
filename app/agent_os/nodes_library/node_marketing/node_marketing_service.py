
from agent_os.nodes_library.node_marketing.node_marketing_protocol import MarketingOutput


class MarketingService:
    """
    Pure Domain Logic - Chịu trách nhiệm xử lý nghiệp vụ sáng tạo và biên tập nội dung marketing.
    Tuyệt đối cô lập hoàn toàn, không tương tác với State Bus hệ thống.
    """
    
    @staticmethod
    async def generate_marketing_content(sanitized_input: str) -> MarketingOutput:
        # Kiểm tra tính hợp lệ tối thiểu của đầu vào nghiệp vụ
        if not sanitized_input or len(sanitized_input.strip()) == 0:
            return MarketingOutput(
                campaign_copy="[Hệ thống] Không có thông tin đầu vào để biên soạn nội dung tiếp thị.",
                target_audience="General",
                tone_of_voice="Neutral"
            )
            
        # Giả lập logic xử lý chuyên môn của tầng Marketing 
        # (Trong thực tế, bước này sẽ gọi llm từ ctx để sinh văn bản dựa trên prompt template marketing)
        composed_copy = (
            f"🚀 [CHIẾN DỊCH ĐẶC BIỆT] 🚀\n\n"
            f"Bạn đang tìm kiếm giải pháp tối ưu? Đừng bỏ lỡ: {sanitized_input}\n\n"
            f"👉 Đăng ký ngay hôm nay để nhận ưu đãi độc quyền dành riêng cho bạn!"
        )
        
        # Trả về kết quả đóng gói dạng Pydantic Object bất biến
        return MarketingOutput(
            campaign_copy=composed_copy,
            target_audience="Tech-savvy Professionals & Innovators",
            tone_of_voice="Inspirational & Persuasive"
        )