from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry

from agent_os.system.bus.protocol import (
    StandardFrame,
    BodyFrame,
)

from agent_os.container import (
    AgentServices,
    get_ctx,
)

from .qa_retriever_service import (
    QARetrieverService,
)


async def node_QA_RETRIEVER(
    state: MainBus
) -> dict:

    ctx: AgentServices = await get_ctx()

    retrieval_svc = ctx.retrieval

    brief = (

        state.get(
            "user_input",
            "Hi",
        )

        if isinstance(state, dict)

        else getattr(
            state,
            "user_input",
            "Hi",
        )
    )

    top_k = 3

    raw_chunks = []

    status = "SUCCESS"

    error_message = None

    if retrieval_svc:

        try:

            payload = retrieval_svc.Request(

                query=brief,

                top_k=top_k,
            )

            db_result = await retrieval_svc.retrieve(
                payload
            )

            raw_chunks = (

                db_result.chunks

                if db_result

                else []
            )

        except Exception as err:

            status = "FAILED"

            error_message = str(err)

    else:

        status = "FAILED"

        error_message = (
            "Retrieval Service unavailable"
        )

    contexts_list = []

    score_threshold = 0.45

    if status != "FAILED":

        domain_service = QARetrieverService(
            score_threshold=score_threshold
        )

        result_dict = (
            domain_service
            .process_retrieved_chunks(
                raw_chunks=raw_chunks
            )
        )

        contexts_list = result_dict.get(
            "contexts",
            []
        )

        score_threshold = result_dict.get(
            "score_threshold",
            0.45,
        )

        if not contexts_list:

            status = "EMPTY"

    return StandardFrame.emit(

        registry_key=BusRegistry.QAR,

        payload=BodyFrame(

            status=status,

            text=
            f"QA Retriever completed for query: '{brief}'",

            records=contexts_list,

            state={

                "query":
                brief,

                "retrieval_status":
                status,
            },

            metrics={

                "count":
                len(contexts_list),

                "top_k":
                top_k,

                "score_threshold":
                score_threshold,
            },

            context={

                "source":
                "node_qa_retriever",

                "pipeline":
                "rag_retrieval",
            },

            error=error_message,
        ),
    )