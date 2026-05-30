from __future__ import annotations

from typing import List
from pathlib import Path
import shutil

from django.contrib import admin, messages
from django.http import HttpRequest
from django.utils.html import format_html

from .models import DocumentSource


def _rebuild_rag():
    """Rebuild FAISS index từ tất cả file còn lại."""
    from agent_os.rag.rag_service import RAG, PERSIST_DIR
    from agent_os.rag.document_loader_service import DocumentLoader

    # Xóa index cũ
    if PERSIST_DIR.exists():
        shutil.rmtree(PERSIST_DIR)
        PERSIST_DIR.mkdir(exist_ok=True)

    # Re-ingest tất cả file còn lại
    rag = RAG()
    loader = DocumentLoader()

    for doc in DocumentSource.objects.filter(status="completed"):
        try:
            docs = loader.load_file(doc.file.path)
            if docs:
                import asyncio
                asyncio.run(rag.add(docs[0].text, **docs[0].metadata))
        except Exception as e:
            pass


@admin.action(description="🚀 Reprocess selected")
def reprocess_documents(modeladmin, request: HttpRequest, queryset: List[DocumentSource]):
    from agent_os.rag.rag_service import RAG
    from agent_os.rag.document_loader_service import DocumentLoader
    import asyncio

    rag = RAG()
    loader = DocumentLoader()

    for obj in queryset:
        try:
            docs = loader.load_file(obj.file.path)
            if docs:
                result = asyncio.run(rag.add(docs[0].text, **docs[0].metadata))
                obj.chunk_count = rag._store.stats().get("chunks", 0)  # rough count
                obj.status = "completed"
                obj.error_message = None
                obj.save()
        except Exception as e:
            obj.status = "failed"
            obj.error_message = str(e)
            obj.save()

    messages.success(request, f"Reprocessed {len(queryset)} documents.")


@admin.action(description="🧹 Xóa và rebuild index")
def delete_and_rebuild(modeladmin, request: HttpRequest, queryset):
    for obj in queryset:
        obj.delete()  # Gọi delete() đã override → xóa file

    _rebuild_rag()
    messages.warning(request, "Đã xóa documents và rebuild RAG index.")


@admin.register(DocumentSource)
class DocumentSourceAdmin(admin.ModelAdmin):

    list_display = (
        "id", "title", "display_status", "extension_badge",
        "chunk_count", "file_size_display", "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("title", "error_message")
    ordering = ("-created_at",)
    actions = (reprocess_documents, delete_and_rebuild)

    readonly_fields = (
        "status", "chunk_count", "error_message",
        "created_at", "updated_at", "processed_at",
    )

    fieldsets = (
        ("Tài liệu", {"fields": ("title", "file")}),
        ("Trạng thái", {"fields": ("status", "chunk_count", "error_message")}),
        ("Thời gian", {"fields": ("created_at", "updated_at", "processed_at")}),
    )

    def display_status(self, obj):
        colors = {
            "pending": "#6b7280", "processing": "#2563eb",
            "completed": "#16a34a", "failed": "#dc2626",
        }
        return format_html(
            "<b style='color:white;background:{};padding:4px 10px;border-radius:12px;'>{}</b>",
            colors.get(obj.status, "#111827"), obj.get_status_display(),
        )
    display_status.short_description = "Trạng thái"

    def extension_badge(self, obj):
        return format_html(
            "<span style='background:#f3f4f6;padding:3px 8px;border-radius:8px;'>{}</span>",
            obj.extension.upper(),
        )
    extension_badge.short_description = "Loại"

    def file_size_display(self, obj):
        if not obj.file:
            return "-"
        size = obj.file.size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"
    file_size_display.short_description = "Kích thước"

    def delete_model(self, request, obj):
        obj.delete()
        _rebuild_rag()
        messages.success(request, f"Đã xóa {obj.title} và rebuild index.")

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()
        _rebuild_rag()
        messages.success(request, f"Đã xóa {len(queryset)} tài liệu và rebuild index.")