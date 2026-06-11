from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event, text
from app.config import get_settings

_s = get_settings()

# ── Engine ───────────────────────────────────────────────────────
# Bỏ StaticPool + check_same_thread để SQLite không bị lock khi
# nhiều coroutine ghi đồng thời.
engine = create_async_engine(
    _s.DATABASE_URL,
    echo=_s.is_dev,
    pool_pre_ping=True,
    # Với aiosqlite KHÔNG dùng StaticPool — để mặc định (NullPool-like)
    # connect_args để aiosqlite tự xử lý thread-safety
)


# ── WAL mode: bật ngay khi mở connection mới ────────────────────
# WAL cho phép nhiều reader đọc song song với 1 writer,
# tránh "database is locked" khi pipeline ghi nhiều node cùng lúc.
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")       # multi-reader / single-writer
    cursor.execute("PRAGMA synchronous=NORMAL")     # nhanh hơn FULL, vẫn safe
    cursor.execute("PRAGMA foreign_keys=ON")        # enforce FK
    cursor.execute("PRAGMA busy_timeout=5000")      # chờ tối đa 5s thay vì fail ngay
    cursor.close()


# ── Session factory ──────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Init tất cả bảng ─────────────────────────────────────────────
async def init_db() -> None:
    from app.chat.models      import Base as ChatBase
    from app.rag.models       import Base as RagBase
    from app.marketing.models import Base as MarketingBase
    from app.brand.models     import Base as BrandBase
    from app.research.models  import Base as ResearchBase 
    from app.tasks.models import Base as TaskBase

    async with engine.begin() as conn:
        await conn.run_sync(TaskBase.metadata.create_all) 
        await conn.run_sync(ChatBase.metadata.create_all)
        await conn.run_sync(RagBase.metadata.create_all)
        await conn.run_sync(MarketingBase.metadata.create_all)
        await conn.run_sync(BrandBase.metadata.create_all)
        await conn.run_sync(ResearchBase.metadata.create_all) 


# ── Dependency FastAPI ───────────────────────────────────────────
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session