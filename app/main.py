from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router
from app.db.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="LangGraph Agent API", lifespan=lifespan)
app.include_router(router)
