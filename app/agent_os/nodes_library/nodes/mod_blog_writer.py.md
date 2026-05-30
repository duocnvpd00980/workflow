import json
from agent_os.system import (
    ShieldInput, ShieldOutput, AgentConfig, safe_node,
    StateBus, _FIREWALL, POLICY, _emit, sanitise, BlogDraft
)

WRITER_CFG = AgentConfig(
    agent_id="BLOG_WRITER",
    role="Creative Copywriter",
    goal="Turn an outline into a full blog post.",
    backstory="Blends data and emotion for high engagement.",
    output_schema_hint='{"content":"..."}',
    temperature=0.5
)

class BlogWriterShield:
    def __init__(self, firewall, policy_engine):
        self.firewall = firewall
        self.policy = policy_engine

    async def process(self, packet: ShieldInput) -> ShieldOutput:
        seed = packet.payload.get("seed")
        outline = packet.payload.get("outline")
        feedback = packet.payload.get("feedback")
        state = packet.metadata.get("state")
        
        # Hardware Check: Nếu không có outline thì ngắt mạch luôn
        if not outline:
            return ShieldOutput(data={"blog_draft": None}, audit=None)

        writer_input = json.dumps({
            "action": "REVISE" if feedback else "INITIAL",
            "seed": seed.model_dump() if seed else {},
            "outline": outline.model_dump() if hasattr(outline, 'model_dump') else str(outline),
            "feedback": feedback
        }, ensure_ascii=False)

        # FIX: Firewall v11 call
        result, audit = await self.firewall.call(
            agent_id=WRITER_CFG.agent_id,
            system=f"Role: {WRITER_CFG.role}. Goal: {WRITER_CFG.goal}",
            user=writer_input,
            schema=BlogDraft,
            session_id=getattr(state, "session_id", "temp_sid"),
            current_cost=getattr(state, "total_cost", 0.0),
            budget_limit=getattr(state, "budget_limit", 2.0)
        )
        return ShieldOutput(data={"blog_draft": result}, audit=audit)

async def node_BLOG_WRITER(s: StateBus) -> dict:
    shield = BlogWriterShield(firewall=_FIREWALL, policy_engine=POLICY)
    # Truyền s vào metadata để lấy cost/session
    packet = ShieldInput(
        payload={"seed": s.seed, "outline": s.blog_outline, "feedback": s.feedback},
        metadata={"state": s}
    )
    
    res_dict = await safe_node("BLOG_WRITER", shield.process(packet))
    
    inner_data = res_dict.get("data", {})
    audit = res_dict.get("audit")

    return {
        "blog_draft": inner_data.get("blog_draft"),
        "pending_tool": "", # Bắt buộc để tránh ValidationError
        "audit_log": [audit] if audit else [],
        "total_cost": getattr(audit, "cost_usd", 0.0) if audit else 0.0
    }