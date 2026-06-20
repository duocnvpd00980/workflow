from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, Index, event, func
from sqlalchemy.orm import relationship
from sqlalchemy.engine import Connection
from datetime import datetime, timezone
from app.db import Base
import uuid


def _utcnow() -> datetime:
    """Timezone-aware UTC now — dùng cho Python-side defaults."""
    return datetime.now(timezone.utc)


class Brand(Base):
    # Dùng lại tên bảng cũ "brands" để 10 nơi khác (như workflow_sessions) không bị lỗi
    __tablename__ = "brands"

    # ── Primary key ───────────────────────────────────────────────
    # Dùng lại tên cột "id" thay vì "brand_id" để khớp với Foreign Key cũ
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    business_id = Column(
        String(36),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metadata_info = Column(JSON, default=dict)
    
    # ── Voice config (user nhập) ──────────────────────────────────
    name            = Column(String(255), nullable=False)   # "Nike Sporty"
    purpose         = Column(String(500), nullable=False)   # "Bán giày chạy"
    channels        = Column(JSON,        default=list)     # ["social", "blog"]
    desired_tone    = Column(String(100), nullable=False)   # "energetic"
    target_audience = Column(String(500), nullable=False)   # "Runner 20-30 tuổi"

    # ── 8 fields (LLM extract) ────────────────────────────────────
    personality  = Column(Text, nullable=False)
    tone         = Column(JSON, nullable=False)
    style        = Column(JSON, nullable=False)
    vocabulary   = Column(JSON, nullable=False)
    format_rules = Column(JSON, nullable=False)
    cta_style    = Column(JSON, nullable=False)
    examples     = Column(JSON, default=list)

    # ── RAG sources ───────────────────────────────────────────────
    # website_url    = Column(String(2048), nullable=True)
    # uploaded_files = Column(JSON,         default=list)  # list of file paths / S3 keys
    # pasted_text    = Column(Text,         nullable=True)


    # ── 4 Trục khẩu khí định lượng (0 -> 100) phục vụ Radar & Sliders ──
    tone_funny_serious               = Column(Integer, default=50, nullable=False)
    tone_formal_casual               = Column(Integer, default=50, nullable=False)
    tone_respectful_irreverent       = Column(Integer, default=50, nullable=False)
    tone_enthusiastic_matter_of_fact = Column(Integer, default=50, nullable=False)

    
    # ── Meta ──────────────────────────────────────────────────────
    is_default = Column(String(1), default="0")       # "1" = default voice for business

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=_utcnow,           # ← Thêm default
        onupdate=_utcnow,          # ← Sửa onupdate
        nullable=False,            # ← Thêm nullable=False
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    # Đồng bộ lại back_populates trỏ về "brands" ở phía Business nếu cần
    business = relationship("Business", back_populates="brands")

    # ── Indexes ───────────────────────────────────────────────────
    __table_args__ = (
        Index("idx_bv_business_default", "business_id", "is_default"),
        Index("idx_bv_business_deleted", "business_id", "deleted_at"),
    )

    # ── SQLite: bật CASCADE DELETE via PRAGMA foreign_keys ────────
    @staticmethod
    def _set_sqlite_pragma(connection: Connection, _record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")


# ── Helper: đăng ký PRAGMA cho aiosqlite engine ───────────────────
def register_sqlite_fk_pragma(engine) -> None:
    from sqlalchemy import event as sa_event

    @sa_event.listens_for(engine.sync_engine if hasattr(engine, "sync_engine") else engine, "connect")
    def _fk_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()