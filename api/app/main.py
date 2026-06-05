from contextlib import asynccontextmanager
import logging
import os
import psutil
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.chat.router import router as chat_router
from app.rag.router import router as rag_router
from app.marketing.router import router as marketing_router

from app.db import init_db


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Khởi động server...")
    await init_db()
    logger.info("✅ Database ready.")
    yield
    logger.info("🛑 Server shutting down.")


app = FastAPI(
    title="LangGraph Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://workflow-ui-2bg.pages.dev", "https://viable-superb-basilisk.ngrok-free.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(marketing_router, prefix="/api/v1")

@app.get("/metrics/system", tags=["Monitoring"])
def system_metrics():
    proc = psutil.Process(os.getpid())
    mem  = proc.memory_info()
    return {
        "cpu_percent":  proc.cpu_percent(interval=1),
        "ram_used_mb":  round(mem.rss / 1024 / 1024, 1),
        "ram_used_vms": round(mem.vms / 1024 / 1024, 1),
        "threads":      proc.num_threads(),
        "open_files":   len(proc.open_files()),
    }