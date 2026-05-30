from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

from .event_bus_service import EventBusService


service = EventBusService()


async def node_EVENT_BUS(
    state: MainBus,
    config: RunnableConfig | None = None,
) -> dict:

    payload = {

        "event_name": "workflow.completed",

        "event_data": {},
    }

    await service.publish(
        payload["event_name"],
        payload["event_data"],
    )

    return StandardFrame.emit(
        BusRegistry.EB,
        payload,
    )