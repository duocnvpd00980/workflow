from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from .schemas import BusinessCreate, BusinessListOut, BusinessOut, BusinessUpdate
from . import service

router = APIRouter(prefix="/businesses", tags=["Business"])


@router.post("", response_model=BusinessOut, status_code=201)
async def create(payload: BusinessCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_business(db, payload)


@router.get("", response_model=BusinessListOut)
async def list_all(
    owner_id: str | None = Query(None),
    status: str = Query("active"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_businesses(db, owner_id=owner_id, status=status, skip=skip, limit=limit)
    return {"items": items, "total": total}


@router.get("/{business_id}", response_model=BusinessOut)
async def get_one(business_id: str, db: AsyncSession = Depends(get_db)):
    obj = await service.get_business(db, business_id)
    if not obj:
        raise HTTPException(404, "Business not found")
    return obj


@router.patch("/{business_id}", response_model=BusinessOut)
async def update(business_id: str, payload: BusinessUpdate, db: AsyncSession = Depends(get_db)):
    obj = await service.update_business(db, business_id, payload)
    if not obj:
        raise HTTPException(404, "Business not found")
    return obj


@router.delete("/{business_id}", status_code=204)
async def delete(business_id: str, db: AsyncSession = Depends(get_db)):
    ok = await service.delete_business(db, business_id)
    if not ok:
        raise HTTPException(404, "Business not found")
