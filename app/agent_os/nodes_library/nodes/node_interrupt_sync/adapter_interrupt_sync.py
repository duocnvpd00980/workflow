from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

from .interrupt_sync_protocol import InterruptSyncOutput
from .interrupt_sync_service import InterruptSyncService


service = InterruptSyncService()


async def node_INTERRUPT_SYNC(
    state: MainBus,
    config: RunnableConfig,
) -> dict:

    # =========================================================
    # NORMALIZE ACTIVE BRANCHES
    # =========================================================

    raw_active = getattr(state, "active_branches", []) or []

    # remove duplicate
    active_branches = sorted(list(set(raw_active)))

    # =========================================================
    # AUTO BUILD COMPLETED MODULES
    # =========================================================

    completed_modules: list[str] = []

    # EMAIL
    if getattr(state, "reg_email", None):
        completed_modules.append("email")

    # ADS
    if getattr(state, "reg_ads", None):
        completed_modules.append("ads")

    # BLOG
    if getattr(state, "reg_blog_writer", None) or getattr(state, "reg_validator", None):
        completed_modules.append("blog")

    completed_modules = sorted(list(set(completed_modules)))

    # =========================================================
    # SYNC CHECK
    # =========================================================

    result: InterruptSyncOutput = await service.run(
        completed_modules=completed_modules,
        active_branches=active_branches,
    )

    # =========================================================
    # NO LOOP / NO INTERRUPT
    # =========================================================

    # Không dùng NodeInterrupt nữa
    # vì hiện tại system chưa có human resume flow chuẩn

    return StandardFrame.emit(
        BusRegistry.IS,
        result.model_dump(),
    )
