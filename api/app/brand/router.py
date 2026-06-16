"""
routers/brand_voice.py
────────────────────────────────
CRUD + generate endpoint cho Brand system.
Dùng app.llm_clients (async_groq_client, call_groq) — KHÔNG dùng litellm.

Endpoints:
    POST   /brand-voices                       → tạo mới (LLM extract background)
    GET    /brand-voices                       → list theo business_id
    GET    /brand-voices/{voice_id}            → chi tiết
    PATCH  /brand-voices/{voice_id}            → user edit sau preview
    DELETE /brand-voices/{voice_id}            → soft delete
    POST   /brand-voices/{voice_id}/set-default → đặt làm default
    POST   /brand-voices/{voice_id}/generate   → tạo content từ voice
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.business.models import Business
from app.tasks.service import create_task, finish_task, fail_task, update_task
from app.llm_clients import async_groq_client, GROQ_MODEL  # ← dùng client chung

from .models import Brand
from .schemas import (
    BrandCreate,
    BrandListOut,
    BrandOut,
    BrandUpdate,
)
from .brand_voice_extract import extract_brand_voice
from .brand_voice_prompt import build_system_prompt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brand-voices", tags=["Brand Voice"])


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _get_voice_or_404(voice_id: str, db: AsyncSession) -> Brand:
    result = await db.execute(
        select(Brand).filter(
            Brand.id == voice_id,
            Brand.deleted_at.is_(None),
        )
    )
    voice = result.scalars().first()
    if not voice:
        raise HTTPException(status_code=404, detail="Brand voice không tồn tại.")
    return voice


async def _get_business_or_404(business_id: str, db: AsyncSession) -> Business:
    result = await db.execute(select(Business).filter(Business.id == business_id))
    business = result.scalars().first()
    if not business:
        raise HTTPException(status_code=404, detail="Business không tồn tại.")
    return business


# ═══════════════════════════════════════════════════════════════════
# BACKGROUND TASK — extract 8 fields rồi update record
# ═══════════════════════════════════════════════════════════════════

async def _extract_and_save_bg(
    db: AsyncSession,
    voice_id: str,
    business_dict: Dict[str, Any],
    voice_config_dict: Dict[str, Any],
    rag_content: str,
    task_id: int,
) -> None:
    """Pattern giống BrandProfileService.generate_from_documents_bg()."""
    try:
        # Step 1: LLM extract (dùng async_groq_client bên trong service)
        eight_fields = await extract_brand_voice(
            business=business_dict,
            voice_config=voice_config_dict,
            rag_content=rag_content,
        )
        await update_task(db, task_id, steps_done=1)

        # Step 2: Update DB record
        result = await db.execute(
            select(Brand).filter(Brand.id == voice_id)
        )
        voice = result.scalars().first()
        if not voice:
            await fail_task(db, task_id, error_message=f"Brand {voice_id} không tìm thấy.")
            return

        voice.personality  = eight_fields["personality"]
        voice.tone         = eight_fields["tone"]
        voice.style        = eight_fields["style"]
        voice.vocabulary   = eight_fields["vocabulary"]
        voice.format_rules = eight_fields["format_rules"]
        voice.cta_style    = eight_fields["cta_style"]
        voice.examples     = eight_fields.get("examples", [])

        await db.commit()
        await finish_task(db, task_id, steps_done=2)
        logger.info("extract_bg done | voice_id=%s | task_id=%s", voice_id, task_id)

    except Exception as exc:
        logger.error("extract_bg failed | voice_id=%s | err=%s", voice_id, exc)
        await fail_task(db, task_id, error_message=str(exc))


# ═══════════════════════════════════════════════════════════════════
# POST /brand-voices — tạo mới
# ═══════════════════════════════════════════════════════════════════

@router.post("", response_model=BrandOut, status_code=status.HTTP_202_ACCEPTED)
async def create_brand_voice(
    payload: BrandCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Brand:
    """
    202 Accepted — tạo record ngay, LLM extract 8 fields chạy background.
    Client dùng task_id để polling GET /tasks/{task_id}.
    """
    business = await _get_business_or_404(payload.business_id, db)

    # Lấy RAG content — có thì dùng, không thì dùng business info
    rag_content = ""
    if payload.rag_source:
        rag_content = payload.rag_source.pasted_text or ""
    
    # Fallback: nếu rag_content rỗng, dùng business info
    if not rag_content:
        rag_content = f"""
        Tên doanh nghiệp: {business.name}
        Ngành: {business.industry or 'Không rõ'}
        Địa chỉ: {business.address or 'Không rõ'}
        """

    # Tạo record với placeholder — 8 fields fill sau khi Groq xong
    voice = Brand(
        business_id     = payload.business_id,
        name            = payload.voice_config.name,
        purpose         = payload.voice_config.purpose,
        channels        = payload.voice_config.channels,
        desired_tone    = payload.voice_config.desired_tone,
        target_audience = payload.voice_config.target_audience,
        # 8 fields placeholder
        personality  = "",
        tone         = {"base": [], "overrides": {}},
        style        = {"sentenceLength": "medium", "voice": "active", "perspective": "second"},
        vocabulary   = {"wordsToUse": [], "wordsToAvoid": [], "phrasesToUse": [], "phrasesToAvoid": []},
        format_rules = {"paragraphMaxSentences": 4, "useEmoji": False, "useHashtags": False, "bulletPointStyle": "none"},
        cta_style    = {"style": "none", "phrases": []},
        examples     = [],
        # RAG sources
        website_url    = payload.rag_source.website_url,
        uploaded_files = payload.rag_source.uploaded_files,
        pasted_text    = payload.rag_source.pasted_text,
    )
    db.add(voice)
    await db.commit()
    await db.refresh(voice)

    # Task record để client polling (pattern từ router cũ)
    task = await create_task(
        db,
        source      = "brand_voice",
        source_id   = voice.id,
        title       = f"Extract brand voice: {voice.name}",
        triggered_by= "user",
        steps_total = 2,
        model       = GROQ_MODEL,
    )

    # RAG content — pasted_text trước, website/file TODO sau
    rag_content = payload.rag_source.pasted_text or ""

    # Business dict sạch (không lẫn _sa_instance_state)
    business_dict = {c.name: getattr(business, c.name) for c in business.__table__.columns}

    background_tasks.add_task(
        _extract_and_save_bg,
        db              = db,
        voice_id        = voice.id,
        business_dict   = business_dict,
        voice_config_dict = payload.voice_config.model_dump(),
        rag_content     = rag_content,
        task_id         = task.id,
    )

    logger.info("create_brand_voice | voice_id=%s | task_id=%s", voice.id, task.id)
    return voice


# ═══════════════════════════════════════════════════════════════════
# GET /brand-voices — list
# ═══════════════════════════════════════════════════════════════════

@router.get("", response_model=BrandListOut)
async def list_brand_voices(
    business_id: str = Query(..., description="Filter theo business"),
    skip: int  = Query(0,  ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    base_filter = (
        Brand.business_id == business_id,
        Brand.deleted_at.is_(None),
    )
    items_result = await db.execute(
        select(Brand)
        .filter(*base_filter)
        .order_by(Brand.created_at.desc())
        .offset(skip).limit(limit)
    )
    count_result = await db.execute(
        select(func.count()).select_from(Brand).filter(*base_filter)
    )
    return {"items": items_result.scalars().all(), "total": count_result.scalar_one()}


# ═══════════════════════════════════════════════════════════════════
# GET /brand-voices/{voice_id} — chi tiết
# ═══════════════════════════════════════════════════════════════════

@router.get("/{voice_id}", response_model=BrandOut)
async def get_brand_voice(voice_id: str, db: AsyncSession = Depends(get_db)) -> Brand:
    return await _get_voice_or_404(voice_id, db)


# ═══════════════════════════════════════════════════════════════════
# PATCH /brand-voices/{voice_id} — user edit sau preview
# ═══════════════════════════════════════════════════════════════════

@router.patch("/{voice_id}", response_model=BrandOut)
async def update_brand_voice(
    voice_id: str,
    data: BrandUpdate,
    db: AsyncSession = Depends(get_db),
) -> Brand:
    """
    Typed PATCH — merge dict thay vì overwrite hoàn toàn.
    VD: gửi {"tone": {"base": ["bold"]}} sẽ không xóa tone.overrides đang có.
    """
    voice = await _get_voice_or_404(voice_id, db)

    for field, value in data.model_dump(exclude_unset=True).items():
        current = getattr(voice, field, None)
        if isinstance(current, dict) and isinstance(value, dict):
            setattr(voice, field, {**current, **value})
        else:
            setattr(voice, field, value)

    await db.commit()
    await db.refresh(voice)
    return voice


# ═══════════════════════════════════════════════════════════════════
# DELETE /brand-voices/{voice_id} — soft delete
# ═══════════════════════════════════════════════════════════════════

@router.delete("/{voice_id}", status_code=status.HTTP_200_OK)
async def delete_brand_voice(
    voice_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    voice = await _get_voice_or_404(voice_id, db)
    voice.deleted_at = _utcnow()
    await db.commit()
    return {"status": "success", "message": "Đã xóa brand voice.", "voice_id": voice_id}


# ═══════════════════════════════════════════════════════════════════
# POST /brand-voices/{voice_id}/set-default
# ═══════════════════════════════════════════════════════════════════

@router.post("/{voice_id}/set-default", status_code=status.HTTP_200_OK)
async def set_default_voice(
    voice_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    voice = await _get_voice_or_404(voice_id, db)

    # Unset các default khác cùng business
    siblings = await db.execute(
        select(Brand).filter(
            Brand.business_id == voice.business_id,
            Brand.is_default  == "1",
            Brand.id          != voice_id,
            Brand.deleted_at.is_(None),
        )
    )
    for s in siblings.scalars().all():
        s.is_default = "0"

    voice.is_default = "1"
    await db.commit()
    return {"status": "success", "message": f"'{voice.name}' đã là default.", "voice_id": voice_id}


# ═══════════════════════════════════════════════════════════════════
# POST /brand-voices/{voice_id}/generate — tạo content
# ═══════════════════════════════════════════════════════════════════

@router.post("/{voice_id}/generate")
async def generate_content(
    voice_id: str,
    content_type: Literal["blog", "email", "social", "ad", "landing_page", "other"],
    user_input: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Tạo content từ Brand Voice bằng Groq async streaming (call_groq_stream).

    user_input: { topic?, keywords?, length?, additional_instructions? }
    """
    voice = await _get_voice_or_404(voice_id, db)

    if not voice.personality:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Brand voice đang được xử lý. Vui lòng thử lại sau khi extraction hoàn tất.",
        )

    brand_voice_dict = {
        "personality":  voice.personality,
        "tone":         voice.tone,
        "style":        voice.style,
        "vocabulary":   voice.vocabulary,
        "format_rules": voice.format_rules,
        "cta_style":    voice.cta_style,
        "examples":     voice.examples or [],
    }

    system_prompt = await build_system_prompt(
        brand_voice  = brand_voice_dict,
        content_type = content_type,
        user_input   = user_input,
    )

    # Gọi Groq async — dùng async_groq_client từ app.llm_clients
    try:
        response = await async_groq_client.chat.completions.create(
            model    = GROQ_MODEL,
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_input.get("topic", "Viết nội dung theo brand voice.")},
            ],
            max_completion_tokens = 2000,
            temperature           = 0.7,
            timeout               = 60,
        )
        content = response.choices[0].message.content or ""
    except Exception as exc:
        logger.error("generate_content Groq error | voice_id=%s | err=%s", voice_id, exc)
        raise HTTPException(status_code=500, detail=f"Lỗi sinh nội dung: {exc}")

    logger.info("generate_content done | voice_id=%s | content_type=%s", voice_id, content_type)

    return {
        "voice_id":     voice_id,
        "content_type": content_type,
        "content":      content,
    }