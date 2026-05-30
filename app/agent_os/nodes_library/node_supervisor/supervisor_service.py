"""
supervisor_service.py
=====================
Pure Domain Execution Layer — node_supervisor
Chịu trách nhiệm cấu trúc hóa Prompt, tích hợp Episodic Memory và giao tiếp
với High-IQ LLM để trả về quyết định điều hướng chuẩn SupervisorResult.
Không phụ thuộc vào Bus, không biết đến MainBus hay StandardFrame.
"""

import os
from typing import Any

from jinja2 import Environment, FileSystemLoader, FileSystemLoader

from .supervisor_protocol import SupervisorResult


# ---------------------------------------------------------------------------
# SERVICE CLASS
# ---------------------------------------------------------------------------
class SupervisorService:
    """
    Lớp nghiệp vụ thuần — nhận tham số thô, trả về SupervisorResult (Pydantic).
    Không bao giờ trả về dict hay raise exception ra ngoài.
    """

    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self._env = Environment(loader=FileSystemLoader(current_dir))

    async def execute(
        self,
        user_input: str,
        history: list,
        user_profile: dict,
        relevant_episodes: list,
        evaluation_feedback: str,
        llm_engine: Any,
    ) -> SupervisorResult:
        """
        Phân tích ngữ cảnh và đưa ra quyết định điều hướng Agent tiếp theo.

        Args:
            history             : Lịch sử hội thoại dạng list[dict].
            user_profile        : Hồ sơ người dùng (sở thích, ngôn ngữ…).
            relevant_episodes   : Các kỷ niệm thành công từ Long-term Memory.
            evaluation_feedback : Phản hồi lỗi từ Evaluator (Correction Loop).
                                  Chuỗi rỗng nếu đây là lần chạy đầu tiên.
            llm_engine          : High-IQ LLM instance inject từ Container.

        Returns:
            SupervisorResult : Object bất biến chứa quyết định điều hướng.
        """

        template = self._env.get_template("supervisor.jinja2")
        system_prompt = template.render(
            user_message=user_input,  # ← thêm dòng này
            user_profile_text=self._format_profile(user_profile),
            history_text=self._format_history(history),
            episodes_text=self._format_episodes(relevant_episodes),
            feedback_block=evaluation_feedback,
        )

        result = await llm_engine.generate(
            system=system_prompt,
            user=user_input,  # ← thay bằng tin nhắn thật
            schema=SupervisorResult,
            temperature=0.0,
        )

        return result

    # -----------------------------------------------------------------------
    # PRIVATE HELPERS
    # -----------------------------------------------------------------------
    def _format_history(self, history: list) -> str:
        """Chuyển list lịch sử hội thoại thành chuỗi Human/AI có cấu trúc."""
        if not history:
            return "(Chưa có lịch sử hội thoại)"

        lines: list[str] = []
        for turn in history:
            role = turn.get("role", "unknown").upper()
            content = turn.get("content", "")
            lines.append(f"[{role}]: {content}")
        return "\n".join(lines)

    def _format_profile(self, profile: dict) -> str:
        """Chuyển user_profile dict thành chuỗi key-value dễ đọc cho LLM."""
        if not profile:
            return "(Không có hồ sơ người dùng)"
        return "\n".join(f"  - {k}: {v}" for k, v in profile.items())

    def _format_episodes(self, episodes: list) -> str:
        """Chuyển Episodic Memory thành các few-shot examples có đánh số."""
        if not episodes:
            return "(Không có kỷ niệm thành công nào được truy xuất)"

        sections: list[str] = []
        for idx, ep in enumerate(episodes, start=1):
            if isinstance(ep, dict):
                query = ep.get("query", "")
                agent = ep.get("agent_used", "")
                outcome = ep.get("outcome", "")
                sections.append(
                    f"  [{idx}] Query: '{query}' → Agent: '{agent}' → Kết quả: {outcome}"
                )
            else:
                sections.append(f"  [{idx}] {ep}")
        return "\n".join(sections)
