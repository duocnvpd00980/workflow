"""
Supervisor AI Node — Marketing Automation System
Chạy trong Jupyter Lab, dùng Groq API (Llama 4 Scout)

Cách dùng:
    supervisor = SupervisorAgent()
    supervisor.chat("Tháng 7 có ngày lễ gì đáng đăng không?")
    supervisor.chat("Làm bài đăng Facebook cho bánh mì thịt nướng hôm nay")
"""

import requests
import json
import re
from datetime import datetime
from typing import Optional

# ─── CONFIG ───────────────────────────────────────────────────────────────────

GROQ_API_KEY = "YOUR_GROQ_API_KEY"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "meta-llama/llama-4-scout-17b-16e-instruct"

# ─── FAKE DATABASE (mô phỏng 3 bảng nội bộ) ─────────────────────────────────

FAKE_DB = {
    "runs": [
        {
            "run_id": "run_001",
            "created_at": "2025-06-01T10:00:00",
            "request_summary": "Bài đăng Facebook giới thiệu menu hè",
            "agents_used": ["research", "social", "image", "qa", "publisher"],
            "channels": ["facebook"],
            "status": "success",
            "qa_score": 8.5,
            "published_at": "2025-06-01T11:30:00"
        },
        {
            "run_id": "run_002",
            "created_at": "2025-06-03T14:00:00",
            "request_summary": "Blog SEO về xu hướng đồ ăn 2025",
            "agents_used": ["research", "blog", "qa", "publisher"],
            "channels": ["wordpress"],
            "status": "success",
            "qa_score": 9.0,
            "published_at": "2025-06-03T16:00:00"
        },
        {
            "run_id": "run_003",
            "created_at": "2025-06-04T09:00:00",
            "request_summary": "Quảng cáo Facebook cho combo trưa",
            "agents_used": ["research", "ads", "qa", "publisher"],
            "channels": ["facebook"],
            "status": "success",
            "qa_score": 7.8,
            "published_at": "2025-06-04T10:00:00"
        }
    ],
    "outputs": [
        {
            "output_id": "out_001",
            "run_id": "run_001",
            "agent": "social",
            "content_type": "caption",
            "content": "☀️ Mùa hè này, làm mới vị giác với menu HÈ 2025 của chúng tôi! Từ salad thanh mát đến nước ép trái cây tươi nguyên chất — tất cả chỉ từ 35k. Ghé ngay hôm nay nhé! #MenuHe #DoAnNgon",
            "created_at": "2025-06-01T11:00:00",
            "channel": "facebook"
        },
        {
            "output_id": "out_002",
            "run_id": "run_002",
            "agent": "blog",
            "content_type": "blog_post",
            "content": "# 5 Xu Hướng Đồ Ăn Nổi Bật Năm 2025\n\nNgành F&B đang chứng kiến làn sóng thay đổi mạnh mẽ...",
            "created_at": "2025-06-03T15:30:00",
            "channel": "wordpress"
        },
        {
            "output_id": "out_003",
            "run_id": "run_003",
            "agent": "ads",
            "content_type": "fb_ad",
            "content": "🍱 COMBO TRƯA CHỈ 55K — Cơm + Canh + Tráng miệng\nĐặt ngay, nhận ngay. Freeship nội thành!\n👉 Inbox hoặc gọi 0909-XXX-XXX",
            "created_at": "2025-06-04T09:30:00",
            "channel": "facebook"
        }
    ],
    "usage": [
        {"usage_id": "u_001", "run_id": "run_001", "agent": "supervisor", "tokens_input": 500, "tokens_output": 300, "tokens_total": 800, "called_at": "2025-06-01T10:05:00", "model": GROQ_MODEL},
        {"usage_id": "u_002", "run_id": "run_001", "agent": "research",   "tokens_input": 1200, "tokens_output": 800, "tokens_total": 2000, "called_at": "2025-06-01T10:10:00", "model": GROQ_MODEL},
        {"usage_id": "u_003", "run_id": "run_002", "agent": "blog",       "tokens_input": 1500, "tokens_output": 2000, "tokens_total": 3500, "called_at": "2025-06-03T14:30:00", "model": GROQ_MODEL},
        {"usage_id": "u_004", "run_id": "run_003", "agent": "ads",        "tokens_input": 800,  "tokens_output": 600,  "tokens_total": 1400, "called_at": "2025-06-04T09:20:00", "model": GROQ_MODEL},
    ]
}

# ─── HỒ SƠ DOANH NGHIỆP ───────────────────────────────────────────────────────

BUSINESS_PROFILE = {
    "brand_name": "Nhà Hàng Ngon Corner",
    "industry": "F&B — Nhà hàng / Quán ăn",
    "default_tone": "Thân thiện, vui tươi, gần gũi",
    "default_channels": ["facebook"],
    "brand_colors": ["#E85D04", "#F48C06", "#FFFFFF"],
    "image_style": "Ảnh thực phẩm tươi sáng, góc chụp top-down hoặc 45 độ",
    "token_quota_monthly": 100000,
}

# ─── TOOLS (chế độ 1 — Supervisor tự xử) ─────────────────────────────────────

def tool_query_db(table: str, filters: dict = None) -> list:
    """Truy vấn bảng nội bộ: runs / outputs / usage"""
    data = FAKE_DB.get(table, [])
    if not filters:
        return data
    result = []
    for row in data:
        match = all(str(row.get(k, "")).lower().__contains__(str(v).lower()) for k, v in filters.items())
        if match:
            result.append(row)
    return result

def tool_get_business_profile() -> dict:
    return BUSINESS_PROFILE

def tool_calculate_token_usage(month: str = None) -> dict:
    """Tính tổng token đã dùng trong tháng (format: '2025-06')"""
    if not month:
        month = datetime.now().strftime("%Y-%m")
    total = sum(
        r["tokens_total"] for r in FAKE_DB["usage"]
        if r["called_at"].startswith(month)
    )
    quota = BUSINESS_PROFILE["token_quota_monthly"]
    return {"used": total, "quota": quota, "remaining": quota - total, "month": month}

def tool_get_run_stats(month: str = None) -> dict:
    """Đếm số lần chạy thành công trong tháng"""
    if not month:
        month = datetime.now().strftime("%Y-%m")
    runs = [r for r in FAKE_DB["runs"] if r["created_at"].startswith(month) and r["status"] == "success"]
    return {"month": month, "success_count": len(runs), "runs": runs}

# ─── GROQ API CALL ────────────────────────────────────────────────────────────

def call_groq(messages: list, temperature: float = 0.7) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1024,
    }
    resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()

# ─── SUPERVISOR SYSTEM PROMPT ─────────────────────────────────────────────────

def build_system_prompt(profile: dict, context_data: str = "") -> str:
    now = datetime.now().strftime("%A, %d/%m/%Y %H:%M")
    return f"""Bạn là Supervisor AI — node trung tâm trong hệ thống marketing tự động cho doanh nghiệp.

## Thời điểm hiện tại: {now}

## Hồ sơ doanh nghiệp (KHÔNG hỏi lại những thông tin này):
- Tên thương hiệu: {profile['brand_name']}
- Ngành: {profile['industry']}
- Tone mặc định: {profile['default_tone']}
- Kênh mặc định: {', '.join(profile['default_channels'])}
- Style ảnh: {profile['image_style']}

## Dữ liệu ngữ cảnh từ CSDL nội bộ:
{context_data if context_data else "(Chưa có dữ liệu ngữ cảnh)"}

## LUẬT HOẠT ĐỘNG:

### Chế độ 1 — Tự xử (Direct Response)
Áp dụng khi:
- Khách hỏi thông tin (ngày lễ, xu hướng, đối thủ, dữ liệu)
- Khách đang brainstorm, chưa có yêu cầu rõ ràng
- Câu hỏi về lịch sử chạy, nội dung cũ, token usage

→ Trả lời trực tiếp, dùng dữ liệu ngữ cảnh nếu có. KHÔNG hỏi "muốn tạo nội dung không?" sau khi trả lời.

### Chế độ 2 — Phân công (Dispatch)
Áp dụng khi khách ra lệnh sản xuất nội dung CỤ THỂ — phải có ĐỦ 3 dấu hiệu:
1. Sản phẩm/chủ đề rõ
2. Từ hành động rõ: làm, viết, chạy, đăng, tạo
3. Thời gian (nói rõ hoặc ngầm hiểu là ngay)

Quy trình dispatch:
1. Kiểm tra thiếu gì → hỏi TỐI ĐA 3 câu (không hỏi lại info trong hồ sơ)
2. Tự suy những gì có thể suy (giờ vàng, kênh, tone mặc định)
3. Tóm tắt lại: làm gì / kênh nào / tone gì / đăng lúc nào / ưu đãi gì
4. Hỏi xác nhận — CHƯA dispatch cho đến khi khách xác nhận

### Khi khách xác nhận dispatch:
Phân tích yêu cầu và trả về JSON với format:
```json
{{
  "action": "dispatch",
  "summary": "...",
  "agents": ["research", "social", "qa", "publisher"],
  "channel": "facebook",
  "tone": "...",
  "schedule": "...",
  "special_message": "..."
}}
```

### Những điều KHÔNG được làm:
- Không tự dispatch sau khi trả lời câu hỏi
- Không hỏi quá 3 câu/lượt
- Không hỏi lại info đã có trong hồ sơ
- Không chào hàng sau mỗi câu trả lời
- Không chạy agent khi chưa có xác nhận

Hãy trả lời bằng tiếng Việt, tự nhiên, thân thiện nhưng chuyên nghiệp.
"""

# ─── SUPERVISOR AGENT CLASS ───────────────────────────────────────────────────

class SupervisorAgent:
    def __init__(self):
        self.history = []          # lịch sử hội thoại
        self.state = "idle"        # idle | collecting | awaiting_confirm
        self.pending_request = {}  # thông tin đang thu thập
        self.profile = tool_get_business_profile()
        print(f"✅ Supervisor khởi động — {self.profile['brand_name']}")
        print(f"   Model: {GROQ_MODEL}")
        print(f"   Gõ .reset() để xoá lịch sử, .history để xem hội thoại\n")

    def _get_context_data(self, user_msg: str) -> str:
        """Tự động lấy dữ liệu ngữ cảnh dựa trên câu hỏi của user"""
        ctx_parts = []
        msg_lower = user_msg.lower()

        # Token / usage
        if any(kw in msg_lower for kw in ["token", "quota", "dùng hết", "còn bao nhiêu", "tháng này"]):
            usage = tool_calculate_token_usage()
            ctx_parts.append(f"Token tháng này: đã dùng {usage['used']:,} / {usage['quota']:,} — còn lại {usage['remaining']:,}")

        # Lịch sử chạy
        if any(kw in msg_lower for kw in ["bao nhiêu bài", "đã đăng", "đã chạy", "lần chạy", "tháng này", "tuần này"]):
            stats = tool_get_run_stats()
            ctx_parts.append(f"Số lần chạy thành công tháng này: {stats['success_count']} lần")
            for r in stats["runs"]:
                ctx_parts.append(f"  - [{r['created_at'][:10]}] {r['request_summary']} (QA: {r['qa_score']}) — kênh: {', '.join(r['channels'])}")

        # Nội dung cũ
        if any(kw in msg_lower for kw in ["bài cũ", "xem lại", "quảng cáo", "blog", "caption", "nội dung cũ", "tuần trước"]):
            outputs = FAKE_DB["outputs"]
            ctx_parts.append(f"Các nội dung đã tạo gần đây ({len(outputs)} items):")
            for o in outputs:
                preview = o["content"][:80].replace("\n", " ") + "..."
                ctx_parts.append(f"  - [{o['created_at'][:10]}] [{o['agent'].upper()}] [{o['channel']}] {preview}")

        return "\n".join(ctx_parts)

    def _detect_mode(self, user_msg: str) -> str:
        """Gọi LLM để phân loại mode — trả về 'direct' hoặc 'dispatch_candidate'"""
        classify_prompt = [
            {
                "role": "system",
                "content": """Phân loại tin nhắn sau thuộc loại nào:
- "direct": hỏi thông tin, brainstorm, hỏi lịch sử, hỏi token, chưa ra lệnh sản xuất nội dung
- "dispatch_candidate": có từ hành động rõ (làm/viết/chạy/đăng/tạo) + sản phẩm cụ thể

Chỉ trả về đúng 1 từ: direct HOẶC dispatch_candidate"""
            },
            {"role": "user", "content": user_msg}
        ]
        result = call_groq(classify_prompt, temperature=0.1)
        return "dispatch_candidate" if "dispatch_candidate" in result.lower() else "direct"

    def _is_confirmation(self, user_msg: str) -> bool:
        """Kiểm tra xem khách có xác nhận không"""
        confirm_keywords = ["ok", "được", "đúng rồi", "chạy đi", "xác nhận", "yes", "ừ", "đồng ý", "chuẩn", "làm đi"]
        return any(kw in user_msg.lower() for kw in confirm_keywords)

    def chat(self, user_msg: str) -> str:
        """Gửi tin nhắn và nhận phản hồi từ Supervisor"""
        print(f"\n👤 User: {user_msg}")
        print("─" * 60)

        # Thêm vào history
        self.history.append({"role": "user", "content": user_msg})

        # ── XỬ LÝ THEO STATE ──────────────────────────────────────────────

        # Đang chờ xác nhận → kiểm tra
        if self.state == "awaiting_confirm":
            if self._is_confirmation(user_msg):
                return self._handle_dispatch_confirmed()
            else:
                # Khách muốn sửa → quay về collecting
                self.state = "collecting"

        # Phân loại mode nếu đang idle
        if self.state == "idle":
            mode = self._detect_mode(user_msg)
            if mode == "dispatch_candidate":
                self.state = "collecting"
                self.pending_request = {"original": user_msg}

        # ── BUILD CONTEXT ──────────────────────────────────────────────────
        context_data = self._get_context_data(user_msg)

        # ── GỌI LLM ───────────────────────────────────────────────────────
        system_prompt = build_system_prompt(self.profile, context_data)
        messages = [{"role": "system", "content": system_prompt}] + self.history

        response = call_groq(messages)

        # ── PARSE KẾT QUẢ ─────────────────────────────────────────────────
        # Kiểm tra xem LLM có tóm tắt và hỏi xác nhận không
        if self.state == "collecting":
            # Nếu response có tóm tắt dạng "Tôi sẽ..." hoặc "Để xác nhận..."
            confirm_phrases = ["xác nhận", "đúng không", "có muốn tôi", "bắt đầu không", "chạy không"]
            if any(p in response.lower() for p in confirm_phrases):
                self.state = "awaiting_confirm"

        # Kiểm tra dispatch JSON trong response
        dispatch_data = self._extract_dispatch(response)
        if dispatch_data:
            self.state = "idle"
            self.pending_request = {}
            display = self._format_dispatch_result(dispatch_data)
            self.history.append({"role": "assistant", "content": response})
            print(f"🤖 Supervisor: {response}")
            print(f"\n{display}")
            return response

        # Reset state nếu chế độ 1
        if self.state == "idle" or (self.state == "collecting" and "awaiting" not in self.state):
            # Không reset nếu đang thu thập
            pass

        self.history.append({"role": "assistant", "content": response})
        
        # Hiển thị state indicator
        state_icon = {"idle": "💬", "collecting": "📋", "awaiting_confirm": "✋"}.get(self.state, "💬")
        print(f"🤖 Supervisor [{state_icon} {self.state}]: {response}\n")
        return response

    def _extract_dispatch(self, text: str) -> Optional[dict]:
        """Trích xuất JSON dispatch từ response nếu có"""
        pattern = r'```json\s*(\{.*?\})\s*```'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if data.get("action") == "dispatch":
                    return data
            except:
                pass
        return None

    def _handle_dispatch_confirmed(self) -> str:
        """Xử lý khi khách xác nhận dispatch"""
        print("🚀 Khách xác nhận — Đang tạo dispatch plan...")
        
        confirm_prompt = [
            {
                "role": "system",
                "content": f"""Khách vừa xác nhận yêu cầu. Dựa trên hội thoại, hãy:
1. Nói ngắn "Đã xác nhận! Đang khởi động..." 
2. Trả về JSON dispatch plan với format:
```json
{{
  "action": "dispatch",
  "summary": "mô tả ngắn yêu cầu",
  "agents": ["danh sách agent cần chạy"],
  "channel": "kênh đăng",
  "tone": "tone giọng",
  "schedule": "thời gian đăng",
  "special_message": "thông điệp đặc biệt nếu có"
}}
```

Agent mapping:
- Facebook post / caption → ["research", "social", "image", "qa", "publisher"]  
- Blog SEO → ["research", "blog", "qa", "publisher"]
- Quảng cáo / Ads → ["research", "ads", "qa", "publisher"]
- Full campaign → ["research", "blog", "ads", "social", "image", "qa", "publisher"]
- Chỉ research → ["research", "report"]

Hồ sơ doanh nghiệp: {json.dumps(self.profile, ensure_ascii=False)}"""
            }
        ] + self.history + [{"role": "user", "content": "Xác nhận, chạy đi!"}]

        response = call_groq(confirm_prompt, temperature=0.3)
        
        dispatch_data = self._extract_dispatch(response)
        
        self.history.append({"role": "user", "content": "Xác nhận"})
        self.history.append({"role": "assistant", "content": response})
        self.state = "idle"
        self.pending_request = {}

        print(f"🤖 Supervisor: {response}")
        
        if dispatch_data:
            print(f"\n{self._format_dispatch_result(dispatch_data)}")

        return response

    def _format_dispatch_result(self, data: dict) -> str:
        """Format hiển thị dispatch result"""
        agents_str = " → ".join(data.get("agents", []))
        lines = [
            "━" * 60,
            "🚀 DISPATCH PLAN",
            "━" * 60,
            f"📋 Yêu cầu  : {data.get('summary', 'N/A')}",
            f"🤖 Agents   : {agents_str}",
            f"📣 Kênh     : {data.get('channel', 'N/A')}",
            f"🎯 Tone     : {data.get('tone', 'N/A')}",
            f"⏰ Lịch đăng: {data.get('schedule', 'N/A')}",
            f"💬 Thông điệp: {data.get('special_message', 'Không có')}",
            "━" * 60,
            "✅ Giai đoạn 2 đã được khởi động (mock)",
        ]
        return "\n".join(lines)

    def reset(self):
        """Xoá toàn bộ lịch sử và reset state"""
        self.history = []
        self.state = "idle"
        self.pending_request = {}
        print("🔄 Supervisor đã reset — lịch sử hội thoại đã xoá")

    @property
    def status(self):
        """Xem trạng thái hiện tại"""
        print(f"State: {self.state}")
        print(f"History: {len(self.history)} messages")
        print(f"Pending: {self.pending_request}")


# ─── DEMO RUNNER ──────────────────────────────────────────────────────────────

def run_demo():
    """Chạy demo các tình huống từ spec"""
    print("=" * 60)
    print("  SUPERVISOR AI DEMO — Marketing Automation")
    print("=" * 60)

    sup = SupervisorAgent()

    test_cases = [
        # Chế độ 1 — tự xử
        ("T1 - Hỏi thông tin",     "Tháng 7 có ngày lễ gì đáng đăng không?"),
        ("T2 - Brainstorm",        "Hay là mình làm gì đó cho mùa hè nhỉ..."),
        ("T5 - Lịch sử sản xuất",  "Tháng này mình đã đăng bao nhiêu bài rồi?"),
        ("T7 - Token còn lại",     "Tháng này còn bao nhiêu token?"),
        # Chế độ 2 — dispatch
        ("T3 - Ra lệnh (step 1)",  "Làm bài đăng Facebook cho bánh mì thịt nướng hôm nay, tone vui"),
    ]

    for label, msg in test_cases:
        print(f"\n{'═'*60}")
        print(f"  TEST: {label}")
        print(f"{'═'*60}")
        sup.chat(msg)
        input("[ Nhấn Enter để tiếp tục... ]")

    print("\n\n--- Tiếp tục luồng T3 (trả lời câu hỏi thiếu info) ---")
    sup.chat("Không có ưu đãi gì đặc biệt")
    input("[ Nhấn Enter để xác nhận dispatch... ]")
    sup.chat("Ok chạy đi")


# ─── INTERACTIVE MODE ─────────────────────────────────────────────────────────

def interactive():
    """Chạy interactive chat trong Jupyter"""
    sup = SupervisorAgent()
    print("\nGõ 'exit' để thoát, 'reset' để xoá lịch sử\n")
    while True:
        try:
            msg = input("👤 Bạn: ").strip()
            if not msg:
                continue
            if msg.lower() == "exit":
                print("👋 Tạm biệt!")
                break
            if msg.lower() == "reset":
                sup.reset()
                continue
            if msg.lower() == "status":
                sup.status
                continue
            sup.chat(msg)
        except KeyboardInterrupt:
            print("\n👋 Tạm biệt!")
            break


# ─── JUPYTER QUICK START ──────────────────────────────────────────────────────

if __name__ == "__main__":
    # Chạy demo tự động
    run_demo()