# =========================================================
# FILE: response_resolver_service.py
# =========================================================
from typing import Any
from .response_resolver_protocol import ResponseResolverOutput


class ResponseResolverService:
    """
    CORE DOMAIN SERVICE: Response Resolver (Pure Logic)

    Phân tích ý định người dùng và định tuyến luồng điều chỉnh quy chế (Regulation/QA).
    Tách biệt hoàn toàn khỏi hạ tầng MainBus, nhận LLM Engine qua Dependency Injection.
    """

    SYSTEM_PROMPT = """
    You are a Strategic Intent Classifier for a Regulation and Policy System.
    Determine the correct execution path based on the user question.

    RULES:
    - "qa": The user is asking about company regulations, policies, laws, circulars, or requires document retrieval.
    - "direct_qa": Ordinary greetings, small talk, casual chitchat, or generic questions that do not need system knowledge lookup.
    - "invalid": Out of scope, completely ambiguous, or abusive content.

    You MUST strictly return the JSON matching the required schema.
    """

    def __init__(self, llm_engine: Any = None):
        """
        Khởi tạo và đón Engine (Cloud/Local) được Adapter bơm vào thông qua Dependency Injection.
        """
        self._llm = llm_engine

    async def classify_intent(
        self, user_input: str, context: dict, llm_engine: Any = None
    ) -> ResponseResolverOutput:
        """
        Thực thi gọi LLM bóc tách cấu trúc dữ liệu theo đúng cam kết Protocol.
        """
        # Hỗ trợ lấy engine linh hoạt từ tham số truyền vào hàm (đúng chuẩn mẫu Adapter mới)
        active_llm = llm_engine or self._llm
        if not active_llm:
            raise RuntimeError(
                "[ResponseResolverService] Missing LLM Engine infrastructure!"
            )

        try:
            # LLM được cấu hình đổ thẳng dữ liệu vào schema Pydantic Object xịn
            result = await active_llm.generate(
                system=self.SYSTEM_PROMPT,
                user=f"User Input: {user_input}\nContext: {context}",
                schema=ResponseResolverOutput,
                temperature=0.1,
            )

            # PURE PYDANTIC NATIVE: Trả về trực tiếp Object vì dữ liệu đã được validate chặt chẽ từ Core LLM
            return result

        except Exception as e:
            # FALLBACK AN TOÀN TUYỆT ĐỐI: Đảm bảo nếu Cloud đứt mạng, hệ thống chuyển mạch về 'invalid' để bảo vệ mạch đồ thị
            return ResponseResolverOutput(
                route="invalid",
                reasoning=f"Fallback triggered due to generation error: {str(e)}",
                confidence_score=0.0,
                next_steps=[],
            )
