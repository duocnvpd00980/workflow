from __future__ import annotations

import logging

from agent_os.container import (
    AgentServices,
    get_ctx,
)

from agent_os.system.bus.main_bus import MainBus

from agent_os.system.bus.protocol import (
    BodyFrame,
    StandardFrame,
)

from agent_os.system.bus.registry import (
    BusRegistry,
)

from .qa_response_protocol import (
    QaResponseOutput,
)

from .qa_response_service import (
    QaResponseService,
)

logger = logging.getLogger(__name__)


async def node_QA_RESPONSE(
    state: MainBus
) -> dict:

    logger.info(
        "[NodeQAResponse] Executing"
    )

    ctx: AgentServices = (
        await get_ctx()
    )

    llm_engine = (
        ctx.llm_factory
        .get_model("default")
    )

    if isinstance(state, dict):

        user_input = (
            state.get("user_input")
            or state.get("query")
            or "Hi"
        )

        retriever_state = state.get(
            BusRegistry.QAR,
            {},
        )

    else:

        user_input = (
            getattr(
                state,
                "user_input",
                None,
            )
            or getattr(
                state,
                "query",
                None,
            )
            or "Hi"
        )

        retriever_state = getattr(
            state,
            BusRegistry.QAR,
            {},
        )

    bus_contexts = []

    if retriever_state:

        payload = (

            retriever_state.get(
                "payload",
                {},
            )

            if isinstance(
                retriever_state,
                dict,
            )

            else getattr(
                retriever_state,
                "payload",
                {},
            )
        )

        if hasattr(
            payload,
            "model_dump",
        ):

            payload_dict = (
                payload.model_dump()
            )

        elif hasattr(
            payload,
            "__dict__",
        ):

            payload_dict = vars(payload)

        elif isinstance(
            payload,
            dict,
        ):

            payload_dict = payload

        else:

            payload_dict = {}

        bus_contexts = (
            payload_dict.get(
                "records",
                [],
            )
        )

    module = QaResponseService(
        llm_engine=llm_engine
    )

    decision = (
        await module.generate_response(
            user_input=user_input,
            contexts=bus_contexts,
        )
    )

    safe_output = QaResponseOutput(

        answer=getattr(
            decision,
            "answer",
            "",
        ),

        source_used=bool(
            bus_contexts
            and isinstance(
                bus_contexts,
                list,
            )
        ),

        tone=getattr(
            decision,
            "tone",
            "neutral",
        ),

        citations=getattr(
            decision,
            "citations",
            [],
        ),
    )

    return StandardFrame.emit(

        registry_key=BusRegistry.QA,

        payload=BodyFrame(

            status=(

                "SUCCESS"

                if safe_output.answer

                else "EMPTY"
            ),

            text=
            safe_output.answer,

            records=[
                safe_output.answer
            ],

            state={

                "source_used":
                safe_output.source_used,

                "tone":
                safe_output.tone,
            },

            context={

                "citations":
                safe_output.citations,
            },
        ),
    )