from langgraph.types import interrupt
from google import genai
from google.genai import types
import uuid
import logging
from app.brand.service import BrandProfileService
from app.db import AsyncSessionLocal
from app.config import get_settings
from groq import Groq
import re
import os
from pathlib import Path
import re
import uuid
from pathlib import Path
import requests



logger = logging.getLogger(__name__)
_s = get_settings()

gemini_client = genai.Client(api_key=_s.GEMINI_API_KEY)
MODEL = "gemini-2.5-flash"
LLM_TIMEOUT = 30


groq_client = Groq(api_key=_s.GROQ_API_KEY)
MODEL = _s.GROQ_MODEL
LLM_TIMEOUT = 30

MEDIA_ROOT = Path("app/media")


def call_groq(prompt: str, max_tokens: int = 500) -> str:
    try:
        msg = groq_client.chat.completions.create(
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
    
def call_gemini(prompt: str, max_tokens: int = 1000) -> str:
    """Helper: Gọi trực tiếp mô hình Gemini 2.5 Flash xử lý văn bản"""
    try:
        response = gemini_client.models.generate_content(
            model=MODEL,
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



import requests

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


# ── LangGraph Nodes Xử Lý ───────────────────────────────────────────────────────
from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload

from app.brand.models import Brand, BrandProfile, BrandVoiceRule, BrandMessaging
from app.research.models import ResearchResult
from app.rag.models import DocumentSource, DocumentPage, HotelRoom

async def prepare(state: dict) -> dict:
    r = state.get("request", "").lower()
    brand_id = state.get("brand_id", "default")
    business_name = state.get("business_name", brand_id)
    
    template = (
        "social"   if any(w in r for w in ["tweet", "caption", "post", "social", "instagram", "fb"]) else
        "blog"     if any(w in r for w in ["article", "blog", "write", "bài viết"]) else
        "image"    if any(w in r for w in ["image", "visual", "design", "ảnh", "hình"]) else
        "research" if any(w in r for w in ["research", "report", "analyze", "nghiên cứu"]) else
        "social"
    )

    brand_profile = {}
    research_data = {}
    knowledge_rag = []  

    try:
        async with AsyncSessionLocal() as db:
            # 1. BỐC DATA THƯ MỤC BRAND
            brand_stmt = (
                select(Brand)
                .where(Brand.id == brand_id)
                .options(
                    joinedload(Brand.profile),
                    joinedload(Brand.voice_rules),
                    joinedload(Brand.messaging)
                )
            )
            brand_result = await db.execute(brand_stmt)
            brand_record = brand_result.scalars().one_or_none()  # ← Đổi thành .one_or_none()

            if brand_record:
                profile_data = brand_record.profile
                forbidden_words = [r.value for r in brand_record.voice_rules if r.rule_type == "forbidden_word"]
                tone_patterns   = [r.value for r in brand_record.voice_rules if r.rule_type == "tone_pattern"]
                cta_patterns    = [r.value for r in brand_record.voice_rules if r.rule_type == "cta_pattern"]
                pain_points = [m.value for m in brand_record.messaging if m.message_type == "pain_point"]
                proof_points = [m.value for m in brand_record.messaging if m.message_type == "proof_point"]
                objections = [{"objection": m.objection, "counter": m.counter} for m in brand_record.messaging if m.message_type == "objection"]

                brand_profile = {
                    "brand_name":      brand_record.name,
                    "positioning":    profile_data.positioning if profile_data else "Chuyên nghiệp, tinh tế",
                    "target_audience": profile_data.audience if profile_data else "Khách hàng đại chúng",
                    "visual_identity": profile_data.visual_identity if profile_data else {},
                    "tone_patterns":   tone_patterns or ["Thân thiện, tin cậy"],
                    "forbidden_words": forbidden_words,
                    "cta_samples":     cta_patterns or ["Khám phá ngay"],
                    "pain_points":     pain_points,
                    "proof_points":    proof_points,
                    "objections":      objections
                }

            # 2. BỐC DATA THƯ MỤC RESEARCH
            research_stmt = (
                select(ResearchResult)
                .where(ResearchResult.business_name == business_name)
                .order_by(desc(ResearchResult.created_at))
                .limit(1)
            )
            research_result = await db.execute(research_stmt)
            research_record = research_result.scalars().one_or_none()  # ← Đổi thành .one_or_none()

            if research_record:
                research_data = {
                    "has_research":        True,
                    "competitor_analysis": research_record.competitor_analysis,
                    "competitors_scraped": research_record.competitors_scraped or [],
                    "tiktok_comments":     research_record.tiktok_comments or [],
                    "researched_at":       research_record.created_at.strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                research_data = {"has_research": False, "competitor_analysis": "Chưa có dữ liệu phân tích đối thủ."}

            # 3. BỐC DATA THƯ MỤC RAG
            page_stmt = select(DocumentPage).order_by(desc(DocumentPage.created_at)).limit(5)
            page_result = await db.execute(page_stmt)
            for page in page_result.scalars().all():
                knowledge_rag.append({
                    "rag_type": "document_page",
                    "title": page.title,
                    "source_url": page.url,
                    "text_content": page.content
                })

            room_stmt = select(HotelRoom).where(HotelRoom.status == "active")
            room_result = await db.execute(room_stmt)
            for room in room_result.scalars().all():
                knowledge_rag.append({
                    "rag_type": "hotel_room",
                    "room_name": room.name,
                    "room_type": room.room_type,
                    "price": f"{room.price_per_night:,.0f} {room.currency}" if room.price_per_night else "Liên hệ",
                    "amenities": room.amenities or [],
                    "image_urls": room.image_urls or [],
                    "embedded_snapshot": room.embed_text() 
                })

    except Exception as e:
        logger.error(f"Lỗi hệ thống khi dồn dịch CSDL từ 3 nguồn Brand-Research-RAG: {str(e)}")

    if not brand_profile:
        brand_profile = {"brand_name": "Default", "positioning": "Chuyên nghiệp", "tone_patterns": ["Thân thiện"], "forbidden_words": []}
    if not knowledge_rag:
        knowledge_rag = [{
            "rag_type": "hotel_room", 
            "room_name": "Phòng Tiêu Chuẩn View Biển", 
            "embedded_snapshot": "Phòng Deluxe King View Biển | diện tích 35m2 | Tiện nghi: Wifi, Điều hòa | Giá: 1,500,000 VND/đêm"
        }]

    return {
        **state,
        "template":       template,
        "brand_profile":  brand_profile,  
        "research_data":  research_data,  
        "knowledge_rag":  knowledge_rag,  
        "memory_history": state.get("memory_history", []),
        "usage":          {"total_tokens": 0, "total_cost": 0.0, "calls": []},
        "approved":       False,
        "error":          None,
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