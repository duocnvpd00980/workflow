from pydantic import BaseModel
from agent_os.system import (
    ShieldInput, ShieldOutput, AgentConfig, safe_node,
    StateBus, _FIREWALL, POLICY, _emit, BlogOutline
)

# 1. Datasheet
PLANNER_CFG = AgentConfig(
    agent_id="BLOG_PLANNER",
    role="Senior Content Strategist",
    goal="Build a detailed, language-correct blog outline.",
    backstory="Believes success starts with a sharp outline.",
    output_schema_hint = """
    {
    "title": "Tên bài viết",
    "sections": "Danh sách các đầu mục nội dung, ngăn cách bằng dấu gạch đứng |"
    }
    """,
    temperature=0.25
)

# 2. Shield logic
class BlogPlannerShield:
    def __init__(self, firewall, policy_engine):
        self.firewall = firewall
        self.policy = policy_engine

    async def process(self, packet: ShieldInput) -> ShieldOutput:

        seed = packet.payload.get("seed")
        state = packet.metadata.get("state")

        # Firewall trả RAW dict
        raw_result, audit = await self.firewall.call(
            agent_id=PLANNER_CFG.agent_id,
            system=f"Role: {PLANNER_CFG.role}. Goal: {PLANNER_CFG.goal}.",
            user=f"Seed Strategy: {str(seed)}",
            schema=None,
            session_id=getattr(state, "session_id", "temp_sid"),
            current_cost=getattr(state, "total_cost", 0.0),
            budget_limit=getattr(state, "budget_limit", 2.0),
        )

        # Manual validation
        try:

            if not raw_result:
                raise ValueError("Empty planner result")

            result = BlogOutline(**raw_result)

        except Exception as exc:

            _emit(
                "warning",
                event="planner_invalid_schema",
                error=str(exc),
                raw=str(raw_result)[:500],
            )

            result = BlogOutline(
                title="Draft Title",
                sections="Intro|Content|CTA",
            )

        # Policy check
        ok, reason = self.policy.check_content(result.title)

        if not ok:

            _emit(
                "warning",
                event="planner_policy_fail",
                reason=reason,
            )

            result = BlogOutline(
                title="Draft Title",
                sections="Intro|Content|CTA",
            )

        return ShieldOutput(
            data={"blog_outline": result},
            audit=audit,
        )

# 3. Adapter (Hàn vào Mainboard)
async def node_BLOG_PLANNER(s: StateBus) -> dict:
    shield = BlogPlannerShield(firewall=_FIREWALL, policy_engine=POLICY)
    packet = ShieldInput(payload={"seed": s.seed}, metadata={"state": s})
    
    res_dict = await safe_node("BLOG_PLANNER", shield.process(packet))
    
    inner_data = res_dict.get("data", {})
    audit = res_dict.get("audit")
    outline = inner_data.get("blog_outline")

    return {
        "blog_outline": outline, 
        "audit_log": [audit] if audit else [],
        "total_cost": getattr(audit, "cost_usd", 0.0) if audit else 0.0
    }