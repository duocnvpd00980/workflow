from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Literal, Optional
import jinja2
from langgraph.types import interrupt

from app.marketing.rag_context import fetch_rag_context
from app.llm_clients import call_gemini_imagen, call_groq
from app.db import AsyncSessionLocal
from app.brand.brand_voice_prompt import get_brand_prompt_by_id
from datetime import datetime

# ── IMPORT TẤT CẢ MODELS TRƯỚC KHI DÙNG ──────────────────────────
import app.business.models
import app.brand.models
import app.chat.models
import app.rag.models
import app.marketing.models
import app.research.models
import app.tasks.models




logger = logging.getLogger(__name__)

# ── Load Jinja2 templates ─────────────────────────────────────

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_TEMPLATE_DIR),
    autoescape=False,
)

def _render_prompt(template_name: str, **kwargs) -> str:
    """Render prompt từ Jinja2 template."""
    template = _jinja_env.get_template(template_name)
    return template.render(**kwargs)


# ── Helper: merge usage ───────────────────────────────────────

def _merge_usage(current: dict, tokens: int, node: str) -> dict:
    current = current or {"total_tokens": 0, "total_cost": 0.0, "calls": []}
    return {
        "total_tokens": current.get("total_tokens", 0) + tokens,
        "total_cost": 0.0,
        "calls": current.get("calls", []) + [{"node": node, "tokens": tokens}],
    }



async def _get_brand_prompt_async(brand_id: str, content_type: str, user_input: dict):
    """Helper async để gọi get_brand_prompt_by_id."""
    from app.db import AsyncSessionLocal
    from app.brand.brand_voice_prompt import get_brand_prompt_by_id
    
    async with AsyncSessionLocal() as db:
        return await get_brand_prompt_by_id(
            brand_id=brand_id,
            content_type=content_type,
            user_input=user_input,
            db=db,
        )
    
def _compress_research_for_prompt_sync(research_data: dict, max_chars: int = 3200) -> str:
    """
    Nén research data thành context string để inject vào prompt.
    Sync version — gọi được từ bất kỳ đâu.
    """
    if not research_data:
        return ""
    
    parts = []
    
    # SERP insights
    serp = research_data.get("result", {}).get("serp_data", {})
    if serp.get("keyword_cluster"):
        parts.append(f"Từ khóa khách tìm: {', '.join(serp['keyword_cluster'][:5])}")
    if serp.get("intent"):
        parts.append(f"Search intent: {', '.join(serp['intent'][:3])}")
    
    # Top posts summary
    posts = research_data.get("posts", [])
    top_posts = sorted(posts, key=lambda p: len(p.get("content", "")), reverse=True)[:2]
    for p in top_posts:
        content = p.get("content", "")[:200].replace("\n", " ")
        parts.append(f"Bài viết tham khảo: {content}...")
    
    # FB brand info
    fb = research_data.get("result", {}).get("fb_brand", {})
    if fb.get("intro"):
        intro = fb["intro"][:300].replace("\n", " ")
        parts.append(f"Giới thiệu brand: {intro}")
    
    result = " | ".join(parts)
    if len(result) > max_chars:
        result = result[:max_chars]
    
    return result




# ══════════════════════════════════════════════════════════════
#  BLOG NODES — với LOG chi tiết
# ══════════════════════════════════════════════════════════════
_ALLOWED_FUNCTIONS = {"blog_post", "email_sale", "social_media"}


def blog_prepare(state: dict) -> dict:
    """Chỉ gọi get_brand_prompt_by_id — đã làm sẵn hết."""
    print("\n" + "="*60)
    print("🟢 NODE: blog_prepare")
    print("="*60)

    started = time.time()

    user_request = state.get("request", "")
    function     = state.get("function", "blog_post")
    brand_id     = state.get("brand_id")
    selected_length = state.get("length", "vừa")
    selected_tone   = state.get("tone", "chuyên nghiệp")

    if not brand_id:
        return {**state, "error": "missing_brand_id", "system_prompt": None, "needs_image": False}

    if function not in _ALLOWED_FUNCTIONS:
        return {**state, "error": f"invalid_function: {function}", "system_prompt": None, "needs_image": False}

    image_map  = {"blog_post": True, "product_description": True, "website_copy": False}
    needs_image = image_map.get(function, False)

    
    try:
        research_context = _compress_research_for_prompt_sync(state.get("research_data", {}))
        user_input = {"topic": user_request, "length": selected_length, "tone": selected_tone}
        
        # Chạy async function trong sync context
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # Đang trong event loop → chạy trong thread mới
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    _get_brand_prompt_async(brand_id, function, user_input)
                )
                system_prompt = future.result()
        except RuntimeError:
            # Không có event loop → chạy trực tiếp
            if research_context:
                user_input["additional_instructions"] = (
                    user_input.get("additional_instructions", "") 
                    + f"\n\nNGỮ CẢNH TỪ RESEARCH: {research_context}"
                )

            system_prompt = asyncio.run(_get_brand_prompt_async(brand_id, function, user_input))
        
        print(f"✅ get_brand_prompt_by_id success | prompt length: {len(system_prompt)}")
    except Exception as e:
        logger.exception(f"[BLOG_PREPARE ERROR] brand_id={brand_id}: {e}")
        return {**state, "error": "brand_db_error", "system_prompt": None, "needs_image": needs_image}

    if not system_prompt:
        return {**state, "error": "empty_system_prompt", "system_prompt": None, "needs_image": needs_image}

    elapsed = round(time.time() - started, 3)
    print(f"⏱️  Elapsed: {elapsed}s | needs_image={needs_image}")
    print(f"------------------------------{system_prompt}---------------------")
    return {
        **state,
        "function":      function,
        "needs_image":   needs_image,
        "system_prompt": system_prompt,
        "enriched_topic": user_request,
        "usage":  state.get("usage") or {"total_tokens": 0, "total_cost": 0.0, "calls": []},
        "approved": False,
        "error":    None,
    }





def execute_blog_content(state: dict) -> dict:
    """Viết nội dung — handle error chuẩn hóa từ Groq."""

    print("\n" + "="*60)
    print("🟢 NODE: execute_blog_content")
    print("="*60)

    function = state.get("function", "blog_post")
    request = state.get("request", "")
    system_prompt = state.get("system_prompt", "")
    enriched_topic = state.get("enriched_topic", request)

    if not system_prompt:
        return {
            **state,
            "status": "failed",
            "error": "missing_system_prompt",
            "draft": {
                "content": "",
                "metadata": {"status": "error"},
                "version": 0,
            },
            "needs_image": False,
        }

    if function not in _ALLOWED_FUNCTIONS:
        return {
            **state,
            "status": "failed",
            "error": f"invalid_function: {function}",
        }

    prompt = _render_prompt(
        f"blog_{function}.j2",
        topic=enriched_topic,
        system_prompt=system_prompt,
    )

    print(f"📝 PROMPT LENGTH: {len(prompt)}")

    # 🔥 IMPORTANT: HANDLE EXCEPTION HERE
    try:
        raw_text = call_groq(prompt, max_tokens=3000, temperature=0.7, gpt=True)

    except PermissionError as e:
        return {
            **state,
            "status": "failed",
            "error": str(e),
            "error_type": "auth",
            "needs_image": False,
            "draft": {
                "content": "",
                "metadata": {"status": "error", "type": "auth"},
                "version": 0,
            },
        }

    except TimeoutError as e:
        return {
            **state,
            "status": "failed",
            "error": str(e),
            "error_type": "timeout",
            "needs_image": False,
        }

    except RuntimeError as e:
        return {
            **state,
            "status": "failed",
            "error": str(e),
            "error_type": "runtime",
            "needs_image": False,
        }

    # =========================
    # parse normal output
    # =========================

    title = None
    for line in raw_text.split("\n"):
        s = line.strip()
        if s.startswith("# "):
            title = s[2:]
            break
        if s.startswith("## "):
            title = s[3:]
            break

    if not title:
        title = raw_text.strip().split("\n")[0][:100]

    images = re.findall(r"\[IMAGE:\s*(.*?)\]", raw_text)

    return {
        **state,
        "status": "success",
        "title": title,
        "content": raw_text.strip(),
        "draft": {
            "content": raw_text.strip(),
            "title": title,
            "metadata": {
                "type": function,
                "word_count": len(raw_text.split()),
                "images": images,
            },
            "version": (state.get("draft") or {}).get("version", 0) + 1,
        },
        "error": None,
        "error_type": None,
        "usage": _merge_usage(
            state.get("usage", {}),
            len(raw_text.split()),
            f"blog_{function}"
        ),
    }


def execute_blog_image(state: dict) -> dict:
    """Tạo ảnh cho blog."""
    print("\n" + "="*60)
    print("🟢 NODE: execute_blog_image")
    print("="*60)
    
    session_id = state.get("session_id", "default")
    save_path = Path("app/media") / session_id
    os.makedirs(save_path, exist_ok=True)
    
    draft = state.get("draft") or {"content": "", "metadata": {}, "version": 0}
    content = draft.get("content", "")
    title = state.get("title", "")

    print(f"📥 Input:")
    print(f"   - session_id: {session_id}")
    print(f"   - title: {title}")
    print(f"   - content length: {len(content)}")
    print(f"   - save_path: {save_path}")

    def generate_and_save(match):
        desc = match.group(1)
        print(f"🎨 Generating image for: '{desc}'")
        try:
            img_bytes = call_gemini_imagen(f"Professional marketing photo of: {desc}")
            
            file_name = f"image_{uuid.uuid4().hex[:8]}.png"
            file_full_path = save_path / file_name
            with open(file_full_path, "wb") as f:
                f.write(img_bytes)
            
            file_size = file_full_path.stat().st_size
            print(f"✅ Image saved: {file_name} ({file_size} bytes)")
                
            return f"![{desc}](/media/{session_id}/{file_name})"
            
        except Exception as e:
            print(f"❌ Image gen failed: {e}")
            return f"[Ảnh minh họa: {desc}]"

    # Match [IMAGE: ...] hoặc [PLACEHOLDER_IMAGE_X: ...]
    final_content = re.sub(
        r"\[(?:PLACEHOLDER_IMAGE_\d+|IMAGE):\s*(.*?)\]",
        generate_and_save,
        content
    )
    
    # Check if any replacement happened
    images_created = final_content != content
    print(f"🖼️  Images created: {images_created}")

    # Fallback: create thumbnail from title if no placeholders
    image_url = None
    if not images_created and title:
        print(f"🎨 No placeholders, creating thumbnail from title...")
        try:
            img_bytes = call_gemini_imagen(f"Professional marketing thumbnail for: {title}")
            file_name = f"thumbnail_{uuid.uuid4().hex[:8]}.png"
            file_full_path = save_path / file_name
            with open(file_full_path, "wb") as f:
                f.write(img_bytes)
            
            image_url = f"/media/{session_id}/{file_name}"
            print(f"✅ Thumbnail created: {image_url}")
        except Exception as e:
            print(f"❌ Thumbnail failed: {e}")
            image_url = None
    else:
        # Extract first image URL
        img_match = re.search(r'!\[.*?\]\((/media/.*?)\)', final_content)
        image_url = img_match.group(1) if img_match else None
        if image_url:
            print(f"✅ Found image URL: {image_url}")

    print(f"✅ Output: image_url={image_url}")

    return {
        **state,
        "image_url": image_url,
        "draft": {**draft, "content": final_content},
        "usage": _merge_usage(state.get("usage", {}), 150, "blog_image"),
    }

def blog_review_pause(state: dict) -> dict:
    """Human-in-the-loop: pause để user review."""
    print("\n" + "="*60)
    print("🟡 NODE: blog_review_pause (WAITING FOR USER)")
    print("="*60)

    action = interrupt({
        "status":     "paused",
        "node":       "blog_review_pause",
        "draft":      state.get("draft"),
        "title":      state.get("title"),
        "image_url":  state.get("image_url"),
        "usage":      state.get("usage"),
        "session_id": state.get("session_id"),
    })

    print(f"📥 User action received: {action}")
    user_action = action.get("action", "save")

    if user_action == "approve":
        print(f"✅ User APPROVED")
        
        current_draft = state.get("draft") or {}
        
        # ✅ FIX: Nếu user gửi kèm content đã edit → cập nhật draft
        edited_content = action.get("content")
        if edited_content:
            current_draft = {
                **current_draft,
                "content": edited_content,
            }
            print(f"📝 Content updated by user ({len(edited_content)} chars)")
        
        return {
            **state,
            "approved": True,
            "draft": current_draft,   # ✅ draft đã có content mới
            "content": edited_content or state.get("content"),  # ✅ sync cả field content
            "error": None,
        }

    elif user_action == "revise":
        feedback = action.get("feedback", "Hãy tối ưu lại bài viết.")
        print(f"🔄 User REVISE: {feedback}")
        return {
            **state,
            "approved": False,
            "revision_note": feedback,
            "request": state.get("request", "") + "\n\nRevision:\n" + feedback,
            "error": None,
        }

    print(f"💾 User SAVE (fallback)")
    return {**state, "approved": False, "error": None}


def blog_save(state: dict) -> dict:
    """Gói draft cuối + lưu."""
    print("\n" + "="*60)
    print("🟢 NODE: blog_save")
    print("="*60)

    current_draft = state.get("draft") or {}

    # ✅ FIX: Ưu tiên draft["content"] — đây là source of truth sau khi user edit
    final_content = current_draft.get("content") or state.get("content")

    draft = {
        "group":     "blog_web",
        "function":  state.get("function"),
        "title":     current_draft.get("title") or state.get("title"),
        "content":   final_content,   # ✅ lấy từ draft, không phải state["content"]
        "image_url": state.get("image_url"),
        "seo_meta":  state.get("seo_meta"),
        "approved":  state.get("approved", False),
    }

    print(f"💾 Saving draft:")
    print(f"   - title: {draft['title']}")
    print(f"   - content length: {len(draft['content'] or '')}")
    print(f"   - approved: {draft['approved']}")

    return {
        **state,
        "draft": draft,
        "publish_status": "published" if state.get("approved") else "saved",
        "status_action": None,
    }

# ── Conditional Edges ───────────────────────────────────────

def blog_needs_visual(state: dict):
    if state.get("status") == "failed":
        return "error"

    return "needs_image" if state.get("needs_image") else "no_image"


def blog_route_after_review(state: dict) -> Literal["approve", "revise"]:
    """Sau review: user đồng ý hay sửa?"""
    if state.get("approved", False):
        print(f"🔀 EDGE: blog_route_after_review → approve")
        return "approve"
    if state.get("revision_note"):
        print(f"🔀 EDGE: blog_route_after_review → revise")
        return "revise"
    print(f"🔀 EDGE: blog_route_after_review → approve (fallback)")
    return "approve"


async def blog_handle_error(state: dict) -> dict:
    print("\n" + "="*60)
    print("🔴 NODE: blog_handle_error")
    print("="*60)

    session_id = state.get("session_id")
    error      = state.get("error", "unknown_error")
    error_type = state.get("error_type", "unknown")

    print(f"   - session_id: {session_id}")
    print(f"   - error: {error}")
    print(f"   - error_type: {error_type}")

    # ✅ error column là String(50) — chỉ lưu short code
    ERROR_CODES = {
        "GROQ_AUTH_401: Invalid API key or unauthorized": "auth_failed",
        "missing_system_prompt":  "missing_prompt",
        "missing_brand_id":       "missing_brand",
        "brand_db_error":         "db_error",
        "GROQ_TIMEOUT":           "timeout",
        "GROQ_RATE_LIMIT":        "rate_limit",
    }
    error_code = ERROR_CODES.get(error, error[:50])  # truncate đến 50 ký tự

    if session_id:
        try:
            from sqlalchemy import text
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        UPDATE workflow_sessions
                        SET status         = :status,
                            error          = :error,
                            publish_status = :publish_status,
                            updated_at     = :updated_at
                        WHERE id = :id
                    """),
                    {
                        "status":         "failed",
                        "error":          error_code,
                        "publish_status": "failed",
                        "updated_at":     datetime.now(),
                        "id":             session_id,
                    }
                )
                await db.commit()
                print(f"✅ DB updated: status=failed | error={error_code}")
        except Exception as e:
            logger.exception(f"[blog_handle_error] DB update failed: {e}")

    return {
        **state,
        "status":         "failed",
        "publish_status": "failed",
        "error":          error_code,  # trả về code ngắn
        "draft":          None,
    }


