from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from pydantic import BaseModel
from pydantic import BaseModel, HttpUrl  
from typing import Optional

# ── Internal pipeline types ───────────────────────────────
@dataclass
class Doc:
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Chunk:
    score: float
    text: str
    meta: dict


@dataclass
class Result:
    query: str
    chunks: list[Chunk]
    source: str


# ── API response schemas ──────────────────────────────────
class DocOut(BaseModel):
    id: int
    title: str
    status: str
    document_type: str  # ✅ THÊM
    chunk_count: int
    file_size: Optional[str] = None
    created_at: str

# ── Constants ──────────────────────────────────────
DOCUMENT_TYPES = {
    "product_knowledge": "📚 Kiến thức Sản phẩm",
    "brand_guideline": "🎨 Hướng dẫn Thương hiệu",
    "competitor_analysis": "📊 Phân tích Đối thủ",
    "web_page": "🌐 Trang Web",
}


class UploadOut(BaseModel):
    id: int
    title: str
    status: str
    message: str


class SearchOut(BaseModel):
    query: str
    results: list[dict]
    source: str



# ── API request schemas (BỔ SUNG THÊM VÀO CUỐI FILE) ───────────────────

class WebCrawlRequest(BaseModel):
    """Schema nhận payload khi user yêu cầu cào dữ liệu từ một URL"""
    url: str
    # Mặc định nếu không truyền thì hệ thống tự hiểu là tài liệu sản phẩm
    document_type: str = "product_knowledge" 


class SearchRequest(BaseModel):
    """Schema nhận payload khi user thực hiện tìm kiếm/truy vấn RAG"""
    query: str
    top_k: int = 4
    # Quan trọng: Thêm tag này để RAG Engine biết đường cô lập vùng tìm kiếm
    document_type: Optional[str] = None



# ── Business crawl schemas ────────────────────────────────────────────────────

class CrawlBusinessIn(BaseModel):
    url: str
    title: str = ""
    document_type: str = "brand"


class PageSummaryOut(BaseModel):
    """Dùng cho GET /rag/{doc_id}/pages — danh sách tóm tắt."""
    id: int
    url: str
    title: str
    created_at: str

    model_config = {"from_attributes": True}


class PageDetailOut(BaseModel):
    """Dùng cho GET /rag/page/{page_id} — chi tiết đầy đủ."""
    id: int
    document_id: int
    url: str
    title: str
    content: Optional[str]
    extracted: Optional[dict]
    created_at: str

    model_config = {"from_attributes": True}


class CrawlBusinessIn(BaseModel):
    """Schema cho business crawl — dùng HttpUrl để validate URL."""
    url: HttpUrl  # Đổi từ str sang HttpUrl
    title: str = ""
    document_type: str = "brand"

    model_config = {"from_attributes": True}