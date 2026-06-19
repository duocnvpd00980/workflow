"""
models.py
DB models + State cho Research Pipeline (Suggestions -> SERP -> Facebook).

Thiết kế:
- Tự chứa hoàn toàn (Base riêng, KHÔNG phụ thuộc app.db / Business / PipelineTask ngoài).
- KHÔNG dùng ForeignKey / relationship chéo bảng -> business_id là string thường.
- Mỗi business chỉ giữ BẢN MỚI NHẤT (upsert: xóa cũ rồi ghi mới), không lưu lịch sử nhiều lần chạy.
- Mọi cột JSON đều có SCHEMA CỨNG (đủ key cố định, thiếu thì điền default) để bên lấy dữ liệu
  (brand) không bị KeyError / None bất ngờ.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    JSON,
    DateTime,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════════
# SCHEMA CỨNG cho các cột JSON — dùng safe_get() để luôn đủ key
# ═══════════════════════════════════════════════════════════════════════

SUGGESTIONS_TAGGED_SCHEMA = {
    "budget": [],
    "location": [],
    "food": [],
    "experience": [],
    "family": [],
    "question": [],
    "other": [],
}

SERP_DATA_SCHEMA = {
    "top_urls": [],
    "people_also_ask": [],
    "related_searches": [],
    "snippets": [],
    "keyword_cluster": [],
    "content_angle": [],
    "intent": [],
    "competitor_pattern": [],
}

FB_BRAND_SCHEMA = {
    "page_info": {"title": "", "followers": "", "following": ""},
    "intro": "",
    "phones": [],
    "emails": [],
    "domains": [],
}


def safe_get(d: Optional[dict], schema: dict) -> dict:
    """
    Đảm bảo dict trả về LUÔN đủ key theo schema.
    - Key có trong d -> dùng giá trị của d (nếu không None).
    - Key thiếu hoặc giá trị None -> dùng default trong schema.
    Không bao giờ trả thiếu key, không bao giờ trả None cho key đã khai báo.
    """
    d = d or {}
    result = {}
    for key, default in schema.items():
        val = d.get(key, None)
        result[key] = val if val is not None else default
    return result


def default_suggestions_tagged() -> dict:
    return {k: (list(v) if isinstance(v, list) else dict(v)) for k, v in SUGGESTIONS_TAGGED_SCHEMA.items()}


def default_serp_data() -> dict:
    return {k: (list(v) if isinstance(v, list) else dict(v)) for k, v in SERP_DATA_SCHEMA.items()}


def default_fb_brand() -> dict:
    out = {}
    for k, v in FB_BRAND_SCHEMA.items():
        out[k] = dict(v) if isinstance(v, dict) else (list(v) if isinstance(v, list) else v)
    return out


# ═══════════════════════════════════════════════════════════════════════
# DB MODELS
# ═══════════════════════════════════════════════════════════════════════

class PipelineTask(Base):
    """1 dòng / business — trạng thái lần chạy gần nhất."""
    __tablename__ = "pipeline_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(String(64), unique=True, nullable=False, index=True)
    business_name = Column(String(255), nullable=True)
    query = Column(Text, nullable=False)
    fb_url = Column(Text, nullable=True)
    status = Column(String(32), default="queued")  # queued, running, done, error
    error = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PipelineEvent(Base):
    """Log từng bước của lần chạy gần nhất (xóa cũ trước khi ghi mới)."""
    __tablename__ = "pipeline_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(String(64), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    node_name = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class ResearchResult(Base):
    """1 dòng / business — dữ liệu tổng hợp đầy đủ của 3 node, brand tra theo business_id."""
    __tablename__ = "research_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(String(64), unique=True, nullable=False, index=True)
    business_name = Column(String(255), nullable=True)

    # Node 1: Suggestions — nguyên cục, không tách field lẻ
    suggestions_raw = Column(JSON, nullable=False, default=list)                            # list[str]
    suggestions_tagged = Column(JSON, nullable=False, default=default_suggestions_tagged)   # dict 7 key cố định

    # Node 2: SERP — nguyên cục, đủ 8 key cố định
    serp_data = Column(JSON, nullable=False, default=default_serp_data)

    # Node 3: Facebook — brand info (posts/comments tách bảng riêng bên dưới)
    fb_brand = Column(JSON, nullable=False, default=default_fb_brand)                        # dict 5 key cố định

    # Báo cáo tổng hợp dạng text (đọc nhanh, không cần parse JSON)
    final_report = Column(Text, nullable=True)

    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FbPost(Base):
    """Nhiều dòng / business — mỗi bài post Facebook là 1 dòng (xóa cũ trước khi ghi mới)."""
    __tablename__ = "fb_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(String(64), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class FbComment(Base):
    """Nhiều dòng / business — mỗi comment (kèm replies) là 1 dòng (xóa cũ trước khi ghi mới)."""
    __tablename__ = "fb_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(String(64), nullable=False, index=True)
    author = Column(String(255), nullable=True)
    time = Column(String(64), nullable=True)
    comment = Column(Text, nullable=True)
    replies = Column(JSON, nullable=False, default=list)  # list[str]
    created_at = Column(DateTime, default=datetime.now)


def init_db(db_path: str = "research.db"):
    """Tạo engine + tạo bảng nếu chưa có. Gọi 1 lần khi pipeline khởi tạo."""
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return engine


# ═══════════════════════════════════════════════════════════════════════
# STATE (dataclass) — dùng trong lúc chạy pipeline, KHÔNG phải DB model
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ResearchState:
    """State runtime cho 1 lần chạy pipeline."""

    # Input
    query: str
    fb_url: str
    business_id: str
    business_name: Optional[str] = None

    # Node 1: Suggestions
    suggestions: List[str] = field(default_factory=list)
    tagged_suggestions: dict = field(default_factory=default_suggestions_tagged)

    # Node 2: SERP
    serp_data: dict = field(default_factory=default_serp_data)

    # Node 3: Facebook
    # fb_data = {"brand": {...5 key...}, "posts": [str,...], "comments": [{author,time,comment,replies},...]}
    fb_data: dict = field(default_factory=lambda: {
        "brand": default_fb_brand(),
        "posts": [],
        "comments": [],
    })

    # Node 4: Report
    report: dict = field(default_factory=dict)

    # Tracking
    status: str = "queued"  # queued, running, done, error
    error: Optional[str] = None
    events: List[dict] = field(default_factory=list)

    def add_event(self, seq: int, node_name: str, payload: dict):
        self.events.append({
            "seq": seq,
            "node": node_name,
            "payload": payload,
            "time": datetime.now().isoformat(),
        })

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "fb_url": self.fb_url,
            "business_id": self.business_id,
            "business_name": self.business_name,
            "suggestions_count": len(self.suggestions),
            "suggestions_tagged": self.tagged_suggestions,
            "serp_data": self.serp_data,
            "fb_data": self.fb_data,
            "report": self.report,
            "status": self.status,
            "error": self.error,
            "events": self.events,
        }