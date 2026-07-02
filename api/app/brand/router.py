"""
routers/brand_voice.py — MARKDOWN-FIRST VERSION (K1 → K7)
────────────────────────────────────────────────────────────
Key changes vs FIXED VERSION:
1. extract_brand_voice() giờ trả về 7 block Markdown (k1_brand_foundation
   → k7_vocabulary_rules) thay vì 8 field JSON (personality/tone/style/
   vocabulary/format_rules/cta_style/examples).
2. Brand record không còn JSON voice fields — chỉ gán trực tiếp Text
   markdown, không transform / parse.
3. create_brand_voice() khởi tạo K1-K7 = None (rỗng) — sẽ được fill bởi
   background task sau khi extract xong.
4. Helper _apply_k_fields() dùng chung cho cả 2 background task để tránh
   lặp code khi gán 7 block + 4 trục tone.
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

from app.brand.brand_voice_prompt import ContentType
from app.brand.service_slice import extract_brand_voice
from app.research.models import PipelineEvent
from app.db import get_db
from app.business.models import Business
from app.tasks.service import create_task, finish_task, fail_task, update_task
from app.llm_clients import async_groq_client, GROQ_MODEL
from app.db import get_db, AsyncSessionLocal

from .models import Brand
from .schemas import (
    BrandCreate,
    BrandListOut,
    BrandOut,
    BrandUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brand-voices", tags=["Brand Voice"])

# Tên 7 block markdown (K1 → K7) — dùng chung khi extract/gán dữ liệu
K_FIELD_NAMES = [
    "k1_brand_foundation",
    "k2_customer_insights",
    "k3_content_patterns",
    "k4_behavior_rules",
    "k5_examples",
    "k6_tone_analysis",
    "k7_vocabulary_rules",
]


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


def _apply_k_fields(voice: Brand, k_fields: Dict[str, Any], research) -> None:
    """
    Gán trực tiếp 7 block Markdown (K1-K7) + metadata + 4 trục tone vào Brand.
    Không parse / transform — extract_brand_voice() phải trả về Markdown
    thuần cho mỗi key trong K_FIELD_NAMES.
    """
    logo_url = (research.fb_brand or {}).get("og_image", "")

    voice.metadata_info = {
        "logo_url": logo_url,
        "updated_at": _utcnow().isoformat(),
    }

    for field in K_FIELD_NAMES:
        setattr(voice, field, k_fields.get(field))

    # Optional: extractor có thể trả thêm taglines / business_facts
    if "taglines" in k_fields:
        voice.taglines = k_fields["taglines"]
    if "business_facts" in k_fields:
        voice.business_facts = k_fields["business_facts"]

    voice.tone_funny_serious = k_fields.get("tone_funny_serious", 50)
    voice.tone_formal_casual = k_fields.get("tone_formal_casual", 50)
    voice.tone_respectful_irreverent = k_fields.get("tone_respectful_irreverent", 50)
    voice.tone_enthusiastic_matter_of_fact = k_fields.get(
        "tone_enthusiastic_matter_of_fact", 50
    )


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
# BACKGROUND TASK #1 — Extract từ existing research
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
    extract_brand_voice() → trả về K1-K7 Markdown
        ↓
    save Brand (gán trực tiếp, không parse)
    """

    async with AsyncSessionLocal() as db:

        try:
            # =====================================================
            # Load business + research
            # =====================================================

            research = await _get_latest_research(db, business_id)

            if not research:
                raise ValueError("Business chưa có research")

            fb_posts = await _get_fb_posts_for_research(db, business_id)
            fb_comments = await _get_fb_comments_for_research(db, business_id)

            events = (
                await db.execute(
                    select(PipelineEvent)
                    .where(PipelineEvent.business_id == business_id)
                    .order_by(PipelineEvent.seq)
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
            # Extract — trả về dict 7 block Markdown (K1-K7)
            # =====================================================

            k_fields = await extract_brand_voice(full_record)

            await update_task(db, task_id, steps_done=1)

            # =====================================================
            # Load brand
            # =====================================================

            result = await db.execute(select(Brand).where(Brand.id == voice_id))
            voice = result.scalars().first()

            if not voice:
                await fail_task(
                    db,
                    task_id,
                    error_message=f"Brand {voice_id} không tồn tại",
                )
                return

            # =====================================================
            # Save — gán trực tiếp K1-K7, không transform
            # =====================================================

            _apply_k_fields(voice, k_fields, research)

            await db.commit()
            await finish_task(db, task_id, steps_done=2)

            logger.info("_extract_and_save_bg success | voice=%s", voice_id)

        except Exception as exc:
            logger.exception("_extract_and_save_bg failed")
            await fail_task(db, task_id, error_message=str(exc))


# ═══════════════════════════════════════════════════════════════════
# BACKGROUND TASK #2 — Research + Extract
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
    - Extract brand voice → K1-K7 Markdown
    - Save Brand
    """

    async with AsyncSessionLocal() as db:
        try:
            business = await _get_business_or_404(business_id, db)

            # =====================================================
            # Ensure research exists
            # =====================================================

            research = await _get_latest_research(db, business_id)

            if not research:
                logger.info("_research_and_extract_bg | run research")

                from app.research.research_service import run_research

                query = (
                    f"{business.name} "
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

            await update_task(db, task_id, steps_done=1)

            # =====================================================
            # Reload DB (source of truth)
            # =====================================================

            research = await _get_latest_research(db, business_id)

            if not research:
                raise RuntimeError("Research pipeline completed nhưng DB rỗng")

            fb_posts = await _get_fb_posts_for_research(db, business_id)
            fb_comments = await _get_fb_comments_for_research(db, business_id)

            events = (
                await db.execute(
                    select(PipelineEvent)
                    .where(PipelineEvent.business_id == business_id)
                    .order_by(PipelineEvent.seq)
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
            # Extract — trả về dict 7 block Markdown (K1-K7)
            # =====================================================

            k_fields = await extract_brand_voice(full_record)

            await update_task(db, task_id, steps_done=2)

            # =====================================================
            # Load brand
            # =====================================================

            result = await db.execute(select(Brand).where(Brand.id == voice_id))
            voice = result.scalars().first()

            if not voice:
                await fail_task(
                    db,
                    task_id,
                    error_message=f"Brand {voice_id} không tồn tại",
                )
                return

            # =====================================================
            # Save — gán trực tiếp K1-K7, không transform
            # =====================================================

            _apply_k_fields(voice, k_fields, research)

            await db.commit()
            await finish_task(db, task_id, steps_done=3)

            logger.info("_research_and_extract_bg success | voice=%s", voice_id)

        except Exception as exc:
            logger.exception("_research_and_extract_bg failed")
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
    """202 Accepted — tạo record ngay, LLM extract K1-K7 chạy background.
    Tự động forcing chạy research nếu DB trống hoặc đổi website_url mới.
    """
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
                address="",
                industry="",
            )
            is_research_needed = True

    # ── Create Brand record ─────────────────────────────────────
    # K1-K7 khởi tạo rỗng (None) — background task sẽ fill markdown sau khi extract.
    voice = Brand(
        business_id     = business.id,
        name            = payload.business_name,
        purpose         = "Tăng trưởng kinh doanh và nhận diện thương hiệu",
        channels        = ["social", "blog"],
        desired_tone    = "Chuyên nghiệp",
        target_audience = "Khách hàng mục tiêu",

        website_url=payload.website_url,

        k1_brand_foundation = None,
        k2_customer_insights = None,
        k3_content_patterns = None,
        k4_behavior_rules = None,
        k5_examples = None,
        k6_tone_analysis = None,
        k7_vocabulary_rules = None,

        tone_funny_serious               = 50,
        tone_formal_casual               = 50,
        tone_respectful_irreverent       = 50,
        tone_enthusiastic_matter_of_fact = 50,
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

    
@router.get("/{brand_id}/preview-prompt", response_model=Dict[str, Any])
async def preview_brand_prompt(
    brand_id: str,
    content_type: ContentType = Query(...),
    topic: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from app.brand.brand_voice_prompt import get_brand_prompt_by_id
    from app.marketing.rag_context import fetch_rag_context  # debug trực tiếp

    user_input: Dict[str, Any] = {"topic": topic or ""}

    brand_row = (await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None))
    )).scalars().one_or_none()


    # Debug: gọi thẳng fetch_rag_context để xem RAW output, tách biệt khỏi luồng build prompt
    rag_raw_debug = None
    try:
        rag_raw_debug = await fetch_rag_context(business_id=brand_row.business_id, query=topic or "", top_k=5)
    except Exception as exc:
        rag_raw_debug = {"error": str(exc)}

    prompt = await get_brand_prompt_by_id(
        brand_id=brand_id, content_type=content_type, user_input=user_input, db=db,
    )

    return {
        "brand_id": brand_id,
        "brand_id_input": brand_id,
        "brand_business_id_actual": brand_row.business_id if brand_row else None,
        "rag_raw_debug": rag_raw_debug,   
        "system_prompt": prompt,
        "prompt_length": len(prompt),
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
# GET /brand-voices/{voice_id} — chi tiết (trả nguyên K1-K7 Markdown)
# ═══════════════════════════════════════════════════════════════════

@router.get("/{voice_id}", response_model=BrandOut)
async def get_brand_voice(voice_id: str, db: AsyncSession = Depends(get_db)) -> Brand:
    return await _get_voice_or_404(voice_id, db)


# ═══════════════════════════════════════════════════════════════════
# PATCH /brand-voices/{voice_id} — user edit trực tiếp Markdown từng block
# ═══════════════════════════════════════════════════════════════════

@router.patch("/{voice_id}", response_model=BrandOut)
async def update_brand_voice(
    voice_id: str,
    data: BrandUpdate,
    db: AsyncSession = Depends(get_db),
) -> Brand:
    """
    Cho phép cập nhật trực tiếp bất kỳ block K1-K7 (hoặc field khác).
    K1-K7 là Text Markdown — gán thẳng, không merge/parse.
    Field dict (taglines/business_facts/metadata_info) vẫn merge như cũ.
    """
    voice = await _get_voice_or_404(voice_id, db)

    for field, value in data.model_dump(exclude_unset=True).items():
        if field in K_FIELD_NAMES:
            # Markdown block — overwrite nguyên văn, không transform
            setattr(voice, field, value)
            continue

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