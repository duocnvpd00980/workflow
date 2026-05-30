import json


class ClipperService:
    """
    CORE DOMAIN: Dọn dẹp bộ nhớ Bus.
    Nhiệm vụ: Giữ lại những gì quan trọng nhất, xóa bỏ các trường trung gian.
    """

    @staticmethod
    def cleanup(state_dict: dict) -> dict:
        # Danh sách các "chân tín hiệu" cần giữ lại cho báo cáo cuối
        keep_keys = {
            "user_input",
            "refined_topic",
            "blog_draft",
            "ads_output",
            "mail_output",
        }

        # Các trường rác cần xóa (Raw logs, intermediate steps)
        trash_keys = {"tool_results", "current_query", "pending_tool", "is_safe"}

        cleaned_data = {k: v for k, v in state_dict.items() if k in keep_keys}

        # Có thể thêm logic tóm tắt (Summarize) nếu nội dung quá dài (Optionally)
        return cleaned_data
