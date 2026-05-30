import re


_INJECTION_SIGNALS = frozenset({
    "ignore previous",
    "ignore all",
    "system prompt",
    "reveal key",
    "reveal secret",
    "act as",
    "jailbreak",
})

_RE_SCRIPT = re.compile(r"<script[\s\S]*?</script>", re.I)

_RE_TAG = re.compile(r"<[^>]+>")

_RE_FENCE = re.compile(r"```[\s\S]*?```")

_RE_INLINE = re.compile(r"`[^`]+`")

_RE_NULL = re.compile(r"\x00")


def sanitise(text: str) -> str:

    if not text:
        return ""

    text = _RE_NULL.sub("", text)

    text = _RE_SCRIPT.sub("", text)

    text = _RE_TAG.sub("", text)

    text = _RE_FENCE.sub("", text)

    text = _RE_INLINE.sub("", text)

    return text.strip()


def detect_language(text: str) -> str:

    vi = len(
        re.findall(
            r"[àáâãèéêìíòóôõùúýăđơưạảấầẩẫậ]",
            text,
            re.I,
        )
    )

    return "vi" if vi > 2 else "en"