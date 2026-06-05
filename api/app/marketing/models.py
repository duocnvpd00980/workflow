from sqlalchemy import String, JSON, DateTime, Integer
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, mapped_column

class Base(DeclarativeBase):
    pass

class WorkflowSession(Base):
    __tablename__ = "workflow_sessions"
    
    id = mapped_column(String(8), primary_key=True)
    thread_id = mapped_column(String(20), unique=True)
    request = mapped_column(String(500))
    template = mapped_column(String(20))
    status = mapped_column(String(20))  # running, paused, completed, error
    draft = mapped_column(JSON)          # {content, metadata, version, versions: []}
    usage = mapped_column(JSON)          # {total_tokens, total_cost, calls: []}
    publish_status = mapped_column(String(20))  # pending, published, failed, dead_letter
    approved = mapped_column(Integer, default=0)  # 0/1
    error = mapped_column(String(50))    # timeout, rate_limit, invalid, fatal
    created_at = mapped_column(DateTime, default=datetime.now)
    updated_at = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)