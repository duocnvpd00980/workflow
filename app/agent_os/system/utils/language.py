import re


def detect_language(
    text: str,
) -> str:

    vi = len(
        re.findall(
            r"[àáâãèéêìíòóôõùúýăđơưạảấầẩẫậ]",
            text,
            re.I,
        )
    )

    return "vi" if vi > 2 else "en"