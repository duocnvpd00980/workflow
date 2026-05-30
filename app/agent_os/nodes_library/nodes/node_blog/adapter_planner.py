from langchain_core.runnables import RunnableConfig
from django.conf import settings as django_settings
from agent_os.system.bus.main_bus import MainBus
from .planner_service import PlannerService
from .planner_schema import PlannerParser


async def node_BLOG_PLANNER(state: MainBus, config: RunnableConfig) -> dict:

    services = django_settings.SYSTEM_SERVICES
    selected_model = services["llm_factory"].get_model("qwen2.5")

    service = PlannerService(llm_engine=selected_model)
    raw_output = await service.run(
        topic=state.user_input, language=getattr(state, "language", "vi")
    )

    plan = PlannerParser.parse(raw_output)

    return {"blog_plan": plan}
