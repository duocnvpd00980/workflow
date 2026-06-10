from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


# ── Internal pipeline types ───────────────────────────────────────────────────

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


# ── Constants ─────────────────────────────────────────────────────────────────

DOCUMENT_TYPES = {
    "product_knowledge": "📚 Kiến thức Sản phẩm",
    "brand_guideline": "🎨 Hướng dẫn Thương hiệu",
    "competitor_analysis": "📊 Phân tích Đối thủ",
    "web_page": "🌐 Trang Web",
}


# ── General RAG schemas ───────────────────────────────────────────────────────

class DocOut(BaseModel):
    id: int
    title: str
    status: str
    document_type: str
    chunk_count: int
    file_size: Optional[str] = None
    created_at: str


class UploadOut(BaseModel):
    id: int
    title: str
    status: str
    message: str


class SearchOut(BaseModel):
    query: str
    results: list[dict]
    source: str


class WebCrawlRequest(BaseModel):
    url: str
    document_type: str = "product_knowledge"


class SearchRequest(BaseModel):
    query: str
    top_k: int = 4
    document_type: Optional[str] = None


# ── Business crawl schemas ────────────────────────────────────────────────────

class CrawlBusinessIn(BaseModel):
    url: HttpUrl
    title: str = ""
    document_type: str = "brand"

    model_config = {"from_attributes": True}


class PageSummaryOut(BaseModel):
    id: int
    url: str
    title: str
    created_at: str

    model_config = {"from_attributes": True}


class PageDetailOut(BaseModel):
    id: int
    document_id: int
    url: str
    title: str
    content: Optional[str]
    extracted: Optional[dict]
    created_at: str

    model_config = {"from_attributes": True}


# ── Image schemas ─────────────────────────────────────────────────────────────

class ImageAddIn(BaseModel):
    image_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID tự sinh nếu không truyền",
    )
    url: str = Field(..., description="URL hoặc path tham chiếu tới ảnh")
    title: str = Field(default="", description="Tiêu đề ảnh")
    meta: dict = Field(default_factory=dict, description="Metadata tuỳ chọn")

    model_config = {
        "json_schema_extra": {
            "example": {
                "image_id": "product-001",
                "url": "https://example.com/images/product.jpg",
                "title": "Ảnh sản phẩm A",
                "meta": {"category": "product", "tags": ["new", "sale"]},
            }
        }
    }


class ImageOut(BaseModel):
    id: int
    image_id: str
    title: str
    url: str
    status: str
    created_at: str

    model_config = {"from_attributes": True}


class ImageSearchIn(BaseModel):
    url: str = Field(..., description="URL hoặc path ảnh dùng để tìm kiếm")
    k: int = Field(default=5, ge=1, le=20, description="Số kết quả trả về")

    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://example.com/images/query.jpg",
                "k": 5,
            }
        }
    }


class ImageSearchResultItem(BaseModel):
    image_id: str
    score: float
    url: str
    title: str
    meta: dict


class ImageSearchOut(BaseModel):
    results: list[ImageSearchResultItem]


class ImageTextSearchIn(BaseModel):
    query: str = Field(..., description="Text query để tìm ảnh, ví dụ: 'sản phẩm A màu đỏ'")
    k: int = Field(default=5, ge=1, le=20, description="Số kết quả trả về")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "sản phẩm A màu đỏ",
                "k": 5,
            }
        }
    }


# ── Hotel schemas ─────────────────────────────────────────────────────────────

class HotelCrawlIn(BaseModel):
    url: HttpUrl = Field(..., description="URL trang web khách sạn cần crawl")

    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://duonggiahotel.vn/phong-nghi",
            }
        }
    }


class HotelRoomOut(BaseModel):
    id: int
    name: str
    slug: str
    source_url: str
    room_type: Optional[str]
    bed_type: Optional[str]
    capacity: Optional[int]
    area_sqm: Optional[float]
    price_per_night: Optional[float]
    currency: str
    description: Optional[str]
    amenities: Optional[list]
    image_urls: Optional[list]
    status: str
    created_at: str

    model_config = {"from_attributes": True}


class HotelCrawlOut(BaseModel):
    total: int
    rooms: list[HotelRoomOut]
    message: str


class HotelSearchIn(BaseModel):
    query: str = Field(..., description="Câu tìm kiếm tự do, ví dụ: 'phòng đôi', 'có bồn tắm', 'view biển'")
    k: int = Field(default=5, ge=1, le=20)
    room_type: Optional[str] = Field(default=None)
    max_price: Optional[float] = Field(default=None)
    min_capacity: Optional[int] = Field(default=None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "phòng đôi view biển",
            }
        }
    }


class HotelSearchOut(BaseModel):
    query: str
    total: int
    rooms: list[HotelRoomOut]