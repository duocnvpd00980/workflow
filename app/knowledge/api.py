from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from asgiref.sync import sync_to_async
from django.utils import timezone
from ninja import File, Form, Router
from ninja.files import UploadedFile
from pydantic import BaseModel

from .models import DocumentSource
from agent_os.rag.document_loader_service import DocumentLoader
from agent_os.rag.rag_service import RAG

logger = logging.getLogger(__name__)

router = Router(tags=["Knowledge"])

_loader = DocumentLoader()
_rag = RAG()


# ── Schemas ─────────────────────────────────────────────────────────────────

class DocOut(BaseModel):
    id: int
    title: str
    status: str
    chunk_count: int
    file_size: Optional[str] = None
    created_at: str

class UploadOut(BaseModel):
    id: int
    title: str
    status: str
    message: str

class ErrorOut(BaseModel):
    detail: str

class SearchOut(BaseModel):
    query: str
    results: List[dict]
    source: str


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/", response=List[DocOut], auth=None)
async def list_docs(request):
    # Sử dụng sync_to_async cho các truy vấn DB trong view async
    docs = await sync_to_async(list)(DocumentSource.objects.order_by("-created_at")[:100])
    return [
        DocOut(
            id=d.id,
            title=d.title,
            status=d.status,
            chunk_count=d.chunk_count,
            file_size=f"{d.file.size // 1024} KB" if d.file else None,
            created_at=d.created_at.isoformat(),
        )
        for d in docs
    ]


@router.post("/upload/", response={201: UploadOut, 400: ErrorOut}, auth=None)
async def upload(request, title: str = Form(...), file: UploadedFile = File(...)):
    if not title.strip():
        return 400, {"detail": "Tiêu đề trống."}

    # 1. Tạo object (chưa lưu DB)
    doc = DocumentSource(title=title.strip(), status="processing")
    
    # 2. Lưu record vào DB trước để lấy ID (Bắt buộc dùng sync_to_async)
    await sync_to_async(doc.save)()
    
    # 3. Lưu file (Thao tác này gọi lại .save() của record, cũng là DB)
    safe_filename = f"{uuid.uuid4().hex}_{file.name}"
    await sync_to_async(doc.file.save)(safe_filename, file, save=False) # save=False để tránh trùng lặp
    
    try:
        # Ingest (thao tác đọc file local không cần sync_to_async)
        docs = _loader.load_file(doc.file.path)
        if not docs:
            raise ValueError("Không trích xuất được nội dung.")

        await _rag.add(docs[0].text, **docs[0].metadata)

        # 4. Cập nhật status
        doc.status = "completed"
        doc.chunk_count = len(docs)
        doc.processed_at = timezone.now()
        await sync_to_async(doc.save)()

        return 201, UploadOut(
            id=doc.id,
            title=doc.title,
            status="completed",
            message="Đã ingest thành công.",
        )

    except Exception as e:
        doc.status = "failed"
        doc.error_message = str(e)
        await sync_to_async(doc.save)()
        logger.error("[Upload] %s: %s", doc.id, e)
        return 400, {"detail": f"Lỗi: {str(e)}"}


@router.post("/search/", response=SearchOut, auth=None)
async def search(request, query: str = Form(...), top_k: int = Form(3)):
    if not query.strip():
        return SearchOut(query="", results=[], source="empty")

    result = await _rag.search(query.strip(), top_k=top_k)
    return SearchOut(
        query=result.query,
        results=[{"text": c.text, "score": c.score, "meta": c.meta} for c in result.chunks],
        source=result.source,
    )


@router.delete("/{doc_id}/", response={204: None, 404: ErrorOut}, auth=None)
async def delete(request, doc_id: int):
    try:
        # Bọc get() và delete() trong sync_to_async
        doc = await sync_to_async(DocumentSource.objects.get)(id=doc_id)
        await sync_to_async(doc.delete)()
        return 204, None
    except Exception:
        return 404, {"detail": "Không tìm thấy tài liệu."}