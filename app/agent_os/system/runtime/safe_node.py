from agent_os.system.infra.logging_system import emit


async def safe_node(
    *,
    node_name: str,
    coro,
    fallback=None,
):

    try:

        result = await coro

        return result

    except Exception as exc:

        emit(
            "error",
            event="safe_node_exception",
            node=node_name,
            error=str(exc),
        )

        return fallback or {}