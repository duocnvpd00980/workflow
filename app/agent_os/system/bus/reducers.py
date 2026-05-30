import hashlib

# =============================================================================
# REDUCERS
# =============================================================================

def sum_cost(a: float, b: float) -> float:

    return round(float(a or 0) + float(b or 0), 6)


def append_telemetry(a: list, b: list) -> list:

    return (a or []) + (b or [])


def append_faults(a: list, b: list) -> list:

    return (a or []) + (b or [])


def append_tools(a: list, b: list) -> list:

    return (a or []) + (b or [])


def append_list(a: list, b: list) -> list:

    return (a or []) + (b or [])


def or_degraded(a: bool, b: bool) -> bool:

    return a or b

def take_last_feedback(current: str, update: str) -> str:

    if not update:
        return current

    return update


def or_degraded(a: bool, b: bool) -> bool:

    return a or b


def dedup_content(a: list, b: list) -> list:

    seen = set()

    out = []

    for item in (a or []) + (b or []):

        if not item:
            continue

        content = getattr(item, "content", None)

        if not content:
            continue

        h = hashlib.md5(content.encode()).hexdigest()

        if h not in seen:
            seen.add(h)
            out.append(item)

    return out