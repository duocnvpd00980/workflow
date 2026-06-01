import time

from pydantic import BaseModel, Field

# =============================================================================
# SHIELD FAULTS
# =============================================================================


class ShieldFault(BaseModel):
    shield: str

    code: str

    message: str

    recoverable: bool = True

    ts: float = Field(default_factory=time.time)


class FuseBlownException(RuntimeError):
    pass


class InjectionDetectedException(ValueError):
    pass


class CircuitOpenException(RuntimeError):
    pass


class ToolForbiddenException(PermissionError):
    pass


class PipelineError(Exception):
    def __init__(
        self,
        message: str,
        node: str = "unknown",
        code: str = "EXECUTION_ERROR",
        recoverable: bool = False,
    ):
        self.node = node
        self.code = code
        self.message = message
        self.recoverable = recoverable
        super().__init__(self.message)
