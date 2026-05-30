from __future__ import annotations

from django.db import models
from pathlib import Path


class DocumentSource(models.Model):
    """
    Nguồn sự thật duy nhất. FAISS chỉ là cache search.
    """

    title = models.CharField(max_length=512)
    file = models.FileField(upload_to="knowledge/%Y/%m/")

    status = models.CharField(
        max_length=32,
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
    )

    chunk_count = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "knowledge_document_source"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def extension(self) -> str:
        if not self.file:
            return "unknown"
        return Path(self.file.name).suffix.lstrip(".")

    def delete(self, *args, **kwargs):
        """Xóa file gốc khi xóa record."""
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)