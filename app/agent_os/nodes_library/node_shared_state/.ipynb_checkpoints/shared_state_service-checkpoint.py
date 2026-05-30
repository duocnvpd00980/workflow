from _protocol import SharedStateOutput

class SharedStateService:
    """
    Pure Domain Logic - Xử lý chuẩn hóa dữ liệu trạng thái cần đồng bộ.
    Tuyệt đối độc lập và tách biệt khỏi State Bus hệ thống.
    """
    
    @staticmethod
    async def synchronize_state(final_text: str) -> SharedStateOutput:
        if not final_text:
            return SharedStateOutput(
                is_synced=False,
                updated_keys=[],
                persisted_text=""
            )
            
        # Giả lập logic đóng gói dữ liệu phục vụ lưu trữ lâu dài
        # (Trong thực tế, bước này có thể chuẩn bị payload để adapter ghi vào Redis/Postgres qua DB Engine)
        tracked_keys = ["last_verified_response", "workflow_completion_flag"]
        
        return SharedStateOutput(
            is_synced=True,
            updated_keys=tracked_keys,
            persisted_text=final_text
        )