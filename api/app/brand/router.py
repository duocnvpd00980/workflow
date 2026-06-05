from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db import get_db
from .service import BrandProfileService
from .schemas import BrandProfileSchema
from .models import Brand
from app.rag.loader import DocumentLoader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brand-profile", tags=["Brand Profile"])

@router.post("/mine", status_code=status.HTTP_200_OK)
async def mine_brand(
    brand_name: str,
    website_url: Optional[str] = None,
    raw_text_content: Optional[str] = None,
    document_type: str = Query("brand_guideline", description="Client tự chọn loại tài liệu: brand_guideline, competitor_analysis..."),
    db: AsyncSession = Depends(get_db)
):
    """Mines a fresh brand profile draft from raw text injection or clean url loading with dynamic document type tagging"""
    try:
        if not raw_text_content and not website_url:
            raise HTTPException(status_code=400, detail="Mày phải cung cấp ít nhất link website hoặc nội dung text của Guideline.")
            
        context_data = []
        if brand_name:
            context_data.append(f"Brand Name Target: {brand_name}")
            
        if website_url:
            context_data.append(f"Primary Seed URL: {website_url}")
            try:
                loader = DocumentLoader()
                loaded_web_doc = loader.load_web(website_url, document_type=document_type)
                if loaded_web_doc and loaded_web_doc.text:
                    context_data.append(f"Extracted Web Content:\n{loaded_web_doc.text}")
            except Exception as loader_err:
                logger.warning(f"[Loader Error] Không crawl được URL {website_url}: {str(loader_err)}")
                context_data.append(f"[Warning] Thất bại khi cào dữ liệu tự động từ URL này.")

        if raw_text_content:
            context_data.append(f"Injected Guideline Content:\n{raw_text_content}")
            
        rag_context = "\n\n".join(context_data)
        
        mined_draft = BrandProfileService.mine_from_rag(document_content=rag_context, document_type=document_type)
        
        return {
            "status": "mined",
            "document_type_applied": document_type,
            "draft_profile": mined_draft,
            "message": "Kiểm tra lại dữ liệu thô trước khi lưu chính thức vào Database."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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