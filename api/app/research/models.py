from typing import TypedDict, List, Annotated
from datetime import datetime
import operator

from sqlalchemy import String, JSON, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import mapped_column, relationship
from app.db import Base


class PipelineTask(Base):
    __tablename__ = "pipeline_tasks"

    task_id       = mapped_column(String(36), primary_key=True)
    business_name = mapped_column(String(255), nullable=False)
    address       = mapped_column(String(500), nullable=True)
    industry      = mapped_column(String(100), nullable=True)
    status        = mapped_column(String(20), default="queued")
    result        = mapped_column(JSON, nullable=True)
    error         = mapped_column(Text, nullable=True)
    created_at    = mapped_column(DateTime, default=datetime.now)
    updated_at    = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    events = relationship(
        "PipelineEvent",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="PipelineEvent.seq",
    )


class PipelineEvent(Base):
    __tablename__ = "pipeline_events"

    id      = mapped_column(Integer, primary_key=True, autoincrement=True)
    seq     = mapped_column(Integer, nullable=False)
    task_id = mapped_column(String(36), ForeignKey("pipeline_tasks.task_id"), nullable=False, index=True)
    payload = mapped_column(Text, nullable=False)

    task = relationship("PipelineTask", back_populates="events")


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
    tiktok_data:    Annotated[List[dict], operator.add]
    tiktok_comments: Annotated[List[dict], operator.add]
    social_sources:  Annotated[List[str], operator.add]

    # Final
    final_report: Annotated[str, keep_last]


class ResearchResult(Base):
    __tablename__ = "research_results"

    id                   = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id              = mapped_column(String(36), ForeignKey("pipeline_tasks.task_id"), unique=True, nullable=False)
    business_name        = mapped_column(String(255), nullable=True)
    created_at           = mapped_column(DateTime, default=datetime.now)
    competitors_clean    = mapped_column(JSON, nullable=True)
    competitors_scraped  = mapped_column(JSON, nullable=True)
    competitor_analysis  = mapped_column(Text, nullable=True)
    tiktok_comments      = mapped_column(JSON, nullable=True)
    final_report         = mapped_column(Text, nullable=True)