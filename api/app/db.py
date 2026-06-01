from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings

_s = get_settings()

engine = create_async_engine(
    _s.database_url,
    echo=_s.is_dev,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    from app.chat.models import Base as ChatBase   # ← đúng path
    from app.rag.models import Base as RagBase     # ← đúng path

    async with engine.begin() as conn:
        await conn.run_sync(ChatBase.metadata.create_all)
        await conn.run_sync(RagBase.metadata.create_all)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session