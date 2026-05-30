# =============================================================================
# FILE: agent_os/system/interfaces/bus.py
# =============================================================================

from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class IStateBus(Protocol):
    """
    Standard motherboard bus protocol.
    Every node communicates ONLY through this interface.
    """

    seed: Any
    session_id: str
    total_cost: float
    budget_limit: float