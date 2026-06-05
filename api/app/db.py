from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from app.config import get_settings

_s = get_settings()

engine = create_async_engine(
    _s.DATABASE_URL,
    echo=_s.is_dev,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool, 
)

AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def init_db() -> None:
    from app.chat.models import Base as ChatBase
    from app.rag.models import Base as RagBase
    from app.marketing.models import Base as MarketingBase
    from app.brand.models import Base as BrandBase

    async with engine.begin() as conn:
        await conn.run_sync(ChatBase.metadata.create_all)
        await conn.run_sync(RagBase.metadata.create_all)
        await conn.run_sync(MarketingBase.metadata.create_all)
        await conn.run_sync(BrandBase.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session