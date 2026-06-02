from __future__ import annotations
import logging
import time

from .final_response_protocol import (
    FinalResponseOutput, AnswerSource, FinishReason,
)

log = logging.getLogger(__name__)


class FinalResponseService:

    def run(
        self,
        *,
        cache_payload:  object | None,
        guard_payload:  object | None,
        search_payload: object | None,
        t0:             float,
        node_path:      list[str],
    ) -> FinalResponseOutput:

        # ── Chọn payload theo priority: cache > guard > search ────────────
        answer        = ""
        answer_source = AnswerSource.LLM
        finish_reason = FinishReason.SUCCESS

        if self._valid(cache_payload):
            answer        = cache_payload.text
            answer_source = AnswerSource.CACHE
            confidence    = 1.0

        elif self._valid(guard_payload):
            answer        = guard_payload.text
            answer_source = AnswerSource.RAG
            confidence    = 0.8

        elif self._valid(search_payload):
            answer        = search_payload.text
            answer_source = AnswerSource.SEARCH
            finish_reason = FinishReason.FALLBACK
            confidence    = 0.6

        else:
            log.warning("[FinalResponseService] no valid upstream payload")
            return FinalResponseOutput(
                answer        = "",
                answer_source = AnswerSource.LLM,
                finish_reason = FinishReason.ERROR,
                confidence    = 0.0,
                latency_ms    = self._ms(t0),
                node_path     = node_path,
            )

        return FinalResponseOutput(
            answer        = answer,
            answer_source = answer_source,
            finish_reason = finish_reason,
            confidence    = confidence,
            latency_ms    = self._ms(t0),
            node_path     = node_path,
        )

    @staticmethod
    def _valid(payload: object | None) -> bool:
        return (
            payload is not None
            and getattr(payload, "status", "") == "SUCCESS"
            and bool(getattr(payload, "text", ""))
        )

    @staticmethod
    def _ms(t0: float) -> float:
        return round((time.time() - t0) * 1000, 1)