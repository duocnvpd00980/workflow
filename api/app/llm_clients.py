from __future__ import annotations

import logging
from pathlib import Path

from google import genai
from google.genai import types
from groq import Groq, AsyncGroq
import requests

from app.config import get_settings

logger = logging.getLogger(__name__)
_s = get_settings()

# ── Clients ───────────────────────────────────────────────

gemini_client = genai.Client(api_key=_s.GEMINI_API_KEY)
GEMINI_MODEL = _s.GEMINI_MODEL

groq_client = Groq(api_key=_s.GROQ_API_KEY)
async_groq_client = AsyncGroq(api_key=_s.GROQ_API_KEY)
GROQ_MODEL = _s.GROQ_MODEL
GROQ_MODEL_GPT = _s.GROQ_MODEL_GPT

LLM_TIMEOUT = 30
MEDIA_ROOT = Path("app/media")


# ── Groq ──────────────────────────────────────────────────

def call_groq(prompt: str, max_tokens: int = 1500, temperature: float = 0.2, gpt: bool = False) -> str:
    """Call Groq synchronously, automatically clean up format and raise normalized exceptions."""

    # 1. Đặt giới hạn tối đa cho max_tokens để tránh lỗi tràn TPM
    MAX_ALLOWED_TOKENS = 4000 
    actual_max_tokens = min(max_tokens, MAX_ALLOWED_TOKENS)

    # 2. Chọn model dựa trên tham số gpt (mặc định GROQ_MODEL, gpt=True lấy GROQ_MODEL_GPT)
    selected_model = GROQ_MODEL_GPT if gpt else GROQ_MODEL

    try:
        msg = groq_client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=actual_max_tokens,
            temperature=temperature,
            top_p=1,
            stop=None,
            timeout=LLM_TIMEOUT,
        )

        content = msg.choices[0].message.content
        if not content:
            raise RuntimeError("GROQ_EMPTY_RESPONSE")
            
        content = content.strip()
        return content

    except Exception as e:
        err = str(e).lower()

        # 401 Unauthorized
        if "401" in err or "unauthorized" in err:
            raise PermissionError("GROQ_AUTH_401: Invalid API key or unauthorized")

        # timeout
        if "timeout" in err:
            raise TimeoutError("GROQ_TIMEOUT: request exceeded time limit")

        # rate limit
        if "rate" in err or "429" in err:
            raise RuntimeError("GROQ_RATE_LIMIT: too many requests")

        # fallback
        raise RuntimeError(f"GROQ_FATAL_ERROR: {str(e)}")
    
    
async def call_groq_stream(prompt: str, max_tokens: int = 500):
    """Gọi Groq async streaming."""
    stream = await async_groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=max_tokens,
        temperature=0.7,
        stream=True,
    )
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


async def stream_groq(prompt: str, max_tokens: int = 2000):
    """Yield từng token từ Groq API."""
    stream = await async_groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=max_tokens,
        temperature=0.7,
        stream=True,
    )
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


# ── Gemini ────────────────────────────────────────────────

def call_gemini(prompt: str, max_tokens: int = 1000) -> str:
    """Gọi Gemini sync, trả về text."""
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
        logger.error(f"Gemini error: {e}")
        error_type = str(e).lower()
        if "timeout" in error_type:
            return "[ERROR:timeout]"
        if "rate" in error_type or "429" in error_type:
            return "[ERROR:rate_limit]"
        return "[ERROR:fatal]"


def call_gemini_imagen(prompt_desc: str) -> bytes:
    """Gọi Pollinations API bằng cách xác thực qua Cấu hình hệ thống"""
    try:
        safe_prompt = prompt_desc.replace(" ", "%20")
        url = f"https://gen.pollinations.ai/image/{safe_prompt}?model=flux&width=1024&height=576&nologo=true"
        
        headers = {
            "Authorization": f"Bearer {_s.POLLINATIONS_API_KEY}"
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