from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

from .persistence_service import PersistenceService


service = PersistenceService()


async def node_PERSISTENCE_ENGINE(
    state: MainBus,
    config: RunnableConfig | None = None,
) -> dict:

    ok = await service.persist(
        state
    )

    payload = {

        "persisted": ok,

        "storage_backend": "postgres",
    }

    return StandardFrame.emit(
        BusRegistry.POE,
        payload,
    )