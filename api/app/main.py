from contextlib import asynccontextmanager
import logging
import os
import psutil
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.chat.router import router as chat_router
from app.rag.router import router as rag_router
from app.rag.image_router import router as image_router
from app.marketing.router import router as marketing_router
from app.brand.router import router as brand_router
from app.research.router import router as research_router
from app.rag.hotel_router import router as hotel_router
from app.tasks.router import router as tasks_router
from app.business.router import router as business_router

from app.db import init_db



# 1. Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# 2. Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Khởi động server...")
    logger.info(f"LANGSMITH_TRACING={os.getenv('LANGSMITH_TRACING')}")
    logger.info(f"LANGSMITH_PROJECT={os.getenv('LANGSMITH_PROJECT')}")
    logger.info(f"HAS_API_KEY={bool(os.getenv('LANGSMITH_API_KEY'))}")

    await init_db()
    logger.info("✅ Database ready.")
    yield
    logger.info("🛑 Server shutting down.")

# 3. Khởi tạo FastAPI App trước
app = FastAPI(
    title="LangGraph Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

# 4. Tự động kiểm tra và tạo thư mục static (Đường dẫn tuyệt đối)
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "static")
os.makedirs(static_dir, exist_ok=True)

# 5. Mount thư mục static bằng biến static_dir chuẩn hóa
app.mount("/media", StaticFiles(directory="app/media"), name="media")

# 6. Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 7. Include Routers
app.include_router(chat_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(marketing_router, prefix="/api/v1")
app.include_router(brand_router, prefix="/api/v1")
app.include_router(research_router, prefix="/api/v1")
app.include_router(image_router, prefix="/api/v1")
app.include_router(hotel_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(business_router, prefix="/api/v1")


# 8. Metrics Endpoint
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