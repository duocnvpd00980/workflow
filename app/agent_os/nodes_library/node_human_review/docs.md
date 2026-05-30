ARCHITECTURAL SPECIFICATION DOCUMENT
MODULE: node_human_review (Human-In-The-Loop & Exception Escalation Gate)
I. BUSINESS OVERVIEW & INTENT
node_human_review đóng vai trò là Tầng Can thiệp và Quản trị tối cao (Human-In-The-Loop Plane) của hệ thống Multi-Agent. Node này được kích hoạt tự động qua cơ chế ngắt đồ thị (LangGraph interrupt) trong hai kịch bản đặc biệt:

Vòng lặp sửa lỗi quá tải (Loop Threshold Exceeded): Khi node_evaluator từ chối bản thảo vượt quá số lần cấu hình (ví dụ: > 3 lần), hệ thống tự hiểu LLM đã rơi vào trạng thái bế tắc (Stuck Condition) và cần con người nhảy vào can thiệp.

Tác vụ nhạy cảm cao (High-Risk Escalation): Khi Supervisor phát hiện yêu cầu của User chạm vào các vùng nghiệp vụ cần phê duyệt bắt buộc (ví dụ: giải quyết khiếu nại tài chính lớn, thay đổi điều khoản hợp đồng).

Con người (Reviewer) sẽ xem xét toàn bộ nhật ký suy luận trên Bus để thực hiện một trong hai hành động: chỉnh sửa trực tiếp nội dung để xuất bản (Pass), hoặc viết chỉ thị thủ công để đẩy ngược về bắt các Agent làm lại (Reject).

II. COMPONENT FILES SPECIFICATION
1. Core Contract (human_review_protocol.py)
Định nghĩa cấu trúc dữ liệu bất biến đại diện cho hành động can thiệp của con người từ giao diện Quản trị (Admin Dashboard).

Tiêu chuẩn kỹ thuật: Sử dụng Pydantic v2, cấu hình ConfigDict(frozen=True, extra="ignore").

Cấu trúc Object: HumanReviewInput

decision (str): Quyết định của chuyên viên ("APPROVED" hoặc "REJECTED").

overridden_text (str): Nội dung văn bản do con người chỉnh sửa trực tiếp (để trống nếu từ chối).

human_feedback (str): Chỉ thị thủ công của con người giải thích lý do từ chối và hướng dẫn Agent cách sửa bài.

reviewer_id (str): Mã định danh của chuyên viên thực hiện phê duyệt để phục vụ kiểm toán (Auditing).

2. Pure Domain Execution (human_review_service.py)
Tầng xử lý logic nghiệp vụ thuần túy kiểm tra dữ liệu đầu vào từ phía Con người (Human Input Validation). Tầng này hoàn toàn Deterministic (không dùng LLM) vì con người chính là thực thể thông minh xử lý ở đây.

Tiêu chuẩn kỹ thuật: class HumanReviewService chứa hàm xử lý def process_review(self, review_payload: dict) -> HumanReviewInput.

Logic thực thi nội bộ:

Nhận review_payload thô từ State gửi lên qua Giao diện UI Admin.

Kiểm tra tính hợp lệ: Nếu decision == "APPROVED" nhưng overridden_text trống, hoặc decision == "REJECTED" nhưng không có human_feedback, lập tức kích hoạt validation error nội bộ để yêu cầu Admin điền lại.

Đóng gói dữ liệu sạch vào Object Pydantic đóng băng HumanReviewInput.

3. Mainboard Gatekeeper (adapter_human_review.py)
Điểm đấu nối chứa cơ chế ngắt (interrupt) của LangGraph. Node này chịu trách nhiệm đóng băng đồ thị, chờ đợi tín hiệu từ con người, bóc tách dữ liệu Admin và cập nhật lên mạng Bus.

Tiêu chuẩn kỹ thuật: Hàm xử lý đồ thị async def node_human_review(state: MainBus, config: RunnableConfig = None) -> dict.

Cơ chế Ngắt & Đấu nối (State Interruption):

Safe Post-Guard: Kiểm tra xem trên Bus đã có dữ liệu can thiệp của con người chưa (thường được truyền thông qua cấu hình config hoặc interrupt resume payload của LangGraph).

Nếu chưa có dữ liệu (Lần đầu tiên luồng chạy chạm vào Node này): Đồ thị sẽ phát ra tín hiệu interrupt() để dừng runtime của hệ thống lại một cách an toàn, giữ nguyên trạng thái Bus, mở cổng chờ giao diện Admin gửi Payload lên. CẤM sử dụng lệnh raise.

Khi đồ thị được resume với dữ liệu từ Admin Dashboard, Adapter tiếp nhận Payload, đẩy qua HumanReviewService để chuẩn hóa.

BodyFrame Schema Mapping (Strict Constraint): Đóng gói dữ liệu ra Bus qua đúng 8 trường phẳng quy chuẩn của BodyFrame:

status: "SUCCESS" sau khi nhận được phản hồi hợp lệ từ con người, hoặc "FAILED" nếu phiên làm việc của con người bị timeout / hủy bỏ.

text: Nếu được duyệt (APPROVED), lưu nội dung con người đã sửa (overridden_text). Nếu bị từ chối (REJECTED), lưu chuỗi chỉ thị của con người (human_feedback).

records: Không xử lý (để trống).

entities: Không xử lý (để trống).

state: Lưu trạng thái runtime phục vụ Conditional Edges rẽ nhánh: {"next_action": "pass" if result.decision == "APPROVED" else "retry", "process_completed": False}.

metrics: Lưu thông tin định danh {"reviewer_id": result.reviewer_id, "mode": "HUMAN_IN_THE_LOOP"}.

context: Không xử lý (để trống).

error: Chuỗi thông báo lỗi chi tiết nếu status == "FAILED".

III. CERTIFIED WORKFLOW DOCSTRING TEMPLATE
Mã nguồn hàm Adapter của Human Review bắt buộc phải đính kèm Docstring chuẩn hóa sau:

Python
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [node_human_review]
    ======================================================================
    [BUSINESS INTENT]
    Cung cấp chốt chặn Human-In-The-Loop tối cao. Kích hoạt trạng thái ngắt đồ thị 
    (State Interruption) khi hệ thống LLM bị bế tắc hoặc chạm tác vụ nguy cơ cao, 
    ủy quyền cho chuyên viên kiểm duyệt can thiệp chỉnh sửa hoặc điều hướng thủ công.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard / Interrupt Check - Kiểm tra sự tồn tại của dữ liệu can thiệp từ Admin. Nếu trống, thực hiện ngắt đồ thị an toàn (LangGraph Interrupt).
    - Step 2: Context Extraction & DI - Sau khi luồng được Resume, trích xuất Payload thô của chuyên viên từ trạng thái kích hoạt và nạp dịch vụ xác thực.
    - Step 3: Pure Domain Execution - Gọi HumanReviewService để thẩm định cấu trúc quyết định (Duyệt/Từ chối), sinh ra Pydantic Object đóng băng.
    - Step 4: Status Normalization & Bus Emit - Chuẩn hóa thông điệp của con người vào trường 'text', gán cờ rẽ nhánh 'next_action' (pass/retry) và phát sóng lên Bus.
    ======================================================================
    """
IV. STRICT LAWS FOR AI INTEGRATION (ĐIỀU KHOẢN CẤM)
TUYỆT ĐỐI KHÔNG tự ý sinh thêm trường dữ liệu nằm ngoài cấu trúc 8 trường quy định của BodyFrame.

CẤM sử dụng LLM trong Node này. Toàn bộ quyết định phải dựa trên dữ liệu đầu vào Deterministic do Con người đẩy lên để đảm bảo tính tối cao của quyền kiểm soát Human-In-The-Loop.

CẤM sử dụng lệnh raise phá vỡ Runtime khi chuyên viên điền thiếu trường. Adapter phải bắt lỗi thông qua Service, giữ trạng thái đồ thị ở chế độ chờ ngắt (interrupt) và yêu cầu Frontend Admin thông báo cho người dùng sửa lại dữ liệu đầu vào trên Form.