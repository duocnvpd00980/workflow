from __future__ import annotations

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
from app.db import get_db
from app.rag.schemas import DocOut, SearchOut, UploadOut
from app.rag.service import RAG
from app.rag.loader import DocumentLoader
from .models import DocumentSource

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["rag"])


# ── GET /rag/ ─────────────────────────────────────────────
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
            document_type=d.document_type,  # ✅ THÊM
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


# ── POST /rag/upload/ ─────────────────────────────────────
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
        return UploadOut(id=doc.id, title=doc.title,
                         status="completed", message="Đã ingest thành công.")

    except Exception as e:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
        doc.status        = "failed"
        doc.error_message = str(e)
        await db.commit()
        logger.error("[upload] %s: %s", doc.id, e)
        raise HTTPException(400, f"Lỗi: {e}")


# ── POST /rag/crawl/ ──────────────────────────────────────
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

    try:
        loaded  = loader.load_web(url_str, document_type=payload.document_type)          
        await rag.add(loaded.text, **loaded.metadata)

        doc.status      = "completed"
        doc.chunk_count = 1                          
        await db.commit()
        return UploadOut(id=doc.id, title=doc.title,
                         status="completed", message="Đã crawl thành công.")

    except Exception as e:
        doc.status        = "failed"
        doc.error_message = str(e)
        await db.commit()
        logger.error("[crawl] %s: %s", doc.id, e)
        raise HTTPException(400, f"Lỗi crawl: {e}")


# ── POST /rag/search/ ─────────────────────────────────────
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


# ── DELETE /rag/{doc_id}/ ─────────────────────────────────
@router.delete("/{doc_id}/", status_code=204)
async def delete(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(DocumentSource, doc_id)
    if not doc:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    await db.delete(doc)
    await db.commit()