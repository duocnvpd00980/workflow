"""RAG Background Tasks — upload, crawl, crawl-business.

FIX: Mỗi background job chạy trong ThreadPoolExecutor riêng biệt với asyncio.run()
     → hoàn toàn tách khỏi uvicorn event loop → HTTP handlers không bị block.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.db import AsyncSessionLocal
from app.rag.loader import DocumentLoader
from app.rag.models import DocumentSource
from app.rag.service import RAG
from app.rag.business_service import BusinessCrawler
from app.tasks import create_task, update_task, finish_task, fail_task

logger = logging.getLogger(__name__)

# ── Dedicated thread pool cho background crawl jobs ───────────────────────────
# max_workers=2: tránh quá tải CPU/RAM khi nhiều crawl chạy đồng thời.
# Tăng lên nếu server có nhiều core và RAM đủ cho nhiều FAISS/BM25 instance.
_CRAWL_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="crawl-worker")


def _run_in_new_loop(coro_factory):
    """
    Chạy một coroutine trong event loop MỚI, hoàn toàn độc lập với uvicorn loop.
    Gọi từ thread worker — KHÔNG được gọi từ async context.

    coro_factory: callable không nhận tham số, trả về coroutine.
    Dùng factory thay vì coroutine trực tiếp vì coroutine phải được tạo
    trong cùng thread sẽ chạy nó (tránh lỗi "attached to a different loop").
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro_factory())
    finally:
        try:
            # Hủy tất cả task còn sót trước khi đóng loop
            pending = asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        finally:
            loop.close()
            asyncio.set_event_loop(None)


class RagBackgroundService:

    # ── Upload ────────────────────────────────────────────────────
    @staticmethod
    def _upload_sync(
        content: bytes,
        suffix: str,
        doc_id: int,
        task_id: int,
        document_type: str,
        rag: RAG,
        loader: DocumentLoader,
    ) -> None:
        """Sync wrapper — chạy trong thread worker."""

        async def _run():
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix, prefix=f"{uuid.uuid4().hex}_"
                ) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name

                # loader.load_file() có thể sync — chạy trong executor của loop mới này
                loop = asyncio.get_running_loop()
                docs = await loop.run_in_executor(
                    None, lambda: loader.load_file(tmp_path, document_type=document_type)
                )
                Path(tmp_path).unlink(missing_ok=True)
                tmp_path = None

                if not docs:
                    raise ValueError("Không trích xuất được nội dung.")

                async with AsyncSessionLocal() as db:
                    await update_task(db, task_id, steps_done=1)

                await rag.add(docs[0].text, **docs[0].metadata)

                async with AsyncSessionLocal() as db:
                    doc = await db.get(DocumentSource, doc_id)
                    doc.status = "completed"
                    doc.chunk_count = len(docs)
                    await db.commit()

                async with AsyncSessionLocal() as db:
                    await finish_task(db, task_id, steps_done=2)

            except Exception as e:
                if tmp_path:
                    Path(tmp_path).unlink(missing_ok=True)

                async with AsyncSessionLocal() as db:
                    doc = await db.get(DocumentSource, doc_id)
                    doc.status = "failed"
                    doc.error_message = str(e)
                    await db.commit()

                async with AsyncSessionLocal() as db:
                    await fail_task(db, task_id, error_message=str(e))

                logger.error("[upload_bg] doc_id=%s error=%s", doc_id, e)

        _run_in_new_loop(_run)

    @staticmethod
    def upload_bg(
        content: bytes,
        suffix: str,
        doc_id: int,
        task_id: int,
        document_type: str,
        rag: RAG,
        loader: DocumentLoader,
    ) -> None:
        """
        Gọi từ FastAPI BackgroundTasks — KHÔNG async.
        FastAPI sẽ chạy sync background task trong threadpool mặc định của nó,
        nhưng ta dùng _CRAWL_EXECUTOR riêng để kiểm soát concurrency.
        """
        future = _CRAWL_EXECUTOR.submit(
            RagBackgroundService._upload_sync,
            content, suffix, doc_id, task_id, document_type, rag, loader,
        )
        # Không block — fire and forget. Lỗi đã được xử lý trong _upload_sync.
        future.add_done_callback(
            lambda f: logger.error("[upload_bg] unhandled exception", exc_info=f.exception())
            if f.exception() else None
        )

    # ── Crawl ─────────────────────────────────────────────────────
    @staticmethod
    def _crawl_sync(
        url_str: str,
        document_type: str,
        doc_id: int,
        task_id: int,
        rag: RAG,
        loader: DocumentLoader,
    ) -> None:
        """Sync wrapper — chạy trong thread worker."""

        async def _run():
            try:
                # load_web() là sync → chạy trong executor
                loop = asyncio.get_running_loop()
                loaded = await loop.run_in_executor(
                    None, lambda: loader.load_web(url_str, document_type=document_type)
                )

                async with AsyncSessionLocal() as db:
                    await update_task(db, task_id, steps_done=1)

                await rag.add(loaded.text, **loaded.metadata)

                async with AsyncSessionLocal() as db:
                    doc = await db.get(DocumentSource, doc_id)
                    doc.status = "completed"
                    doc.chunk_count = 1
                    await db.commit()

                async with AsyncSessionLocal() as db:
                    await finish_task(db, task_id, steps_done=2)

            except Exception as e:
                async with AsyncSessionLocal() as db:
                    doc = await db.get(DocumentSource, doc_id)
                    doc.status = "failed"
                    doc.error_message = str(e)
                    await db.commit()

                async with AsyncSessionLocal() as db:
                    await fail_task(db, task_id, error_message=str(e))

                logger.error("[crawl_bg] doc_id=%s error=%s", doc_id, e)

        _run_in_new_loop(_run)

    @staticmethod
    def crawl_bg(
        url_str: str,
        document_type: str,
        doc_id: int,
        task_id: int,
        rag: RAG,
        loader: DocumentLoader,
    ) -> None:
        """Gọi từ FastAPI BackgroundTasks — KHÔNG async."""
        future = _CRAWL_EXECUTOR.submit(
            RagBackgroundService._crawl_sync,
            url_str, doc_id, task_id, document_type, rag, loader,
        )
        future.add_done_callback(
            lambda f: logger.error("[crawl_bg] unhandled exception", exc_info=f.exception())
            if f.exception() else None
        )

    # ── Crawl Business ────────────────────────────────────────────
    @staticmethod
    def _crawl_business_sync(
        url_str: str,
        document_type: str,
        doc_id: int,
        task_id: int,
        rag: RAG,
        loader: DocumentLoader,
    ) -> None:
        """Sync wrapper — chạy trong thread worker với event loop riêng."""

        async def _run():
            try:
                crawler = BusinessCrawler(
                    rag=rag,
                    loader=loader,
                    db_factory=AsyncSessionLocal,
                )
                page_count = await crawler.crawl_business(
                    url=url_str,
                    document_type=document_type,
                    document_id=doc_id,
                )

                async with AsyncSessionLocal() as db:
                    await update_task(db, task_id, steps_done=1)

                async with AsyncSessionLocal() as db:
                    doc = await db.get(DocumentSource, doc_id)
                    doc.status = "completed"
                    doc.chunk_count = page_count
                    await db.commit()

                async with AsyncSessionLocal() as db:
                    await finish_task(db, task_id, steps_done=2)

            except Exception as e:
                async with AsyncSessionLocal() as db:
                    doc = await db.get(DocumentSource, doc_id)
                    doc.status = "failed"
                    doc.error_message = str(e)
                    await db.commit()

                async with AsyncSessionLocal() as db:
                    await fail_task(db, task_id, error_message=str(e))

                logger.error("[crawl_business_bg] doc_id=%s error=%s", doc_id, e)

        _run_in_new_loop(_run)

    @staticmethod
    def crawl_business_bg(
        url_str: str,
        document_type: str,
        doc_id: int,
        task_id: int,
        rag: RAG,
        loader: DocumentLoader,
    ) -> None:
        """Gọi từ FastAPI BackgroundTasks — KHÔNG async."""
        future = _CRAWL_EXECUTOR.submit(
            RagBackgroundService._crawl_business_sync,
            url_str, document_type, doc_id, task_id, rag, loader,
        )
        future.add_done_callback(
            lambda f: logger.error("[crawl_business_bg] unhandled exception", exc_info=f.exception())
            if f.exception() else None
        )