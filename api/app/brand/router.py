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
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.business.models import Business
from app.tasks.service import create_task, finish_task, fail_task, update_task
from app.llm_clients import async_groq_client, GROQ_MODEL
from app.db import get_db, AsyncSessionLocal
# ✅ IMPORTS - HỌ chưa import signal_extractor & research_mapper
from app.brand.research_mapper import build_research_json
from app.brand.signal_extractor import extract_brand_signals
from app.brand.brand_voice_extract import extract_brand_voice
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


# async def _run_research_pipeline(
#     db: AsyncSession,
#     business: Business,
#     brand_task_id: int,
# ) -> Dict[str, Any]:
#     """
#     Gọi pipeline research. run_pipeline tự lưu DB research.
#     KHÔNG tạo task thêm, KHÔNG update brand_task_id.
#     """
#     try:
#         logger.info("Starting research pipeline | business_id=%s", business.id)
        
#         from app.research.research_service import run_research
        
#         # Tạo query từ business info
#         query = f"{business.name} {business.industry or ''}".strip()
#         fb_url = business.website or ""

#         state = await run_research(
#             business_id=business.id,
#             query="nhà hàng hải sản đà nẵng",
#             fb_url="https://www.facebook.com/mocseafood/",
#             business_name=business.name,
#         )
        
#         # Extract output
#         final_report = state.get("final_report", "")
#         competitor_analysis = state.get("competitor_analysis", "")
#         competitors_clean = state.get("competitors_clean", [])
        
#         # Update business
#         business.description = final_report
#         business.status = "active"
#         await db.commit()
        
#         logger.info(
#             "Research pipeline done | business_id=%s | report_len=%d",
#             business.id,
#             len(final_report),
#         )
        
#         return {
#             "business_id": business.id,
#             "final_report": final_report,
#             "competitor_analysis": competitor_analysis,
#             "competitors_clean": competitors_clean,
#         }
        
#     except Exception as exc:
#         logger.error("Research pipeline failed | business_id=%s | err=%s", business.id, exc)
        
#         # Soft delete business
#         business.status = "deleted"
#         business.deleted_at = _utcnow()
#         await db.commit()
        
#         raise RuntimeError(f"Research pipeline failed: {exc}") from exc


# ═══════════════════════════════════════════════════════════════════
# 🔧 FIXED BACKGROUND TASK #1 — Extract từ existing research
# ═══════════════════════════════════════════════════════════════════
async def _extract_and_save_bg(
    voice_id: str,
    business_id: str,
    voice_config_dict: Dict[str, Any],
    task_id: int,
) -> None:
    """
    ✅ Case 1: Existing business + existing research
    Sử dụng AsyncSessionLocal độc lập hoàn toàn để không lỗi đóng kết nối request.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Step 1: Fetch research + posts + comments
            research = await _get_latest_research(db, business_id)
            
            if not research:
                raise ValueError("Chưa có research data cho business này. Hãy chạy research trước.")
            
            fb_posts = await _get_fb_posts_for_research(
                db,
                business_id,
            )

            fb_comments = await _get_fb_comments_for_research(
                db,
                business_id,
)
            
            logger.info(
                "extract_bg | fetched data | business_id=%s | posts=%d | comments=%d",
                business_id, len(fb_posts), len(fb_comments)
            )
            
            # Step 2: Build research_json (gom raw data thành 6 nhóm signal)
            research_json = build_research_json(
                research=research,
                fb_posts=fb_posts,
                fb_comments=fb_comments,
                voice_config=voice_config_dict,
            )
            
            # Step 3: Extract signals (lọc raw data thành brand_voice_input)
            brand_voice_input = extract_brand_signals(research_json)
            
            # Step 4: Extract 8 Brand Voice fields
            eight_fields = await extract_brand_voice(brand_voice_input)
            await update_task(db, task_id, steps_done=1)
            
            # Step 5: Update Brand ORM
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


# ═══════════════════════════════════════════════════════════════════
# 🔧 FIXED BACKGROUND TASK #2 — Research + Extract
# ═══════════════════════════════════════════════════════════════════

# Giả sử file app.db của bạn có async_session_maker (hoặc sessionmanager)

async def _research_and_extract_bg(
    voice_id: str,
    business_id: str,
    voice_config_dict: Dict[str, Any],
    task_id: int,
) -> None:
    """
    Sử dụng AsyncSessionLocal độc lập để đảm bảo pipeline mất vài phút chạy ngầm ổn định.
    """
    async with AsyncSessionLocal() as db:
        try:
            business = await _get_business_or_404(business_id, db)

            # Thử đọc DB trước
            research = await _get_latest_research(db, business_id)

            if research:
                # Có rồi → đọc DB bình thường
                logger.info("_research_and_extract_bg | Research found in DB. Extracting...")
                fb_posts    = await _get_fb_posts_for_research(db, research.id)
                fb_comments = await _get_fb_comments_for_research(db, research.id)
                research_json = build_research_json(
                    research=research,
                    fb_posts=fb_posts,
                    fb_comments=fb_comments,
                    voice_config=voice_config_dict,
                )
            else:
                # Chưa có → gọi run_research → đọc thẳng state
                logger.info("_research_and_extract_bg | Research NOT found. Running research pipeline...")
                from app.research.research_service import run_research

                query = f"{business.name} {business.address or ''} {business.industry or ''}".strip()
                state = await run_research(
                    db=db,
                    business_id=business.id,
                    query="nhà hàng quán nhậu hải sản Đà Nẵng",
                    fb_url="https://www.facebook.com/mocseafood/",
                    business_name=business.name,
                )

                # Build research_json thẳng từ state, KHÔNG qua DB
                research_json = {
                    "customer_language": {
                        "suggestions_raw": list(state.suggestions) if hasattr(state, 'suggestions') else state.get("suggestions", []),
                        "suggestions_tagged": state.tagged_suggestions if hasattr(state, 'tagged_suggestions') else state.get("tagged_suggestions", {}),
                    },
                    "market_patterns": state.serp_data if hasattr(state, 'serp_data') else state.get("serp_data", {}),
                    "existing_brand_voice": {
                        "fb_brand": state.fb_data.get("brand", {}) if hasattr(state, 'fb_data') else state.get("fb_data", {}).get("brand", {}),
                        "posts_raw": state.fb_data.get("posts", []) if hasattr(state, 'fb_data') else state.get("fb_data", {}).get("posts", []),
                    },
                    "customer_feedback": {
                        "comments_raw": state.fb_data.get("comments", []) if hasattr(state, 'fb_data') else state.get("fb_data", {}).get("comments", []),
                    },
                    "competitor_insights": {
                        "competitor_pattern": (state.serp_data or {}).get("competitor_pattern", []) if hasattr(state, 'serp_data') else state.get("serp_data", {}).get("competitor_pattern", []),
                    },
                    "business_context": {
                        "business_id": business.id,
                        "business_name": business.name,
                        "voice_config": voice_config_dict,
                    },
                }

                # Update business status
                business.status = "active"
                await db.commit()

            await update_task(db, task_id, steps_done=1)

            # Trích xuất tín hiệu & gọi Groq LLM xử lý 8 trường
            brand_voice_input = extract_brand_signals(research_json)
            eight_fields = await extract_brand_voice(brand_voice_input)
            await update_task(db, task_id, steps_done=2)

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

            voice.tone_funny_serious               = eight_fields.get("tone_funny_serious", 50)
            voice.tone_formal_casual               = eight_fields.get("tone_formal_casual", 50)
            voice.tone_respectful_irreverent       = eight_fields.get("tone_respectful_irreverent", 50)
            voice.tone_enthusiastic_matter_of_fact = eight_fields.get("tone_enthusiastic_matter_of_fact", 50)

            await db.commit()
            await finish_task(db, task_id, steps_done=3)
            logger.info("_research_and_extract_bg success | voice_id=%s | task_id=%s", voice_id, task_id)

        except Exception as exc:
            logger.error("_research_and_extract_bg failed | voice_id=%s | err=%s", voice_id, exc)
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
    """202 Accepted — tạo record ngay, LLM extract 8 fields chạy background.
    Tự động forcing chạy research nếu DB trống hoặc đổi website_url mới.
    """
    from app.research.models import ResearchResult  # Import model tương ứng của bạn vào đây

    is_research_needed = False
    
    # ── Determine Case ──────────────────────────────────────────
    if payload.business_id:
        # Case 1: Existing business
        logger.info("create_brand_voice | Case 1 | business_id=%s", payload.business_id)
        business = await _get_business_or_404(payload.business_id, db)
        
        # Kiểm tra thực tế trong Database xem đã tồn tại data research của business này chưa
        stmt = select(ResearchResult).where(ResearchResult.business_id == business.id)
        res = await db.execute(stmt)
        research = res.scalars().first()
        
        if not research:
            # Nếu lỡ xóa sạch DB, không thấy data research -> Bắt buộc phải chạy lại pipeline research
            logger.info("Research result NOT found in DB for business_id=%s. Forcing research pipeline...", business.id)
            is_research_needed = True
        else:
            # Nếu đã có data research nhưng URL truyền lên khác với URL cũ đã từng cào dữ liệu
            new_url = payload.rag_source.website_url if payload.rag_source else None
            old_url = None
            if research.serp_data and isinstance(research.serp_data, dict):
                old_url = research.serp_data.get("website_url")

            if new_url and new_url != old_url:
                logger.info("website_url changed (%s -> %s). Forcing re-run research pipeline...", old_url, new_url)
                is_research_needed = True
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
    
    voice_config_dict = payload.voice_config.model_dump()
    
    # ── Schedule background task ────────────────────────────────
    if is_research_needed:
        background_tasks.add_task(
            _research_and_extract_bg,
            voice_id        = voice.id,
            business_id     = business.id,
            voice_config_dict = voice_config_dict,
            task_id         = task.id,
        )
    else:
        background_tasks.add_task(
            _extract_and_save_bg,
            voice_id        = voice.id,
            business_id     = business.id,
            voice_config_dict = voice_config_dict,
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