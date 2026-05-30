import json
from agent_os.system import (
    ShieldInput, ShieldOutput, AgentConfig, safe_node,
    StateBus, ValidatorVerdict, ContentItem, _FIREWALL, POLICY, 
    _emit, detect_language, sanitise, SupervisorStatus, CFG
)

# 1. Datasheet: Cấu hình Auditor
VALIDATOR_CFG = AgentConfig(
    agent_id="VALIDATOR",
    role="Quality Assurance Auditor",
    goal="Critically evaluate if the content meets brand standards and SEO requirements.",
    backstory="A meticulous editor known for spotting the smallest inconsistencies.",
    output_schema_hint='{"score": 0.8, "issues": "missing keywords", "passed": true, "retry_reason": ""}',
    temperature=0.1
)

# 2. Shield Logic
class ValidatorShield:
    def __init__(self, firewall, policy_engine):
        self.firewall = firewall
        self.policy = policy_engine
        self.cta_patterns = ["liên hệ", "contact", "mua ngay", "đăng ký", "gọi ngay", "click here"]

    async def process(self, packet: ShieldInput) -> ShieldOutput:
        state = packet.metadata.get("state")
        draft = packet.payload.get("draft")
        
        # Kiểm tra đầu vào rỗng (không tốn phí LLM)
        if not draft or not hasattr(draft, 'content') or not draft.content:
            return ShieldOutput(data={
                "last_validator_verdict": ValidatorVerdict(
                    passed=False, score=0.0, issues="EMPTY_CONTENT", needs_retry=True
                )
            }, audit=None)

        # --- Giai đoạn 1: Hardware Check (0 cost) ---
        pre_score = 1.0
        structural_issues = []
        
        if len(draft.content) < 500:
            pre_score -= 0.4
            structural_issues.append("TOO_SHORT")
            
        if not any(p in draft.content.lower() for p in self.cta_patterns):
            pre_score -= 0.3
            structural_issues.append("MISSING_CTA")

        # --- Giai đoạn 2: LLM Rubric (Firewall v11) ---
        validator_input = json.dumps({
            "content_preview": sanitise(draft.content[:2000]),
            "target_tone": getattr(state.seed, "tone", "professional"),
            "structural_issues": structural_issues,
            "revision_round": getattr(state, "revision_count", 0)
        }, ensure_ascii=False)

        # FIX: Truyền tham số tường minh theo Protocol v11
        res, audit = await self.firewall.call(
            agent_id=VALIDATOR_CFG.agent_id,
            system=f"Role: {VALIDATOR_CFG.role}. Goal: {VALIDATOR_CFG.goal}",
            user=validator_input,  # Thay user_message bằng user
            schema=ValidatorVerdict,
            session_id=getattr(state, "session_id", "temp_sid"),
            current_cost=getattr(state, "total_cost", 0.0),
            budget_limit=getattr(state, "budget_limit", 2.0)
        )

        # Tránh lỗi nếu LLM tèo
        if not res:
            res = ValidatorVerdict(passed=False, score=0.0, issues="LLM_FAILURE", needs_retry=True)

        # --- Giai đoạn 3: Tổng hợp ---
        final_score = round((pre_score + res.score) / 2, 2)
        final_passed = final_score >= 0.7 and res.passed
        
        verdict = ValidatorVerdict(
            passed=final_passed,
            score=final_score,
            issues=", ".join(structural_issues + [res.issues]),
            needs_retry=not final_passed and state.revision_count < state.max_revisions,
            retry_reason=res.retry_reason
        )

        return ShieldOutput(data={"last_validator_verdict": verdict}, audit=audit)

# 3. ADAPTER (Fix lỗi bóc tách Dict vs Object)
async def node_VALIDATOR(s: StateBus) -> dict:
    shield = ValidatorShield(_FIREWALL, POLICY)
    packet = ShieldInput(payload={"draft": s.blog_draft}, metadata={"state": s})
    
    # safe_node trả về DICT (đã model_dump)
    res_dict = await safe_node("VALIDATOR", shield.process(packet))
    
    # FIX: Bóc tách theo kiểu Dict
    inner_data = res_dict.get("data", {})
    audit = res_dict.get("audit")

    verdict = inner_data.get("last_validator_verdict")
    if isinstance(verdict, dict):
        verdict = ValidatorVerdict.model_validate(verdict)
    
    # Fallback nếu verdict bị rỗng
    if verdict is None:
        verdict = ValidatorVerdict(
            passed=False,
            score=0.0,
            issues="MISSING_VERDICT",
            needs_retry=True
        )

    # Xác định trạng thái điều hướng
    new_status = SupervisorStatus.RUNNING
    if verdict.passed:
        new_status = SupervisorStatus.PASSED
    elif not verdict.needs_retry:
        new_status = SupervisorStatus.EXHAUSTED

    delta = {
        "last_validator_verdict": verdict,
        "supervisor_status": new_status,
        "audit_log": [audit] if audit else [],
        "total_cost": getattr(audit, "cost_usd", 0.0) if audit else 0.0,
        "revision_count": s.revision_count + 1 if verdict.needs_retry else s.revision_count
    }

    # Nếu pass, đẩy vào outputs (Dùng ContentItem chuẩn)
    if verdict.passed and s.blog_draft:
        new_item = ContentItem(
            content=s.blog_draft.content,
            agent="BLOG_PIPELINE",
            language_detected=detect_language(s.blog_draft.content)
        )
        delta["outputs"] = [new_item]
    
    return delta