from agent_os.system import (
    ShieldInput, ShieldOutput, safe_node, StateBus, 
    _emit, _RATE_LIMITER, KILL_SWITCH
)

# =============================================================================
# §27  PERSIST / STREAMING SHIELD (Trạm quan trắc)
# =============================================================================

class PersistStreamingShield:
    """
    Ghi nhật ký vận hành và dọn dẹp tài nguyên phiên (Session Cleanup).
    """
    async def process(self, packet: ShieldInput) -> ShieldOutput:
        state = packet.metadata.get("state")
        
        # 1. Thu thập thông số (Telemetry Collection)
        total_tokens = sum(a.total_tokens for a in state.audit_log if a)
        validator_score = (state.last_validator_verdict.score 
                           if state.last_validator_verdict else None)
        
        # 2. Phát tín hiệu hoàn tất (Broadcast)
        _emit("info", event="pipeline_complete",
              session_id=state.session_id,
              total_cost_usd=state.total_cost,
              total_tokens=total_tokens,
              output_count=len(state.outputs),
              error_count=len(state.errors),
              blog_degraded=state.blog_stage_degraded,
              supervisor_rounds=state.revision_count,
              tool_calls=len(state.tool_call_history),
              validator_score=validator_score)
 
        # 3. Ghi log chi tiết từng Node để tối ưu chi phí sau này
        for entry in state.audit_log:
            if entry:
                _emit("info", event="node_audit",
                      node=entry.node, success=entry.success,
                      ms=entry.runtime_ms, cost=entry.cost_usd)
 
        # 4. Giải phóng tài nguyên (Hardware Release)
        # Tương tự việc ngắt các chân ngắt (Interrupts) trong Arduino
        await _RATE_LIMITER.cleanup(state.session_id)
        
        if hasattr(KILL_SWITCH, "unregister"):
            await KILL_SWITCH.unregister(state.session_id)

        # Trả về ShieldOutput trống vì đây là điểm cuối (Sink)
        return ShieldOutput(data={}, audit=None)

# =============================================================================
# ADAPTER (Điểm cuối của Mainboard)
# =============================================================================

async def node_PERSIST_STREAMING(s: StateBus) -> dict:
    """
    Node thợ hàn cuối cùng: Xuất dữ liệu ra Monitor và dọn dẹp.
    """
    shield = PersistStreamingShield()
    
    # Chúng ta chỉ cần truyền State vào Metadata để Shield đọc thông số
    packet = ShieldInput(payload={}, metadata={"state": s})
    
    await safe_node("PERSIST_STREAMING", shield.process(packet))
    
    # Node này không thay đổi State của Graph nữa nên trả về dict trống
    return {}