# rag/router.py
from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import get_ctx, Services
from app.db import get_db
from app.rag.schemas import DocOut, SearchOut, UploadOut
from .models import DocumentSource

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["rag"])


@router.get("/", response_model=list[DocOut])
async def list_docs(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(DocumentSource).order_by(DocumentSource.created_at.desc()).limit(100)
    )
    return [
        DocOut(
            id=d.id,
            title=d.title,
            status=d.status,
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
    file: UploadFile = ...,
    db: AsyncSession = Depends(get_db),
    svc: Services = Depends(get_ctx),
):
    if not title.strip():
        raise HTTPException(400, "Tiêu đề trống.")

    suffix = Path(file.filename).suffix if file.filename else ""
    content = await file.read()

    doc = DocumentSource(title=title.strip(), status="processing")
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Lưu tạm ra disk rồi gọi load_file
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, prefix=f"{uuid.uuid4().hex}_"
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        docs = svc.loader.load_file(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)  # xóa file tạm

        if not docs:
            raise ValueError("Không trích xuất được nội dung.")

        await svc.rag.add(docs[0].text, **docs[0].metadata)

        doc.status = "completed"
        doc.chunk_count = len(docs)
        await db.commit()
        return UploadOut(
            id=doc.id, title=doc.title,
            status="completed", message="Đã ingest thành công.",
        )

    except Exception as e:
        Path(tmp_path).unlink(missing_ok=True) if "tmp_path" in locals() else None
        doc.status = "failed"
        doc.error_message = str(e)
        await db.commit()
        logger.error("[upload] %s: %s", doc.id, e)
        raise HTTPException(400, f"Lỗi: {e}")


@router.post("/search/", response_model=SearchOut)
async def search(
    query: str = Form(...),
    top_k: int = Form(3),
    svc: Services = Depends(get_ctx),
):
    if not query.strip():
        return SearchOut(query="", results=[], source="empty")

    result = await svc.rag.search(query.strip(), top_k=top_k)
    return SearchOut(
        query=result.query,
        results=[
            {"text": c.text, "score": c.score, "meta": c.meta}
            for c in result.chunks
        ],
        source=result.source,
    )


@router.delete("/{doc_id}/", status_code=204)
async def delete(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(DocumentSource, doc_id)
    if not doc:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    await db.delete(doc)
    await db.commit()