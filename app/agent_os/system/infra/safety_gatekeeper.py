def check_request_safety(state, config):
    # Lấy thông tin từ metadata (truyền vào lúc invoke)
    user_id = config["metadata"].get("user_id")
    idempotency_key = config["configurable"].get("checkpoint_id")
    
    # 1. Check Idempotency (Lỗi 3)
    # Truy vấn DB xem key này đã được xử lý thành công chưa
    
    # 2. Check Quota/Billing (Lỗi 7)
    # Ví dụ: user_quota_service.has_balance(user_id)
    
    is_safe = True # Logic check thực tế ở đây
    return {"reg_gatekeeper": {"payload": {"is_safe": is_safe}}}