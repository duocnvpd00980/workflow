ARCHITECTURAL SPECIFICATION DOCUMENT
MODULE: node_shared_state (Cross-Graph Sync, Ephemeral Memory & Synchronization Plane)
Lưu ý định danh: Tên chính thức của Node này trong hệ thống Mainboard là node_shared_state. Đây không phải là một Node chạy LLM mà là một Infrastructure Node (Node Hạ tầng) thuộc Synchronization Plane, chịu trách nhiệm đồng bộ, hợp nhất trạng thái phiên và ghi nhận dữ liệu chéo giữa các Đồ thị con (Sub-Graphs) hoặc giữa các Task bất đồng bộ chạy song song.

I. BUSINESS OVERVIEW & INTENT
Trong một hệ thống Multi-Agent lớn vận hành bằng LangGraph, các luồng xử lý thường bị rẽ nhánh song song (Parallel Forking) hoặc gọi chéo sang các đồ thị con (Sub-Graph Invocation). Điều này dẫn đến hiện tượng Phân rã ngữ cảnh (Context Isolation) — khi một nhánh Agent cập nhật dữ liệu nhưng nhánh khác không hề hay biết.

node_shared_state ra đời để giải quyết triệt để bài toán này với 3 nhiệm vụ cốt lõi:

State Consolidation (Hợp nhất trạng thái): Đóng vai trò là điểm hội tụ (Join Node) sau các tác vụ chạy song song để thu thập, giải quyết xung đột (Conflict Resolution) và hợp nhất dữ liệu từ các nhánh về lại mạng Bus chính (MainBus).

Cross-Graph Bridging (Cầu nối liên đồ thị): Đọc/Ghi các biến trạng thái dùng chung (Shared States) ra kho lưu trữ phân tán (Redis/Distributed Cache) để các Đồ thị khác chạy song song trên hệ thống có thể truy cập tức thì.

Dynamic Feature Flagging: Cập nhật các biến trạng thái runtime (Ví dụ: is_human_needed, emergency_stop_triggered) dựa trên hành vi tổng hợp của các node trước đó, thiết lập điều kiện tiên quyết cho Control Plane đưa ra quyết định ở chu kỳ sau.

II. COMPONENT FILES SPECIFICATION
1. Core Contract (shared_state_protocol.py)
Định nghĩa giao ước dữ liệu bất biến, quản lý cấu trúc của các biến trạng thái dùng chung một cách nghiêm ngặt nhằm tránh race condition (xung đột ghi dữ liệu).

Tiêu chuẩn kỹ thuật: Sử dụng Pydantic v2, cấu hình ConfigDict(frozen=True, extra="ignore").

Cấu trúc Object: SharedStateSyncResult

synchronized_data (dict): Toàn bộ key-value sau khi đã được hợp nhất và giải quyết xung đột.

modified_keys (list[str]): Danh sách các khóa dữ liệu vừa có sự thay đổi trong phiên chạy này.

sync_timestamp (float): Thời gian thực hiện đồng bộ (Unix timestamp).

requires_immediate_routing (bool): Cờ hiệu báo cho Supervisor biết trạng thái hệ thống đã thay đổi đột ngột, cần tái điều hướng luồng ngay lập tức.

2. Pure Domain Execution (shared_state_service.py)
Chứa đựng logic cơ sở dữ liệu và thuật toán hợp nhất (Merge Algorithm) thuần túy. Hoàn toàn Deterministic (Code thuần, tuyệt đối không gọi LLM để tối ưu Latency < 5ms).

Tiêu chuẩn kỹ thuật: class SharedStateService với hàm xử lý bất đồng bộ async def merge_and_broadcast(self, current_bus_data: dict, external_cache_data: dict, merge_strategy: str = "latest_wins") -> SharedStateSyncResult.

Logic thực thi nội bộ:

So sánh các trường dữ liệu trùng lặp giữa Bus hiện tại và Cache phân tán.

Áp dụng chiến lược giải quyết xung đột: latest_wins (dựa trên timestamp) hoặc deep_merge (hợp nhất các mảng list/dict mà không ghi đè).

Xác định xem có khóa nào critical bị thay đổi (ví dụ: người dùng đổi ý định đột ngột giữa luồng xử lý song song) để kích hoạt requires_immediate_routing=True.

Trả về SharedStateSyncResult đóng băng.

3. Mainboard Gatekeeper (adapter_shared_state.py)
Điểm nút hạ tầng đấu nối trực tiếp vào đồ thị LangGraph. Thường nằm ở vị trí Join Node (sau khi Parallel Steps kết thúc) hoặc vị trí Interceptor trước khi gọi Sub-Graph.

Tiêu chuẩn kỹ thuật: Hàm xử lý đồ thị async def node_shared_state(state: MainBus, config: RunnableConfig = None) -> dict.

Tuân thủ Safe Post-Guard (Chống sập Đồ thị):

Vì đây là Node hạ tầng nhận dữ liệu tổng hợp, nó phải kiểm tra trạng thái của tất cả các nhánh song song đổ về (ví dụ: kiểm tra xem cả hai nhánh node_knowledge và node_marketing chạy song song có nhánh nào phát trạng thái "FAILED" không).

Nếu một trong các nhánh thượng nguồn bị sập, Adapter thực hiện Hạ cánh an toàn (Graceful Isolation): Không raise lỗi. Lấy phần dữ liệu của nhánh chạy thành công, đánh dấu trạng thái tổng hợp trên Bus là "SUCCESS" nhưng ghi nhận cảnh báo vào context, đảm bảo đồ thị tiếp tục chạy mà không bị nghẽn mạch (Deadlock).

Dependency Injection & Context Extraction: Gọi await get_ctx() để lấy Client kết nối Redis/Cache (ctx.storage.redis). Bóc tách toàn bộ state hiện tại trên MainBus.

BodyFrame Schema Mapping (Strict Constraint): Đóng gói dữ liệu ra Bus qua đúng 8 trường phẳng quy chuẩn của BodyFrame:

status: "SUCCESS" nếu quá trình hợp nhất và đồng bộ dữ liệu với kho lưu trữ phân tán hoàn tất, hoặc "FAILED" nếu gặp sự cố kết nối hạ tầng (Database/Redis Timeout).

text: Chuỗi JSON hoặc thông điệp trạng thái hệ thống sau khi hợp nhất (Ví dụ: "State consolidated successfully").

records: Lưu trữ danh sách các khóa dữ liệu bị thay đổi: {"modified_keys": result.modified_keys}.

entities: Không xử lý (để trống).

state: TRỌNG TÂM CỦA NODE - Ghi đè hoặc bổ sung trực tiếp các trạng thái runtime phẳng sau khi đã hợp nhất vào state để các Node phía sau (đặc biệt là Supervisor) đọc trực tiếp: {"is_state_mutated": True, "force_re_route": result.requires_immediate_routing}.

metrics: Lưu thông số vận hành {"sync_latency_ms": ...}.

context: Lưu trữ toàn bộ bản đồ dữ liệu sau khi đồng bộ result.synchronized_data làm Single Source of Truth cho context chung.

error: Chuỗi thông báo lỗi kỹ thuật chi tiết nếu status == "FAILED".

III. CERTIFIED WORKFLOW DOCSTRING TEMPLATE
Mã nguồn hàm Adapter của Shared State bắt buộc phải đính kèm Docstring chuẩn hóa sau:

Python
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [node_shared_state]
    ======================================================================
    [BUSINESS INTENT]
    Node hạ tầng thuộc Synchronization Plane. Chịu trách nhiệm tập hợp trạng thái 
    từ các nhánh chạy song song, giải quyết xung đột dữ liệu (Conflict Resolution), 
    đồng bộ với bộ nhớ đệm phân tán và cập nhật cờ hiệu điều hướng cho Supervisor.

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard - Kiểm tra trạng thái của toàn bộ các node thượng nguồn đổ về điểm hội tụ. Cô lập các nhánh lỗi để bảo vệ mạch đồ thị chạy liên tục.
    - Step 2: Context Extraction & DI - Trích xuất dữ liệu runtime từ Bus và Inject Redis/Cache Storage Client từ bộ khung Container hệ thống.
    - Step 3: Pure Domain Execution - Gọi SharedStateService thực hiện thuật toán hợp nhất dữ liệu Deterministic (Code thuần), tạo ra Pydantic Object đóng băng.
    - Step 4: Status Normalization & Bus Emit - Cập nhật các cờ hiệu trạng thái phẳng vào trường 'state', đồng bộ dữ liệu vào 'context' và phát ra mạng Bus.
    ======================================================================
    """
IV. STRICT LAWS FOR AI INTEGRATION (ĐIỀU KHOẢN CẤM)
TUYỆT ĐỐI NGHIÊM CẤM gọi bất kỳ API LLM nào trong Node này. Toàn bộ logic bắt buộc phải xử lý bằng Code thuần (Deterministic) để đảm bảo tốc độ tối đa và tính toàn vẹn tuyệt đối của dữ liệu hệ thống.

CẤM lưu trữ các object phức tạp, lồng nhau (Nested Objects) vào trường state. Mọi biến cờ hiệu dùng để rẽ nhánh đồ thị (như force_re_route) phải được làm phẳng (Flat structure) ngay tại cấp đầu tiên của state.

CẤM dùng lệnh raise khi gặp lỗi kết nối Redis/Database. Nếu hạ tầng lưu trữ gặp sự cố, Adapter phải bắt ngoại lệ, gán status="FAILED", chuyển sang cơ chế fallback (chỉ sử dụng dữ liệu local hiện tại trên Bus), ghi log lỗi vào error và dùng StandardFrame.emit để đẩy gói tin đi tiếp, không được phép làm treo đồ thị (Thread Deadlock).