from typing import Optional

from pydantic import BaseModel, Field

from agent_os.system.shields.shield_telemetry import (
    ShieldTelemetry,
)

# =============================================================================
# SHIELD IO PROTOCOL
# =============================================================================

class ShieldInput(BaseModel):

    payload: dict = Field(default_factory=dict)

    config: dict = Field(default_factory=dict)

    metadata: dict = Field(default_factory=dict)


class ShieldOutput(BaseModel):

    data: dict = Field(default_factory=dict)

    telemetry: Optional[ShieldTelemetry] = None