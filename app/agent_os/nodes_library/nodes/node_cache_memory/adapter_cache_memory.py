from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

from .cache_memory_service import CacheMemoryService


service = CacheMemoryService()


from .cache_memory_protocol import CacheMemoryOutput # Import schema mới

async def node_CACHE_MEMORY(
    state: MainBus,
    config: RunnableConfig | None = None,
) -> dict:

    cache_key = state.user_input
    cached = await service.get(cache_key)

    # KHỞI TẠO CHUẨN: Gán tên thuộc tính rõ ràng
    output_data = CacheMemoryOutput(
        cache_key=cache_key,
        cache_hit=cached is not None,
        cached_data=cached
    )

    # Emit object thay vì dict
    return StandardFrame.emit(
        BusRegistry.CM,
        output_data,
    )