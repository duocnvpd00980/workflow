from typing import Any, Dict
from .observer_protocol import ObserverOutput, ObservationMetric


class ObserverService:
    """
    Nghiệp vụ giám sát, tổng hợp tài nguyên tiêu thụ và chất lượng luồng chạy (Pure Domain Execution).
    """

    async def summarize(self, state: Any) -> ObserverOutput:
        """
        Quét qua State của MainBus, thu thập dấu vết (Tracing)
        để đánh giá sức khỏe hệ thống.
        """
        # Khởi tạo giá trị mặc định cho phân tích
        system_health = "healthy"
        current_step = "UNKNOWN"
        quality_metrics = {"format_valid": True, "policy_violation": False}

        # Mặc định thông số sử dụng tài nguyên (Giả lập việc bóc tách tổng token từ LLM Factory)
        usage = {
            "input_tokens": ObservationMetric(
                metric_name="Input Tokens", value=1250, unit="tokens"
            ),
            "latency": ObservationMetric(
                metric_name="Execution Time", value=4.5, unit="seconds"
            ),
        }

        # Kiểm tra động phần tử chạy liền trước (Ví dụ: Audit Logger)
        if (
            hasattr(state, "node_reg_audit_logger")
            and state.node_reg_audit_logger is not None
        ):
            audit_frame = state.node_reg_audit_logger
            current_step = "AUDIT_LOGGER"

            if audit_frame.payload.status != "SUCCESS":
                system_health = "warning"
                quality_metrics["format_valid"] = False

        # Kiểm tra gián tiếp nếu luồng vi phạm chính sách ở Policy Engine trước đó
        if (
            hasattr(state, "node_reg_policy_engine")
            and state.node_reg_policy_engine is not None
        ):
            policy_frame = state.node_reg_policy_engine
            if (
                policy_frame.payload.status != "SUCCESS"
                or policy_frame.payload.state.get("route_to") == "dlq"
            ):
                system_health = "critical"
                quality_metrics["policy_violation"] = True

        return ObserverOutput(
            usage_stats=usage,
            quality_check=quality_metrics,
            current_step=current_step,
            system_health=system_health,
        )
