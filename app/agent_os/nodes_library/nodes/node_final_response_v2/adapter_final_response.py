from langchain_core.runnables import RunnableConfig
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame, BodyFrame


async def node_final_response(
    state: MainBus,
    config: RunnableConfig = None,
) -> dict:

    # =========================================================================
    # STEP 1 — SAFE POST-GUARD
    # Có 2 luồng vào final_response:
    #   - Luồng smalltalk  → đọc từ lightweight_chat
    #   - Luồng chính      → đọc từ human_review (đã approved)
    # =========================================================================
    text = None

    # Luồng chính
    human_review = state.human_review
    if (
        human_review
        and human_review.payload
        and human_review.payload.status == "SUCCESS"
    ):
        text = human_review.payload.text

    # Luồng smalltalk
    if not text:
        lightweight_chat = state.lightweight_chat
        if (
            lightweight_chat
            and lightweight_chat.payload
            and lightweight_chat.payload.status == "SUCCESS"
        ):
            text = lightweight_chat.payload.text

    if not text:
        return StandardFrame.emit(
            registry_key=BusRegistry.FR,
            payload=BodyFrame(
                status="FAILED",
                text="",
                error="[node_final_response] Không tìm thấy output hợp lệ từ upstream.",
            ),
        )

    # =========================================================================
    # STEP 2 — BUS EMIT
    # =========================================================================
    return StandardFrame.emit(
        registry_key=BusRegistry.FR,
        payload=BodyFrame(
            status="SUCCESS",
            text=text,
            state={"process_completed": True},
            error=None,
        ),
    )
