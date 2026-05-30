from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame
from .polisher_service import PolisherService
from .polisher_schema import PolisherParser

async def node_FINAL_POLISHER(state: MainBus, config: RunnableConfig) -> dict:
    # services = config["configurable"].get("services")
    # engine = services["llm_factory"].get_model("qwen2.5-max")
    
    # module = PolisherService(llm_engine=engine)
    
    # raw = await module.run(
    #     blog=state.reg_blog_draft.payload if state.reg_blog_draft else "",
    #     ads=state.reg_ads.payload if state.reg_ads else "",
    #     mail=state.reg_email.payload if state.reg_email else ""
    # )
    
    # parsed = PolisherParser.parse(raw)

    output= {
        "final_output": "ok"
    }

    return StandardFrame.emit(BusRegistry.FP, output)