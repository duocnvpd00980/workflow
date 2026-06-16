from typing import TypedDict, List, Annotated
from datetime import datetime
import operator

from sqlalchemy import String, JSON, DateTime, Integer, Text, ForeignKey, Index
from sqlalchemy.orm import mapped_column, relationship
from app.db import Base


class PipelineTask(Base):
    __tablename__ = "pipeline_tasks"
    __table_args__ = (
        Index("ix_pipeline_task_business_id", "business_id"),
    )

    task_id       = mapped_column(String(36), primary_key=True)

    # ── Link về Business ─────────────────────────────────────────
    business_id   = mapped_column(String(36), ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True)

    business_name = mapped_column(String(255), nullable=False)   # giữ lại để hiển thị UI
    address       = mapped_column(String(500), nullable=True)
    industry      = mapped_column(String(100), nullable=True)
    status        = mapped_column(String(20), default="queued")  # queued, running, done, error
    result        = mapped_column(JSON, nullable=True)
    error         = mapped_column(Text, nullable=True)
    created_at    = mapped_column(DateTime, default=datetime.now)
    updated_at    = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    business = relationship("Business", back_populates="pipeline_tasks")
    events = relationship(
        "PipelineEvent",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="PipelineEvent.seq",
    )
    result_record = relationship(
        "ResearchResult",
        back_populates="task",
        uselist=False,
        cascade="all, delete-orphan",
    )


class PipelineEvent(Base):
    __tablename__ = "pipeline_events"

    id      = mapped_column(Integer, primary_key=True, autoincrement=True)
    seq     = mapped_column(Integer, nullable=False)
    task_id = mapped_column(String(36), ForeignKey("pipeline_tasks.task_id"), nullable=False, index=True)
    payload = mapped_column(Text, nullable=False)

    task = relationship("PipelineTask", back_populates="events")


class ResearchResult(Base):
    __tablename__ = "research_results"
    __table_args__ = (
        Index("ix_research_result_business_id", "business_id"),
    )

    id                   = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id              = mapped_column(String(36), ForeignKey("pipeline_tasks.task_id"), unique=True, nullable=True)

    # ── Link về Business ─────────────────────────────────────────
    business_id          = mapped_column(String(36), ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True)

    business_name        = mapped_column(String(255), nullable=True)  # giữ lại để hiển thị UI
    created_at           = mapped_column(DateTime, default=datetime.now)
    competitors_clean    = mapped_column(JSON, nullable=True)
    competitors_scraped  = mapped_column(JSON, nullable=True)
    competitor_analysis  = mapped_column(Text, nullable=True)
    tiktok_comments      = mapped_column(JSON, nullable=True)
    final_report         = mapped_column(Text, nullable=True)

    # Relationships
    task = relationship("PipelineTask", back_populates="result_record")


# ── Reducer helpers ──────────────────────────────────────────────

def keep_last(old, new):
    """Giữ giá trị mới nhất, bỏ qua nếu new falsy."""
    return new if new else old


def merge_dicts(old: List[dict], new: List[dict]) -> List[dict]:
    """Merge list dict, deduplicate theo 'name'."""
    combined = {d.get("name", str(i)): d for i, d in enumerate(old)}
    for d in new:
        key = d.get("name", str(len(combined)))
        combined[key] = d
    return list(combined.values())


# ── LangGraph State (TypedDict) ──────────────────────────────────
class HotelResearchState(TypedDict):
    # Input
    business_name: Annotated[str, keep_last]
    address:       Annotated[str, keep_last]
    industry:      Annotated[str, keep_last]

    # ── business_id xuyên suốt pipeline ─────────────────────────
    business_id:   Annotated[str, keep_last]

    # Base path
    hotel_dir: Annotated[str, keep_last]

    # Node 1+2
    screenshot_paths: Annotated[List[str], operator.add]
    errors:           Annotated[List[str], operator.add]

    # Node 3+4
    competitors_clean: Annotated[List[str], operator.add]

    # Competitor branch
    competitors_with_website: Annotated[List[dict], merge_dicts]
    competitors_scraped:      Annotated[List[dict], merge_dicts]
    competitor_analysis:      Annotated[str, keep_last]

    # Social branch
    tiktok_data:     Annotated[List[dict], operator.add]
    tiktok_comments: Annotated[List[dict], operator.add]
    social_sources:  Annotated[List[str], operator.add]

    # Final
    final_report: Annotated[str, keep_last]