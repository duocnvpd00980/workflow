import json
import logging

# =============================================================================
# STRUCTURED LOGGER
# =============================================================================

_log = logging.getLogger("agent_os_v12")

if not _log.handlers:

    handler = logging.StreamHandler()

    handler.setFormatter(
        logging.Formatter(
            '{"ts":"%(asctime)s","lvl":"%(levelname)s","body":%(message)s}',
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    _log.addHandler(handler)
    _log.setLevel(logging.INFO)


def emit(level: str, **kwargs) -> None:
    getattr(_log, level)(
        json.dumps(kwargs, ensure_ascii=False, default=str)
    )