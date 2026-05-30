from langchain_core.runnables import RunnableConfig

from marketing_crew.system.bus.main_bus import MainBus
from marketing_crew.system.bus.registry import BusRegistry
from marketing_crew.system.bus.protocol import StandardFrame

from .ui_selector_service import UISelectorService


async def node_UI_SELECTOR(state: MainBus, config: RunnableConfig) -> dict:
    """
    ADAPTER: Cầu nối giữa Bus System và UI Selector Domain.
    Rule-based, không LLM — chạy < 5ms, không timeout.
    """

    ui_service = UISelectorService()

    # 1. Lấy Registry của Finalizer (RF)
    finalizer_reg = getattr(state, BusRegistry.RF, None)
    if not finalizer_reg:
        return StandardFrame.emit(
            BusRegistry.UI,
            ui_service._build_fallback("No finalizer data found.").model_dump(),
        )

    # 2. Chuyển Payload sang dict
    raw_payload = getattr(finalizer_reg, "payload", {})
    payload = (
        raw_payload.model_dump()
        if hasattr(raw_payload, "model_dump")
        else (raw_payload or {})
    )

    final_bundle = payload.get("final_bundle", {})
    message      = payload.get("message", "Processing completed.")

    try:
        # Bước A: Rule-based chọn component ID — không LLM, không timeout
        selector_res = ui_service.select_components(final_bundle)

        # Bước B: Map dữ liệu + validate Props
        output = ui_service.resolve_ui(
            selector_res=selector_res,
            final_bundle=final_bundle,
            msg=message,
        )

    except Exception as e:
        print(f"[ADAPTER_UI_ERROR] {e}")
        output = ui_service._build_fallback(message)

    # 3. Phát tín hiệu lên Bus Registry
    return StandardFrame.emit(
        BusRegistry.UI,
        output.model_dump(),
    )