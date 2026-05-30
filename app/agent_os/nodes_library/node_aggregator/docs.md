ARCHITECTURAL SPECIFICATION DOCUMENT
MODULE: node_aggregator (Response Synthesis & Final Assembly)
I. BUSINESS OVERVIEW & INTENT
node_aggregator đóng vai trò là Tầng Tổng hợp và Đóng gói Thành phẩm (Response Synthesis Plane) của hệ thống Multi-Agent. Sau khi bản thảo đã vượt qua chốt chặn khắt khe của node_evaluator, Node này sẽ nhận trách nhiệm:

Sáp nhập & Đánh bóng (Polishing): Tập hợp các phần nội dung đã xử lý từ các Agent chuyên biệt, xử lý chuyển cú pháp, làm mượt văn phong và đảm bảo tính nhất quán từ đầu đến cuối.

Cá nhân hóa chặng cuối (Final Personalization): Áp dụng trực tiếp bộ khung định danh, định dạng UI (Markdown/HTML) phù hợp nhất với hành vi đọc của người dùng dựa trên user_profile đã nạp, tạo ra câu trả lời hoàn thiện nhất trước khi xuất xưởng ra môi trường Output bên ngoài.

II. COMPONENT FILES SPECIFICATION
1. Core Contract (aggregator_protocol.py)
Định nghĩa giao ước dữ liệu đầu ra bất biến của chặng cuối đồ thị, sẵn sàng bàn giao cho các Gateway bên ngoài hệ thống.

Tiêu chuẩn kỹ thuật: Sử dụng Pydantic v2, cấu hình ConfigDict(frozen=True, extra="ignore").

Cấu trúc Object: AggregationResult

final_response (str): Nội dung câu trả lời hoàn chỉnh cuối cùng đã được tối ưu định dạng Markdown.

summary_of_changes (str): Tóm tắt ngắn gọn các bước xử lý hoặc điều chỉnh nội dung (nếu có).

metadata (dict): Ghi nhận thông tin bổ sung phục vụ cho tầng hiển thị UI hoặc Tracking Analytics.

2. Pure Domain Execution (aggregator_service.py)
Chứa đựng logic nghiệp vụ hòa trộn dữ liệu. Sử dụng mô hình ngôn ngữ tối ưu về xử lý văn bản quy mô lớn (Vừa đảm bảo tốc độ vừa có tư duy ngữ pháp tốt như Claude 3.5 Haiku hoặc GPT-4o).

Tiêu chuẩn kỹ thuật: class AggregatorService chứa hàm xử lý bất đồng bộ async def execute(self, original_query: str, certified_drafts: list[dict], user_profile: dict, llm_engine: Any) -> AggregationResult.

Logic thực thi nội bộ:

Xây dựng prompt tổng hợp hướng dẫn LLM đóng vai trò là một "Biên tập viên xuất sắc (Chief Editor)".

Thu gom toàn bộ các mảnh dữ liệu đã được chứng thực (Certified Drafts) từ mạng Bus.

Hòa trộn chúng theo mạch logic của original_query, loại bỏ các thông tin trùng lặp, xử lý các đoạn chuyển dòng và định dạng hiển thị đẹp mắt theo cấu hình ưa thích lưu ở user_profile.

Ép cấu trúc đầu ra qua llm_engine.with_structured_output(AggregationResult).

3. Mainboard Gatekeeper (adapter_aggregator.py)
Điểm kết thúc nghiệp vụ xử lý của đồ thị LangGraph, thực hiện tổng hợp dữ liệu từ Bus mạng và đóng gói thành phẩm.

Tiêu chuẩn kỹ thuật: Hàm xử lý đồ thị async def node_aggregator(state: MainBus, config: RunnableConfig = None) -> dict.

Tuân thủ Safe Post-Guard (Chống sập Đồ thị):

Kiểm tra tính toàn vẹn của Node đứng trước (BusRegistry.EVALUATOR). Đảm bảo trạng thái của Evaluator là "SUCCESS" và có cờ hiệu next_action == "pass".

Nếu phát hiện luồng đi sai logic hoặc Evaluator bị sập ngầm, lập tức thực hiện Hạ cánh an toàn (Graceful Degradation): Gán status="FAILED", đẩy trực tiếp yêu cầu gốc của User sang trường text (để tránh User nhìn thấy màn hình trắng), ghi nhận mã lỗi nghiêm trọng vào error, và phát đi qua StandardFrame.emit để kết thúc đồ thị an toàn mà không sập luồng. CẤM dùng lệnh raise.

Dependency Injection & Context Extraction: Gọi await get_ctx() để lấy LLM Engine từ Container. Dùng toán tử chấm (.) trích xuất an toàn toàn bộ dữ liệu bản thảo sạch từ mạng Bus.

BodyFrame Schema Mapping (Strict Constraint): Đóng gói dữ liệu ra Bus qua đúng 8 trường phẳng quy chuẩn của BodyFrame:

status: "SUCCESS" nếu quá trình biên tập hoàn tất tốt đẹp, hoặc "FAILED" nếu gặp lỗi hệ thống chặng cuối.

text: ĐÂY CHÍNH LÀ SẢN PHẨM CUỐI CÙNG - Lưu trữ toàn bộ chuỗi nội dung văn bản hoàn chỉnh (final_response) để trả thẳng về ứng dụng khách (UI/Client).

records: Không xử lý (để trống).

entities: Không xử lý (để trống).

state: Đặt trạng thái runtime báo hiệu đồ thị kết thúc: {"process_completed": True, "next_action": "end"}.

metrics: Lưu trữ metadata xử lý chặng cuối: {"summary": result.summary_of_changes}.

context: Lưu trữ các thông tin cấu hình hiển thị bổ sung: {"ui_metadata": result.metadata}.

error: Chuỗi thông báo lỗi chi tiết nếu status == "FAILED".

III. CERTIFIED WORKFLOW DOCSTRING TEMPLATE
Mã nguồn hàm Adapter của Aggregator bắt buộc phải đính kèm Docstring chuẩn hóa sau:

Python
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [node_aggregator]
    ======================================================================
    [BUSINESS INTENT]
    Đóng vai trò là Tổng biên tập (Response Synthesis Plane) đóng gói chặng cuối. 
    Hòa trộn, làm mượt các bản thảo thô đã đạt chuẩn chất lượng và áp dụng định dạng 
    cá nhân hóa (Markdown) tối ưu trước khi xuất bản thành phẩm cho Client.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard - Xác định phán quyết đạt chuẩn (Pass) từ Evaluator thượng nguồn. Chuyển hóa lỗi logic thành gói tin kết thúc an toàn thay vì gây crash ứng dụng.
    - Step 2: Context Extraction & DI - Trích xuất tập hợp các bản thảo sạch và Hồ sơ người dùng từ Bus qua toán tử chấm (.) và cấu hình Editor LLM Engine.
    - Step 3: Pure Domain Execution - Gọi AggregatorService để tinh chỉnh và định dạng văn bản chuyên nghiệp, trả về Pydantic Object đóng băng.
    - Step 4: Status Normalization & Bus Emit - Đưa sản phẩm cuối cùng vào trường 'text' của BodyFrame, gán trạng thái kết thúc luồng và phát sóng lên Bus.
    ======================================================================
    """
IV. STRICT LAWS FOR AI INTEGRATION (ĐIỀU KHOẢN CẤM)
TUYỆT ĐỐI KHÔNG tự ý sinh thêm trường dữ liệu nằm ngoài cấu trúc 8 trường quy định của BodyFrame.

CẤM đặt sản phẩm hoàn thiện ở bất kỳ trường nào khác ngoài trường text. Trường text của Node này chính là Single Source of Truth duy nhất mà API Gateway sẽ bóc tách để Stream về cho phía Giao diện người dùng (Frontend).

CẤM sử dụng lệnh raise. Bất kỳ lỗi phát sinh nào ở bước biên tập này đều phải được chuyển hóa thành trạng thái ứng xử an toàn (giao diện fallback) để bảo đảm trải nghiệm người dùng không bị gián đoạn thô bạo.