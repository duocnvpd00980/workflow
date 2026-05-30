from .relevance_check_protocol import RelevanceCheckOutput

# Score từ LlamaIndex là cosine similarity (0-1), cao hơn = tốt hơn
HIGH_REL_THRESHOLD = 0.45


class RelevanceCheckService:
    def run(
        self,
        top_score: float | None,
        node_count: int
    ) -> RelevanceCheckOutput:

        if node_count == 0 or top_score is None:
            return RelevanceCheckOutput(
                relevance_status="low_rel",
                top_score=top_score,
                reason="Không có tài liệu nào được retrieved."
            )

        if top_score >= HIGH_REL_THRESHOLD:
            return RelevanceCheckOutput(
                relevance_status="high_rel",
                top_score=top_score,
                reason=f"Top score {top_score:.4f} vượt ngưỡng {HIGH_REL_THRESHOLD}."
            )

        return RelevanceCheckOutput(
            relevance_status="low_rel",
            top_score=top_score,
            reason=(
                f"Top score {top_score:.4f} thấp hơn ngưỡng "
                f"{HIGH_REL_THRESHOLD}. Tài liệu không đủ liên quan."
            )
        )