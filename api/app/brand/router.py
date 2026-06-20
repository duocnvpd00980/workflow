"""
routers/brand_voice.py — FIXED VERSION
────────────────────────────────
Key fixes:
1. Import signal_extractor & research_mapper
2. Background tasks now follow correct pipeline:
   build_research_json() → extract_brand_signals() → extract_brand_voice()
3. Fetch ResearchResult, FbPost, FbComment từ DB trước khi xử lý
"""

from __future__ import annotations
import logging
from datetime import datetime, timezone
import re
from typing import Any, Dict, Literal, Optional
import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.brand.service_slice import extract_brand_voice
from app.research.models import PipelineEvent
from app.db import get_db
from app.business.models import Business
from app.tasks.service import create_task, finish_task, fail_task, update_task
from app.llm_clients import async_groq_client, GROQ_MODEL
from app.db import get_db, AsyncSessionLocal
from app.brand.brand_voice_prompt import build_system_prompt

from .models import Brand
from .schemas import (
    BrandCreate,
    BrandListOut,
    BrandOut,
    BrandUpdate,
)

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
        .order_by(ResearchResult.updated_at.desc())
        .limit(1)
    )
    return result.scalars().first()

async def _find_business_by_brand_voice(
    db: AsyncSession,
    url: str | None = None,
    name: str | None = None,
) -> str | None:
    """Tìm business_id từ brand voice đã có cùng URL hoặc name."""
    from app.brand.models import Brand  # điều chỉnh import theo project
    
    if url:
        stmt = select(Brand).where(Brand.website_url == url)
        result = await db.execute(stmt)
        brand = result.scalars().first()
        if brand:
            return brand.business_id
    
    if name:
        from app.business.models import Business
        stmt = (
            select(Brand)
            .join(Business, Brand.business_id == Business.id)
            .where(
                or_(
                    func.lower(Brand.name) == name.lower().strip(),
                    func.lower(Business.name) == name.lower().strip(),
                )
            )
        )
        result = await db.execute(stmt)
        brand = result.scalars().first()
        if brand:
            return brand.business_id
    
    return None


async def _get_fb_posts_for_research(
    db: AsyncSession,
    business_id: str,
):
    from app.research.models import FbPost

    result = await db.execute(
        select(FbPost)
        .where(FbPost.business_id == business_id)
    )

    return result.scalars().all()


async def _get_fb_comments_for_research(
    db: AsyncSession,
    business_id: str,
):
    from app.research.models import FbComment

    result = await db.execute(
        select(FbComment)
        .where(FbComment.business_id == business_id)
    )

    return result.scalars().all()
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



# ═══════════════════════════════════════════════════════════════════
# 🔧 FIXED BACKGROUND TASK #1 — Extract từ existing research
# ═══════════════════════════════════════════════════════════════════


async def _extract_and_save_bg(
    voice_id: str,
    business_id: str,
    task_id: int,
) -> None:
    """
    Existing business + existing research.

    Flow:
    load research aggregate
        ↓
    extract_brand_voice()
        ↓
    save Brand
    """

    async with AsyncSessionLocal() as db:

        try:

            # =====================================================
            # Load business + research
            # =====================================================

            # business = await _get_business_or_404(
            #     business_id,
            #     db,
            # )

            research = await _get_latest_research(
                db,
                business_id,
            )

            if not research:
                raise ValueError(
                    "Business chưa có research"
                )

            fb_posts = (
                await _get_fb_posts_for_research(
                    db,
                    business_id,
                )
            )

            fb_comments = (
                await _get_fb_comments_for_research(
                    db,
                    business_id,
                )
            )

            events = (
                await db.execute(
                    select(PipelineEvent)
                    .where(
                        PipelineEvent.business_id
                        == business_id
                    )
                    .order_by(
                        PipelineEvent.seq
                    )
                )
            ).scalars().all()

            logger.info(
                "_extract_and_save_bg | business=%s | posts=%s | comments=%s",
                business_id,
                len(fb_posts),
                len(fb_comments),
            )

            # =====================================================
            # Build aggregate
            # =====================================================

            full_record = {
                "task": None,
                "result": research,
                "posts": fb_posts,
                "comments": fb_comments,
                "events": events,
            }

            # =====================================================
            # Extract
            # =====================================================

            eight_fields = (
                await extract_brand_voice(
                    full_record
                )
            )

            await update_task(
                db,
                task_id,
                steps_done=1,
            )

            # =====================================================
            # Load brand
            # =====================================================

            result = await db.execute(
                select(Brand)
                .where(
                    Brand.id
                    == voice_id
                )
            )

            voice = (
                result
                .scalars()
                .first()
            )

            if not voice:

                await fail_task(
                    db,
                    task_id,
                    error_message=(
                        f"Brand "
                        f"{voice_id}"
                        " không tồn tại"
                    ),
                )

                return

            # =====================================================
            # Save
            # =====================================================

            logo_url = (
                research.fb_brand
                .get(
                    "og_image",
                    "",
                )
            )

            voice.metadata_info = {
                "logo_url": logo_url,
                "updated_at": (
                    _utcnow()
                    .isoformat()
                ),
            }

            voice.personality = (
                eight_fields[
                    "personality"
                ]
            )

            voice.tone = (
                eight_fields[
                    "tone"
                ]
            )

            voice.style = (
                eight_fields[
                    "style"
                ]
            )

            voice.vocabulary = (
                eight_fields[
                    "vocabulary"
                ]
            )

            voice.format_rules = (
                eight_fields[
                    "format_rules"
                ]
            )

            voice.cta_style = (
                eight_fields[
                    "cta_style"
                ]
            )

            voice.examples = (
                eight_fields.get(
                    "examples",
                    [],
                )
            )

            voice.tone_funny_serious = (
                eight_fields.get(
                    "tone_funny_serious",
                    50,
                )
            )

            voice.tone_formal_casual = (
                eight_fields.get(
                    "tone_formal_casual",
                    50,
                )
            )

            voice.tone_respectful_irreverent = (
                eight_fields.get(
                    "tone_respectful_irreverent",
                    50,
                )
            )

            voice.tone_enthusiastic_matter_of_fact = (
                eight_fields.get(
                    "tone_enthusiastic_matter_of_fact",
                    50,
                )
            )

            await db.commit()

            await finish_task(
                db,
                task_id,
                steps_done=2,
            )

            logger.info(
                "_extract_and_save_bg success"
                " | voice=%s",
                voice_id,
            )

        except Exception as exc:

            logger.exception(
                "_extract_and_save_bg failed"
            )

            await fail_task(
                db,
                task_id,
                error_message=str(
                    exc
                ),
            )



# ═══════════════════════════════════════════════════════════════════
# 🔧 FIXED BACKGROUND TASK #2 — Research + Extract
# ═══════════════════════════════════════════════════════════════════

async def _research_and_extract_bg(
    voice_id: str,
    business_id: str,
    task_id: int,
    website_url: str | None = None,
) -> None:
    """
    Background:
    - Đảm bảo research tồn tại
    - Load FULL research aggregate từ DB
    - Extract brand voice
    - Save Brand
    """

    async with AsyncSessionLocal() as db:
        try:
            business = await _get_business_or_404(
                business_id,
                db,
            )

            # =====================================================
            # Ensure research exists
            # =====================================================

            research = await _get_latest_research(
                db,
                business_id,
            )

            if not research:
                logger.info(
                    "_research_and_extract_bg | run research"
                )

                from app.research.research_service import (
                    run_research,
                )

                query = (
                    f"{business.name} "
                    f"{business.address or ''} "
                    f"{business.industry or ''}"
                ).strip()
                
                await run_research(
                    db=db,
                    business_id=business.id,
                    query=query,
                    fb_url=website_url,
                    business_name=business.name,
                )

                business.status = "active"

                await db.commit()

            await update_task(
                db,
                task_id,
                steps_done=1,
            )

            # =====================================================
            # Reload DB (source of truth)
            # =====================================================

            research = await _get_latest_research(
                db,
                business_id,
            )

            if not research:
                raise RuntimeError(
                    "Research pipeline completed nhưng DB rỗng"
                )

            fb_posts = await _get_fb_posts_for_research(
                db,
                business_id,
            )

            fb_comments = await _get_fb_comments_for_research(
                db,
                business_id,
            )

            events = (
                await db.execute(
                    select(PipelineEvent)
                    .where(
                        PipelineEvent.business_id
                        == business_id
                    )
                    .order_by(
                        PipelineEvent.seq
                    )
                )
            ).scalars().all()

            full_record = {
                "task": None,
                "result": research,
                "posts": fb_posts,
                "comments": fb_comments,
                "events": events,
            }

            # =====================================================
            # Extract
            # =====================================================

            eight_fields = await extract_brand_voice(
                full_record
            )

            await update_task(
                db,
                task_id,
                steps_done=2,
            )

            # =====================================================
            # Load brand
            # =====================================================

            result = await db.execute(
                select(Brand)
                .where(
                    Brand.id == voice_id
                )
            )

            voice = (
                result
                .scalars()
                .first()
            )

            if not voice:
                await fail_task(
                    db,
                    task_id,
                    error_message=(
                        f"Brand {voice_id}"
                        " không tồn tại"
                    ),
                )
                return

            # =====================================================
            # Save
            # =====================================================

            logo_url = (
                research.fb_brand
                .get(
                    "og_image",
                    "",
                )
            )

            voice.metadata_info = {
                "logo_url": logo_url,
                "updated_at": (
                    _utcnow()
                    .isoformat()
                ),
            }

            voice.personality = (
                eight_fields[
                    "personality"
                ]
            )

            voice.tone = (
                eight_fields[
                    "tone"
                ]
            )

            voice.style = (
                eight_fields[
                    "style"
                ]
            )

            voice.vocabulary = (
                eight_fields[
                    "vocabulary"
                ]
            )

            voice.format_rules = (
                eight_fields[
                    "format_rules"
                ]
            )

            voice.cta_style = (
                eight_fields[
                    "cta_style"
                ]
            )

            voice.examples = (
                eight_fields.get(
                    "examples",
                    [],
                )
            )

            voice.tone_funny_serious = (
                eight_fields.get(
                    "tone_funny_serious",
                    50,
                )
            )

            voice.tone_formal_casual = (
                eight_fields.get(
                    "tone_formal_casual",
                    50,
                )
            )

            voice.tone_respectful_irreverent = (
                eight_fields.get(
                    "tone_respectful_irreverent",
                    50,
                )
            )

            voice.tone_enthusiastic_matter_of_fact = (
                eight_fields.get(
                    "tone_enthusiastic_matter_of_fact",
                    50,
                )
            )

            await db.commit()

            await finish_task(
                db,
                task_id,
                steps_done=3,
            )

            logger.info(
                "_research_and_extract_bg success"
                " | voice=%s",
                voice_id,
            )

        except Exception as exc:

            logger.exception(
                "_research_and_extract_bg failed"
            )

            await fail_task(
                db,
                task_id,
                error_message=str(exc),
            )


# ═══════════════════════════════════════════════════════════════════
# POST /brand-voices — tạo mới (Case 1 + Case 2)
# ═══════════════════════════════════════════════════════════════════


@router.post("", response_model=BrandOut, status_code=status.HTTP_202_ACCEPTED)
async def create_brand_voice(
    payload: BrandCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Brand:
    """202 Accepted — tạo record ngay, LLM extract 8 fields chạy background.
    Tự động forcing chạy research nếu DB trống hoặc đổi website_url mới.
    """
    from app.research.models import ResearchResult  # Import model tương ứng của bạn vào đây

    is_research_needed = False
    
    # ── Determine Case ──────────────────────────────────────────
    if payload.business_id:
        # Case 1: Existing business
        business = await _get_business_or_404(payload.business_id, db)
        research = await _get_latest_research(db, business.id)
        
        if not research:
            logger.info("No research found → forcing research")
            is_research_needed = True
        else:
            # Lấy URL từ payload nếu có
            new_url = payload.website_url if hasattr(payload, 'website_url') else None
            
            # URL cũ từ research: ưu tiên fb_brand, fallback serp_data
            old_url = None
            if research.fb_brand and isinstance(research.fb_brand, dict):
                old_url = research.fb_brand.get("url") or research.fb_brand.get("link")
            if not old_url and research.serp_data and isinstance(research.serp_data, dict):
                old_url = research.serp_data.get("website_url")
            
            # So sánh URL (nếu cả 2 đều có)
            if new_url and old_url and new_url.rstrip("/") != old_url.rstrip("/"):
                logger.info("URL changed %s → %s → forcing research", old_url, new_url)
                is_research_needed = True
            else:
                logger.info("Research exists → skip research")
                is_research_needed = False

    else:
        # Case 2: New business — check duplicate trước
        existing_bid = await _find_business_by_brand_voice(
            db,
            url=payload.website_url if hasattr(payload, 'website_url') else None,
            name=payload.business_name,
        )
        
        if existing_bid:
            # Đã có brand voice cho URL/name này → reuse
            business = await _get_business_or_404(existing_bid, db)
            research = await _get_latest_research(db, business.id)
            is_research_needed = not bool(research)
            logger.info(
                "create_brand_voice | Reuse existing | business_id=%s | research_needed=%s",
                business.id, is_research_needed
            )
        else:
            # Tạo business mới
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
        
        tone_funny_serious               = payload.tone_funny_serious,
        tone_formal_casual               = payload.tone_formal_casual,
        tone_respectful_irreverent       = payload.tone_respectful_irreverent,
        tone_enthusiastic_matter_of_fact = payload.tone_enthusiastic_matter_of_fact,
        
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
    
    
    # ── Schedule background task ────────────────────────────────
    if is_research_needed:
        background_tasks.add_task(
            _research_and_extract_bg,
            voice_id        = voice.id,
            business_id     = business.id,
            task_id         = task.id,
            website_url=payload.website_url if hasattr(payload, 'website_url') else None,
        )
    else:
        background_tasks.add_task(
            _extract_and_save_bg,
            voice_id        = voice.id,
            business_id     = business.id,
            task_id         = task.id,
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