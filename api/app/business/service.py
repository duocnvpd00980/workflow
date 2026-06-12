from __future__ import annotations

import uuid
import unicodedata
import re
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Business
from .schemas import BusinessCreate, BusinessUpdate


# ── Helpers ──────────────────────────────────────────────────────

def _slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[\s_-]+", "-", value)


async def _unique_slug(db: AsyncSession, base: str) -> str:
    """Đảm bảo slug unique — thêm suffix nếu trùng."""
    slug = _slugify(base)
    existing = (await db.execute(
        select(Business.slug).where(Business.slug.like(f"{slug}%"))
    )).scalars().all()

    if slug not in existing:
        return slug

    # muong-thanh → muong-thanh-2, muong-thanh-3 ...
    i = 2
    while f"{slug}-{i}" in existing:
        i += 1
    return f"{slug}-{i}"


# ── CRUD ─────────────────────────────────────────────────────────

async def create_business(db: AsyncSession, data: BusinessCreate) -> Business:
    slug = await _unique_slug(db, data.name)
    business = Business(
        id=str(uuid.uuid4()),
        slug=slug,
        **data.model_dump(),
    )
    db.add(business)
    await db.commit()
    await db.refresh(business)
    return business


async def get_business(db: AsyncSession, business_id: str) -> Optional[Business]:
    return (await db.execute(
        select(Business).where(Business.id == business_id, Business.deleted_at.is_(None))
    )).scalars().one_or_none()


async def list_businesses(
    db: AsyncSession,
    owner_id: Optional[str] = None,
    status: str = "active",
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Business], int]:
    q = select(Business).where(Business.deleted_at.is_(None))
    if owner_id:
        q = q.where(Business.owner_id == owner_id)
    if status:
        q = q.where(Business.status == status)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (await db.execute(q.offset(skip).limit(limit))).scalars().all()
    return list(items), total


async def update_business(
    db: AsyncSession, business_id: str, data: BusinessUpdate
) -> Optional[Business]:
    business = await get_business(db, business_id)
    if not business:
        return None

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(business, field, value)

    await db.commit()
    await db.refresh(business)
    return business


async def delete_business(db: AsyncSession, business_id: str) -> bool:
    """Soft delete."""
    business = await get_business(db, business_id)
    if not business:
        return False

    from datetime import datetime
    business.deleted_at = datetime.now()
    business.status = "deleted"
    await db.commit()
    return True
