import logging
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_rag, get_loader
from app.db import get_db, AsyncSessionLocal
from app.rag.schemas import DocOut, SearchOut, UploadOut, CrawlBusinessIn, PageSummaryOut, PageDetailOut
from app.rag.service import RAG
from app.rag.loader import DocumentLoader
from .models import DocumentSource, DocumentPage
from app.rag.business_service import BusinessCrawler
from app.tasks import create_task, finish_task, fail_task   # ← THÊM


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["rag"])


class CrawlBusinessOut(BaseModel):
    id: int
    title: str
    status: str
    document_type: str
    chunk_count: int
    extracted_summary: Optional[dict] = None
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# EXISTING ENDPOINTS
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


@router.post("/upload/", response_model=UploadOut, status_code=201)
async def upload(
    title: str = Form(...),
    document_type: str = Form("product_knowledge"),
    file: UploadFile = ...,
    db: AsyncSession = Depends(get_db),
    rag: RAG = Depends(get_rag),
    loader: DocumentLoader = Depends(get_loader),
):
    if not title.strip():
        raise HTTPException(400, "Tiêu đề trống.")

    suffix  = Path(file.filename).suffix if file.filename else ""
    content = await file.read()

    doc = DocumentSource(
        title=title.strip(),
        status="processing",
        document_type=document_type
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # ── Tạo background task ───────────────────────────────────
    async with AsyncSessionLocal() as tdb:
        bg_task = await create_task(
            tdb,
            source="rag",
            source_id=str(doc.id),
            title=f"Upload: {title.strip()[:180]}",
            triggered_by="user",
            steps_total=1,
        )
        bg_task_id = bg_task.id
    # ─────────────────────────────────────────────────────────

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, prefix=f"{uuid.uuid4().hex}_"
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        docs = loader.load_file(tmp_path, document_type=document_type)
        Path(tmp_path).unlink(missing_ok=True)

        if not docs:
            raise ValueError("Không trích xuất được nội dung.")

        await rag.add(docs[0].text, **docs[0].metadata)

        doc.status      = "completed"
        doc.chunk_count = len(docs)
        await db.commit()

        # ── Hoàn thành ────────────────────────────────────────
        async with AsyncSessionLocal() as tdb:
            await finish_task(tdb, bg_task_id, steps_done=1)
        # ─────────────────────────────────────────────────────

        return UploadOut(id=doc.id, title=doc.title,
                         status="completed", message="Đã ingest thành công.")

    except Exception as e:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
        doc.status        = "failed"
        doc.error_message = str(e)
        await db.commit()

        # ── Thất bại ──────────────────────────────────────────
        async with AsyncSessionLocal() as tdb:
            await fail_task(tdb, bg_task_id, error_message=str(e))
        # ─────────────────────────────────────────────────────

        logger.error("[upload] %s: %s", doc.id, e)
        raise HTTPException(400, f"Lỗi: {e}")


class CrawlIn(BaseModel):
    url: HttpUrl
    title: str = ""
    document_type: str = "web_page"


@router.post("/crawl/", response_model=UploadOut, status_code=201)
async def crawl(
    payload: CrawlIn,
    db: AsyncSession = Depends(get_db),
    rag: RAG = Depends(get_rag),
    loader: DocumentLoader = Depends(get_loader),
):
    url_str = str(payload.url)
    title   = payload.title.strip() or url_str

    doc = DocumentSource(
        title=title,
        status="processing",
        document_type=payload.document_type
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # ── Tạo background task ───────────────────────────────────
    async with AsyncSessionLocal() as tdb:
        bg_task = await create_task(
            tdb,
            source="rag",
            source_id=str(doc.id),
            title=f"Crawl: {title[:180]}",
            triggered_by="user",
            steps_total=1,
        )
        bg_task_id = bg_task.id
    # ─────────────────────────────────────────────────────────

    try:
        loaded  = loader.load_web(url_str, document_type=payload.document_type)
        await rag.add(loaded.text, **loaded.metadata)

        doc.status      = "completed"
        doc.chunk_count = 1
        await db.commit()

        # ── Hoàn thành ────────────────────────────────────────
        async with AsyncSessionLocal() as tdb:
            await finish_task(tdb, bg_task_id, steps_done=1)
        # ─────────────────────────────────────────────────────

        return UploadOut(id=doc.id, title=doc.title,
                         status="completed", message="Đã crawl thành công.")

    except Exception as e:
        doc.status        = "failed"
        doc.error_message = str(e)
        await db.commit()

        # ── Thất bại ──────────────────────────────────────────
        async with AsyncSessionLocal() as tdb:
            await fail_task(tdb, bg_task_id, error_message=str(e))
        # ─────────────────────────────────────────────────────

        logger.error("[crawl] %s: %s", doc.id, e)
        raise HTTPException(400, f"Lỗi crawl: {e}")


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


@router.delete("/{doc_id}/", status_code=204)
async def delete(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(DocumentSource, doc_id)
    if not doc:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    await db.delete(doc)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# BUSINESS CRAWL
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/crawl-business/", response_model=CrawlBusinessOut, status_code=201)
async def crawl_business(
    payload: CrawlBusinessIn,
    db: AsyncSession = Depends(get_db),
    rag: RAG = Depends(get_rag),
    loader: DocumentLoader = Depends(get_loader),
):
    url_str = str(payload.url)
    title   = payload.title.strip() or url_str

    doc = DocumentSource(
        title=title,
        status="processing",
        document_type=payload.document_type,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # ── Tạo background task ───────────────────────────────────
    async with AsyncSessionLocal() as tdb:
        bg_task = await create_task(
            tdb,
            source="rag",
            source_id=str(doc.id),
            title=f"Crawl business: {title[:170]}",
            triggered_by="user",
            steps_total=1,
        )
        bg_task_id = bg_task.id
    # ─────────────────────────────────────────────────────────

    try:
        crawler    = BusinessCrawler(rag=rag, loader=loader, db=db)
        page_count = await crawler.crawl_business(
            url=url_str,
            document_type=payload.document_type,
            document_id=doc.id,
        )

        page = await db.execute(
            select(DocumentPage)
            .where(DocumentPage.document_id == doc.id)
            .order_by(DocumentPage.created_at.desc())
            .limit(1)
        )
        first_page = page.scalar_one_or_none()

        extracted_summary = None
        if first_page and first_page.extracted:
            extracted = first_page.extracted
            extracted_summary = {
                "brand_name": extracted.get("brand_identity", {}).get("brand_name"),
                "phones": extracted.get("contact_details", {}).get("phones", []),
                "addresses": extracted.get("contact_details", {}).get("addresses", []),
                "social_links": extracted.get("contact_details", {}).get("social_links", {}),
                "main_products": extracted.get("brand_identity", {}).get("main_products", []),
                "chunk_quality": extracted.get("chunk_quality", {}),
            }

        doc.status      = "completed"
        doc.chunk_count = page_count
        await db.commit()

        # ── Hoàn thành ────────────────────────────────────────
        async with AsyncSessionLocal() as tdb:
            await finish_task(tdb, bg_task_id, steps_done=1)
        # ─────────────────────────────────────────────────────

        return CrawlBusinessOut(
            id=doc.id,
            title=doc.title,
            status="completed",
            document_type=doc.document_type,
            chunk_count=page_count,
            extracted_summary=extracted_summary,
            message=f"Đã crawl thành công {page_count} page.",
        )

    except Exception as e:
        doc.status        = "failed"
        doc.error_message = str(e)
        await db.commit()

        # ── Thất bại ──────────────────────────────────────────
        async with AsyncSessionLocal() as tdb:
            await fail_task(tdb, bg_task_id, error_message=str(e))
        # ─────────────────────────────────────────────────────

        logger.error("[crawl_business] doc_id=%s error=%s", doc.id, e)
        raise HTTPException(400, f"Lỗi crawl business: {e}")


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