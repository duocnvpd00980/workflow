# =========================================================
# FILE: policy_engine_protocol.py
# =========================================================
from pydantic import BaseModel, ConfigDict


class PolicyEngineOutput(BaseModel):
    """
    POLICY ENGINE PROTOCOL
    Định nghĩa hợp đồng dữ liệu đầu ra của Bộ kiểm soát chính sách.
    """
    allow_heavy_execution: bool = False
    allow_memory: bool = False
    allow_knowledge: bool = False
    allow_tools: bool = False
    route: str = "smalltalk"

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
    )