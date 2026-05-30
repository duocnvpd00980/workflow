from langchain_core.runnables import RunnableConfig

from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry

from agent_os.system.bus.protocol import (
    StandardFrame,
    BodyFrame,
)

from .dead_letter_queue_protocol import (
    DeadLetterQueueOutput,
)


async def node_DEAD_LETTER_QUEUE(
    state: MainBus,
    config: RunnableConfig | None = None,
) -> dict:

    # =====================================================
    # 1. EXTRACT ERROR FROM MAINBUS
    # =====================================================

    last_error = (

        state.errors[-1]

        if getattr(state, "errors", None)

        else "Hệ thống gặp sự cố không xác định."
    )

    failed_node = "System"

    error_code = "INTERNAL_ERROR"

    fallback_message = (

        last_error

        if isinstance(
            last_error,
            str,
        )
        and last_error.strip()

        else (
            "Xin lỗi, hệ thống hiện "
            "chưa xử lý được yêu cầu."
        )
    )

    revision_count = getattr(
        state,
        "revision_count",
        0,
    )

    # =====================================================
    # 2. DOMAIN OUTPUT
    # =====================================================

    output_data = DeadLetterQueueOutput(

        failed_node=
        failed_node,

        error_code=
        error_code,

        message=
        fallback_message,

        retry_count=
        revision_count,

        can_retry=
        revision_count < 3,
    )

    result = output_data.model_dump()

    # =====================================================
    # 3. EMIT STANDARD FRAME
    # =====================================================

    return StandardFrame.emit(

        registry_key=BusRegistry.DLQ,

        payload=BodyFrame(

            status="FAILED",

            text=result.get(
                "message",
                fallback_message,
            ),

            state={

                "failed_node":
                result.get(
                    "failed_node",
                    "System",
                ),

                "error_code":
                result.get(
                    "error_code",
                    "INTERNAL_ERROR",
                ),

                "retry_count":
                result.get(
                    "retry_count",
                    0,
                ),

                "can_retry":
                result.get(
                    "can_retry",
                    False,
                ),
            },

            context={

                "source":
                "dead_letter_queue",
            },

            error=result.get(
                "message",
                fallback_message,
            ),
        ),
    )