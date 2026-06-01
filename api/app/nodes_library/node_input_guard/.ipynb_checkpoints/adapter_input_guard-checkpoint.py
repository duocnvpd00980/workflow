from langchain_core.runnables import RunnableConfig


from app.nodes_library.node_input_guard.input_guard_service import InputGuardService
from app.core.main_bus import MainBus
from app.core.registry  import BusRegistry

from app.core.protocol  import (
    StandardFrame,
    BodyFrame,
)


async def node_INPUT_GUARD(
    state: MainBus,
    config: RunnableConfig,
) -> dict:

    conf = (
        config.get("configurable", {})
        if isinstance(config, dict)
        else {}
    )

    thread_id = conf.get("thread_id")

    tenant_id = conf.get("tenant_id")

    user_input = (

        state.get("user_input", "")

        if isinstance(state, dict)

        else getattr(
            state,
            "user_input",
            "",
        )
    )

    brand_color = (

        state.get("brand_color", "#000000")

        if isinstance(state, dict)

        else getattr(
            state,
            "brand_color",
            "#000000",
        )
    )

    module = InputGuardService()

    res = await module.run(

        {
            "headline": user_input,
            "content": user_input,
            "brand_color": brand_color,
        },

        tenant_id=tenant_id,

        thread_id=thread_id,
    )

    return StandardFrame.emit(

        registry_key=BusRegistry.IG,

        payload=BodyFrame(

            status=(
                "SUCCESS"
                if res.gatekeeper_passed
                else "FAILED"
            ),

            text=res.content or "",

            entities=[

                {
                    "violation": str(v)
                }

                for v in getattr(
                    res,
                    "violations",
                    [],
                )
            ],

            state={

                "gatekeeper_passed":
                res.gatekeeper_passed,

                "risk_score":
                getattr(
                    res,
                    "risk_score",
                    0.0,
                ),

                "headline":res.headline or "",
                "brand_color": getattr(
                    res,
                    "brand_color",
                    "#000000",
                ),
            },

            context={

                "tenant_id":
                tenant_id,

                "thread_id":
                thread_id,
            },

            error=(

                None

                if res.gatekeeper_passed

                else getattr(
                    res,
                    "reason",
                    "Security Policy Violation",
                )
            ),
        ),
    )