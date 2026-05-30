from pydantic import BaseModel, model_validator
from typing import Any
from agent_os.system import (
    ShieldInput, ShieldOutput, safe_node, StateBus, 
    SeedStrategy, _FIREWALL, _emit
)

class SeedShield:
    def __init__(self, firewall):
        self.firewall = firewall

    # Bê nguyên logic xịn từ SeedUnit cũ sang đây
    class _SeedResponse(BaseModel):
        target_audience: str = "general"
        main_benefit:    str = "engagement"
        brand_voice:     str = "professional"
        keyword:         str = "marketing"
        language:        str = "vi"
        tone:            str = "professional"
        content_rules:   str = ""

        @model_validator(mode="before")
        @classmethod
        def _flatten_nested(cls, v: Any) -> Any:
            if not isinstance(v, dict): return v
            def _f(x: Any) -> str:
                if isinstance(x, str):  return x
                if isinstance(x, dict): return ", ".join(str(i) for i in x.values() if i)[:300]
                if isinstance(x, list): return ", ".join(str(i) for i in x)[:300]
                return str(x)[:300]
            for k in ("target_audience", "main_benefit", "brand_voice",
                      "keyword", "language", "tone", "content_rules"):
                if k in v:
                    v[k] = _f(v[k])
            return v

    async def process(self, packet: ShieldInput) -> ShieldOutput:
        # Lấy dữ liệu từ packet (không lấy trực tiếp từ state để tránh lỗi NoneType)
        u_input = packet.payload.get("user_input", "")
        lang    = packet.payload.get("language", "vi")
        state   = packet.metadata.get("state") # Vẫn cầm theo để lấy thông tin phụ

        # Gọi LLM (Sử dụng alias .call của firewall)
        seed_raw, audit = await self.firewall.call(
            system=(
                "You are a senior content strategist. "
                "Analyse the request and return a SeedStrategy JSON with these exact keys "
                "(all plain strings): target_audience, main_benefit, brand_voice, keyword, "
                f"language (MUST be '{lang}'), tone, content_rules. "
                "Return ONLY valid JSON."
            ),
            user=u_input,
            schema=self._SeedResponse,
            agent_id="SEED",
            session_id=getattr(state, "session_id", "temp_sid"),
            current_cost=getattr(state, "total_cost", 0.0),
            budget_limit=getattr(state, "budget_limit", 2.0),
        )

        # Chuyển đổi sang SeedStrategy chuẩn
        seed = SeedStrategy.model_validate(seed_raw.model_dump())
        
        # Enforce Language Lock (Logic cốt lõi của ông)
        if seed.language != lang:
            _emit("warning", event="language_lock_enforced", got=seed.language, forced=lang)
            seed = seed.model_copy(update={"language": lang})

        return ShieldOutput(data={"seed": seed}, audit=audit)

# --- ADAPTER (Hàn chân cắm Bus Write) ---
async def node_SEED(s: StateBus) -> dict:
    # 1. Khởi tạo Shield
    shield = SeedShield(_FIREWALL)
    
    # 2. Đóng gói packet (Dùng getattr để chống s bị None)
    packet = ShieldInput(
        payload={
            "user_input": getattr(s, "user_input", ""),
            "language": getattr(s, "language", "vi")
        },
        metadata={"state": s}
    )
    
    # 3. Chạy qua safe_node (Kết quả trả về là DICT)
    res_dict = await safe_node("SEED", shield.process(packet))
    
    # 4. Trả về đúng schema của StateBus
    # safe_node đã dump ShieldOutput thành dict có key "data" và "audit"
    inner_data = res_dict.get("data", {})
    audit = res_dict.get("audit")

    return {
        "seed": inner_data.get("seed"), # Object SeedStrategy
        "audit_log": [audit] if audit else [],
        "total_cost": getattr(audit, "cost_usd", 0.0) if audit else 0.0
    }