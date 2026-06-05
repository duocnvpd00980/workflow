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
    status = mapped_column(String(20))
    draft = mapped_column(JSON)
    usage = mapped_column(JSON)
    publish_status = mapped_column(String(20))
    approved = mapped_column(Integer, default=0)
    error = mapped_column(String(50))
    created_at = mapped_column(DateTime, default=datetime.now)
    updated_at = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)