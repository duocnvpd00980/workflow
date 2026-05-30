import json
from datetime import datetime, timezone
from .audit_logger_protocol import AuditLogOutput


class AuditLoggerService:
    """
    Nghiệp vụ ghi nhật ký hệ thống thuần túy (Pure Domain Execution).
    Không can thiệp hoặc phụ thuộc vào State của mạng Bus.
    """

    def __init__(self):
        # Bộ lưu trữ tạm thời trong memory (Production sẽ thay bằng kết nối File/Database/Kafka)
        self.logs = []

    async def write_log(
        self, event_type: str, actor: str, action: str, success: bool
    ) -> AuditLogOutput:
        """
        Thực thi ghi log hệ thống, gắn nhãn thời gian thực UTC theo tiêu chuẩn ISO.
        """
        # Tạo payload dựa trên schema của Protocol nhằm lọc sạch metadata rác
        payload_obj = AuditLogOutput(
            event_type=event_type, actor=actor, action=action, success=success
        )

        # Chuyển đổi sang dict nội bộ để bổ sung metadata vận hành
        log_entry = payload_obj.model_dump()
        log_entry["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Lưu trữ nội bộ và xuất ra stdout dưới dạng JSON phân cấp
        self.logs.append(log_entry)
        print(json.dumps(log_entry, indent=2))

        return payload_obj
