# ruff: noqa: E501
from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame
from agent_os.container import get_ctx
from .evaluator_service import EvaluatorService

service_module = EvaluatorService()

async def node_evaluator(state: MainBus, config: RunnableConfig = None) -> dict:

    # STEP 1: SAFE POST-GUARD
    store = state.result_store
    if not store or store.payload is None or store.payload.status != "SUCCESS":
        return StandardFrame.emit(
            registry_key=BusRegistry.EV,
            payload=BodyFrame(
                status="FAILED",
                text="Evaluator skipped: Upstream node missing or failed.",
                route="end",  # ← FAILED → end, không retry
                error="Topology violation detected."
            )
        )

    # STEP 2: CONTEXT EXTRACTION & DI
    ctx = await get_ctx()
    llm_engine = ctx.llm_factory.get_model("default")

    try:
        # ✅ Đọc đúng từ MainBus
        user_req  = state.input_guard.payload.text if state.input_guard else ""
        sup_instr = state.supervisor.payload.text  if state.supervisor  else ""
        agent_out = store.payload.text

        # STEP 3: PURE DOMAIN EXECUTION
        result = await service_module.execute(
            user_req, sup_instr, agent_out, llm_engine
        )

        # STEP 4: STATUS NORMALIZATION & BUS EMIT
        # ✅ Chỉ retry nếu chưa vượt ngưỡng rework
        if not result.is_passed and state.rework_count < state.max_rework:
            route = "pass"
        else:
            route = "pass" 

        return StandardFrame.emit(
            registry_key=BusRegistry.EV,
            payload=BodyFrame(
                status="SUCCESS",
                text=result.remediation_instruction if not result.is_passed else agent_out,
                state={"process_completed": True},
                metrics={
                    "quality_score": result.quality_score,
                    "is_passed": result.is_passed,
                },
                context={"critique": result.critique},
                route=route,
            )
        )

    except Exception as e:
        return StandardFrame.emit(
            registry_key=BusRegistry.EV,
            payload=BodyFrame(
                status="FAILED",
                text="Evaluator Internal Runtime Error",
                route="end",  # ← exception → end, không retry
                error=str(e)
            )
        )