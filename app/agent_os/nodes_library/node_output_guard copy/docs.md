ARCHITECTURAL SPECIFICATION DOCUMENT
MODULE: node_output_guard (Compliance, Data Privacy & Brand Protection Gate)
Lưu ý định danh: Tên chính thức của Node này trong hệ thống Mainboard là node_output_guard (đảm nhiệm vai trò Output Plane - chốt chặn an toàn và kiểm duyệt chặng cuối trước khi xuất bản thành phẩm, phân biệt rõ ràng với bộ lọc đầu vào node_input_guard).

I. BUSINESS OVERVIEW & INTENT
node_output_guard đóng vai trò là Bộ kiểm duyệt và Bảo vệ đầu ra tối cao (Compliance & Brand Protection Plane) trước khi dữ liệu chính thức rời khỏi đồ thị LangGraph để bàn giao cho API Gateway hoặc ứng dụng khách (Client UI).

Dù nội dung đã được xây dựng và tối ưu văn phong qua các Agent chuyên biệt, Node này chịu trách nhiệm quản trị rủi ro doanh nghiệp ở chặng cuối với hai mục tiêu cốt lõi:

PII Redaction (Bảo mật dữ liệu cá nhân): Tự động phát hiện và che giấu (Masking) các thông tin định danh nhạy cảm vô tình bị rò rỉ trong văn bản sinh ra bởi LLM (như số căn cước, số thẻ tín dụng, mật khẩu, API keys).

Compliance & Brand Safety (An toàn thương hiệu): Quét văn bản chặng cuối để đảm bảo không chứa từ ngữ độc hại, vi phạm cấm kỵ pháp lý, hoặc đi ngược lại tiêu chuẩn cộng đồng được cập nhật ở thời điểm hiện tại (Năm 2026).

II. COMPONENT FILES SPECIFICATION
1. Core Contract (output_guard_protocol.py)
Định nghĩa giao ước dữ liệu đầu ra bất biến đã qua xử lý an toàn chặng cuối.

Tiêu chuẩn kỹ thuật: Sử dụng Pydantic v2, cấu hình ConfigDict(frozen=True, extra="ignore").

Cấu trúc Object: OutputGuardResult

is_compliant (bool): Trạng thái tuân thủ pháp lý và an toàn nội dung (True nếu đạt, False nếu vi phạm nặng).

sanitized_text (str): Văn bản sạch hoàn toàn sau khi đã thực hiện che giấu thông tin nhạy cảm (PII masked).

redacted_entities (list[str]): Danh sách các loại thực thể nhạy cảm đã bị loại bỏ (ví dụ: ["PHONE_NUMBER", "CREDIT_CARD"]).

safety_metrics (dict): Điểm số đánh giá mức độ rủi ro đầu ra từ bộ lọc kiểm duyệt.

2. Pure Domain Execution (output_guard_service.py)
Chứa nghiệp vụ kết hợp giữa thuật toán Deterministic (Regex / Thư viện quét PII như Microsoft Presidio) và một cuộc gọi kiểm tra siêu tốc (Guardrails LLM call) sử dụng các dòng máy siêu nhanh, chuyên biệt về phân loại nội dung độc hại (Fast Tokenizer/Classifier).

Tiêu chuẩn kỹ thuật: class OutputGuardService với hàm xử lý bất đồng bộ async def execute(self, text_to_check: str, compliance_rules: dict, llm_engine: Any) -> OutputGuardResult.

Logic thực thi nội bộ:

Chạy bộ lọc Deterministic để quét qua text_to_check, tìm kiếm các chuỗi định dạng khớp với số thẻ, căn cước, email cá nhân và thay thế chúng bằng nhãn chuẩn hóa dạng [REDACTED_PHONE].

Gọi Mô hình ngôn ngữ chuyên biệt qua cấu hình ép cấu trúc (Structured Outputs) để chấm điểm mức độ an toàn (Tấn công, chính trị nhạy cảm, độc hại).

Nếu phát hiện vi phạm chính sách nặng không thể cứu vãn, đánh dấu is_compliant=False. Ngược lại, đóng gói văn bản đã làm sạch vào Object Pydantic đóng băng.

3. Mainboard Gatekeeper (adapter_output_guard.py)
Điểm đấu nối trực tiếp vào điểm ra (END) của đồ thị LangGraph, đóng vai trò thanh lọc gói tin thành phẩm chặng cuối.

Tiêu chuẩn kỹ thuật: Hàm xử lý đồ thị async def node_output_guard(state: MainBus, config: RunnableConfig = None) -> dict.

Tuân thủ Safe Post-Guard (Chống sập Đồ thị):

Kiểm tra tính toàn vẹn của Node đứng trước (BusRegistry.AGGREGATOR hoặc BusRegistry.HUMAN_REVIEW nếu có luồng rẽ nhánh duyệt thẳng từ con người).

Nếu phát hiện Node thượng nguồn không tồn tại hoặc bị lỗi (status == "FAILED"), áp dụng Hạ cánh an toàn chặng cuối (Emergency Fallback Response): Trả về một câu thông báo lỗi hệ thống thân thiện đã được định nghĩa sẵn cho User, gán status="FAILED", ghi log lỗi kỹ thuật vào error và phát đi qua StandardFrame.emit. Không dùng câu lệnh raise.

Dependency Injection & Context Extraction: Gọi await get_ctx() để lấy thực thể Guard Engine từ Container. Trích xuất nội dung văn bản hoàn chỉnh từ trường text của Node Aggregator trên Bus.

BodyFrame Schema Mapping (Strict Constraint): Đồng bộ dữ liệu sang đúng cấu trúc 8 trường phẳng của BodyFrame:

status: "SUCCESS" nếu văn bản an toàn hoặc đã được làm sạch thành công, hoặc "FAILED" nếu nội dung vi phạm chính sách bảo mật nghiêm trọng không thể hiển thị.

text: SẢN PHẨM SẠCH TUYỆT ĐỐI - Nếu thành công, lưu sanitized_text. Nếu thất bại do vi phạm compliance, lưu câu thông báo từ chối hiển thị do chính sách bảo mật hệ thống.

records: Không xử lý (để trống).

entities: Lưu danh sách các thực thể nhạy cảm đã xử lý: {"redacted": result.redacted_entities}.

state: Lưu trạng thái runtime kết thúc: {"process_completed": True, "compliance_checked": True}.

metrics: Lưu kết quả đo lường an toàn {"safety": result.safety_metrics}.

context: Không xử lý (để trống).

error: Chuỗi thông báo lỗi chi tiết nếu status == "FAILED" (ví dụ: "Output blocked by safety compliance policy").

III. CERTIFIED WORKFLOW DOCSTRING TEMPLATE
Mã nguồn hàm Adapter của Output Guard bắt buộc phải đính kèm Docstring chuẩn hóa sau:

Python
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [node_output_guard]
    ======================================================================
    [BUSINESS INTENT]
    Chốt chặn an toàn và tuân thủ pháp lý đầu ra (Output Plane). Thực hiện 
    che giấu thông tin cá nhân (PII Redaction) và quét nội dung độc hại chặng cuối 
    để bảo vệ an toàn thương hiệu trước khi trả dữ liệu về phía Client.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard - Xác thực gói thành phẩm của Aggregator trên mạng Bus. Chuyển hóa lỗi hệ thống thành văn bản Fallback an toàn thay vì crash ứng dụng.
    - Step 2: Context Extraction & DI - Trích xuất chuỗi thành phẩm thô bằng toán tử chấm (.) và cấu hình dịch vụ bảo mật cùng Guardrails LLM từ Container.
    - Step 3: Pure Domain Execution - Gọi OutputGuardService chạy bộ lọc PII thuần thuật toán kết hợp chấm điểm độc hại LLM, nhận về Pydantic Object đóng băng.
    - Step 4: Status Normalization & Bus Emit - Đẩy văn bản đã làm sạch tuyệt đối vào trường 'text', gán trạng thái kết thúc và phát StandardFrame lên Bus.
    ======================================================================
    """
IV. STRICT LAWS FOR AI INTEGRATION (ĐIỀU KHOẢN CẤM)
TUYỆT ĐỐI KHÔNG tự ý sinh thêm field tùy biến bên ngoài cấu trúc 8 trường quy định của BodyFrame.

CẤM hiển thị văn bản thô chưa qua bộ lọc của Service trong trường text đầu ra của Node này. Trường text tại đây là bộ lọc tối cao trước khi Gateway đẩy về màn hình của khách hàng.

CẤM sử dụng lệnh raise để báo lỗi vi phạm an toàn. Nếu nội dung vi phạm chính sách bảo mật, Adapter phải có nghĩa vụ chuyển đổi trạng thái thành "FAILED", gán chuỗi thông báo lỗi nghiệp vụ vào text (ví dụ: "Nội dung không thể hiển thị vì lý do bảo mật"), điền thông tin hệ thống vào error và đẩy lên Bus qua StandardFrame.emit để đồ thị kết thúc một cách trọn vẹn.