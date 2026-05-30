from langchain_core.runnables import RunnableConfig
from typing import Literal

from agent_os.nodes_library.node_seed.seed_protocol import SeedOutput
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame
from .seed_service import SeedService

module = SeedService()


async def node_SEED(state: MainBus, config: RunnableConfig) -> dict:
    # mock data (fix đúng Python dict)
    mock_rate_data = {
        "raw_input": state.user_input,
        "normalized_input": state.user_input.strip().lower(),
        "intent": "unknown",  # Literal["ads", "email", "blog", "unknown"]
        "language": "vi",
        "brand_color": getattr(state, "brand_color", "#000000"),
        "confidence": 0.0,
    }

    # validate qua Pydantic / Protocol
    output = SeedOutput(**mock_rate_data)

    # emit ra bus (fix typo output)
    return StandardFrame.emit(BusRegistry.SD, output)
