from typing import Any, Final, Optional
from .ads_protocol import AdOutput


class AdsService:
    """
    DOMAIN COMPONENT: Xử lý nghiệp vụ sáng tạo nội dung quảng cáo.
    Thiết kế theo chuẩn 'Plug-and-Play', nhận Engine từ tầng Adapter.
    """

    # Sử dụng Final để đảm bảo cấu hình Prompt không bị thay đổi trong runtime
    SYSTEM_PROMPT: Final[str] = """
You are a professional performance marketer.
Your goal is to write high-converting advertisement copies.

STRICT RULES:
1. Always return valid JSON matching the schema.
2. Language: {language}
3. Be concise, engaging, and include a strong call-to-action.
"""

    def __init__(self, llm_engine: Any):
        """
        Khởi tạo linh kiện với một bộ engine (LLM) đã được cấu hình.
        """
        self._llm = llm_engine

    async def run(self, user_input: str, language: str = "vi") -> AdOutput:
        """
        Thực thi xử lý nghiệp vụ.
        Tham số được minh bạch hóa (Explicit) thay vì dùng dict 'seed' chung chung.
        """
        # Inject ngôn ngữ trực tiếp vào prompt để tăng độ chính xác
        formatted_system_prompt = self.SYSTEM_PROMPT.format(language=language)

        # Lệnh thực thi được đóng gói gọn gàng
        # Engine (_llm) phải hỗ trợ phương thức .generate với tham số schema (Instructor)
        return await self._llm.generate(
            system=formatted_system_prompt,
            user=f"Context for the advertisement: {user_input}",
            schema=AdOutput,
            temperature=0.4,
        )
