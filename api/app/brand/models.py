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
    __tablename__ = "brands"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    business_id = Column(
        String(36),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metadata_info = Column(JSON, default=dict, nullable=False)
    name            = Column(String(255), nullable=False)   
    purpose = Column(Text, nullable=False)   
    channels        = Column(JSON,        default=list)     
    desired_tone    = Column(String(100), nullable=False)   
    target_audience = Column(Text, nullable=False)  
    website_url = Column(String(2048), nullable=True)
    k1_brand_foundation   = Column(Text, nullable=True)  
    k2_customer_insights  = Column(Text, nullable=True)  
    k3_content_patterns   = Column(Text, nullable=True)  
    k4_behavior_rules     = Column(Text, nullable=True)
    k5_examples           = Column(Text, nullable=True)
    k6_tone_analysis      = Column(Text, nullable=True)
    k7_vocabulary_rules   = Column(Text, nullable=True)
    taglines = Column(JSON, default=list, nullable=True)
    business_facts  = Column(JSON, default=dict, nullable=True)
    tone_funny_serious               = Column(Integer, default=50, nullable=False)
    tone_formal_casual               = Column(Integer, default=50, nullable=False)
    tone_respectful_irreverent       = Column(Integer, default=50, nullable=False)
    tone_enthusiastic_matter_of_fact = Column(Integer, default=50, nullable=False)
    is_default = Column(String(1), default="0") 
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    business = relationship("Business", back_populates="brands")
    __table_args__ = (
        Index("idx_bv_business_default", "business_id", "is_default"),
        Index("idx_bv_business_deleted", "business_id", "deleted_at"),
    )
    @staticmethod
    def _set_sqlite_pragma(connection: Connection, _record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")


def register_sqlite_fk_pragma(engine) -> None:
    from sqlalchemy import event as sa_event

    @sa_event.listens_for(engine.sync_engine if hasattr(engine, "sync_engine") else engine, "connect")
    def _fk_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()