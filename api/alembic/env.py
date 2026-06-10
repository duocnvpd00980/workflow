from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import sys
from pathlib import Path

# Thêm thư mục app vào path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.chat.models import Base as ChatBase
from app.rag.models import Base as RagBase
from app.marketing.models import Base as MarketingBase
from app.brand.models import Base as BrandBase
from app.research.models import Base as ResearchBase

# Tổng hợp tất cả Base
class CombinedBase:
    metadata = ChatBase.metadata
    
for base_class in [RagBase, MarketingBase, BrandBase, ResearchBase]:
    for table in base_class.metadata.tables.values():
        table.to_metadata(CombinedBase.metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = CombinedBase.metadata

# ── Lấy DATABASE_URL từ config, convert async → sync ───────────
_s = get_settings()
db_url = _s.DATABASE_URL
# Convert sqlite+aiosqlite:// → sqlite://
db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = db_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.StaticPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()