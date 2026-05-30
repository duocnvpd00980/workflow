# evaluator_protocol.py
from pydantic import BaseModel


class EvaluationResult(BaseModel):
    is_passed: bool
    quality_score: float
    critique: str
    remediation_instruction: str = ""
