# ruff: noqa: E501
from __future__ import annotations

import json
import logging
from typing import Any, List

from .qa_response_protocol import QaResponseOutput

logger = logging.getLogger(__name__)


class QaResponseService:
    """
    ENTERPRISE KNOWLEDGE PROCESSOR (MULTI-TENANT & MULTI-DOMAIN)

    Tối ưu hóa RAGAS cho SLM (Qwen 0.5B). Hệ thống Prompt được chuyển hoàn toàn
    sang tiếng Việt để giảm thiểu việc mô hình sinh chuỗi trống hoặc lỗi cấu trúc JSON.
    """

    # 🎯 PROMPT 1: Luồng RAG nghiêm ngặt (Chuyển sang tiếng Việt, đơn giản hóa cấu trúc)
    RAG_SYSTEM_PROMPT = """
    BẠN LÀ TRỢ LÝ AI CHUYÊN NGHIỆP. Hãy trả lời câu hỏi của người dùng một cách ngắn gọn, chính xác dựa trên các đoạn văn bản (Contexts) được cung cấp.

    QUY TẮC NỘI DUNG:
    1. Chỉ trả lời dựa trên thông tin có trong "Contexts". Tuyệt đối không tự bịa đặt hoặc suy diễn thông tin nằm ngoài văn bản.
    2. Định dạng câu trả lời rõ ràng bằng Markdown (sử dụng gạch đầu dòng, bôi đậm từ khóa quan trọng).
    3. Luôn giữ giọng điệu chuyên nghiệp, khách quan.

    QUY TẮC ĐỊNH DẠNG JSON (BẮT BUỘC):
    Bạn phải trả về một đối tượng JSON duy nhất có các khóa chính xác như sau:
    - "answer": Chuỗi văn bản thông thường (KHÔNG được lồng thêm object/dict dạng {"default": ...} vào đây).
    - "source_used": true
    - "tone": "professional"
    - "citations": Danh sách các tiêu đề hoặc nguồn tài liệu bạn đã dùng để trả lời (ví dụ: ["PHẦN 3", "PHẦN 4"]).
    """

    # 🎯 PROMPT 2: Luồng Chuyên gia Dự phòng (Bản địa hóa tiếng Việt)
    FALLBACK_SYSTEM_PROMPT = """
    BẠN LÀ CHUYÊN GIA TƯ VẤN DOANH NGHIỆP. Kho dữ liệu nội bộ không tìm thấy tài liệu phù hợp cho câu hỏi này. Hãy sử dụng tri thức hệ thống của bạn để đưa ra một giải pháp toàn diện, hữu ích và mang tính chiến lược cho người dùng.

    QUY TẮC NỘI DUNG:
    1. Tuyệt đối không dùng các câu từ chối sáo rỗng như "Tôi không biết" hoặc "Không tìm thấy tài liệu".
    2. Đưa ra các gợi ý, bước xử lý chi tiết hoặc phương án kỹ thuật thực tế theo nhu cầu của người dùng.

    QUY TẮC ĐỊNH DẠNG JSON (BẮT BUỘC):
    Bạn phải trả về một đối tượng JSON duy nhất có các khóa chính xác như sau:
    - "answer": Chuỗi văn bản tư vấn chuyên gia của bạn (Dạng văn bản thông thường).
    - "source_used": false
    - "tone": "expert"
    - "citations": ["llm_base_knowledge"]
    """

    def __init__(self, llm_engine: Any):
        self._llm = llm_engine

    def _repair_slm_hallucination(self, raw_result: Any) -> QaResponseOutput:
        """
        🛡️ INDUSTRIAL REPAIR LAYER: Bộ cứu hộ sửa lỗi định dạng tự động cho Model nhỏ (Qwen 0.5B).
        """
        content = raw_result
        if hasattr(raw_result, "content"):
            content = raw_result.content
        elif hasattr(raw_result, "text"):
            content = raw_result.text

        extracted_answer = ""
        extracted_source = False
        extracted_tone = "neutral"
        extracted_citations = []

        if isinstance(content, str):
            clean_str = content.strip()
            if clean_str.startswith("```"):
                lines = clean_str.split("\n")
                if lines[0].startswith("```json") or lines[0].startswith("```"):
                    lines = lines[1:-1]
                clean_str = "\n".join(lines).strip()
            try:
                data_dict = json.loads(clean_str)
            except Exception:
                # Nếu không thể parse nổi JSON, coi toàn bộ chuỗi text thô thu được là câu trả lời
                data_dict = {"answer": content}
        elif isinstance(content, dict):
            data_dict = content
        else:
            data_dict = getattr(content, "__dict__", {}) if content else {}

        if data_dict:
            raw_answer = data_dict.get("answer", "")
            # Sửa lỗi Dict lồng nhau đặc trưng của các dòng SLM khi sinh schema sai
            if isinstance(raw_answer, dict):
                logger.warning(
                    "[QaResponseService] Kích hoạt cứu hộ: Sửa lỗi Dict lồng nhau của Qwen 0.5B."
                )
                extracted_answer = (
                    raw_answer.get("default")
                    or raw_answer.get("value")
                    or str(raw_answer)
                )
            else:
                extracted_answer = str(raw_answer)

            extracted_source = bool(data_dict.get("source_used", False))
            extracted_tone = str(data_dict.get("tone", "neutral"))

            raw_citations = data_dict.get("citations", [])
            extracted_citations = (
                raw_citations
                if isinstance(raw_citations, list)
                else [str(raw_citations)]
            )

        return QaResponseOutput(
            answer=extracted_answer.strip(),
            source_used=extracted_source,
            tone=extracted_tone,
            citations=extracted_citations,
        )

    async def generate_response(
        self, user_input: str, contexts: List[str]
    ) -> QaResponseOutput:
        is_rag_route = bool(contexts and len(contexts) > 0 and str(contexts[0]).strip())

        try:
            if is_rag_route:
                logger.info(
                    "[QaResponseService] Kích hoạt luồng xử lý RAG nghiêm ngặt."
                )
                context_str = "\n---\n".join(contexts)

                # Nạp dữ liệu vào LLM với các tham số đã tối ưu cho mô hình nhỏ
                result = await self._llm.generate(
                    system=self.RAG_SYSTEM_PROMPT,
                    user=f"Câu hỏi của người dùng: {user_input}\n\nTài liệu tri thức (Contexts):\n{context_str}",
                    schema=None,  # Để Driver nhận JSON thô, không ép Pydantic validate trước khi cứu hộ
                    temperature=0.2,  # 💡 TĂNG NHẸ: Giúp mô hình nhỏ không bị bó cứng thuật toán tư duy dẫn đến rỗng văn bản
                )

                output = self._repair_slm_hallucination(result)
                output.source_used = True
                return output

            # 🚀 LUỒNG CỨU THUA CHUYÊN GIA (FALLBACK TO BASE KNOWLEDGE)
            logger.warning(
                f"[QaResponseService] Context rỗng! Kích hoạt luồng Fallback cho: '{user_input}'"
            )

            result = await self._llm.generate(
                system=self.FALLBACK_SYSTEM_PROMPT,
                user=f"Câu hỏi của người dùng: {user_input}",
                schema=None,
                temperature=0.4,  # Tăng tính tư duy giải pháp cho luồng không có tài liệu
            )

            output = self._repair_slm_hallucination(result)
            output.source_used = False
            if not output.citations:
                output.citations = ["llm_base_knowledge"]
            return output

        except Exception as e:
            logger.critical(f"[QaResponseService] Sự cố vật lý luồng LLM: {str(e)}")
            return QaResponseOutput(
                answer=f"Hệ thống lõi AI gặp sự cố kỹ thuật khi xử lý câu hỏi: '{user_input}'. Vui lòng liên hệ quản trị viên.",
                source_used=False,
                tone="neutral",
                citations=[],
            )
