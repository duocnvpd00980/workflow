import re
from .input_guard_protocol import InputGuardOutput

BLACKLIST_PATTERNS = [
    r"\bhack\b",
    r"\badmin_pass\b",
    r"\bcrack_pass\b",
    r"\bsql\s*injection\b",
    r"\bdrop\s+table\b",
    r"\bexec\s*\(",
    r"\broot\s*access\b",
    r"\bbypass\b",
]
_compiled = [re.compile(p, re.IGNORECASE) for p in BLACKLIST_PATTERNS]


class InputGuardService:
    def run(self, raw_query: str) -> InputGuardOutput:
        for pattern in _compiled:
            match = pattern.search(raw_query)
            if match:
                return InputGuardOutput(
                    is_safe=False, blocked_keyword=match.group(0), sanitized_text=""
                )
        return InputGuardOutput(
            is_safe=True, blocked_keyword=None, sanitized_text=raw_query.strip()
        )
