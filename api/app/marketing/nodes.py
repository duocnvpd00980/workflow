from langgraph.types import interrupt
from typing import TYPE_CHECKING
from groq import Groq
import uuid

from .config import settings

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
        "total_cost": current.get("total_cost", 0.0),
        "calls": current.get("calls", []) + [{"node": node, "tokens": tokens}],
    }


# ── Nodes ────────────────────────────────────────────────────────────────────

def prepare(state: dict) -> dict:
    r = state["request"].lower()
    template = (
        "social"   if any(w in r for w in ["tweet", "caption", "post", "social", "instagram", "fb"]) else
        "blog"     if any(w in r for w in ["article", "blog", "write", "bài viết"]) else
        "image"    if any(w in r for w in ["image", "visual", "design", "ảnh", "hình"]) else
        "research" if any(w in r for w in ["research", "report", "analyze", "nghiên cứu"]) else
        "social"
    )
    context = {"brand_voice": "Professional, innovative", "tone": "Friendly", "credits": 100}
    if context["credits"] <= 0:
        return {"error": "fatal", "context": context, "template": template}
    return {
        "template": template,
        "context": context,
        "usage": {"total_tokens": 0, "total_cost": 0.0, "calls": []},
        "approved": False,
        "error": None,
    }


def execute_social(state: dict) -> dict:
    platform = "Twitter" if "tweet" in state["request"].lower() else "Facebook"
    caption = call_groq(
        f"Write a {platform} caption for: {state['request']}\n"
        f"Max 280 chars. Tone: {state['context']['tone']}. "
        f"Add 2-3 hashtags. Brand voice: {state['context']['brand_voice']}",
        max_tokens=200,
    )
    if caption.startswith("[ERROR:"):
        return {"error": caption[7:-1]}
    return {
        "draft": {"content": caption, "metadata": {"platform": platform, "type": "social"}, "version": 1},
        "usage": _merge_usage(state["usage"], 150, "social"),
    }


def execute_blog(state: dict) -> dict:
    draft = call_groq(
        f"Write a blog post about: {state['request']}\n"
        f"Tone: {state['context']['tone']}. Brand voice: {state['context']['brand_voice']}\n"
        f"Include H2 headings. Length: 500-800 words.",
        max_tokens=800,
    )
    if draft.startswith("[ERROR:"):
        return {"error": draft[7:-1]}
    return {
        "draft": {"content": draft, "metadata": {"type": "blog", "word_count": len(draft.split())}, "version": 1},
        "usage": _merge_usage(state["usage"], 600, "blog"),
    }


def execute_image(state: dict) -> dict:
    prompt = call_groq(
        f"Create an image generation prompt for: {state['request']}\n"
        f"Style: professional, on-brand. Be descriptive, 50-100 words.",
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
    report = call_groq(
        f"Research and write a comprehensive report on: {state['request']}\n"
        f"Include: summary, key findings, sources, confidence level.\n"
        f"Format with clear sections. Length: 400-600 words.",
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
        "approved": True,
        "publish_status": "published",
        "usage": _merge_usage(state["usage"], 500, "research"),
    }


def review_pause(state: dict) -> dict:
    action = interrupt({
        "status": "paused",
        "node": "review_pause",
        "draft": state["draft"],
        "usage": state["usage"],
        "session_id": state["session_id"],
    })
    if action.get("action") == "approve":
        return {"approved": True}
    if action.get("action") == "edit":
        return {
            "approved": True,
            "draft": {
                "content": action.get("content", state["draft"]["content"]),
                "metadata": state["draft"]["metadata"],
                "version": state["draft"]["version"] + 1,
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