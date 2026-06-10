from __future__ import annotations

import logging
from PIL import Image
import httpx

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.rag.service import ImageRAG
from app.rag.schemas import ImageAddIn, ImageOut, ImageSearchIn, ImageSearchOut, ImageSearchResultItem
from .models import ImageSource
from app.rag.schemas import ImageAddIn, ImageOut, ImageSearchIn, ImageSearchOut, ImageSearchResultItem, ImageTextSearchIn



logger = logging.getLogger(__name__)
router = APIRouter(prefix="/image", tags=["image"])

# singleton
_image_rag = ImageRAG()


def get_image_rag() -> ImageRAG:
    return _image_rag


async def _load_image(url: str) -> Image.Image:
    """Load ảnh từ URL hoặc local path."""
    if url.startswith("http"):
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            r.raise_for_status()
            from io import BytesIO
            return Image.open(BytesIO(r.content)).convert("RGB")
    else:
        return Image.open(url).convert("RGB")


@router.post("/add/", response_model=ImageOut, status_code=201)
async def add_image(
    payload: ImageAddIn,
    db: AsyncSession = Depends(get_db),
    rag: ImageRAG = Depends(get_image_rag),
):
    # Check duplicate
    existing = await db.execute(
        select(ImageSource).where(ImageSource.image_id == payload.image_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "image_id đã tồn tại.")

    record = ImageSource(
        image_id=payload.image_id,
        title=payload.title,
        url=payload.url,
        status="processing",
        meta=payload.meta,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    try:
        image = await _load_image(payload.url)
        status = await rag.add(image, image_id=payload.image_id, url=payload.url, title=payload.title or "")
        record.status = "completed" if status == "ok" else status
        await db.commit()
    except Exception as e:
        record.status = "failed"
        await db.commit()
        logger.error("[image_add] %s: %s", payload.image_id, e)
        raise HTTPException(400, f"Lỗi embed ảnh: {e}")

    return ImageOut(
        id=record.id,
        image_id=record.image_id,
        title=record.title,
        url=record.url,
        status=record.status,
        created_at=record.created_at.isoformat(),
    )


@router.post("/search/", response_model=ImageSearchOut)
async def search_image(
    payload: ImageSearchIn,
    db: AsyncSession = Depends(get_db),
    rag: ImageRAG = Depends(get_image_rag),
):
    try:
        image = await _load_image(payload.url)
    except Exception as e:
        raise HTTPException(400, f"Không load được ảnh: {e}")

    hits = await rag.search(image, k=payload.k)

    # Enrich với metadata từ DB
    results = []
    for h in hits:
        row = await db.execute(
            select(ImageSource).where(ImageSource.image_id == h["image_id"])
        )
        record = row.scalar_one_or_none()
        results.append(ImageSearchResultItem(
            image_id=h["image_id"],
            score=h["score"],
            url=record.url if record else None,
            title=record.title if record else None,
            meta=h.get("meta"),
        ))

    return ImageSearchOut(results=results)


@router.get("/", response_model=list[ImageOut])
async def list_images(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(ImageSource).order_by(ImageSource.created_at.desc()).limit(100)
    )
    return [
        ImageOut(
            id=r.id,
            image_id=r.image_id,
            title=r.title,
            url=r.url,
            status=r.status,
            created_at=r.created_at.isoformat(),
        )
        for r in rows.scalars()
    ]




@router.post("/search/text/", response_model=ImageSearchOut)
async def search_image_by_text(
    payload: ImageTextSearchIn,
    db: AsyncSession = Depends(get_db),
    rag: ImageRAG = Depends(get_image_rag),
):
    hits = await rag.search_by_text(payload.query, k=payload.k)

    results = []
    for h in hits:
        row = await db.execute(
            select(ImageSource).where(ImageSource.image_id == h["image_id"])
        )
        record = row.scalar_one_or_none()
        results.append(ImageSearchResultItem(
            image_id=h["image_id"],
            score=h["score"],
            url=record.url if record else "",
            title=record.title if record else "",
            meta=h.get("meta", {}),
        ))

    return ImageSearchOut(results=results)