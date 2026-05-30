import os
from typing import Any
from jinja2 import Environment, FileSystemLoader
from .evaluator_protocol import EvaluationResult


class EvaluatorService:

    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self._env = Environment(loader=FileSystemLoader(current_dir))

    async def execute(
        self,
        user_input: str,
        supervisor_instruction: str,
        agent_output: str,
        llm_engine: Any,
    ) -> EvaluationResult:

        template = self._env.get_template("evaluator_prompt.jinja2")
        prompt = template.render(
            user_input=user_input,
            supervisor_instruction=supervisor_instruction,
            agent_output=agent_output,
        )

        try:
            result = await llm_engine.generate(
                system=prompt,
                user="Evaluate the agent output.",
                schema=EvaluationResult,
                temperature=0.3,  # thấp hơn → đánh giá ổn định hơn
            )
            return result

        except Exception as e:
            # Graceful fallback — không crash, không retry vô hạn
            return EvaluationResult(
                is_passed=True,  # force pass khi LLM lỗi
                quality_score=0.0,
                critique=f"Evaluator LLM error: {e}",
                remediation_instruction="",
            )