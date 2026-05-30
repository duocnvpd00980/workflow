from typing import Optional
from agent_os.system.bus.protocol import BodyFrame
from .finalizer_protocol import FinalizerOutput


class FinalizerService:
    """
    FINALIZER DOMAIN SERVICE (PURE LOGIC)
    Đóng vai trò là một Reduce Node hội tụ dữ liệu từ các luồng chạy song song.

    RULE:
    - Tiếp nhận các Object BodyFrame sạch từ mạng Bus.
    - Quyết định output canonical dựa trên độ ưu tiên nghiệp vụ: DLQ > QA (RAG) > MARKETING > CHAT.
    - Đóng gói phẳng dữ liệu đầu ra theo đúng hợp đồng FinalizerOutput.
    """

    async def resolve(
        self,
        dlq: Optional[BodyFrame] = None,
        chat: Optional[BodyFrame] = None,
        qa: Optional[BodyFrame] = None,
        ads: Optional[BodyFrame] = None,
        blog: Optional[BodyFrame] = None,
        email: Optional[BodyFrame] = None,
    ) -> FinalizerOutput:

        # ======================================================
        # INITIAL CONTRACT SETUP (Mặc định khi các luồng trống)
        # ======================================================
        status = "SUCCESS"
        flow_type = "default"
        text = "Yêu cầu đã được ghi nhận nhưng chưa có nội dung phản hồi."
        summary_message = "Xử lý thành công."
        error_details = None

        # Cờ đánh dấu để xác định luồng nào sẽ chiếm quyền hiển thị ưu tiên
        priority_locked = False

        # ======================================================
        # ACCUMULATIVE CONTEXT GATHERING & PRIORITY SELECTION
        # ======================================================

        # ─── 1. MẠCH CHIẾM QUYỀN TỐI CAO: DLQ (ERROR FIRST PRIORITY) ───
        # Nếu luồng DLQ được kích hoạt hoặc có lỗi hệ thống ghi nhận từ trước
        if dlq and (dlq.status == "FAILED" or dlq.error):
            status = "FAILED"
            flow_type = "error"
            # Lấy text lỗi fallback từ DLQ hoặc gán câu thông báo mặc định
            text = (
                dlq.text
                if dlq.text and dlq.text != "Skipped due to upstream schema violation."
                else "Xin lỗi, hệ thống hiện chưa xử lý được yêu cầu."
            )
            summary_message = f"Hệ thống gặp sự cố tại Node. Chi tiết: {dlq.error}"
            error_details = dlq.error or "INTERNAL_ERROR"
            priority_locked = (
                True  # Khóa quyền ưu tiên, lỗi xảy ra thì bắt buộc phải hiển thị lỗi
            )

        # ─── 2. ƯU TIÊN 2: LUỒNG ĐÁP ÁN TRI THỨC (QA / RAG FLOW) ───
        if qa and qa.status == "SUCCESS" and qa.text:
            if not priority_locked:
                status = "SUCCESS"
                flow_type = "qa"
                text = str(qa.text).strip()
                summary_message = (
                    "Phân giải thành công: Chọn luồng đáp án tri thức (QA/RAG)."
                )
                priority_locked = (
                    True  # Có câu trả lời RAG -> Ưu tiên hiển thị hơn chat/marketing
                )

        # ─── 3. ƯU TIÊN 3: LUỒNG MARKETING AUTOMATION ───
        # Kiểm tra nếu bất kỳ node marketing nào có dữ liệu text trả về thành công
        has_marketing_content = any(
            [
                (ads and ads.status == "SUCCESS" and ads.text),
                (blog and blog.status == "SUCCESS" and blog.text),
                (email and email.status == "SUCCESS" and email.text),
            ]
        )

        if has_marketing_content:
            if not priority_locked:
                status = "SUCCESS"
                flow_type = "marketing"

                # Trích xuất text theo thứ tự ưu tiên trong nhóm marketing: Ads -> Blog -> Email
                if ads and ads.text:
                    text = ads.text
                elif blog and blog.text:
                    text = blog.text
                else:
                    text = email.text

                summary_message = (
                    "Phân giải thành công: Chọn luồng nội dung Marketing Automation."
                )
                priority_locked = True

        # ─── 4. ƯU TIÊN CUỐI: HỘI THOẠI THÔNG THƯỜNG (CHAT FLOW) ───
        if chat and chat.status == "SUCCESS" and chat.text:
            if not priority_locked:
                status = "SUCCESS"
                flow_type = "chat"
                text = str(chat.text).strip()
                summary_message = (
                    "Phân giải thành công: Chọn luồng hội thoại thông thường (Chat)."
                )

        # ======================================================
        # BUILD OUTPUT (CLEAN COMPLIANT CONTRACT)
        # ======================================================
        return FinalizerOutput(
            status=status,
            text=text,
            flow_type=flow_type,
            summary_message=summary_message,
            error_details=error_details,
        )
