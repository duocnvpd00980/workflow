from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry

from agent_os.system.bus.protocol import (
    StandardFrame,
    BodyFrame,
)


async def node_RATE_LIMITER(state: MainBus) -> dict:

    mock_rate_data = {
        "allowed": True,
        "current_requests": 12,
        "limit_per_minute": 60,
        "remaining_requests": 48,
        "blocked_reason": None,
        "internal_latency_ms": 150,
    }

    return StandardFrame.emit(
        registry_key=BusRegistry.RL,
        payload=BodyFrame(
            status=("SUCCESS" if mock_rate_data["allowed"] else "FAILED"),
            text="Rate limit evaluation completed",
            state={
                "allowed": mock_rate_data["allowed"],
            },
            metrics={
                "current_requests": mock_rate_data["current_requests"],
                "limit_per_minute": mock_rate_data["limit_per_minute"],
                "remaining_requests": mock_rate_data["remaining_requests"],
                "latency_ms": mock_rate_data["internal_latency_ms"],
            },
            context={
                "blocked_reason": mock_rate_data["blocked_reason"],
            },
            error=mock_rate_data["blocked_reason"],
        ),
    )
