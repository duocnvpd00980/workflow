"""
nodes.py — patched
──────────────────
CHANGE: `prepare()` now loads brand context from brand_voice_store
instead of hardcoding {"brand_voice": "Professional, innovative", "tone": "Friendly"}.

All other nodes unchanged — they consume state["context"] the same way.
"""

from langgraph.types import interrupt
from groq import Groq
import uuid
import logging
from app.brand.service import BrandProfileService
from app.db import AsyncSessionLocal

from .config import settings
# ── PATCH: import brand voice store ──────────────────────────────────────────

logger = logging.getLogger(__name__)

client = Groq(api_key=settings.GROQ_API_KEY)
MODEL = settings.GROQ_MODEL
LLM_TIMEOUT = 30


def call_groq(prompt: str, max_tokens: int = 500) -> str:
    try:
        msg = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=max_tokens,
            temperature=0.7,
            top_p=1,
            stop=None,
            timeout=LLM_TIMEOUT,
        )
        return msg.choices[0].message.content or "[No response]"
    except Exception as e:
        error_type = str(e).lower()
        if "timeout" in error_type:
            return "[ERROR:timeout]"
        if "rate" in error_type:
            return "[ERROR:rate_limit]"
        return "[ERROR:fatal]"


def _merge_usage(current: dict, tokens: int, node: str) -> dict:
    return {
        "total_tokens": current.get("total_tokens", 0) + tokens,
        "total_cost":   current.get("total_cost", 0.0),
        "calls":        current.get("calls", []) + [{"node": node, "tokens": tokens}],
    }


# ── Nodes ─────────────────────────────────────────────────────────────────────
# ── Nodes ─────────────────────────────────────────────────────────────────────
async def prepare(state: dict) -> dict:
    # 0. Tránh lỗi KeyError nếu 'request' không tồn tại
    r = state.get("request", "").lower()
    
    template = (
        "social"   if any(w in r for w in ["tweet", "caption", "post", "social", "instagram", "fb"]) else
        "blog"     if any(w in r for w in ["article", "blog", "write", "bài viết"]) else
        "image"    if any(w in r for w in ["image", "visual", "design", "ảnh", "hình"]) else
        "research" if any(w in r for w in ["research", "report", "analyze", "nghiên cứu"]) else
        "social"
    )

    brand_id = state.get("brand_id", "default")
    context = None

    # 1. Thử lấy dữ liệu từ Service trong DB
    try:
        async with AsyncSessionLocal() as db:
            scope = await BrandProfileService.get_writer_scope(db, brand_id)
            
        # Kiểm tra xem scope nhận về có thực sự tồn tại hay không
        if scope:
            # Lấy an toàn các sub-object để tránh AttributeError
            voice_rules = getattr(scope, "brand_voice_rules", None)
            
            context = {
                "brand_voice": getattr(scope, "positioning", "Chuyên nghiệp, sáng tạo công nghệ"),
                "tone": getattr(voice_rules, "tone_patterns", "Thân thiện, tin cậy"),
                "voice_rules": getattr(voice_rules, "forbidden_words", []),
                "cta_samples": getattr(voice_rules, "cta_patterns", ["Khám phá ngay"]),
                "target_audience": getattr(scope, "audience", ["Khách hàng đại chúng"]),
                "products": [],
                "core_message": "Giải pháp tự động hóa quy trình thông minh.",
                "credits": 100,
            }
    except Exception as e:
        logger.error(f"Lỗi kết nối hoặc truy vấn Database: {str(e)}")

    # 2. Cơ chế FALLBACK: Kích hoạt nếu lỗi DB HOẶC nếu DB không trả về data (scope là None)
    if not context:
        logger.warning(f"Không tìm thấy dữ liệu cho Brand ID '{brand_id}'. Đang nạp cấu hình mặc định.")
        context = {
            "brand_voice": "Chuyên nghiệp, sáng tạo, hướng tới tương lai công nghệ",
            "tone": "Thân thiện, rõ ràng, giàu năng lượng",
            "voice_rules": ["cam kết 100%", "rẻ nhất thị trường"],
            "cta_samples": ["Trải nghiệm miễn phí", "Tìm hiểu thêm tại đây"],
            "target_audience": ["Marketers", "SaaS Users"],
            "products": ["Hệ thống Workflow Agent"],
            "core_message": "Tự động hóa công việc bằng AI Agent.",
            "credits": 100,
        }

    # 3. Kiểm tra Credits điều hướng luồng lỗi
    if context["credits"] <= 0:
        return {
            **state,  # Giữ lại các thông tin gốc của state
            "error": "fatal", 
            "context": context, 
            "template": template
        }

    # 4. Trả về state cập nhật (Hợp nhất dữ liệu mới vào state cũ thay vì ghi đè mất state)
    return {
        **state,
        "template": template,
        "context":  context,
        "usage":    {"total_tokens": 0, "total_cost": 0.0, "calls": []},
        "approved": False,
        "error":    None,
    }

def _build_brand_block(ctx: dict) -> str:
    """
    Helper: build a rich brand context block for prompt injection.
    Used by execute_* nodes to make prompts brand-aware.
    """
    rules = "\n".join(f"  - {r}" for r in ctx.get("voice_rules", []))
    ctas  = ", ".join(ctx.get("cta_samples", []))
    prods = ", ".join(ctx.get("products", []))
    audience = ", ".join(ctx.get("target_audience", []))
    
    # Dùng .get() an toàn cho toàn bộ các trường khác
    brand_voice = ctx.get("brand_voice", "Chuyên nghiệp")
    tone = ctx.get("tone", "Thân thiện")
    cta_style = ctx.get("cta_style", "Trực tiếp, ngắn gọn") # Không lo KeyError nữa
    core_message = ctx.get("core_message", "")

    return (
        f"Brand Voice: {brand_voice} ({tone})\n"
        f"CTA Style: {cta_style}\n"
        f"Core Message: {core_message}\n"
        f"Products: {prods}\n"
        f"Target Audience: {audience}\n"
        f"Voice Rules:\n{rules}\n"
        f"Suggested CTAs: {ctas}"
    )


def execute_social(state: dict) -> dict:
    platform = "Twitter" if "tweet" in state["request"].lower() else "Facebook"
    ctx = state["context"]
    caption = call_groq(
        f"Write a {platform} caption for: {state['request']}\n"
        f"Max 280 chars. Add 2-3 hashtags.\n\n"
        f"=== Brand Context ===\n{_build_brand_block(ctx)}",
        max_tokens=200,
    )
    if caption.startswith("[ERROR:"):
        return {"error": caption[7:-1]}
    return {
        "draft": {"content": caption, "metadata": {"platform": platform, "type": "social"}, "version": 1},
        "usage": _merge_usage(state["usage"], 150, "social"),
    }


def execute_blog(state: dict) -> dict:
    ctx = state["context"]
    draft = call_groq(
        f"Write a blog post about: {state['request']}\n"
        f"Include H2 headings. Length: 500-800 words.\n\n"
        f"=== Brand Context ===\n{_build_brand_block(ctx)}",
        max_tokens=800,
    )
    if draft.startswith("[ERROR:"):
        return {"error": draft[7:-1]}
    return {
        "draft": {"content": draft, "metadata": {"type": "blog", "word_count": len(draft.split())}, "version": 1},
        "usage": _merge_usage(state["usage"], 600, "blog"),
    }


def execute_image(state: dict) -> dict:
    ctx = state["context"]
    prompt = call_groq(
        f"Create an image generation prompt for: {state['request']}\n"
        f"Style: {ctx.get('visual_style', 'professional')}, on-brand. Be descriptive, 50-100 words.\n\n"
        f"=== Brand Context ===\n{_build_brand_block(ctx)}",
        max_tokens=150,
    )
    if prompt.startswith("[ERROR:"):
        return {"error": prompt[7:-1]}
    return {
        "draft": {
            "content": f"Image prompt: {prompt}",
            "metadata": {
                "type": "image",
                "image_url": f"https://api.example.com/images/{uuid.uuid4().hex[:12]}.png",
                "prompt": prompt,
            },
            "version": 1,
        },
        "usage": _merge_usage(state["usage"], 120, "image"),
    }


def execute_research(state: dict) -> dict:
    ctx = state["context"]
    report = call_groq(
        f"Research and write a comprehensive report on: {state['request']}\n"
        f"Include: summary, key findings, sources, confidence level.\n"
        f"Format with clear sections. Length: 400-600 words.\n\n"
        f"=== Brand Context ===\n{_build_brand_block(ctx)}",
        max_tokens=700,
    )
    if report.startswith("[ERROR:"):
        return {"error": report[7:-1]}
    return {
        "draft": {
            "content": report,
            "metadata": {"type": "research", "sources": [], "confidence": "high"},
            "version": 1,
        },
        "approved":       True,
        "publish_status": "published",
        "usage":          _merge_usage(state["usage"], 500, "research"),
    }


def review_pause(state: dict) -> dict:
    action = interrupt({
        "status":     "paused",
        "node":       "review_pause",
        "draft":      state["draft"],
        "usage":      state["usage"],
        "session_id": state["session_id"],
    })
    if action.get("action") == "approve":
        return {"approved": True}
    if action.get("action") == "edit":
        return {
            "approved": True,
            "draft": {
                "content":  action.get("content", state["draft"]["content"]),
                "metadata": state["draft"]["metadata"],
                "version":  state["draft"]["version"] + 1,
            },
        }
    return {"approved": False}


def publish(state: dict) -> dict:
    try:
        return {"publish_status": "published"}
    except Exception:
        return {"publish_status": "failed"}


def save(state: dict) -> dict:
    return {}


# ── Edge conditions ───────────────────────────────────────────────────────────

def select_template(state: dict) -> str:
    if state.get("error"):
        return "save"
    return f"execute_{state['template']}"


def route_after_review(state: dict) -> str:
    if state.get("error") or not state.get("approved"):
        return "save"
    return "publish"