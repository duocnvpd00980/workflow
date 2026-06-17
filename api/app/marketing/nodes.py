import json
import time

from langgraph.types import interrupt
from google import genai
from google.genai import types
import uuid
import logging
from app.brand.brand_voice_prompt import get_brand_prompt_by_id
from app.db import AsyncSessionLocal
from app.config import get_settings
from groq import Groq
import os
from pathlib import Path
import re
import uuid
from pathlib import Path
import requests
from groq import AsyncGroq

# ── IMPORT TẤT CẢ MODELS TRƯỚC KHI DÙNG ──────────────────────────
import app.business.models
import app.brand.models
import app.chat.models
import app.rag.models
import app.marketing.models
import app.research.models
import app.tasks.models
from app.brand.models import Brand
from app.research.models import ResearchResult
from app.rag.models import DocumentSource, DocumentPage, HotelRoom
# ──────────────────────────────────────────────────────────────────


# ── LangGraph Nodes Xử Lý ───────────────────────────────────────────────────────
from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload

import requests


logger = logging.getLogger(__name__)
_s = get_settings()

gemini_client = genai.Client(api_key=_s.GEMINI_API_KEY)
GEMINI_MODEL = _s.GEMINI_MODEL

groq_client = Groq(api_key=_s.GROQ_API_KEY)
async_groq_client = AsyncGroq(api_key=_s.GROQ_API_KEY)
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



async def call_groq_stream(prompt: str, max_tokens: int = 500):
    stream = await async_groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=max_tokens,
        temperature=0.7,
        stream=True,
    )
    chunk_count = 0
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            chunk_count += 1
            print(f"[GROQ] chunk #{chunk_count}: {repr(content)}")  # 👈
            yield content
    print(f"[GROQ] total chunks: {chunk_count}")
                
        
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
        safe_prompt = prompt_desc.replace(" ", "%20")
        url = f"https://gen.pollinations.ai/image/{safe_prompt}?model=flux&width=1024&height=576&nologo=true"
        
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
        return requests.get("https://via.placeholder.com/1024x576?text=Image+Unavailable").content
    
def filter_knowledge_with_groq(user_request: str, raw_knowledge: list) -> str:
    if not raw_knowledge:
        return "No relevant context found."
    if not user_request:
        return str(raw_knowledge)

    raw_context = str(raw_knowledge)

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
            temperature=0.0,
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


def build_intent_expansion_prompt(user_request: str, content_type: str, selected_length: str, selected_tone: str) -> str:
    return f"""Bạn là một Giám đốc Sáng tạo và Chuyên gia Content Strategy xuất sắc.
Người dùng đang sử dụng một Form công cụ để tạo nội dung mới với các thông số:
- Loại nội dung (Template): {content_type}
- Độ dài mong muốn từ UI: {selected_length}
- Tone tùy chọn từ UI: {selected_tone}

Yêu cầu gốc từ người dùng rất ngắn gọn, thiếu ý tưởng hoặc sơ sài: "{user_request}"

Nhiệm vụ của bạn là đóng vai trò biên tập viên ngầm: suy luận thông minh, mở rộng chủ đề thô đó thành một định hướng bài viết có chiều sâu, hấp dẫn, đồng thời gợi ý các từ khóa cốt lõi liên quan đến chủ đề đó.

BẠN PHẢI TRẢ VỀ MỘT ĐỐI TƯỢNG JSON SẠCH 100%, KHÔNG CHỨA VĂN BẢN DẪN GIẢI, CÓ CẤU TRÚC SAU:
{{
  "topic": "Chuỗi văn bản đã được bạn làm mịn, mở rộng góc tiếp cận sâu sắc và đầy đủ bối cảnh từ ý tưởng gốc của user",
  "keywords": ["mảng gồm 3 đến 5 từ khóa chuyên sâu quan trọng nhất liên quan trực tiếp đến chủ đề này"],
  "length": "Độ dài chi tiết kết hợp giữa lựa chọn UI '{selected_length}' và tiêu chuẩn của kênh '{content_type}'"
}}"""

async def prepare(state: dict) -> dict:
    started = time.time()

    # 1. Thu thập dữ liệu thô từ Form UI gửi lên State
    user_request = state.get("request", "")
    content_type = state.get("content_type", "blog")  # Lấy trực tiếp từ UI form (e.g., "blog", "social", "email")
    selected_length = state.get("length", "vừa")       # UI: "ngắn", "vừa", "dài"
    selected_tone = state.get("tone", "chuyên nghiệp") # UI: "chuyên nghiệp", "vui vẻ"...
    brand_id = state.get("brand_id")

    # 2. Cơ chế mở rộng ý định: Dựng prompt và tái sử dụng hàm call_groq của hệ thống
    # expansion_prompt = build_intent_expansion_prompt(
    #     user_request=user_request,
    #     content_type=content_type,
    #     selected_length=selected_length,
    #     selected_tone=selected_tone
    # )
    # groq_raw_response = call_groq(prompt=expansion_prompt, max_tokens=800)
    
    # Khởi tạo object fallback mặc định phòng trường hợp call_groq dính lỗi [ERROR:...]
    enriched_input = {
        "topic": user_request,
        "keywords": [],
        "length": f"Độ dài {selected_length}. Tối ưu theo định dạng {content_type}."
    }

    # if not groq_raw_response.startswith("[ERROR:"):
    #     try:
    #         clean_json_str = groq_raw_response.strip()
    #         if clean_json_str.startswith("```json"):
    #             clean_json_str = clean_json_str.split("```json")[1].split("```")[0].strip()
    #         elif clean_json_str.startswith("```"):
    #             clean_json_str = clean_json_str.split("```")[1].split("```")[0].strip()
                
    #         enriched_input = json.loads(clean_json_str)
    #         logger.info(f"[PREPARE] Mở rộng ý định thành công cho request: '{user_request[:30]}...'")
    #     except Exception as json_err:
    #         logger.error(f"[PREPARE JSON ERROR] Không thể parse JSON từ Groq: {groq_raw_response}. Lỗi: {json_err}")
    # else:
    #     logger.warning(f"[PREPARE WARNING] call_groq dính mã lỗi: {groq_raw_response}. Sử dụng dữ liệu thô.")

    system_prompt = ""

    # 3. Gọi Service tập trung của Brand để tạo System Prompt hoàn chỉnh cho đồ thị
    try:
        async with AsyncSessionLocal() as db:
            if brand_id:
                # Truyền object user_input đã được làm giàu (gồm topic, keywords, length đã tối ưu)
                system_prompt = await get_brand_prompt_by_id(
                    brand_id=brand_id,
                    content_type=content_type,
                    user_input=enriched_input,
                    db=db
                )
    except Exception as e:
        logger.exception(f"[LANGGRAPH PREPARE ERROR] Thất bại tại bước tạo brand prompt cho brand_id={brand_id}: {e}")

    # Fallback tối cao nếu toàn bộ các bước DB lỗi để đồ thị không bị sập giữa chừng
    if not system_prompt:
        system_prompt = "Bạn là trợ lý ảo viết bài chuyên nghiệp. Hãy tạo nội dung phù hợp."

    logger.info(f"[PREPARE DONE] Tuyến Form: {content_type} | Xử lý: {round(time.time() - started, 3)}s")

    # 4. Trả về State sạch sẽ, đồng bộ
    return {
        **state,
        "template":       content_type,     # Đồng bộ hóa trường content_type làm template điều hướng
        "system_prompt":  system_prompt,    # System Prompt tối ưu nhất kết hợp giữa Brand Voice + Ý tưởng đã làm giàu
        "enriched_topic": enriched_input.get("topic"), # Lưu lại đề bài xịn để node thực thi bốc ra làm đề bài viết bài chính thức
        "usage":          state.get("usage") or {"total_tokens": 0, "total_cost": 0.0, "calls": []},
        "approved":       False,
        "error":          None,
    }

def visual_intent_analyzer(state: dict) -> dict:
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
    
    res = call_groq(prompt, max_tokens=150)
    
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

    return {
        "visual_intent": {
            "image_count": image_count,
            "style": style,
            "tags": tags
        }
    }


def execute_social(state: dict) -> dict:
    request = state.get("request", "")  # ✅ SỬA: dùng .get() thay vì []
    platform = "Twitter" if "tweet" in request.lower() else "Facebook"
    brand_profile = state.get("brand_profile", {})
    
    prompt = (
        f"Write a {platform} caption for: {request}\n"  # ✅ Dùng biến request
        f"Max 280 chars. Add 2-3 hashtags.\n\n"
        f"=== Brand Context ===\n{_build_brand_block(brand_profile)}\n\n"
        f"=== History Memory ===\n{_build_memory_block(state.get('memory_history', []))}"
    )
    
    caption = call_groq(prompt, max_tokens=300)
    if caption.startswith("[ERROR:"):
        return {**state, "error": caption[7:-1]}
        
    return {
        "draft": {"content": caption, "metadata": {"platform": platform, "type": "social"}, "version": (state.get("draft") or {}).get("version", 0) + 1},
        "usage": _merge_usage(state.get("usage", {}), 200, "social"),
    }


def execute_blog(state: dict) -> dict:
    print("--- NODE 2: EXECUTE BLOG (GEMINI WRITER) ---")
    request = state.get("request", "")  # ✅ SỬA
    brand_profile = state.get("brand_profile", {})
    v_intent = state.get("visual_intent", {})
    
    img_instruction = (
        f"Bài viết này bắt buộc phải chứa đúng {v_intent.get('image_count', 3)} hình ảnh minh họa.\n"
        f"Hãy chèn ký hiệu chính xác dạng `[PLACEHOLDER_IMAGE_X: Mô tả bức ảnh khớp ngữ cảnh bài viết, phong cách {v_intent.get('style', 'chuyên nghiệp')}]` "
        f"vào các đoạn ngắt dòng thích hợp trong bài blog."
    )

    prompt = (
        f"Viết một bài blog chuyên sâu về chủ đề: {request}\n"  # ✅ Dùng biến
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
        
    current_version = (state.get("draft") or {}).get("version", 0)
    return {
        "draft": {"content": draft, "metadata": {"type": "blog", "word_count": len(draft.split())}, "version": current_version + 1},
        "usage": _merge_usage(state.get("usage", {}), 800, "blog"),
    }


def execute_image(state: dict) -> dict:
    request = state.get("request", "")  # ✅ SỬA
    brand_profile = state.get("brand_profile", {})
    prompt = (
        f"Tạo một đoạn Prompt tiếng Anh chi tiết để đưa vào AI sinh ảnh cho chủ đề: {request}\n"  # ✅ Dùng biến
        f"=== Brand Context ===\n{_build_brand_block(brand_profile)}"
    )
    
    img_prompt = call_groq(prompt, max_tokens=300)
    if img_prompt.startswith("[ERROR:"):
        return {**state, "error": img_prompt[7:-1]}
        
    return {
        "draft": {
            "content": f"Image prompt: {img_prompt}",
            "metadata": {"type": "image", "image_url": f"https://api.example.com/images/{uuid.uuid4().hex[:12]}.png", "prompt": img_prompt},
            "version": 1,
        },
        "usage": _merge_usage(state.get("usage", {}), 150, "image"),
    }

def execute_research(state: dict) -> dict:
    request = state.get("request", "")  # ✅ SỬA
    brand_profile = state.get("brand_profile", {})
    prompt = (
        f"Research and write a comprehensive report on: {request}\n"  # ✅ Dùng biến
        f"=== Brand Context ===\n{_build_brand_block(brand_profile)}"
    )
    
    report = call_groq(prompt, max_tokens=1500)
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
        "usage":          _merge_usage(state.get("usage", {}), 900, "research"),
    }


def review_pause(state: dict) -> dict:
    print("--- NODE 3: REVIEW PAUSE (WAITING FOR USER) ---")
    action = interrupt({
        "status":     "paused",
        "node":       "review_pause",
        "draft":      state.get("draft"),
        "usage":      state.get("usage"),
        "session_id": state.get("session_id"),
    })
    
    user_action = action.get("action", "save")
    
    if user_action == "approve":
        return {**state, "approved": True, "error": None, "status_action": None}
        
    elif user_action == "revise":
        return {
            **state,
            "approved": False, 
            "status_action": "revise", 
            "request": action.get("feedback", "Hãy tối ưu lại bài viết."),
            "error": None,
        }
        
    return {**state, "approved": False, "error": None, "status_action": None}




def visual_asset_selector(state: dict) -> dict:
    print("--- NODE 3b: TẠO ẢNH & LƯU VÀO APP/MEDIA ---")
    
    session_id = state.get("session_id", "default")
    save_path = Path("app/media") / session_id
    os.makedirs(save_path, exist_ok=True)
    
    draft = state.get("draft") or {"content": "", "metadata": {}, "version": 0}
    content = draft.get("content", "")
    
    def generate_and_save(match):
        desc = match.group(1)
        try:
            img_bytes = call_gemini_imagen(f"Professional marketing photo of: {desc}")
            
            file_name = f"image_{uuid.uuid4().hex[:8]}.png"
            file_full_path = save_path / file_name
            with open(file_full_path, "wb") as f:
                f.write(img_bytes)
                
            return f"![{desc}](/media/{session_id}/{file_name})"  # bỏ /static
        except Exception as e:
            return f"![Ảnh lỗi: {desc}](https://via.placeholder.com/150?text=Error)"

    final_content = re.sub(r"\[PLACEHOLDER_IMAGE_\d+: (.*?)\]", generate_and_save, content)
    
    return {
        **state,
        "draft": { **draft, "content": final_content }
    }

def context_synthesizer(state: dict) -> dict:
    print("--- NODE 4: CONTEXT SYNTHESIZER (UPDATING MEMORY) ---")
    current_memory = state.get("memory_history") or []
    
    current_memory.append({
        "user_feedback": state.get("request", "Cần điều chỉnh văn phong bài viết.")
    })
    
    return {
        **state,
        "memory_history": current_memory,
        "status_action": None,
        "error": None
    }


def publish(state: dict) -> dict:
    return {**state, "publish_status": "published", "status_action": None}


def save(state: dict) -> dict:
    return {**state, "status_action": None}


# ── Edge Conditions ───────────────────────────────────

def select_template(state: dict) -> str:
    if state.get("error") and not state.get("status_action"):
        return "save"
    return f"execute_{state.get('template', 'social')}"


def route_after_review(state: dict) -> str:
    if state.get("status_action") == "revise":
        return "revise"
    if state.get("approved"):
        return "publish"
    if state.get("error"):
        return "save"
    return "save"