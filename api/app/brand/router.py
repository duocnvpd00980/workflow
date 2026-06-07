import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from litellm import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db import get_db
from .service import BrandProfileService
from .schemas import BrandProfileSchema, CreateBrandIn
from .models import Brand
from .schemas import (
    BrandProfileSchema,
    GenerateBrandProfileIn,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brand-profile", tags=["Brand Profile"])

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_brand(payload: CreateBrandIn, db: AsyncSession = Depends(get_db)):
    """API sinh ra brand_id và gắn nó với owner_id"""
    try:
        # Tự động sinh mã UUID duy nhất cho thương hiệu
        generated_brand_id = str(uuid.uuid4())
        
        new_brand = Brand(
            id=generated_brand_id,
            name=payload.name,
            owner_id=payload.owner_id
        )
        
        db.add(new_brand)
        await db.commit()
        
        return {
            "status": "success",
            "message": "Đã tạo thương hiệu thành công",
            "brand_id": generated_brand_id,
            "name": payload.name,
            "owner_id": payload.owner_id
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi tạo Brand: {str(e)}")

# ─── API MỚI BỔ SUNG: XÓA MỀM THƯƠNG HIỆU ──────────────────────────────────
@router.delete("/{brand_id}", status_code=status.HTTP_200_OK)
async def delete_brand(brand_id: str, db: AsyncSession = Depends(get_db)):
    """Soft delete thực thể thương hiệu bằng cách cập nhật timestamp deleted_at"""
    result = await db.execute(
        select(Brand).filter(Brand.id == brand_id, Brand.deleted_at == None)
    )
    brand = result.scalars().first()
    
    if not brand:
        raise HTTPException(
            status_code=404, 
            detail="Không tìm thấy thương hiệu tương ứng hoặc thương hiệu đã bị xóa."
        )
    
    try:
        # Đánh dấu thời gian xóa (Đồng bộ hóa với điều kiện lọc ở hàm list_profiles)
        brand.deleted_at = func.now()
        db.add(brand)
        await db.commit()
        
        return {
            "status": "success",
            "message": "Đã xóa thương hiệu thành công",
            "brand_id": brand_id
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi trong quá trình xóa thương hiệu: {str(e)}")
    
@router.post(
    "/{brand_id}/generate",
    status_code=status.HTTP_200_OK,
)
async def generate_profile(
    brand_id: str,
    payload: GenerateBrandProfileIn,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Brand)
        .filter(Brand.id == brand_id)
    )

    brand = result.scalars().first()

    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Brand không tồn tại."
        )

    try:
        profile = (
            await BrandProfileService.generate_from_documents(
                db=db,
                brand_id=brand_id,
                document_ids=payload.document_ids,
            )
        )

        return {
            "status": "generated",
            "brand_id": brand_id,
            "profile": profile.model_dump(),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
    
@router.put("/{brand_id}", status_code=status.HTTP_200_OK)
async def save_profile(
    brand_id: str,
    profile: BrandProfileSchema,
    db: AsyncSession = Depends(get_db)
):
    """Saves or updates full transactional brand config profile"""
    result = await db.execute(select(Brand).filter(Brand.id == brand_id))
    brand = result.scalars().first()
    if not brand:
        raise HTTPException(status_code=404, detail="Không tìm thấy Brand ID tương ứng trên hệ thống.")
    
    try:
        await BrandProfileService.save_profile(db, brand_id, profile.model_dump())
        return {
            "brand_id": brand_id,
            "status": "saved",
            "message": "Cấu hình thực thể Brand Voice đã được lưu thành công bằng Bulk Insert."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{brand_id}", response_model=BrandProfileSchema)
async def get_profile(brand_id: str, db: AsyncSession = Depends(get_db)):
    """Gets complete full profile blueprint"""
    try:
        return await BrandProfileService.get_full_profile(db, brand_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{brand_id}")
async def partial_update(brand_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Patches single/partial attribute inside profile schema"""
    try:
        full = await BrandProfileService.get_full_profile(db, brand_id)
        updated_data = full.model_dump()
        
        for k, v in data.items():
            if k in updated_data and isinstance(updated_data[k], dict) and isinstance(v, dict):
                updated_data[k].update(v)
            else:
                updated_data[k] = v
                
        await BrandProfileService.save_profile(db, brand_id, updated_data)
        return {"status": "updated", "patched_fields": list(data.keys())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{brand_id}/scope/writer")
async def get_writer_scope(brand_id: str, db: AsyncSession = Depends(get_db)):
    try:
        scope = await BrandProfileService.get_writer_scope(db, brand_id)
        return scope.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{brand_id}/scope/designer")
async def get_designer_scope(brand_id: str, db: AsyncSession = Depends(get_db)):
    """Đã dọn sạch Session cũ và đồng bộ hoàn toàn sang AsyncSession"""
    try:
        scope = await BrandProfileService.get_designer_scope(db, brand_id)
        return scope.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{brand_id}/scope/ads")
async def get_ads_scope(brand_id: str, db: AsyncSession = Depends(get_db)):
    try:
        scope = await BrandProfileService.get_ads_scope(db, brand_id)
        return scope.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{brand_id}/scope/landing-page")
async def get_landing_page_scope(brand_id: str, db: AsyncSession = Depends(get_db)):
    try:
        scope = await BrandProfileService.get_landing_page_scope(db, brand_id)
        return scope.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("")
async def list_profiles(
    owner_id: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Lists basic summary meta info of active owner brands"""
    try:
        base_query = select(Brand).filter(Brand.owner_id == owner_id, Brand.deleted_at == None)
        result = await db.execute(base_query.limit(limit).offset(offset))
        brands = result.scalars().all()
        
        count_query = select(func.count()).select_from(Brand).filter(Brand.owner_id == owner_id, Brand.deleted_at == None)
        count_result = await db.execute(count_query)
        total = count_result.scalar_one()
        
        return {
            "brands": [{"id": b.id, "name": b.name, "created_at": b.created_at} for b in brands],
            "total": total
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))