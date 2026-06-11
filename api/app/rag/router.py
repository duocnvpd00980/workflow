import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_rag, get_loader
from app.db import get_db, AsyncSessionLocal
from app.rag.background_service import RagBackgroundService
from app.rag.schemas import (
    CrawlBusinessIn, CrawlIn, DocOut, SearchOut, UploadOut,
    PageSummaryOut, PageDetailOut,
)
from app.rag.service import RAG
from app.rag.loader import DocumentLoader
from .models import DocumentSource, DocumentPage
from app.tasks import create_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["rag"])


# ═══════════════════════════════════════════════════════════════════════════════
# DOCS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/", response_model=list[DocOut])
async def list_docs(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(DocumentSource)
        .order_by(DocumentSource.created_at.desc())
        .limit(100)
    )
    return [
        DocOut(
            id=d.id,
            title=d.title,
            status=d.status,
            document_type=d.document_type,
            chunk_count=d.chunk_count,
            file_size=(
                f"{Path(d.file_path).stat().st_size // 1024} KB"
                if d.file_path and Path(d.file_path).exists()
                else None
            ),
            created_at=d.created_at.isoformat(),
        )
        for d in rows.scalars()
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/upload/", status_code=202)
async def upload(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    document_type: str = Form("product_knowledge"),
    file: UploadFile = ...,
    db: AsyncSession = Depends(get_db),
    rag: RAG = Depends(get_rag),
    loader: DocumentLoader = Depends(get_loader),
):
    if not title.strip():
        raise HTTPException(400, "Tiêu đề trống.")

    content = await file.read()
    suffix = Path(file.filename).suffix if file.filename else ""

    doc = DocumentSource(
        title=title.strip(), status="processing", document_type=document_type
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    async with AsyncSessionLocal() as tdb:
        bg_task = await create_task(
            tdb, source="rag", source_id=str(doc.id),
            title=f"Upload: {title.strip()[:180]}",
            triggered_by="user", steps_total=2,
        )
        bg_task_id = bg_task.id

    background_tasks.add_task(
        RagBackgroundService.upload_bg,
        content, suffix, doc.id, bg_task_id, document_type, rag, loader,
    )

    return {
        "status": "processing",
        "doc_id": doc.id,
        "task_id": bg_task_id,
        "task_status_url": f"/tasks/{bg_task_id}",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CRAWL
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/crawl/", status_code=202)
async def crawl(
    background_tasks: BackgroundTasks,
    payload: CrawlIn,
    db: AsyncSession = Depends(get_db),
    rag: RAG = Depends(get_rag),
    loader: DocumentLoader = Depends(get_loader),
):
    url_str = str(payload.url)
    title = payload.title.strip() or url_str

    doc = DocumentSource(
        title=title, status="processing", document_type=payload.document_type
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    async with AsyncSessionLocal() as tdb:
        bg_task = await create_task(
            tdb, source="rag", source_id=str(doc.id),
            title=f"Crawl: {title[:180]}",
            triggered_by="user", steps_total=2,
        )
        bg_task_id = bg_task.id

    background_tasks.add_task(
        RagBackgroundService.crawl_bg,
        url_str, payload.document_type, doc.id, bg_task_id, rag, loader,
    )

    return {
        "status": "processing",
        "doc_id": doc.id,
        "task_id": bg_task_id,
        "task_status_url": f"/tasks/{bg_task_id}",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CRAWL BUSINESS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/crawl-business/", status_code=202)
async def crawl_business(
    background_tasks: BackgroundTasks,
    payload: CrawlBusinessIn,
    db: AsyncSession = Depends(get_db),
    rag: RAG = Depends(get_rag),
    loader: DocumentLoader = Depends(get_loader),
):
    url_str = str(payload.url)
    title = payload.title.strip() or url_str

    doc = DocumentSource(
        title=title, status="processing", document_type=payload.document_type
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    async with AsyncSessionLocal() as tdb:
        bg_task = await create_task(
            tdb, source="rag", source_id=str(doc.id),
            title=f"Crawl business: {title[:170]}",
            triggered_by="user", steps_total=2,
        )
        bg_task_id = bg_task.id

    background_tasks.add_task(
        RagBackgroundService.crawl_business_bg,
        url_str, payload.document_type, doc.id, bg_task_id, rag, loader,
    )

    return {
        "status": "processing",
        "doc_id": doc.id,
        "task_id": bg_task_id,
        "task_status_url": f"/tasks/{bg_task_id}",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/search/", response_model=SearchOut)
async def search(
    query: str = Form(...),
    top_k: int = Form(3),
    document_type: Optional[str] = Form(None),
    rag: RAG = Depends(get_rag),
):
    if not query.strip():
        return SearchOut(query="", results=[], source="empty")

    result = await rag.search(query.strip(), top_k=top_k, document_type=document_type)
    return SearchOut(
        query=result.query,
        results=[{"text": c.text, "score": c.score, "meta": c.meta} for c in result.chunks],
        source=result.source,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE
# ═══════════════════════════════════════════════════════════════════════════════

@router.delete("/{doc_id}/", status_code=204)
async def delete(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(DocumentSource, doc_id)
    if not doc:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    await db.delete(doc)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/doc/{doc_id}/pages", response_model=list[PageSummaryOut])
async def list_pages(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(DocumentSource, doc_id)
    if not doc:
        raise HTTPException(404, "Không tìm thấy tài liệu.")

    rows = await db.execute(
        select(DocumentPage)
        .where(DocumentPage.document_id == doc_id)
        .order_by(DocumentPage.created_at.asc())
    )
    return [
        PageSummaryOut(
            id=p.id,
            url=p.url,
            title=p.title,
            created_at=p.created_at.isoformat(),
        )
        for p in rows.scalars()
    ]


@router.get("/page/{page_id}", response_model=PageDetailOut)
async def get_page(page_id: int, db: AsyncSession = Depends(get_db)):
    page = await db.get(DocumentPage, page_id)
    if not page:
        raise HTTPException(404, "Không tìm thấy page.")

    return PageDetailOut(
        id=page.id,
        document_id=page.document_id,
        url=page.url,
        title=page.title,
        content=page.content,
        extracted=page.extracted,
        created_at=page.created_at.isoformat(),
    )