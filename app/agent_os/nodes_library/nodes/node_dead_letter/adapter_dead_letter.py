from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

from .dead_letter_service import DeadLetterService


service = DeadLetterService()


async def node_DEAD_LETTER(
    state: MainBus,
    config: RunnableConfig | None = None,
) -> dict:

    payload = {
        "failed_node": "unknown",
        "error_code": "unknown",
        "error_message": "captured",
    }

    await service.push(payload)

    return StandardFrame.emit(
        BusRegistry.DL,
        payload,
    )
