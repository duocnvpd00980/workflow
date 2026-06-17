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

LLM_TIMEOUT = 30
MEDIA_ROOT = Path("app/media")


# ── Groq ──────────────────────────────────────────────────

def call_groq(prompt: str, max_tokens: int = 500) -> str:
    """Gọi Groq sync, trả về text."""
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