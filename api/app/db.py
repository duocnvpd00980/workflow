from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event, text
from app.config import get_settings
from sqlalchemy.orm import DeclarativeBase

_s = get_settings()

# ── Engine ───────────────────────────────────────────────────────
engine = create_async_engine(
    _s.DATABASE_URL,
    echo=_s.is_dev,
    pool_pre_ping=True,
)

# ── WAL mode cho SQLite ──────────────────────────────────────────
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")       
    cursor.execute("PRAGMA synchronous=NORMAL")     
    cursor.execute("PRAGMA foreign_keys=ON")        
    cursor.execute("PRAGMA busy_timeout=5000")      
    cursor.close()

# ── Base trung tâm duy nhất của toàn bộ hệ thống ─────────────────
class Base(DeclarativeBase):
    pass

# ── Session factory ──────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Init tất cả bảng ─────────────────────────────────────────────
async def init_db() -> None:
    import app.chat.models
    import app.rag.models
    import app.marketing.models
    import app.brand.models
    import app.research.models
    import app.tasks.models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ── Dependency FastAPI ───────────────────────────────────────────
async def get_db(): 
    async with AsyncSessionLocal() as session:
        yield session