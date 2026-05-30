import time

from pydantic import BaseModel, Field

# =============================================================================
# TOOL CONTRACTS
# =============================================================================

class ToolCallRecord(BaseModel):

    agent_id: str

    tool_name: str

    query: str

    result: str = ""

    success: bool = False

    ts: float = Field(default_factory=time.time)