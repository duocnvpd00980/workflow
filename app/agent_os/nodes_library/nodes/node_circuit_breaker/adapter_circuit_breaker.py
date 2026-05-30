from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry

from agent_os.system.bus.protocol import (
    StandardFrame,
    BodyFrame,
)


async def node_CIRCUIT_BREAKER(state: MainBus) -> dict:

    mock_cb_data = {
        "is_open": False,
        "failure_count": 0,
        "threshold": 5,
        "blocked_node": None,
        "internal_debug_log": "All systems nominal",
    }

    return StandardFrame.emit(
        registry_key=BusRegistry.CB,
        payload=BodyFrame(
            status=("FAILED" if mock_cb_data["is_open"] else "SUCCESS"),
            text="Circuit breaker evaluation completed",
            state={
                "is_open": mock_cb_data["is_open"],
                "blocked_node": mock_cb_data["blocked_node"],
            },
            metrics={
                "failure_count": mock_cb_data["failure_count"],
                "threshold": mock_cb_data["threshold"],
            },
            context={
                "debug_log": mock_cb_data["internal_debug_log"],
            },
            error=(
                "Circuit breaker is OPEN. System is blocked."
                if mock_cb_data["is_open"]
                else None
            ),
        ),
    )
