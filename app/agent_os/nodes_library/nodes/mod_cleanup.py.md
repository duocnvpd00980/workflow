from agent_os.system import (
    StateBus, _PLACEHOLDER, _emit, sanitise, 
    POLICY, detect_language, ContentItem
)

# --- §1: AGGREGATOR (Bộ gom linh kiện) ---
async def node_AGGREGATOR(s: StateBus) -> dict:
    # Log thử xem s.outputs có gì không
    _emit("debug", event="aggregator_check", current_count=len(s.outputs))

    if not s.outputs or len(s.outputs) == 0:
        _emit("warning", event="aggregator_empty", message="No agents produced content. Using placeholder.")
        # Tạo placeholder item
        placeholder_item = ContentItem(
            agent="SYSTEM_RECOVERY", 
            content="[Generation failed or policy rejected content]",
            language_detected="vi"
        )
        return {"outputs": [placeholder_item]}
    
    return {} # Không cần trả về gì nếu đã có data

# --- §2: CONTEXT CLIPPER (Bộ xả tụ điện / RAII Cleanup) ---
async def node_CONTEXT_CLIPPER(s: StateBus) -> dict:
    _emit("info", event="context_clipping", message="Pruning transient artefacts.")
    
    return {
        # Đừng gán None cho các trường String/List nếu Schema không cho phép
        "blog_plan": None,      # Nếu blog_plan là Object thì để None được
        "blog_content": "",     # Chuyển thành chuỗi rỗng
        "tool_result": "",      
        "feedback": "",         
        "pending_tool": ""      # <--- KHÔNG ĐỂ None, PHẢI LÀ ""
    }

# --- §3: FINAL POLISHER (Bộ mài bóng sản phẩm) ---
async def node_FINAL_POLISHER(s: StateBus) -> dict:
    """Lần kiểm tra cuối cùng trước khi đóng gói gửi cho khách hàng."""
    polished_list = []
    
    for item in s.outputs:
        # 1. Làm sạch ký tự lạ, format thừa
        clean_text = sanitise(item.content)
        
        # 2. Kiểm tra Policy cuối cùng (An toàn tuyệt đối)
        is_ok, reason = POLICY.check_content(clean_text)
        
        if not is_ok:
            _emit("error", event="polisher_rejection", agent=item.agent, reason=reason)
            final_content = f"[REJECTED BY POLICY: {reason}]"
        else:
            final_content = clean_text

        # 3. Cập nhật lại nhãn dán cho item
        polished_list.append(item.model_copy(update={
            "content": final_content,
            "language_detected": detect_language(final_content)
        }))

    _emit("info", event="final_polish_complete")
    return {"outputs": polished_list}