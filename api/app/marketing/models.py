from sqlalchemy import String, JSON, DateTime, Integer, ForeignKey, Index
from datetime import datetime
from sqlalchemy.orm import mapped_column, relationship
from app.db import Base

class WorkflowSession(Base):
    __tablename__ = "workflow_sessions"
    __table_args__ = (
        Index("ix_workflow_business_id", "business_id"),
        Index("ix_workflow_brand_id", "brand_id"),
    )

    id = mapped_column(String(8), primary_key=True)
    thread_id = mapped_column(String(20), unique=True)
    request = mapped_column(String(500))
    template = mapped_column(String(20))
    status = mapped_column(String(20))        # running, paused, completed, error

    # ── Link về Business + Brand ─────────────────────────────────
    business_id = mapped_column(String(36), ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True)
    brand_id = mapped_column(String(36), ForeignKey("brands.id", ondelete="SET NULL"), nullable=True)

    draft = mapped_column(JSON)               # {content, metadata, version, versions: []}
    usage = mapped_column(JSON)               # {total_tokens, total_cost, calls: []}
    publish_status = mapped_column(String(20))  # pending, published, failed, dead_letter
    approved = mapped_column(Integer, default=0)  # 0/1
    error = mapped_column(String(50))         # timeout, rate_limit, invalid, fatal
    created_at = mapped_column(DateTime, default=datetime.now)
    updated_at = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    business = relationship("Business", back_populates="workflow_sessions")
    brand = relationship("Brand")