from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.chat.router import router as chat_router
from app.rag.router import router as rag_router
from app.db import init_db
from app.container import lifespan as services_lifespan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. DB trước
    logger.info("🚀 Khởi động server...")
    await init_db()
    logger.info("✅ Database ready.")

    # 2. Services (ModelRegistry, RAG, ...) sau
    async with services_lifespan(app):
        yield

    logger.info("🛑 Server shutting down.")


app = FastAPI(
    title="LangGraph Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")