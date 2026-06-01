# BẢN ĐẶC TẢ KIẾN TRÚC HỆ THỐNG MARKETING CREW (SYSTEM ARCHITECTURE SPECIFICATION)

Tài liệu này định hình triết lý thiết kế, cấu trúc phần cứng phần mềm, và quy chuẩn lập trình bắt buộc cho toàn bộ hệ thống. Mọi kỹ sư và AI khi tham gia phát triển, nâng cấp hoặc thêm mới các Node vào bo mạch hệ thống đều phải tuân thủ nghiêm ngặt cẩm nang này.

---

## I. TRIẾT LÝ BO MẠCH CHÍNH (THE MAINBOARD PHILOSOPHY)

Hệ thống được thiết kế dựa trên tư duy **Ports & Adapters (Kiến trúc Lục giác / Lập trình nhúng)** để đạt mức độ cô lập tuyệt đối giữa hạ tầng điều phối (Framework) và logic nghiệp vụ (Domain Services).

### 1. Trục MainBus Trung Tâm
* **`MainBus`** đóng vai trò như một bảng mạch/thanh ghi tĩnh (State) lưu trữ trạng thái của hệ thống.
* Các Node không được phép can thiệp, chỉnh sửa dữ liệu trực tiếp của nhau một cách tùy tiện mà phải thông qua cơ chế đọc/ghi có kiểm soát.

### 2. Định Danh Vùng Nhớ (`BusRegistry`)
* Mỗi linh kiện gắn lên bo mạch bắt buộc phải đăng ký một địa chỉ vùng nhớ duy nhất tại `BusRegistry` dưới dạng hằng số (ví dụ: `BusRegistry.GK` cho Gatekeeper, `BusRegistry.AD` cho Ads, `BusRegistry.DAR` cho Dynamic Agent Router).

### 3. Khung Tín Hiệu Tiêu Chuẩn (`StandardFrame`)
* Dữ liệu trả về từ các Node bắt buộc phải được đóng gói vào `StandardFrame` thông qua lệnh `StandardFrame.emit(registry_key, payload)`. Khung này đảm bảo tính nhất quán dữ liệu trước khi phóng tín hiệu trả lại trục Bus chính.

---

## II. MẠCH ĐỊNH TUYẾN ĐỘNG TRÊN BUS (DYNAMIC ROUTING CORE)

Thay vì sử dụng các bộ chia luồng thụ động, nhánh xử lý Marketing được điều khiển bởi cặp bài trùng "Bộ cấp phép" và "Rơ-le kỹ thuật số" để tối ưu hiệu năng.

```text
[ USER INPUT ] ──► [ Intent Classifier ] ──► [ Policy Engine (Planner) ]
                                                    │ (Cấu hình switch On/Off)
                                                    ▼
                                      [ Dynamic Agent Router (Rơ-le) ]
                                                    │
                  ┌─────────────────────────────────┼─────────────────────────────────┐
           (run_ads = True)                 (run_email = False)               (run_blog = True)
                  │                                 │                                 │
                  ▼                                 ▼                                 ▼
           [ node_reg_ads ]                      (SKIP)                     [ node_reg_blog_plan ]


1. PolicyEngine (Bộ cấp phép & Lập kế hoạch - Planner)
Nhiệm vụ: Đọc dữ liệu đầu vào và phân tích ý định (Intent).

Đầu ra: Xuất ra các cờ switch logic rời rạc dạng Boolean độc lập (run_ads, run_email, run_blog) nằm trong vùng nhớ BusRegistry.POE. Thằng này chịu trách nhiệm về mặt quyết định chiến lược.

2. DynamicAgentRouter (Bộ định tuyến Agent động - Router)
Nhiệm vụ: Đóng vai trò là một Rơ-le điện tử chủ động đứng phân phối dòng luồng dữ liệu.

Cơ chế: Đọc cấu hình từ thanh ghi POE. Nếu cờ của Agent nào là True, nó nạp địa chỉ Node đó vào mảng kích hoạt (activated_channels), nếu False thì sẽ bỏ qua (skip). Thằng này chịu trách nhiệm về mặt thực thi đóng ngắt mạch.

## III. MÀNG BẢO VỆ VÀ TRẠM GIÁM SÁT NĂNG LƯỢNG TỔNG (SHIELDS & TELEMETRY)
Mọi Node khi gắn lên bo mạch (mainboard.py) đều được bọc qua lớp vỏ bảo vệ thông qua cú pháp:
VA = Node(BusRegistry.VA, node_VALIDATOR).shield().retry(AI_RETRY).mount(board)

1. Trách Nhiệm Của Tầng Bảo Vệ (run_shielded.py)
Tầng Shield đóng vai trò như một Middleware (Tầng trung gian) xử lý tập trung các tác vụ hạ tầng mang tính lặp lại (Cross-Cutting Concerns):

Bọc giáp Cô lập lỗi (.shield()): Kích hoạt bộ chặn pre_guard và post_guard để rà soát dữ liệu đầu vào/đầu ra, ngăn chặn lỗi logic tầng dưới làm sập toàn bộ hệ thống đồ thị LangGraph.

Cầu chì Thời gian (Timeout): Ép khống chế thời gian chạy của Node tối đa là 60 giây (NODE_TIMEOUT_SECONDS). Vượt quá thời gian này, rơ-le tự động ngắt mạch, quăng lỗi PipelineError để giải phóng tài nguyên.

Watchdog tự hồi phục (.retry(AI_RETRY)): Sử dụng RetryPolicy với cấu hình giãn cách thời gian (backoff_factor=1.5, thử lại tối đa 2 lần) khi bắt được lỗi PipelineError nhằm tự động nạp lại dòng điện cho Agent chạy lại từ đầu.

2. Cơ Chế Bấm Giờ & Đếm Tiền Tập Trung (Telemetry Enrichment)
Để tránh trùng lặp mã nguồn (Boilerplate code) tại các Node, logic Telemetry được xử lý tuyệt đối tập trung tại tầng Shield:

Đo độ trễ (Latency): Shield đứng ngoài bấm giờ từ lúc Node bắt đầu chạy cho đến khi kết thúc (kể cả khi Node bị sập văng lỗi) để đo chính xác latency_ms.

Tính tiền động (Dynamic Cost Calculation): * Shield rà soát payload của Adapter gửi lên. Nếu không thấy trường usage, nó tự hiểu đây là Node code logic thuần (Router, Policy Engine) và ghi nhận Cost = $0.

Nếu thấy trường usage, nó sẽ bốc số Token tiêu thụ, kết hợp với trường model (GPT-4o, Claude, Gemini...) do Adapter khai báo để tra cứu bảng giá MODEL_PRICING và tự động quy đổi ra chi phí USD (cost_usd).

IV. QUY CHUẨN THIẾT KẾ MODULE: PHÂN TÁCH 3 FILE - 3 STYLE
Để hệ thống vận hành trơn tru và dễ bảo trì, mỗi Node khi tạo mới bắt buộc phải tách biệt thành 3 file độc lập với 3 phong cách viết code khác nhau:

1. *_protocol.py (Style: Strict Declarative)
Nhiệm vụ: Định hình hợp đồng dữ liệu đầu ra bằng Pydantic Model sạch.

Quy tắc: Sử dụng ConfigDict(frozen=True, extra="ignore") để khóa cứng cấu trúc dữ liệu, chống tràn hoặc nhiễu tín hiệu rác từ bên ngoài. Tuyệt đối không nhét các biến hệ thống như usage hay latency vào mô hình nghiệp vụ sạch này.

2. *_service.py (Style: Pure Algorithmic)
Nhiệm vụ: Tập trung 100% vào logic nghiệp vụ và tối ưu Prompt cho LLM.

Quy tắc: Đây là khối mạch "ngây thơ". Cấm import LangGraph, cấm import MainBus hay BusRegistry. Nhận tham số vào một cách minh bạch (Explicit) và trả dữ liệu ra dạng Python nguyên thủy hoặc Object nghiệp vụ. Áp dụng pattern Dependency Injection (Bơm phụ thuộc) để nhận cấu hình LLM Engine từ tầng Adapter chuyển xuống.

3. adapter_*.py (Style: Peripheral I/O)
Nhiệm vụ: Đóng vai trò là "Driver" điều phối dòng điện dữ liệu.

Quy tắc: 1. Đọc và trích xuất dữ liệu an toàn từ MainBus.
2. Bơm các tham số thô đó vào cho Service thực thi.
3. Hứng kết quả nghiệp vụ từ Service, đồng thời trích xuất thông tin usage và tên model thực tế từ bộ thư viện mạng (instructor/litellm).
4. Đóng gói toàn bộ thông tin nghiệp vụ + thông tin hệ thống (usage, model) vào Payload của StandardFrame.
5. Gọi lệnh StandardFrame.emit() để phát tín hiệu dữ liệu hoàn chỉnh lên Bus chính.

Bản đặc tả cấu trúc hoàn thành. Mọi thiết kế nâng cấp bo mạch tiếp theo bắt buộc phải tuân theo khung kiến trúc này.








### 💡 Gợi ý mẹo dùng Prompt này cho AI khác:
Khi bạn gửi bản đặc tả này cho một AI mới (hoặc kỹ sư mới), bạn chỉ cần viết thêm câu lệnh mồi: 
> *"Dưới đây là bản đặc tả kiến trúc hệ thống của tôi. Hãy đọc kỹ triết lý Mainboard, cơ chế Shield, Telemetry và quy chuẩn 3 File - 3 Style. Bây giờ, hãy viết cho tôi một Node mới có tên là `node_reg_content_writer` tuân thủ đúng 100% kiến trúc trên."*

AI nhận lệnh sẽ ngay lập tức tự động code chuẩn chỉ, chia đúng 3 file, cấu hình đúng Payload, nạp đúng thông tin `usage` cho Shield mà bạn không cần phải giải thích lại từ đầu!