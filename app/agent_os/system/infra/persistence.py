import environ
import contextlib
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

env = environ.Env()


class PostgresFactory:
    def __init__(self):
        self.db_url = (
            f"postgresql://{env('POSTGRES_USER')}:"
            f"{env('POSTGRES_PASSWORD')}@"
            f"{env('POSTGRES_HOST')}:"
            f"{env('POSTGRES_PORT')}/"
            f"{env('POSTGRES_DB')}"
        )
        self.pool = None

    @contextlib.asynccontextmanager
    async def get_checkpointer(self):
        if self.pool is None:
            self.pool = AsyncConnectionPool(
                conninfo=self.db_url,
                max_size=20,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                },
                open=False,
            )

        if not self.pool._opened:
            await self.pool.open()

        saver = AsyncPostgresSaver(self.pool)
        await saver.setup()
        yield saver


factory = PostgresFactory()
