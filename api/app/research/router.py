from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.research.research_service import run_research

from .models import (
    FbPhoto,
    PipelineTask,
    PipelineEvent,
    ResearchResult,
    FbPost,
    FbComment,
)

from .schemas import TestPipelineRequest

router = APIRouter(
    prefix="/research",
    tags=["Research"],
)


# ─────────────────────────────────────────────
# RUN PIPELINE
# ─────────────────────────────────────────────

@router.post("/test")
async def test_pipeline(
    payload: TestPipelineRequest = Depends(),
    db: AsyncSession = Depends(get_db),
):
    await payload.validate_fb_exists()

    return await run_research(
        db=db,
        query=payload.query,
        fb_url=payload.fb_url,
        business_id=payload.business_id,
        business_name=payload.business_name,
    )


# ─────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────

@router.get("/list")
async def list_businesses(
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(PipelineTask)
        )
    ).scalars().all()

    return rows


# ─────────────────────────────────────────────
# TASK
# ─────────────────────────────────────────────

@router.get("/{business_id}/task")
async def get_task(
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(PipelineTask)
            .where(
                PipelineTask.business_id
                == business_id
            )
        )
    ).scalars().first()

    if not row:
        raise HTTPException(404, "Task không tồn tại")

    return row


# ─────────────────────────────────────────────
# EVENTS
# ─────────────────────────────────────────────

@router.get("/{business_id}/events")
async def get_events(
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    return (
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


# ─────────────────────────────────────────────
# RESULT
# ─────────────────────────────────────────────

@router.get("/{business_id}/result")
async def get_result(
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(ResearchResult)
            .where(
                ResearchResult.business_id
                == business_id
            )
        )
    ).scalars().first()

    if not row:
        raise HTTPException(404, "ResearchResult không tồn tại")

    return row


# ─────────────────────────────────────────────
# POSTS
# ─────────────────────────────────────────────

@router.get("/{business_id}/posts")
async def get_posts(
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    return (
        await db.execute(
            select(FbPost)
            .where(
                FbPost.business_id
                == business_id
            )
        )
    ).scalars().all()


# ─────────────────────────────────────────────
# COMMENTS
# ─────────────────────────────────────────────

@router.get("/{business_id}/comments")
async def get_comments(
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    return (
        await db.execute(
            select(FbComment)
            .where(
                FbComment.business_id
                == business_id
            )
        )
    ).scalars().all()


# ─────────────────────────────────────────────
# COMMENTS
# ─────────────────────────────────────────────

@router.get("/{business_id}/photos")
async def get_photos(
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    return (
        await db.execute(
            select(FbPhoto)
            .where(
                FbPhoto.business_id
                == business_id
            )
        )
    ).scalars().all()

# ─────────────────────────────────────────────
# FULL
# ─────────────────────────────────────────────

@router.get("/{business_id}/full")
async def get_full(
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    async def one(model):
        return (
            await db.execute(
                select(model)
                .where(
                    model.business_id
                    == business_id
                )
            )
        ).scalars()

    return {
        "task": (await one(PipelineTask)).first(),
        "result": (await one(ResearchResult)).first(),
        "posts": (await one(FbPost)).all(),
        "comments": (await one(FbComment)).all(),
        "events": (
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
        ).scalars().all(),
    }