ARCHITECTURAL SPECIFICATION DOCUMENT
MODULE: node_knowledge & node_marketing (Execution Plane - Specialized Agents)
I. BUSINESS OVERVIEW & INTENT
Các Node thuộc tầng Execution Plane (node_knowledge và node_marketing) là các Agent chuyên biệt đảm nhận nhiệm vụ xử lý tác vụ thực thi sâu. Chúng cô lập không gian hành vi (Action Space) để giải quyết một bài toán duy nhất theo chỉ thị từ Control Plane, giúp giảm thiểu hiện tượng loãng thông tin (Context Drift):

node_knowledge (Knowledge Agent): Tập trung tra cứu hệ thống tri thức, phân tích tài liệu và xử lý các vấn đề kỹ thuật hoặc thông tin chuyên sâu.

node_marketing (Marketing Agent): Tập trung sáng tạo nội dung, tối ưu hóa thông điệp truyền thông, áp dụng chính xác Tone & Style được cấu hình riêng theo từng Profile khách hàng.

II. COMPONENT FILES SPECIFICATION
1. Core Contract (specialized_agent_protocol.py)
Định nghĩa cấu trúc dữ liệu đầu ra đồng nhất và bất biến cho các tác vụ xử lý chuyên biệt thuộc Execution Plane.

Tiêu chuẩn kỹ thuật: Sử dụng Pydantic v2, cấu hình ConfigDict(frozen=True, extra="ignore").

Cấu trúc Object: AgentExecutionResult

raw_content (str): Bản thảo nội dung (Draft) thô do Agent sinh ra sau khi thực hiện tác vụ.

extracted_facts (list[str]): Danh sách các sự kiện hoặc thông tin quan trọng được bóc tách trong quá trình xử lý.

token_usage (dict[str, int]): Số liệu quan sát hệ thống (Observability Metrics) về lượng token tiêu thụ.

2. Pure Domain Execution (specialized_agent_service.py)
Chứa đựng logic nghiệp vụ của các Agent chuyên biệt. Sử dụng các mô hình ngôn ngữ nhỏ, tối ưu về tốc độ và chi phí (Fast/Cheap Model như Claude 3.5 Haiku / GPT-4o-mini).

Tiêu chuẩn kỹ thuật: class SpecializedAgentService chứa hàm xử lý bất đồng bộ async def execute(self, instruction: str, context_data: dict, llm_engine: Any) -> AgentExecutionResult.

Logic thực thi nội bộ:

Nhận chỉ thị (instruction) trực tiếp từ Supervisor luân chuyển trên hệ thống.

Trích xuất dữ liệu đặc thù từ context_data (Ví dụ: node_marketing đọc thói quen viết bài của user, node_knowledge đọc thông tin tri thức nền tảng).

Gọi API LLM để thực thi tác vụ chuyên biệt, đóng gói kết quả thu được vào Object AgentExecutionResult đóng băng.

3. Mainboard Gatekeeper (adapter_specialized_agent.py)
Điểm đấu nối trung gian, bóc tách chỉ thị từ Supervisor trên Bus và chuyển giao kết quả một cách an toàn tới tầng Evaluator kế tiếp.

Tiêu chuẩn kỹ thuật: Hàm xử lý đồ thị độc lập cho từng agent: async def node_knowledge(state: MainBus, config: RunnableConfig = None) -> dict và async def node_marketing(state: MainBus, config: RunnableConfig = None) -> dict.

Tuân thủ Safe Post-Guard (Chống sập Đồ thị):

Kiểm tra tính hợp lệ của thanh ghi quyết định từ Control Plane (BusRegistry.SUPERVISOR).

Nếu phát hiện Supervisor không tồn tại hoặc có trạng thái "FAILED", lập tức thực hiện Hạ cánh an toàn (Graceful Degradation): Đóng gói trạng thái "FAILED", gán chuỗi lỗi "Upstream Control Plane Defect: Missing or invalid Supervisor frame." vào trường error và đẩy lên Bus qua StandardFrame.emit. CẤM sử dụng lệnh raise làm đứng luồng LangGraph.

Dependency Injection & Context Extraction: Gọi await get_ctx() để lấy Fast Model Engine (ctx.llm_factory.get_model("default_fast")). Dùng toán tử chấm (.) trích xuất an toàn chuỗi chỉ thị state.reg_supervisor.payload.text và cấu trúc ngữ cảnh nền tảng từ Bus.

BodyFrame Schema Mapping (Strict Constraint): Đồng bộ hóa kết quả từ Service sang đúng 8 trường cố định của BodyFrame:

status: "SUCCESS" nếu tác vụ thực thi hoàn tất, hoặc "FAILED" nếu LLM gặp sự cố hoặc timeout.

text: Lưu trữ nội dung bản thảo thô vừa sinh ra (raw_content). Đây là Single Source of Truth cho các bước thẩm định phía sau.

records: Không xử lý (để trống).

entities: Lưu trữ danh sách các dữ kiện quan trọng bóc tách được {"facts": result.extracted_facts}.

state: Lưu trạng thái runtime phục vụ truy vết: {"agent_type": "MARKETING" / "KNOWLEDGE", "process_completed": True}.

metrics: Lưu thông số hệ thống {"tokens": result.token_usage}.

context: Lưu trữ dữ liệu cấu hình hoặc metadata được dùng để chạy prompt.

error: Chuỗi thông báo lỗi chi tiết nếu status == "FAILED".

III. CERTIFIED WORKFLOW DOCSTRING TEMPLATE
Mã nguồn hàm Adapter của các Specialized Agents bắt buộc phải đính kèm Docstring chuẩn hóa sau:

Python
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [node_knowledge / node_marketing]
    ======================================================================
    [BUSINESS INTENT]
    Thực thi tác vụ chuyên biệt (Sáng tạo nội dung Marketing hoặc xử lý tri thức sâu) 
    theo chỉ thị cụ thể từ Supervisor bằng cách tối ưu hóa không gian hành vi trên các 
    dòng máy LLM hiệu năng cao, chi phí thấp.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard - Kiểm tra sự toàn vẹn và trạng thái SUCCESS của Supervisor Agent liền trước. Chuyển hóa lỗi điều phối lên Bus thay vì gây crash ứng dụng.
    - Step 2: Context Extraction & DI - Trích xuất chỉ thị ngôn ngữ tự nhiên từ Supervisor bằng toán tử chấm (.) và cấu hình Fast LLM Engine từ Container.
    - Step 3: Pure Domain Execution - Gọi SpecializedAgentService xử lý chuyên sâu, nhận về kết quả đóng thảo thô dưới dạng Pydantic Object đóng băng.
    - Step 4: Status Normalization & Bus Emit - Chuẩn hóa dữ liệu đầu ra về đúng cấu trúc phẳng BodyFrame và phát StandardFrame lên mạng Bus hệ thống.
    ======================================================================
    """
IV. STRICT LAWS FOR AI INTEGRATION (ĐIỀU KHOẢN CẤM)
TUYỆT ĐỐI KHÔNG tự ý sinh thêm các field tùy biến bên ngoài cấu trúc 8 trường cốt lõi của BodyFrame.

CẤM sinh cấu trúc schema lồng nhau trong trường entities hay state. Dữ liệu bóc tách được phải được ép về định dạng phẳng (Flattened list/dict).

CẤM sử dụng lệnh raise để báo lỗi API LLM. Nếu kết nối mạng bị gián đoạn, Adapter bắt buộc phải bắt ngoại lệ (Exception Catching), chuyển hóa thành status="FAILED" kèm thông tin lỗi chi tiết trong trường error, phát ra Bus qua StandardFrame.emit để bảo toàn tính toàn vẹn của đồ thị LangGraph.