"""
routers/brand_voice.py
────────────────────────────────
CRUD + generate endpoint cho Brand system.
Dùng app.llm_clients (async_groq_client, call_groq) — KHÔNG dùng litellm.

Endpoints:
    POST   /brand-voices                       → tạo mới (auto-research nếu cần)
    GET    /brand-voices                       → list theo business_id
    GET    /brand-voices/{voice_id}            → chi tiết
    PATCH  /brand-voices/{voice_id}            → user edit sau preview
    DELETE /brand-voices/{voice_id}            → soft delete
    POST   /brand-voices/{voice_id}/set-default → đặt làm default
    POST   /brand-voices/{voice_id}/generate   → tạo content từ voice

LOGIC MỚI:
    - Case 1: business_id có → extract voice thẳng
    - Case 2: business_id = None, business_name + owner_id → 
             tạo business mới → run pipeline research → update business → extract voice
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
import re
from typing import Any, Dict, Literal, Optional
import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.business.models import Business
from app.tasks.service import create_task, finish_task, fail_task, update_task
from app.llm_clients import async_groq_client, GROQ_MODEL

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


async def _get_latest_research(db: AsyncSession, business_id: str):
    """Lấy research result mới nhất của business."""
    from app.research.models import ResearchResult
    
    result = await db.execute(
        select(ResearchResult)
        .filter(ResearchResult.business_id == business_id)
        .order_by(ResearchResult.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()


# ═══════════════════════════════════════════════════════════════════
# CASE 2 HELPERS — Create business + Research pipeline
# ═══════════════════════════════════════════════════════════════════

async def _generate_unique_slug(db: AsyncSession, business_name: str) -> str:
    """Tạo slug unique, tự động append suffix nếu trùng."""
    base = re.sub(r'[^a-z0-9]+', '-', business_name.lower()).strip('-')
    base = re.sub(r'-+', '-', base)  # collapse multiple dashes
    
    if not base:
        base = f"biz-{uuid.uuid4().hex[:6]}"
    
    slug = base
    counter = 1
    
    while True:
        result = await db.execute(
            select(func.count()).select_from(Business).filter(Business.slug == slug)
        )
        if result.scalar_one() == 0:
            break
        slug = f"{base}-{counter}"
        counter += 1
        if counter > 100:
            slug = f"{base}-{uuid.uuid4().hex[:6]}"
            break
    
    if slug != base:
        logger.info(
            "Slug auto-fixed | business_name=%s | original=%s | final=%s",
            business_name, base, slug
        )
    
    return slug


async def _create_new_business(
    db: AsyncSession,
    business_name: str,
    owner_id: str,
    address: Optional[str] = None,
    industry: Optional[str] = None,
) -> Business:
    """
    Tạo business record mới với status="pending" (chưa research).
    Slug được tự động unique hóa, không báo lỗi cho user.
    """
    slug = await _generate_unique_slug(db, business_name)
    
    business = Business(
        name=business_name,
        slug=slug,
        owner_id=owner_id,
        address=address,
        industry=industry,
        status="pending",
    )
    db.add(business)
    await db.commit()
    await db.refresh(business)
    logger.info("Created new business | business_id=%s | name=%s | slug=%s", 
                business.id, business_name, slug)
    return business


async def _run_research_pipeline(
    db: AsyncSession,
    business: Business,
    brand_task_id: int,
) -> Dict[str, Any]:
    """
    Gọi pipeline research. run_pipeline tự lưu DB research.
    KHÔNG tạo task thêm, KHÔNG update brand_task_id.
    """
    try:
        logger.info("Starting research pipeline | business_id=%s", business.id)
        
        from app.research.service import run_pipeline
        
        # Chạy pipeline, tự lưu research_results, KHÔNG tạo task
        state = await run_pipeline(
            business_name=business.name,
            address=business.address or "",
            industry=business.industry or "",
            business_id=business.id,
        )
        
        # Extract output
        final_report = state.get("final_report", "")
        competitor_analysis = state.get("competitor_analysis", "")
        competitors_clean = state.get("competitors_clean", [])
        
        # Update business
        business.description = final_report
        business.status = "active"
        await db.commit()
        
        logger.info(
            "Research pipeline done | business_id=%s | report_len=%d",
            business.id,
            len(final_report),
        )
        
        return {
            "business_id": business.id,
            "final_report": final_report,
            "competitor_analysis": competitor_analysis,
            "competitors_clean": competitors_clean,
        }
        
    except Exception as exc:
        logger.error("Research pipeline failed | business_id=%s | err=%s", business.id, exc)
        
        # Soft delete business
        business.status = "deleted"
        business.deleted_at = _utcnow()
        await db.commit()
        
        raise RuntimeError(f"Research pipeline failed: {exc}") from exc


# ═══════════════════════════════════════════════════════════════════
# BACKGROUND TASK — extract 8 fields + save
# ═══════════════════════════════════════════════════════════════════

async def _extract_and_save_bg(
    db: AsyncSession,
    voice_id: str,
    business_id: str,
    voice_config_dict: Dict[str, Any],
    user_rag: str,
    research_rag: str,
    task_id: int,
) -> None:
    """
    Case 1: Existing business, chỉ extract voice.
    """
    try:
        # Merge RAG
        rag_parts = []
        if user_rag.strip():
            rag_parts.append(f"=== USER INPUT ===\n{user_rag}")
        if research_rag.strip():
            rag_parts.append(f"=== RESEARCH DATA ===\n{research_rag}")
        
        rag_content = "\n\n".join(rag_parts)
        
        if not rag_content:
            # Fallback
            business = await _get_business_or_404(business_id, db)
            rag_content = f"Tên: {business.name}\nNgành: {business.industry or '?'}"

        # Step 1: LLM extract
        business = await _get_business_or_404(business_id, db)
        business_dict = {c.name: getattr(business, c.name) for c in business.__table__.columns}
        
        eight_fields = await extract_brand_voice(
            business=business_dict,
            voice_config=voice_config_dict,
            rag_content=rag_content,
        )
        await update_task(db, task_id, steps_done=1)

        # Step 2: Update DB
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


        voice.tone_funny_serious               = eight_fields.get("tone_funny_serious", 50)
        voice.tone_formal_casual               = eight_fields.get("tone_formal_casual", 50)
        voice.tone_respectful_irreverent       = eight_fields.get("tone_respectful_irreverent", 50)
        voice.tone_enthusiastic_matter_of_fact = eight_fields.get("tone_enthusiastic_matter_of_fact", 50)

        await db.commit()
        await finish_task(db, task_id, steps_done=2)
        logger.info("extract_bg done | voice_id=%s | task_id=%s", voice_id, task_id)

    except Exception as exc:
        logger.error("extract_bg failed | voice_id=%s | err=%s", voice_id, exc)
        await fail_task(db, task_id, error_message=str(exc))


async def _research_and_extract_bg(
    db: AsyncSession,
    voice_id: str,
    business_id: str,
    voice_config_dict: Dict[str, Any],
    rag_source_dict: Dict[str, Any],
    task_id: int,
) -> None:
    """
    Case 2: New business + research + extract.
    Steps: 1. research, 2. extract, 3. save
    """
    try:
        # Step 1: Research pipeline
        business = await _get_business_or_404(business_id, db)
        pipeline_output = await _run_research_pipeline(db, business, task_id)
        await update_task(db, task_id, steps_done=1)  # Step 1 done
        
        # Step 2: Prepare RAG + Extract voice
        rag_content = rag_source_dict.get("pasted_text") or ""
        if pipeline_output.get("final_report"):
            rag_content += f"\n\n=== PIPELINE RESEARCH REPORT ===\n{pipeline_output['final_report']}"
        
        # Refresh business dict từ DB (sau khi pipeline update description)
        result = await db.execute(select(Business).filter(Business.id == business_id))
        business = result.scalars().first()
        business_dict = {c.name: getattr(business, c.name) for c in business.__table__.columns}
        
        eight_fields = await extract_brand_voice(
            business=business_dict,
            voice_config=voice_config_dict,
            rag_content=rag_content,
        )
        await update_task(db, task_id, steps_done=2)  # Step 2 done
        
        # Step 3: Update Brand record
        result = await db.execute(select(Brand).filter(Brand.id == voice_id))
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
        await finish_task(db, task_id, steps_done=3)  # Step 3 done
        logger.info(
            "research_and_extract_bg done | voice_id=%s | business_id=%s | task_id=%s",
            voice_id, business_id, task_id
        )
        
    except Exception as exc:
        logger.error(
            "research_and_extract_bg failed | voice_id=%s | business_id=%s | err=%s",
            voice_id, business_id, exc
        )
        await fail_task(db, task_id, error_message=str(exc))


# ═══════════════════════════════════════════════════════════════════
# POST /brand-voices — tạo mới (Case 1 + Case 2)
# ═══════════════════════════════════════════════════════════════════

@router.post("", response_model=BrandOut, status_code=status.HTTP_202_ACCEPTED)
async def create_brand_voice(
    payload: BrandCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Brand:
    """
    202 Accepted — tạo record ngay, LLM extract 8 fields chạy background.
    """
    
    # ── Determine Case ──────────────────────────────────────────
    if payload.business_id:
        # Case 1: Existing business
        logger.info("create_brand_voice | Case 1 | business_id=%s", payload.business_id)
        business = await _get_business_or_404(payload.business_id, db)
        is_research_needed = False
    else:
        # Case 2: New business + research
        logger.info(
            "create_brand_voice | Case 2 | business_name=%s | owner_id=%s",
            payload.business_name, payload.owner_id
        )
        business = await _create_new_business(
            db,
            business_name=payload.business_name,
            owner_id=payload.owner_id,
            address=payload.address,
            industry=payload.industry,
        )
        is_research_needed = True
    
    # ── Prepare RAG content ─────────────────────────────────────
    # 1. User input
    user_rag = ""
    if payload.rag_source and payload.rag_source.pasted_text:
        user_rag = payload.rag_source.pasted_text

    # 2. Auto-query research DB (song song, luôn lấy)
    research_rag = ""
    research = await _get_latest_research(db, business.id)
    if research and research.final_report:
        research_rag = research.final_report

    # Merge cho fallback
    rag_content = user_rag
    if research_rag:
        if rag_content:
            rag_content += f"\n\n=== RESEARCH REPORT ===\n{research_rag}"
        else:
            rag_content = research_rag

    if not rag_content:
        rag_content = f"""
        Tên doanh nghiệp: {business.name}
        Ngành: {business.industry or 'Không rõ'}
        Địa chỉ: {business.address or 'Không rõ'}
        """
    
    # ── Create Brand record ─────────────────────────────────────
    voice = Brand(
        business_id     = business.id,
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

        # Nhận dữ liệu mặc định hoặc thiết lập tay từ ban đầu
        tone_funny_serious               = payload.tone_funny_serious,
        tone_formal_casual               = payload.tone_formal_casual,
        tone_respectful_irreverent       = payload.tone_respectful_irreverent,
        tone_enthusiastic_matter_of_fact = payload.tone_enthusiastic_matter_of_fact,


        # RAG sources
        website_url    = payload.rag_source.website_url if payload.rag_source else None,
        uploaded_files = payload.rag_source.uploaded_files if payload.rag_source else [],
        pasted_text    = payload.rag_source.pasted_text if payload.rag_source else None,
    )
    db.add(voice)
    await db.commit()
    await db.refresh(voice)
    
    # ── Create Task record ──────────────────────────────────────
    steps_total = 3 if is_research_needed else 2
    task = await create_task(
        db,
        source      = "brand_voice",
        source_id   = voice.id,
        title       = f"Extract brand voice: {voice.name}" + (" (+ research)" if is_research_needed else ""),
        triggered_by= "user",
        steps_total = steps_total,
        model       = GROQ_MODEL,
    )
    
    # ── Prepare dicts ───────────────────────────────────────────
    voice_config_dict = payload.voice_config.model_dump()
    rag_source_dict = payload.rag_source.model_dump() if payload.rag_source else {}
    
    # ── Schedule background task ────────────────────────────────
    if is_research_needed:
        background_tasks.add_task(
            _research_and_extract_bg,
            db              = db,
            voice_id        = voice.id,
            business_id     = business.id,
            voice_config_dict = voice_config_dict,
            rag_source_dict = rag_source_dict,
            task_id         = task.id,
        )
    else:
        background_tasks.add_task(
            _extract_and_save_bg,
            db=db,
            voice_id=voice.id,
            business_id=business.id,
            voice_config_dict=voice_config_dict,
            user_rag=user_rag,
            research_rag=research_rag,
            task_id=task.id,
        )
    
    logger.info(
        "create_brand_voice scheduled | voice_id=%s | business_id=%s | task_id=%s | research=%s",
        voice.id, business.id, task.id, is_research_needed
    )
    return voice


# ═══════════════════════════════════════════════════════════════════
# GET /brand-voices — list
# ═══════════════════════════════════════════════════════════════════

@router.get("", response_model=BrandListOut)
async def list_brand_voices(
    business_id: Optional[str] = Query(None, description="Filter theo business"),
    skip: int  = Query(0,  ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    conditions = [Brand.deleted_at.is_(None)]
    
    if business_id:
        conditions.append(Brand.business_id == business_id)
        
    items_result = await db.execute(
        select(Brand)
        .filter(*conditions)
        .order_by(Brand.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    count_result = await db.execute(
        select(func.count()).select_from(Brand).filter(*conditions)
    )
    
    return {
        "items": items_result.scalars().all(), 
        "total": count_result.scalar_one()
    }


# ═══════════════════════════════════════════════════════════════════
# GET /brand-voices/options — Lightweight API
# ═══════════════════════════════════════════════════════════════════

@router.get("/options", response_model=list[Dict[str, Any]])
async def get_brand_voice_options(
    db: AsyncSession = Depends(get_db)
) -> list[Dict[str, Any]]:
    result = await db.execute(
        select(Brand.id, Brand.name, Brand.business_id, Brand.is_default)
        .filter(Brand.deleted_at.is_(None))
        .order_by(Brand.name.asc())
    )
    
    return [
        {
            "id": row.id, 
            "name": row.name, 
            "business_id": row.business_id,
            "is_default": row.is_default == "1"
        } 
        for row in result.all()
    ]


# ═══════════════════════════════════════════════════════════════════
# GET /brand-voices/{voice_id} — chi tiết
# ═══════════════════════════════════════════════════════════════════

@router.get("/{voice_id}", response_model=BrandOut)
async def get_brand_voice(voice_id: str, db: AsyncSession = Depends(get_db)) -> Brand:
    return await _get_voice_or_404(voice_id, db)


# ═══════════════════════════════════════════════════════════════════
# PATCH /brand-voices/{voice_id} — user edit
# ═══════════════════════════════════════════════════════════════════

@router.patch("/{voice_id}", response_model=BrandOut)
async def update_brand_voice(
    voice_id: str,
    data: BrandUpdate,
    db: AsyncSession = Depends(get_db),
) -> Brand:
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