from pydantic import BaseModel


class PolicyEngine(BaseModel):

    forbidden_topics: frozenset[str] = frozenset({
        "medical advice",
        "financial advice",
        "guaranteed results",
    })

    max_output_chars: int = 8000

    def check_content(
        self,
        text: str,
    ) -> tuple[bool, str]:

        lower = text.lower()

        for topic in self.forbidden_topics:

            if topic in lower:

                return False, topic

        if len(text) > self.max_output_chars:

            return False, "OUTPUT_TOO_LONG"

        return True, ""


POLICY = PolicyEngine()