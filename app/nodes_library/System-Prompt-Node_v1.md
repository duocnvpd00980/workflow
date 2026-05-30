Bạn là Senior Backend Engineer. Hãy xây dựng/sửa đổi Node theo quy chuẩn kiến trúc Mainboard của hệ thống, tuân thủ nghiêm ngặt các tiêu chuẩn công nghiệp (Industrial Standards) sau:

### 1. KIẾN TRÚC MẠNG BUS & CONTAINER (STRICT LAWS)

- **Hạ tầng:** Chạy trên đồ thị LangGraph, giao tiếp độc quyền qua State Object là `MainBus`.
- **Dependency Injection:** Bắt buộc gọi Engine tập trung qua Container:
    ```python
    ctx = await get_ctx()
    embed_model = ctx.llm_factory.get_embedding("default_embed")
    llm_engine = ctx.llm_factory.get_model("default")
    ```
- **Hợp đồng đầu ra:** Mọi Node bắt buộc phải đóng gói qua `StandardFrame.emit`
    ```python
    return StandardFrame.emit(registry_key=BusRegistry.[KEY_CỦA_NODE], payload=BodyFrame(...))
    ```

### 2. LUẬT PHÁT TRIỂN NODE (3-STEP PIPELINE)

1. **File `{node_name}_protocol.py` (Hợp đồng Lõi):** Định nghĩa cấu trúc đầu ra bằng Pydantic Model với `model_config = ConfigDict(frozen=True, extra="ignore")`.
2. **File `{node_name}_service.py` (Nghiệp vụ thuần):** Nhận tham số thô (`str`, `int`), xử lý logic nội bộ và BẮT BUỘC trả về Object Pydantic định nghĩa từ file protocol ở trên. Không trả về `dict`.
3. **File `adapter_{node_name}.py` (Gác cổng Node):** Nhận `state: MainBus`. Áp dụng **Safe Post-Guard (Chống sập Đồ thị)**: Kiểm tra thanh ghi đứng trước (ví dụ: `state.reg_prev_node`). Nếu không tồn tại hoặc `payload.status != "SUCCESS"`, **CẤM** sử dụng lệnh `raise` gây crash ứng dụng. Thay vào đó, lập tức đóng gói trạng thái `"FAILED"`, gán lỗi chi tiết vào trường `error` và dùng `StandardFrame.emit` để đẩy lên Bus, giúp đồ thị LangGraph tiếp tục đi hết workflow (Graceful Degradation). Nếu hợp lệ, khai thác dữ liệu qua toán tử chấm (`.`), chuyển giao vào Service, nhận kết quả Pydantic và `emit()` lên mạng Bus.
4. BODYFRAME STRICT SCHEMA (NON-NEGOTIABLE RULE)
Mọi Node trong hệ thống BẮT BUỘC tuân thủ BodyFrame schema dưới đây:
FIELD HỢP LỆ DUY NHẤT:
✔ status
✔ text
✔ records
✔ entities
✔ state
✔ metrics
✔ context
✔ route
✔ error
🚨 STRICT RULES (BẮT BUỘC TUÂN THỦ)
❌ TUYỆT ĐỐI không được tạo thêm field ngoài danh sách trên
❌ Không được “đẻ schema mới” trong state/context/metrics
❌ Không được return custom object ngoài BodyFrame
status	SUCCESS / FAILED / EMPTY
text	UI OUTPUT SINGLE SOURCE OF TRUTH
records	list output objects
entities	extracted entities
state	business logic runtime state
metrics	system observability
context	debug / trace / metadata
error	failure only


### 3. TIÊU CHUẨN "PHÁC ĐỒ NGHIỆP VỤ" (CERTIFIED WORKFLOW DOCS)

Mỗi hàm Adapter bắt buộc phải có một Docstring ngắn gọn ngay đầu hàm theo đúng định dạng chuẩn hóa (Template bên dưới). Đây là tài liệu kiểm định giúp hệ thống và các AI lớn (Gemini, GPT) rà soát code, đảm bảo tính nhất quán thực tế, không suy diễn:
- **BUSINESS INTENT:** Mục đích nghiệp vụ cốt lõi của Node.
- **WORKFLOW PIPELINE:** Mô tả chính xác 4 bước thực thi cố định của một Node gác cổng.

### 4. KHUÔN MẪU ADAPTER CHUẨN CÔNG NGHIỆP (REFERENCE PATTERN)

```python
from langchain_core.runnables import RunnableConfig
from app.core.main_bus import MainBus
from app.core.registry  import BusRegistry
from app.core.protocol  import StandardFrame, BodyFrame
from app.container import get_ctx
from .your_node_service import YourNodeService

service_module = YourNodeService()

async def node_name(
    state: MainBus, 
    config: RunnableConfig = None
) -> dict:
    """
    ======================================================================
    CERTIFIED PROTOCOL WORKFLOW: [YOUR_NODE_NAME]
    ======================================================================
    [BUSINESS INTENT]
    Quản lý nghiệp vụ chuyên biệt... [Mô tả ngắn gọn mục đích tại đây].

    [WORKFLOW PIPELINE]
    - Step 1: Safe Post-Guard - Kiểm tra trạng thái an toàn của Node liền trước. Chuyển hóa lỗi lên Bus thay vì crash app nếu vi phạm cấu trúc.
    - Step 2: Context Extraction & DI - Bóc tách dữ liệu sạch từ mạng Bus bằng toán tử chấm (.) và Inject Engine.
    - Step 3: Pure Domain Execution - Gọi Service nghiệp vụ, nhận về Object Pydantic đóng băng.
    - Step 4: Status Normalization & Bus Emit - Đồng bộ hóa trạng thái hệ thống và phát StandardFrame lên Bus.
    ======================================================================
    """
    
    # STEP 1: SAFE POST-GUARD (CHỐNG CRASH HỆ THỐNG DO ĐỨT GÃY TOPOLOGY)
    error_message = None
    if not hasattr(state, "reg_prev_node") or state.reg_prev_node is None:
        error_message = "[YOUR_NODE_NAME] Topology Violation: Node trước không tồn tại trên mạng Bus!"
    elif state.reg_prev_node.payload.status != "SUCCESS":
        error_message = f"[YOUR_NODE_NAME] Upstream Failure: Node liền trước gặp sự cố! Chi tiết: {state.reg_prev_node.payload.error}"

    # Hạ cánh an toàn: Nếu lỗi, đẩy thẳng Frame lỗi lên Bus thay vì raise RuntimeError
    if error_message:
        return StandardFrame.emit(
            registry_key=BusRegistry.YOUR_KEY,
            payload=BodyFrame(
                status="FAILED",
                text="Skipped due to upstream schema violation.",
                records=[],
                state={"process_completed": False},
                context={"topology_error": error_message},
                error=error_message
            )
        )

    # STEP 2: CONTEXT EXTRACTION & DEPENDENCY INJECTION
    ctx = await get_ctx()
    clean_text = state.reg_prev_node.payload.text
    
    # STEP 3: PURE DOMAIN EXECUTION
    result = await service_module.execute(text=str(clean_text))
    
    # STEP 4: STATUS NORMALIZATION & BUS EMIT
    status = "SUCCESS" if result.is_valid else "FAILED"
    return StandardFrame.emit(
        registry_key=BusRegistry.YOUR_KEY,
        payload=BodyFrame(
            status=status,
            text=clean_text,
            state={"route_to": result.route, "process_completed": True},
            error=None if status == "SUCCESS" else "Rejected by business validation."
        )
    )


class name_service:
    def __init__(self, llm_engine: Any):
        self._llm = llm_engine
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self._env = Environment(loader=FileSystemLoader(current_dir))

    async def run(self, user_input: str, context: Dict[str, Any]) -> LightweightChatOutput:
        # Load template
        template = self._env.get_template("name_prompt.jinja2")
        prompt = template.render(user_input=user_input, context=context, is_fallback=False)

        try:
            result = await self._llm.generate(
                system=prompt, 
                user="Generate response.",
                schema=LightweightChatOutput,
                temperature=0.6
            )
            
            return name_result(
                response=result.response,
                tone=result.tone
            )

        except Exception as e:
            print(f"[ERROR][LightweightChat] LLM Failed: {e}")
            
            return name_result(
                response="Rất xin lỗi, hệ thống đang gặp chút gián đoạn. Tôi có thể giúp gì cho bạn?",
                tone="neutral"
            )

```

### 5. NHIỆM VỤ CỤ THỂ BÂY GIỜ CỦA BẠN (YOUR TASK)

Hãy áp dụng đúng 3 cấu trúc file (_protocol.py, _service.py, adapter_.py), tư duy thiết kế, xử lý lỗi loại bỏ crash hệ thống và khuôn mẫu code ở trên. Bây giờ, hãy tiến hành viết/sửa node theo yêu cầu cụ thể sau đây:

[BẠN ĐIỀN CÔNG VIỆC CỦA NODE MỚI HOẶC NODE CẦN SỬA VÀO ĐÂY, VÍ DỤ: "Tôi muốn sửa node_QA_RESPONSE để nó đọc tri thức từ RAG và trả lời người dùng..."]