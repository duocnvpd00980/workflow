from langchain_core.runnables import RunnableConfig

from django.conf import settings as django_settings

from agent_os.system.bus.main_bus import MainBus

from agent_os.system.bus.registry import BusRegistry

from agent_os.system.bus.protocol import StandardFrame

from .router_protocol import RouterOutput

from .router_service import RouterService


async def node_ROUTER(state: MainBus, config: RunnableConfig) -> dict:

    services = django_settings.SYSTEM_SERVICES
    engine = services["llm_factory"].get_model("cloud_router")

    module = RouterService(llm_engine=engine)

    brief = state.user_input
    context = getattr(state.reg_seed, "payload", {}) or {}

    decision = await module.classify(user_input=brief, context=context)

    intent = getattr(decision, "intent", "invalid")
    mapping = {
        "ads_only": ["ads"],
        "blog_only": ["blog"],
        "email_only": ["email"],
        "full_campaign": ["ads", "blog", "email"],
    }
    active_branches = mapping.get(intent, [])

    safe_output = RouterOutput(
        intent=intent,
        reasoning=getattr(decision, "reasoning", "auto"),
        confidence_score=getattr(decision, "confidence_score", 0.0),
        next_steps=getattr(decision, "next_steps", []),
        active_branches=active_branches,
    )

    return {
        "active_branches": active_branches,
        "route": intent,
        **StandardFrame.emit(BusRegistry.RT, safe_output),
    }
