from langgraph.types import interrupt
from google import genai
from google.genai import types
import uuid
import logging
from app.db import AsyncSessionLocal
from app.config import get_settings
from groq import Groq
import os
from pathlib import Path
import re
import uuid
from pathlib import Path
import requests

# ── LangGraph Nodes Xử Lý ───────────────────────────────────────────────────────
from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload

from app.brand.models import Brand, BrandProfile, BrandVoiceRule, BrandMessaging
from app.research.models import ResearchResult
from app.rag.models import DocumentSource, DocumentPage, HotelRoom

import requests


logger = logging.getLogger(__name__)
_s = get_settings()

gemini_client = genai.Client(api_key=_s.GEMINI_API_KEY)
GEMINI_MODEL = _s.GEMINI_MODEL

groq_client = Groq(api_key=_s.GROQ_API_KEY)
GROQ_MODEL = _s.GROQ_MODEL

LLM_TIMEOUT = 30

MEDIA_ROOT = Path("app/media")


def call_groq(prompt: str, max_tokens: int = 500) -> str:
    try:
        msg = groq_client.chat.completions.create(
            model=GROQ_MODEL,
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
    
def call_gemini(prompt: str, max_tokens: int = 1000) -> str:
    """Helper: Gọi trực tiếp mô hình Gemini 2.5 Flash xử lý văn bản"""
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=0.7,
                top_p=0.95,
            ),
        )
        return response.text or "[No response]"
    except Exception as e:
        error_type = str(e).lower()
        logger.error(f"Lỗi gọi Gemini API: {str(e)}")
        if "timeout" in error_type:
            return "[ERROR:timeout]"
        if "rate" in error_type or "429" in error_type:
            return "[ERROR:rate_limit]"
        return "[ERROR:fatal]"



def call_gemini_imagen(prompt_desc: str) -> bytes:
    """Gọi Pollinations API bằng cách xác thực qua Header"""
    try:
        # URL của Pollinations hỗ trợ prompt tiếng Anh
        # Thay thế khoảng trắng bằng %20 để URL hợp lệ
        safe_prompt = prompt_desc.replace(" ", "%20")
        url = f"https://gen.pollinations.ai/image/{safe_prompt}?model=flux&width=1024&height=576&nologo=true"
        
        # Header xác thực theo tài liệu của Pollinations
        headers = {
            "Authorization": "Bearer sk_J68kYhDowZ8FTDPupSlolhNEcnqsWZ1P"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"Pollinations Error: {response.status_code} - {response.text}")
            raise Exception("Auth Failed")
            
    except Exception as e:
        logger.error(f"Lỗi hệ thống tạo ảnh: {str(e)}")
        # Trả về placeholder nếu lỗi
        return requests.get("https://via.placeholder.com/1024x576?text=Image+Unavailable").content
    
def filter_knowledge_with_groq(user_request: str, raw_knowledge: list) -> str:
    """
    Filters raw RAG context using advanced System Prompt Engineering (XML tagging, 
    Role anchoring, and strict context extraction instructions) via Groq.
    """
    if not raw_knowledge:
        return "No relevant context found."
    if not user_request:
        return str(raw_knowledge)

    raw_context = str(raw_knowledge)

    # SYSTEM PROMPT: Thiết lập vai trò chuyên gia, luật và cấu trúc dữ liệu (Kiểu Jasper/Copy.ai)
    system_prompt = (
        "You are an Elite Context Optimization Engine. Your sole purpose is to analyze a user's content creation request "
        "and surgically extract ONLY the highly relevant facts, data points, or room/service specifications from the "
        "provided raw database dump.\n\n"
        "STRICT OPERATIONAL RULES:\n"
        "1. Strip out all irrelevant, duplicated, or off-topic data items.\n"
        "2. Do NOT summarize or lose the core parameters (e.g., prices, specific amenities, dimensions).\n"
        "3. Output ONLY the refined factual context. No conversational filler, no 'Here is the filtered data', no markdown commentary.\n"
        "4. Maintain a clear, dense, professional structure optimized for downstream Copywriting LLMs."
    )

    # USER PROMPT: Truyền dữ liệu qua các thẻ XML bọc cô lập để tránh Prompt Injection
    user_prompt = f"""
    <user_intent>
    {user_request}
    </user_intent>

    <raw_context_data>
    {raw_context}
    </raw_context_data>

    Instruction: Review the <user_intent> and filter the <raw_context_data>. Output the final optimized context block now.
    """

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,  # Tuyệt đối không cho sáng tạo ở bước lọc dữ liệu
            timeout=LLM_TIMEOUT
        )
        
        filtered_text = response.choices[0].message.content.strip()
        return filtered_text

    except Exception as e:
        logger.error(f"⚠️ Groq Context Filtering Error: {str(e)}. Falling back to raw data.")
        return raw_context
    


def _merge_usage(current: dict, tokens: int, node: str) -> dict:
    current = current or {"total_tokens": 0, "total_cost": 0.0, "calls": []}
    return {
        "total_tokens": current.get("total_tokens", 0) + tokens,
        "total_cost":   0.0,
        "calls":        current.get("calls", []) + [{"node": node, "tokens": tokens}],
    }


def _build_brand_block(brand_profile: dict) -> str:
    """🌟 ĐÃ SỬA: Nhận trực tiếp dict brand_profile phẳng từ State"""
    rules = "\n".join(f"  - {r}" for r in brand_profile.get("tone_patterns", []))
    ctas  = ", ".join(brand_profile.get("cta_samples", []))
    forbidden = ", ".join(brand_profile.get("forbidden_words", []))
    
    brand_name = brand_profile.get("brand_name", "Hệ thống")
    positioning = brand_profile.get("positioning", "Chuyên nghiệp")
    audience = brand_profile.get("target_audience", "Mọi đối tượng")

    return (
        f"Brand Name: {brand_name}\n"
        f"Positioning: {positioning}\n"
        f"Target Audience: {audience}\n"
        f"Voice Rules (Tone): \n{rules}\n"
        f"Forbidden Words: {forbidden}\n"
        f"Suggested CTAs: {ctas}"
    )


def _build_memory_block(memory_history: list) -> str:
    if not memory_history:
        return "Không có lịch sử chỉnh sửa trước đó (Bản Draft đầu tiên)."
    
    block = "Các yêu cầu chỉnh sửa trước đó của người dùng:\n"
    for i, mem in enumerate(memory_history, 1):
        block += f"  - Lượt {i}: Khách hàng yêu cầu: '{mem.get('user_feedback', '')}'\n"
    return block



async def prepare(state: dict) -> dict:
    import json, time

    started = time.time()
    r = state.get("request", "").lower()
    business_id = state.get("business_id")
    brand_id    = state.get("brand_id")

    template = (
        "social"   if any(x in r for x in ["tweet","caption","post","social","instagram","fb"]) else
        "blog"     if any(x in r for x in ["article","blog","write","bài viết"]) else
        "image"    if any(x in r for x in ["image","visual","design","ảnh","hình"]) else
        "research" if any(x in r for x in ["research","report","analyze","nghiên cứu"]) else
        "social"
    )

    brand_profile, research_data, knowledge_rag = {}, {}, []

    try:
        async with AsyncSessionLocal() as db:

            # ── 1. Brand theo brand_id (thuộc business đã chọn) ─────────────
            if brand_id:
                brand = (await db.execute(
                    select(Brand)
                    .where(Brand.id == brand_id, Brand.business_id == business_id)
                    .options(
                        joinedload(Brand.profile),
                        joinedload(Brand.voice_rules),
                        joinedload(Brand.messaging),
                    )
                )).scalars().one_or_none()

                if brand:
                    p    = brand.profile
                    rules = lambda t: [x.value for x in brand.voice_rules if x.rule_type == t]
                    msgs  = lambda t: [x.value for x in brand.messaging   if x.message_type == t]

                    brand_profile = {
                        "brand_name":      brand.name,
                        "positioning":     p.positioning     if p else "Chuyên nghiệp",
                        "target_audience": p.audience        if p else "Đại chúng",
                        "visual_identity": p.visual_identity if p else {},
                        "tone_patterns":   rules("tone_pattern")  or ["Thân thiện"],
                        "forbidden_words": rules("forbidden_word"),
                        "cta_samples":     rules("cta_pattern")   or ["Khám phá ngay"],
                        "pain_points":     msgs("pain_point"),
                        "proof_points":    msgs("proof_point"),
                        "objections": [
                            {"objection": x.objection, "counter": x.counter}
                            for x in brand.messaging if x.message_type == "objection"
                        ],
                    }

            # ── 2. ResearchResult mới nhất theo business_id ──────────────────
            if business_id:
                rs = (await db.execute(
                    select(ResearchResult)
                    .where(ResearchResult.business_id == business_id)
                    .order_by(desc(ResearchResult.created_at))
                    .limit(1)
                )).scalars().one_or_none()

                research_data = (
                    {
                        "has_research":       True,
                        "competitor_analysis": rs.competitor_analysis,
                        "competitors_scraped": rs.competitors_scraped or [],
                        "tiktok_comments":     rs.tiktok_comments     or [],
                        "researched_at":       rs.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    if rs else
                    {"has_research": False, "competitor_analysis": "Chưa có dữ liệu"}
                )

                # ── 3. DocumentPage theo business_id (qua DocumentSource) ────
                pages = (await db.execute(
                    select(DocumentPage)
                    .join(DocumentPage.source)
                    .where(DocumentSource.business_id == business_id)
                    .order_by(desc(DocumentPage.created_at))
                    .limit(5)
                )).scalars().all()

                # ── 4. HotelRoom theo business_id ────────────────────────────
                rooms = (await db.execute(
                    select(HotelRoom)
                    .where(
                        HotelRoom.business_id == business_id,
                        HotelRoom.status == "active",
                    )
                )).scalars().all()

                knowledge_rag += (
                    [
                        {
                            "rag_type":    "document_page",
                            "title":       x.title,
                            "source_url":  x.url,
                            "text_content": x.content,
                        }
                        for x in pages
                    ] + [
                        {
                            "rag_type":          "hotel_room",
                            "room_name":         x.name,
                            "room_type":         x.room_type,
                            "price":             f"{x.price_per_night:,.0f} {x.currency}" if x.price_per_night else "Liên hệ",
                            "amenities":         x.amenities  or [],
                            "image_urls":        x.image_urls or [],
                            "embedded_snapshot": x.embed_text(),
                        }
                        for x in rooms
                    ]
                )

    except Exception as e:
        logger.exception(f"[PREPARE] {e}")

    # ── Fallback ─────────────────────────────────────────────────────────────
    brand_profile = brand_profile or {
        "brand_name":      "Default",
        "positioning":     "Chuyên nghiệp",
        "tone_patterns":   ["Thân thiện"],
        "forbidden_words": [],
    }

    knowledge_rag = knowledge_rag or [{
        "rag_type":          "hotel_room",
        "room_name":         "Default",
        "embedded_snapshot": "Phòng tiêu chuẩn",
    }]

    # ── Filter context bằng Groq ─────────────────────────────────────────────
    try:
        full_context = {
            "brand_profile": brand_profile,
            "research_data": research_data,
            "knowledge_rag": knowledge_rag,
        }

        raw = json.dumps(full_context, ensure_ascii=False)
        logger.info(
            f"[CTX BEFORE] all={len(raw)} "
            f"brand={len(json.dumps(brand_profile, ensure_ascii=False))} "
            f"research={len(json.dumps(research_data, ensure_ascii=False))} "
            f"rag={len(json.dumps(knowledge_rag, ensure_ascii=False))}"
        )

        filtered = filter_knowledge_with_groq(
            user_request=state.get("request", ""),
            raw_knowledge=full_context,
        )

        if filtered:
            try:
                ctx          = json.loads(filtered)
                brand_profile = ctx.get("brand_profile", brand_profile)
                research_data = ctx.get("research_data", research_data)
                knowledge_rag = ctx.get("knowledge_rag", knowledge_rag)
            except Exception:
                logger.warning("[FILTER INVALID JSON]")

        final = json.dumps(
            {"brand_profile": brand_profile, "research_data": research_data, "knowledge_rag": knowledge_rag},
            ensure_ascii=False,
        )
        logger.info(f"[CTX AFTER] all={len(final)} saved={len(raw)-len(final)}")

    except Exception as e:
        logger.exception(f"[CTX FILTER] {e}")

    logger.info(f"[PREPARE DONE] {round(time.time()-started, 2)}s")

    return {
        **state,
        "template":      template,
        "brand_profile": brand_profile,
        "research_data": research_data,
        "knowledge_rag": knowledge_rag,
        "memory_history": state.get("memory_history", []),
        "usage":   {"total_tokens": 0, "total_cost": 0.0, "calls": []},
        "approved": False,
        "error":    None,
    }

def visual_intent_analyzer(state: dict) -> dict:
    """Node 1b: Dùng Gemini phân tích cấu trúc bài viết để lên layout hình ảnh hoàn chỉnh"""
    print("--- NODE 1b: VISUAL INTENT ANALYZER (GEMINI) ---")
    request_text = state.get("request", "")
    brand_profile = state.get("brand_profile", {})
    
    prompt = (
        f"Dựa trên yêu cầu: '{request_text}' và thông tin thương hiệu:\n{_build_brand_block(brand_profile)}\n\n"
        f"Hãy phân tích và trả về cấu trúc hình ảnh thích hợp cho bài viết này. "
        f"Chỉ trả ra đúng 3 thông tin ngắn gọn theo định dạng mẫu sau, không viết thêm lời dẫn:\n"
        f"image_count: [Số lượng ảnh lý tưởng, ví dụ: 3]\n"
        f"style: [Phong cách thiết kế ảnh, ví dụ: luxury_bright]\n"
        f"tags: [Các từ khóa tìm kiếm ảnh viết cách nhau dấu phẩy]"
    )
    
    res = call_gemini(prompt, max_tokens=150)
    
    image_count = 3
    style = "bright_luxury"
    tags = ["khách sạn", "không gian"]
    
    for line in res.split("\n"):
        if "image_count:" in line:
            try: image_count = int(line.split(":", 1)[1].strip())
            except: pass
        elif "style:" in line:
            style = line.split(":", 1)[1].strip()
        elif "tags:" in line:
            tags = [t.strip() for t in line.split(":", 1)[1].split(",")]

    # 🌟 ĐÃ SỬA: KHÔNG unpack **state. Chỉ trả về đúng key 'visual_intent'
    return {
        "visual_intent": {
            "image_count": image_count,
            "style": style,
            "tags": tags
        }
    }


def execute_social(state: dict) -> dict:
    platform = "Twitter" if "tweet" in state["request"].lower() else "Facebook"
    brand_profile = state.get("brand_profile", {})
    
    prompt = (
        f"Write a {platform} caption for: {state['request']}\n"
        f"Max 280 chars. Add 2-3 hashtags.\n\n"
        f"=== Brand Context ===\n{_build_brand_block(brand_profile)}\n\n"
        f"=== History Memory ===\n{_build_memory_block(state.get('memory_history', []))}"
    )
    
    caption = call_gemini(prompt, max_tokens=300)
    if caption.startswith("[ERROR:"):
        return {"error": caption[7:-1]} # 🌟 ĐÃ SỬA: Trả về lỗi riêng biệt, không unpack state
        
    return {
        "draft": {"content": caption, "metadata": {"platform": platform, "type": "social"}, "version": state.get("draft", {}).get("version", 0) + 1},
        "usage": _merge_usage(state["usage"], 200, "social"),
    }


def execute_blog(state: dict) -> dict:
    """Node 2: Tạo bản thảo Blog có nhúng vị trí ảnh định sẵn từ Node 1b"""
    print("--- NODE 2: EXECUTE BLOG (GEMINI WRITER) ---")
    brand_profile = state.get("brand_profile", {})
    v_intent = state.get("visual_intent", {})
    
    img_instruction = (
        f"Bài viết này bắt buộc phải chứa đúng {v_intent.get('image_count', 3)} hình ảnh minh họa.\n"
        f"Hãy chèn ký hiệu chính xác dạng `[PLACEHOLDER_IMAGE_X: Mô tả bức ảnh khớp ngữ cảnh bài viết, phong cách {v_intent.get('style', 'chuyên nghiệp')}]` "
        f"vào các đoạn ngắt dòng thích hợp trong bài blog."
    )

    prompt = (
        f"Viết một bài blog chuyên sâu về chủ đề: {state['request']}\n"
        f"Yêu cầu: Sử dụng thẻ tiêu đề H2, văn phong tự nhiên, độ dài khoảng 600-900 từ.\n"
        f"{img_instruction}\n\n"
        f"=== Nguyên tắc thương hiệu ===\n{_build_brand_block(brand_profile)}\n\n"
        f"=== Lịch sử chỉnh sửa bài viết cũ ===\n{_build_memory_block(state.get('memory_history', []))}"
    )
    
    draft = call_groq(prompt, max_tokens=1500)
    if "[ERROR:" in draft:
        return {
            "draft": {
                "content": "Bài viết đang được chuẩn bị. Hệ thống đang bảo trì kết nối Groq. Vui lòng thử lại sau.",
                "metadata": {"type": "blog", "status": "error_retry"},
                "version": 0
            }
        }
        
    current_version = state.get("draft", {}).get("version", 0) if state.get("draft") else 0
    return {
        "draft": {"content": draft, "metadata": {"type": "blog", "word_count": len(draft.split())}, "version": current_version + 1},
        "usage": _merge_usage(state["usage"], 800, "blog"),
    }


def execute_image(state: dict) -> dict:
    brand_profile = state.get("brand_profile", {})
    prompt = (
        f"Tạo một đoạn Prompt tiếng Anh chi tiết để đưa vào AI sinh ảnh cho chủ đề: {state['request']}\n"
        f"=== Brand Context ===\n{_build_brand_block(brand_profile)}"
    )
    
    img_prompt = call_gemini(prompt, max_tokens=300)
    if img_prompt.startswith("[ERROR:"):
        return {"error": img_prompt[7:-1]}
        
    return {
        "draft": {
            "content": f"Image prompt: {img_prompt}",
            "metadata": {"type": "image", "image_url": f"https://api.example.com/images/{uuid.uuid4().hex[:12]}.png", "prompt": img_prompt},
            "version": 1,
        },
        "usage": _merge_usage(state["usage"], 150, "image"),
    }

def execute_research(state: dict) -> dict:
    brand_profile = state.get("brand_profile", {})
    prompt = (
        f"Research and write a comprehensive report on: {state['request']}\n"
        f"=== Brand Context ===\n{_build_brand_block(brand_profile)}"
    )
    
    report = call_gemini(prompt, max_tokens=1500)
    if report.startswith("[ERROR:"):
        return {**state, "error": report[7:-1]}
        
    return {
        **state,
        "draft": {
            "content": report,
            "metadata": {"type": "research", "sources": ["Gemini Base"], "confidence": "high"},
            "version": 1,
        },
        "approved":       True,
        "publish_status": "published",
        "usage":          _merge_usage(state["usage"], 900, "research"),
    }


def review_pause(state: dict) -> dict:
    print("--- NODE 3: REVIEW PAUSE (WAITING FOR USER) ---")
    action = interrupt({
        "status":     "paused",
        "node":       "review_pause",
        "draft":      state["draft"],
        "usage":      state["usage"],
        "session_id": state["session_id"],
    })
    
    user_action = action.get("action", "save")
    
    if user_action == "approve":
        return {**state, "approved": True, "error": None}
        
    elif user_action == "revise":
        # 🌟 ĐÃ SỬA: Đặt cờ hiệu "status_action" riêng biệt thay vì gán đè vào "error" 
        return {
            **state,
            "approved": False, 
            "status_action": "revise", 
            "request": action.get("feedback", "Hãy tối ưu lại bài viết.")
        }
        
    return {**state, "approved": False, "error": None}




def visual_asset_selector(state: dict) -> dict:
    print("--- NODE 3b: TẠO ẢNH & LƯU VÀO APP/MEDIA ---")
    
    # Lấy thông tin session để phân thư mục
    session_id = state.get("session_id", "default")
    save_path = Path("app/media") / session_id
    os.makedirs(save_path, exist_ok=True)
    
    content = state["draft"]["content"]
    
    def generate_and_save(match):
        desc = match.group(1)
        try:
            # Gọi hàm tạo ảnh thật
            img_bytes = call_gemini_imagen(f"Professional marketing photo of: {desc}")
            
            # Lưu xuống ổ đĩa
            file_name = f"image_{uuid.uuid4().hex[:8]}.png"
            file_full_path = save_path / file_name
            with open(file_full_path, "wb") as f:
                f.write(img_bytes)
                
            # Trả về link để client hiển thị
            return f"![{desc}](/static/media/{session_id}/{file_name})"
        except Exception as e:
            return f"![Ảnh lỗi: {desc}](https://via.placeholder.com/150?text=Error)"

    # Regex thay thế placeholder
    final_content = re.sub(r"\[PLACEHOLDER_IMAGE_\d+: (.*?)\]", generate_and_save, content)
    
    return {
        **state,
        "draft": { **state["draft"], "content": final_content }
    }

def context_synthesizer(state: dict) -> dict:
    print("--- NODE 4: CONTEXT SYNTHESIZER (UPDATING MEMORY) ---")
    current_memory = state.get("memory_history", [])
    if current_memory is None:
        current_memory = []
        
    current_memory.append({
        "user_feedback": state.get("request", "Cần điều chỉnh văn phong bài viết.")
    })
    
    return {
        **state,
        "memory_history": current_memory,
        "status_action": None, # Reset cờ hiệu revise
        "error": None
    }


def publish(state: dict) -> dict:
    return {**state, "publish_status": "published"}


def save(state: dict) -> dict:
    return {**state}


# ── Edge Conditions (Hàm điều hướng Router) ───────────────────────────────────

def select_template(state: dict) -> str:
    if state.get("error"):
        return "save"
    return f"execute_{state['template']}"


def route_after_review(state: dict) -> str:
    # 🌟 ĐÃ SỬA: Kiểm tra theo cờ hiệu "status_action" để định tuyến sửa bài chính xác
    if state.get("status_action") == "revise":
        return "revise"
    if state.get("approved"):
        return "publish"
    return "save"