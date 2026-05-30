ARCHITECTURAL SPECIFICATION DOCUMENT
MODULE: node_lightweight_chat (Edge Execution & Low-Latency Streaming Plane)
Lưu ý định danh: Tên chính thức của Node này trong hệ thống Mainboard là node_lightweight_chat. Đây là một Node thực thi chuyên biệt thuộc Edge Execution Plane, được thiết kế riêng để xử lý các phản hồi nhanh, hội thoại ngắn (Smalltalk), câu hỏi xã giao, hoặc các tác vụ có độ phức tạp thấp mà không cần đi qua tầng điều phối nặng node_supervisor.

I. BUSINESS OVERVIEW & INTENT
Trong các hệ thống Multi-Agent công nghiệp, việc đẩy mọi tin nhắn của người dùng qua Control Plane (node_supervisor) chạy các mô hình High-IQ (như Claude 3.5 Sonnet / Gemini 1.5 Pro) gây ra hai điểm nghẽn nghiêm trọng: Độ trễ phản hồi lớn (High Latency) và Chi phí Token cực kỳ lãng phí đối với các câu thoại đơn giản (ví dụ: "Chào bạn", "Bạn là ai?", "Cảm ơn nhé").

node_lightweight_chat giải quyết triệt để bài toán này với 3 nhiệm vụ cốt lõi:

Fast-Track Smalltalk Processing: Tách luồng xử lý siêu tốc cho các hội thoại xã giao, chào hỏi bằng cách sử dụng các dòng LLM siêu nhẹ (Edge/Fast Models như Claude 3.5 Haiku / GPT-4o-mini / Gemini 1.5 Flash).

Ultra-Low Latency Response: Triệt tiêu hoàn toàn thời gian suy luận rẽ nhánh của đồ thị, tối ưu hóa thuật toán Prompting tối giản để tăng tốc độ phản hồi chặng đầu (Time-to-First-Token).

Context Maintenance: Đảm bảo dù xử lý ở luồng "nhanh", Agent vẫn ghi nhận đầy đủ lịch sử hội thoại cận kề và Profile cơ bản của người dùng để đưa ra câu trả lời tự nhiên, mượt mà mà không làm đứt gãy mạch trải nghiệm.

II. COMPONENT FILES SPECIFICATION
1. Core Contract (lightweight_chat_protocol.py)
Định nghĩa giao ước dữ liệu đầu ra bất biến của luồng phản hồi nhanh.

Tiêu chuẩn kỹ thuật: Sử dụng Pydantic v2, cấu hình ConfigDict(frozen=True, extra="ignore").

Cấu trúc Object: LightweightChatResult

chat_response (str): Nội dung câu trả lời nhanh đã được tối ưu hóa văn phong.

is_fallback_required (bool): Cờ hiệu báo động nếu câu hỏi của user bất ngờ leo thang độ phức tạp, cần đẩy ngược lại luồng Supervisor xử lý (True nếu cần leo thang).

detected_sentiment (str): Phân tích sắc thái nhanh của cuộc hội thoại ngắn ("positive", "neutral", "negative").

2. Pure Domain Execution (lightweight_chat_service.py)
Chứa đựng hệ thống System Prompt tối giản, loại bỏ hoàn toàn các cấu trúc lập luận phức tạp (CoT). Gọi API LLM thông qua cơ chế Structured Outputs để ép cấu trúc dữ liệu đầu ra.

Tiêu chuẩn kỹ thuật: class LightweightChatService với hàm xử lý bất đồng bộ async def execute(self, fresh_message: str, chat_history: list, user_profile: dict, llm_engine: Any) -> LightweightChatResult.

Logic thực thi nội bộ:

Nhúng cấu trúc Profile rút gọn của khách hàng và lịch sử 3 câu thoại gần nhất.

Sử dụng System Prompt quy định rõ: “Bạn là trợ lý phản hồi nhanh. Hãy trả lời ngắn gọn dưới 3 câu, giữ Tone & Style thân thiện. Nếu câu hỏi yêu cầu tính toán, tra cứu tri thức sâu hoặc nghiệp vụ phức tạp, hãy gán is_fallback_required=True.”

Gọi llm_engine.with_structured_output(LightweightChatResult) để thu về kết quả đóng băng.

3. Mainboard Gatekeeper (adapter_lightweight_chat.py)
Điểm nút giao thông đấu nối vào đồ thị. Node này thường được kích hoạt dựa trên kết quả phân loại ý định nhanh từ cổng vào hoặc từ Conditional Edge phân phối sớm.

Tiêu chuẩn kỹ thuật: Hàm xử lý đồ thị async def node_lightweight_chat(state: MainBus, config: RunnableConfig = None) -> dict.

Tuân thủ Safe Post-Guard (Chống sập Đồ thị):

Kiểm tra tính hợp lệ của dữ liệu đầu vào trên MainBus (yêu cầu phải có tin nhắn mới nhất của User).

Nếu tin nhắn thô trống hoặc Node đầu nguồn gặp lỗi, áp dụng Hạ cánh an toàn (Graceful Recovery): Gán status="FAILED", đẩy trực tiếp một thông điệp chào hỏi mặc định hệ thống vào trường text, ghi nhận log lỗi kỹ thuật vào error và phát đi qua StandardFrame.emit. Không dùng câu lệnh raise.

Dependency Injection & Context Extraction: Gọi await get_ctx() để lấy Fast Model Engine (ctx.llm_factory.get_model("default_fast")). Trích xuất an toàn user_profile và lịch sử hội thoại bằng toán tử chấm (.).

BodyFrame Schema Mapping (Strict Constraint): Đóng gói dữ liệu ra Bus qua đúng 8 trường phẳng quy chuẩn của BodyFrame:

status: "SUCCESS" nếu LLM phản hồi thành công, hoặc "FAILED" nếu gặp sự cố kết nối API.

text: SẢN PHẨM PHẢN HỒI - Lưu trữ toàn bộ chuỗi nội dung câu trả lời nhanh (chat_response). Trường này sẽ được chuyển tiếp thẳng sang Output Guard để xuất xưởng trả về cho User.

records: Không xử lý (để trống).

entities: Không xử lý (để trống).

state: Lưu trạng thái runtime phục vụ rẽ nhánh khẩn cấp nếu phát hiện câu hỏi quá khó: {"process_completed": not result.is_fallback_required, "escalate_to_supervisor": result.is_fallback_required}.

metrics: Lưu thông số phân tích sắc thái hệ thống: {"sentiment": result.detected_sentiment}.

context: Không xử lý (để trống).

error: Chuỗi thông báo lỗi chi tiết nếu status == "FAILED".

III. CERTIFIED WORKFLOW DOCSTRING TEMPLATE
Mã nguồn hàm Adapter của Lightweight Chat bắt buộc phải đính kèm Docstring chuẩn hóa sau:

Python
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [node_lightweight_chat]
    ======================================================================
    [BUSINESS INTENT]
    Xử lý phản hồi siêu tốc cho các hội thoại ngắn, xã giao (Smalltalk) thuộc 
    Edge Execution Plane. Tối ưu hóa chi phí token và hạ tầng bằng cách cô lập 
    luồng xử lý trên dòng máy LLM cấu hình thấp, bỏ qua tầng điều phối nặng.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard - Xác thực sự tồn tại của tin nhắn người dùng trên mạng Bus. Chuyển hóa lỗi cấu trúc đầu vào thành câu chào mặc định thay vì crash đồ thị.
    - Step 2: Context Extraction & DI - Bóc tách lịch sử hội thoại cận kề, hồ sơ người dùng qua toán tử chấm (.) và cấu hình Fast LLM Engine từ Container.
    - Step 3: Pure Domain Execution - Gọi LightweightChatService, ép cấu trúc đầu ra qua LLM để nhận về kết quả phản hồi và cờ hiệu leo thang Pydantic đóng băng.
    - Step 4: Status Normalization & Bus Emit - Đẩy thẳng câu trả lời vào trường 'text', thiết lập cờ rẽ nhánh 'escalate_to_supervisor' và phát sóng lên Bus.
    ======================================================================
    """
IV. STRICT LAWS FOR AI INTEGRATION (ĐIỀU KHOẢN CẤM)
TUYỆT ĐỐI KHÔNG tự ý tạo thêm field tùy biến bên ngoài cấu trúc 8 trường quy định của BodyFrame.

CẤM sử dụng các dòng mô hình High-IQ (Sonnet, Pro, GPT-4) trong node này. Node này được sinh ra với mục đích tối thượng là tiết kiệm chi phí và hạ Latency, bắt buộc phải dùng dòng máy Fast/Flash.

CẤM sử dụng lệnh raise. Nếu API LLM bị nghẽn mạng hoặc Timeout, Adapter bắt buộc phải tự động bắt ngoại lệ (Catch Exception), chuyển trạng thái status="FAILED", gán chuỗi hội thoại mặc định (Fallback text) ra Bus và phát đi bằng StandardFrame.emit để kết thúc đồ thị an toàn.