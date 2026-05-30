from agent_os.system import (
    ShieldInput, ShieldOutput, ContentItem, safe_node, AgentConfig,
    StateBus, _emit, detect_language, _FIREWALL, POLICY, _PLACEHOLDER
)

# =============================================================================
# §21  EMAIL SHIELD (Linh kiện độc lập)
# =============================================================================

# 1. Datasheet: Thông số kỹ thuật nằm ngay tại xưởng này
EMAIL_CONFIG = AgentConfig(
    agent_id="AGENT_EMAIL",
    role="Email Marketing Strategist",
    goal="Craft high-converting email sequences based on the campaign brief.",
    backstory="Expert in psychological triggers and inbox deliverability.",
    output_schema_hint='{"content":"<email body>","has_cta":true}',
    temperature=0.35,
)

# =============================================================================
# §21  EMAIL SHIELD (Fix v11)
# =============================================================================

class EmailShield:
    def __init__(self, firewall, policy_engine):
        self.firewall = firewall
        self.policy = policy_engine

    async def process(self, packet: ShieldInput) -> ShieldOutput:
        seed_data = packet.payload.get("seed")
        state = packet.metadata.get("state") # Lấy state để trích xuất session/cost

        # FIX: Bỏ config=, dùng tham số tường minh cho Firewall v11
        result, audit = await self.firewall.call(
            agent_id=EMAIL_CONFIG.agent_id,
            system=f"Role: {EMAIL_CONFIG.role}. Goal: {EMAIL_CONFIG.goal}. Backstory: {EMAIL_CONFIG.backstory}",
            user=f"Seed Strategy: {str(seed_data)}",
            schema=ContentItem,
            session_id=getattr(state, "session_id", "temp_sid"),
            current_cost=getattr(state, "total_cost", 0.0),
            budget_limit=getattr(state, "budget_limit", 2.0)
        )
 
        if not result or not result.content:
            item = _PLACEHOLDER.model_copy(update={"agent": EMAIL_CONFIG.agent_id})
        else:
            item = result.model_copy(update={
                "agent": EMAIL_CONFIG.agent_id,
                "language_detected": detect_language(result.content)
            })
            
            ok, reason = self.policy.check_content(item.content)
            if not ok:
                _emit("warning", event="email_policy_fail", reason=reason)
                item = _PLACEHOLDER.model_copy(update={"agent": EMAIL_CONFIG.agent_id})
 
        return ShieldOutput(data={"item": item}, audit=audit)

# =============================================================================
# ADAPTER (Fix Bus Write)
# =============================================================================

async def node_AGENT_EMAIL(s: StateBus) -> dict:
    packet = ShieldInput(payload={"seed": s.seed}, metadata={"state": s})
    shield = EmailShield(firewall=_FIREWALL, policy_engine=POLICY)
    
    res_dict = await safe_node("AGENT_EMAIL", shield.process(packet))
    
    inner_data = res_dict.get("data", {})
    audit = res_dict.get("audit")
    
    # TƯƠNG TỰ: Đảm bảo dữ liệu là Object chuẩn
    raw_item = inner_data.get("item")
    if raw_item:
        new_item = ContentItem(**raw_item) if isinstance(raw_item, dict) else raw_item
    else:
        new_item = None

    return {
        "outputs": [new_item] if new_item else [],
        "audit_log": [audit] if audit else [],
        "total_cost": getattr(audit, "cost_usd", 0.0) if audit else 0.0
    }