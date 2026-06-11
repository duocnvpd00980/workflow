from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.service import create_task
from app.db import get_db
from app.rag.hotel_service import HotelService
from app.rag.models import HotelRoom
from app.rag.schemas import (
    HotelCrawlIn, HotelCrawlOut, HotelRoomOut,
    HotelSearchIn, HotelSearchOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/hotel", tags=["hotel"])

# singleton
_hotel_service = HotelService()


def get_hotel_service() -> HotelService:
    return _hotel_service


def _to_out(room: HotelRoom) -> HotelRoomOut:
    return HotelRoomOut(
        id=room.id,
        name=room.name,
        slug=room.slug,
        source_url=room.source_url,
        room_type=room.room_type,
        bed_type=room.bed_type,
        capacity=room.capacity,
        area_sqm=room.area_sqm,
        price_per_night=room.price_per_night,
        currency=room.currency,
        description=room.description,
        amenities=room.amenities,
        image_urls=room.image_urls,
        status=room.status,
        created_at=room.created_at.isoformat(),
    )


@router.post("/crawl/", status_code=202)
async def crawl_hotel(
    background_tasks: BackgroundTasks,
    payload: HotelCrawlIn,
    db: AsyncSession = Depends(get_db),
    svc: HotelService = Depends(get_hotel_service),
):
    task = await create_task(
        db,
        source="hotel",
        source_id=str(payload.url),
        title=f"Crawl hotel: {payload.url}",
        triggered_by="user",
        steps_total=3,   # fetch → extract → save
        model="groq",
    )

    background_tasks.add_task(
        svc.crawl_bg,
        url=str(payload.url),
        db=db,
        task_id=task.id,
    )

    return {
        "status": "processing",
        "message": "Đang crawl khách sạn trong nền",
        "task_id": task.id,
        "task_status_url": f"/tasks/{task.id}",
    }


@router.post("/search/", response_model=HotelSearchOut)
async def search_hotel(
    payload: HotelSearchIn,
    db: AsyncSession = Depends(get_db),
    svc: HotelService = Depends(get_hotel_service),
):
    try:
        rooms = await svc.search(
            query=payload.query,
            db=db,
            k=payload.k,
            room_type=payload.room_type,
            max_price=payload.max_price,
            min_capacity=payload.min_capacity,
        )
    except Exception as e:
        logger.error("[hotel_search] %s", e)
        raise HTTPException(500, f"Lỗi tìm kiếm: {e}")

    return HotelSearchOut(
        query=payload.query,
        total=len(rooms),
        rooms=[_to_out(r) for r in rooms],
    )


@router.get("/rooms/", response_model=list[HotelRoomOut])
async def list_rooms(
    room_type: Optional[str] = None,
    status: str = "active",
    db: AsyncSession = Depends(get_db),
):
    q = select(HotelRoom).where(HotelRoom.status == status)
    if room_type:
        q = q.where(HotelRoom.room_type == room_type)
    q = q.order_by(HotelRoom.created_at.desc()).limit(100)
    rows = await db.execute(q)
    return [_to_out(r) for r in rows.scalars()]


@router.get("/rooms/{room_id}/", response_model=HotelRoomOut)
async def get_room(room_id: int, db: AsyncSession = Depends(get_db)):
    room = await db.get(HotelRoom, room_id)
    if not room:
        raise HTTPException(404, "Không tìm thấy phòng.")
    return _to_out(room)


@router.delete("/rooms/{room_id}/", status_code=204)
async def delete_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    svc: HotelService = Depends(get_hotel_service),
):
    ok = await svc.delete(room_id, db)
    if not ok:
        raise HTTPException(404, "Không tìm thấy phòng.")


@router.get("/stats/")
async def hotel_stats(svc: HotelService = Depends(get_hotel_service)):
    return svc.stats()