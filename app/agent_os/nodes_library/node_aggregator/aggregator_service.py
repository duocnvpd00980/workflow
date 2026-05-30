from typing import Any
from .aggregator_protocol import AggregationResult

_SYSTEM_PROMPT = """\
Bạn là Tổng biên tập. Nhiệm vụ: hoàn thiện câu trả lời cuối cùng cho người dùng.
Quy tắc:
1. Giữ nguyên thông tin — KHÔNG bịa đặt.
2. Loại bỏ trùng lặp, làm mượt văn phong.
3. Áp dụng Markdown phù hợp với user_profile.
4. Giọng văn nhất quán — chuyên nghiệp nhưng thân thiện.
"""

_USER_TEMPLATE = """\
YÊU CẦU GỐC: {original_query}

HỒ SƠ NGƯỜI DÙNG: {user_profile}

NỘI DUNG CẦN HOÀN THIỆN:
{agent_output}
"""


class AggregatorService:

    async def execute(
        self,
        original_query: str,
        agent_output: str,
        user_profile: dict,
        llm_engine: Any,
    ) -> AggregationResult:

        user_message = _USER_TEMPLATE.format(
            original_query=original_query,
            user_profile=self._fmt_profile(user_profile),
            agent_output=agent_output,
        )

        structured_llm = llm_engine.with_structured_output(AggregationResult)
        return await structured_llm.ainvoke([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ])

    def _fmt_profile(self, profile: dict) -> str:
        if not profile:
            return "(Không có)"
        return "\n".join(f"  - {k}: {v}" for k, v in profile.items())