from pydantic import BaseModel
from agent_os.system import (
    ShieldInput, ShieldOutput, AgentConfig, safe_node,
    StateBus, _FIREWALL, POLICY
)

EDITOR_CFG = AgentConfig(
    agent_id="BLOG_EDITOR",
    role="Chief Editor",
    goal="Ensure quality and adherence to tone.",
    backstory="Zero tolerance for low-quality content.",
    output_schema_hint='{"is_approved":bool, "feedback":"..."}',
    temperature=0.2
)

class EditorResponse(BaseModel):
    is_approved: bool
    feedback: str

class BlogEditorShield:
    def __init__(self, firewall, policy_engine):
        self.firewall = firewall
        self.policy = policy_engine

    async def process(self, packet: ShieldInput) -> ShieldOutput:
        draft = packet.payload.get("draft")
        seed = packet.payload.get("seed")
        state = packet.metadata.get("state")
        
        # Cầu chì: Nếu Writer chưa ra bài, Editor không làm việc
        if not draft or not hasattr(draft, 'content') or not draft.content:
            return ShieldOutput(data={"is_approved": False, "feedback": "No draft to review"}, audit=None)

        # FIX: Firewall v11 call
        res, audit = await self.firewall.call(
            agent_id=EDITOR_CFG.agent_id,
            system=f"Role: {EDITOR_CFG.role}. Goal: {EDITOR_CFG.goal}",
            user=f"Review this draft: {draft.content[:1500]}", # Gửi preview
            schema=EditorResponse,
            session_id=getattr(state, "session_id", "temp_sid"),
            current_cost=getattr(state, "total_cost", 0.0),
            budget_limit=getattr(state, "budget_limit", 2.0)
        )

        # Fallback nếu LLM lỗi
        if not res:
            res = EditorResponse(is_approved=False, feedback="Editor logic failed")

        return ShieldOutput(
            data={"is_approved": res.is_approved, "feedback": res.feedback}, 
            audit=audit
        )

async def node_BLOG_EDITOR(s: StateBus) -> dict:
    shield = BlogEditorShield(firewall=_FIREWALL, policy_engine=POLICY)
    packet = ShieldInput(
        payload={"seed": s.seed, "draft": s.blog_draft},
        metadata={"state": s}
    )
    
    res_dict = await safe_node("BLOG_EDITOR", shield.process(packet))
    
    inner_data = res_dict.get("data", {})
    audit = res_dict.get("audit")

    return {
        "feedback": inner_data.get("feedback", ""),
        # Cập nhật status để Validator hoặc Supervisor biết đường điều hướng
        "supervisor_status": "REVISE" if not inner_data.get("is_approved") else "PASSED",
        "audit_log": [audit] if audit else [],
        "total_cost": getattr(audit, "cost_usd", 0.0) if audit else 0.0
    }