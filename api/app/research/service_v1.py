from pathlib import Path
from typing import AsyncGenerator, Dict, Any
import json
import asyncio

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.research.models import HotelResearchState, PipelineTask, PipelineEvent, ResearchResult
from app.research.workflow import build_graph

# ── RAM cache ───────────────────────────────────────────────────
TASK_STORE: Dict[str, Dict[str, Any]] = {}

# ── NODE_META: đồng bộ tên node với workflow.py ─────────────────
NODE_META = [
    ("screenshots",       "📸 Chụp ảnh màn hình",      10),
    ("vision_extract",    "🔍 Trích xuất dữ liệu",      25),
    ("competitor_branch", "🏆 Phân tích đối thủ",       50),
    ("social_branch",     "📱 Dữ liệu mạng xã hội",    50),
    ("merge_data",        "🔄 Tổng hợp dữ liệu",       65),
    ("final_report",      "📝 Báo cáo chiến lược",      85),
    ("cleanup",           "🧹 Dọn dẹp",                 95),
]


# ── Helpers DB ───────────────────────────────────────────────────

async def _db_create_task(task_id: str, business_name: str, address: str, industry: str) -> None:
    """Tạo task mới trong DB. Nếu đã tồn tại thì bỏ qua (idempotent)."""
    async with AsyncSessionLocal() as session:
        existing = await session.get(PipelineTask, task_id)
        if existing:
            return  # Đã tồn tại, không tạo lại
        session.add(PipelineTask(
            task_id=task_id,
            business_name=business_name,
            address=address,
            industry=industry,
            status="running",
        ))
        await session.commit()


async def _db_append_event(task_id: str, seq: int, payload: str) -> None:
    async with AsyncSessionLocal() as session:
        session.add(PipelineEvent(task_id=task_id, seq=seq, payload=payload))
        await session.commit()


async def _db_finish_task(task_id: str, status: str, result: dict | None = None, error: str | None = None) -> None:
    async with AsyncSessionLocal() as session:
        task = await session.get(PipelineTask, task_id)
        if task:
            task.status = status
            task.result = result
            task.error  = error
            await session.commit()


async def _db_save_result(task_id: str, data: dict) -> None:
    """Lưu kết quả pipeline đầy đủ vào research_results."""
    async with AsyncSessionLocal() as session:
        session.add(ResearchResult(
            task_id=task_id,
            business_name=data.get("business_name"),
            competitors_clean=data.get("competitors_clean"),
            competitors_scraped=data.get("competitors_scraped"),
            competitor_analysis=data.get("competitor_analysis"),
            tiktok_comments=data.get("tiktok_comments"),
            final_report=data.get("final_report"),
        ))
        await session.commit()


async def load_task_from_db(task_id: str) -> bool:
    async with AsyncSessionLocal() as session:
        task = await session.get(PipelineTask, task_id)
        if not task:
            return False

        result = await session.execute(
            select(PipelineEvent)
            .where(PipelineEvent.task_id == task_id)
            .order_by(PipelineEvent.seq)
        )
        events = result.scalars().all()

        TASK_STORE[task_id] = {
            "status": task.status,
            "events": [e.payload for e in events],
        }
        return True


# ── State factory ─────────────────────────────────────────────────

def create_initial_state(hotel_dir: str, business_name: str, address: str, industry: str) -> HotelResearchState:
    return {
        "business_name": business_name,
        "address": address,
        "industry": industry,
        "hotel_dir": hotel_dir,
        "screenshot_paths": [],
        "competitors_clean": [],
        "competitors_with_website": [],
        "competitors_scraped": [],
        "competitor_analysis": "",
        "tiktok_data": [],
        "tiktok_comments": [],
        "social_sources": [],
        "final_report": "",
        "errors": [],
    }


def _make_config(business_name: str) -> dict:
    return {"configurable": {"thread_id": f"hotel-research-{business_name}"}}


# ── Đồng bộ ──────────────────────────────────────────────────────

async def run_pipeline(business_name: str, address: str, industry: str) -> HotelResearchState:
    hotel_dir = "hotels"
    Path(hotel_dir).mkdir(parents=True, exist_ok=True)
    graph = build_graph()
    state = create_initial_state(hotel_dir=hotel_dir, business_name=business_name, address=address, industry=industry)
    config = _make_config(business_name)
    return await graph.ainvoke(state, config=config)


# ── Stream generator ─────────────────────────────────────────────

async def run_pipeline_stream(
    business_name: str,
    address: str,
    industry: str,
) -> AsyncGenerator[str, None]:

    hotel_dir = "hotels"
    Path(hotel_dir).mkdir(parents=True, exist_ok=True)

    state = create_initial_state(hotel_dir=hotel_dir, business_name=business_name, address=address, industry=industry)
    node_map = {name: (label, pct) for name, label, pct in NODE_META}
    graph = build_graph()
    config = _make_config(business_name)

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async for event in graph.astream(state, config=config, stream_mode="updates"):
        for node_name, node_state in event.items():
            label, progress = node_map.get(node_name, (node_name, 0))

            if node_state and isinstance(node_state, dict):
                state = {**state, **node_state}

            summary: dict = {}
            if node_name == "screenshots":
                summary["screenshots"] = len(state.get("screenshot_paths", []))
            elif node_name == "vision_extract":
                summary["hotels_found"] = len(state.get("competitors_clean", []))
                summary["sample"] = state.get("competitors_clean", [])[:3]
            elif node_name == "competitor_branch":
                summary["with_website"] = len([h for h in state.get("competitors_with_website", []) if h.get("website")])
                summary["crawled_ok"] = len([s for s in state.get("competitors_scraped", []) if s.get("success")])
                summary["analysis_chars"] = len(state.get("competitor_analysis", ""))
            elif node_name == "social_branch":
                summary["comments"] = len(state.get("tiktok_comments", []))
                summary["social_sources"] = len(state.get("social_sources", []))
            elif node_name == "final_report":
                summary["report_chars"] = len(state.get("final_report", ""))
                summary["errors"] = state.get("errors", [])

            yield sse({
                "node": node_name,
                "label": label,
                "status": "done",
                "progress": progress,
                "message": f"{label} hoàn thành",
                "data": summary,
            })

    yield sse({
        "node": "FINISHED",
        "label": "✅ Pipeline hoàn thành",
        "status": "finished",
        "progress": 100,
        "message": "Tất cả nodes đã chạy xong",
        "data": {
            "business_name": state.get("business_name"),
            "address": state.get("address"),
            "competitors_scraped": state.get("competitors_scraped", []),
            "tiktok_comments": state.get("tiktok_comments", []),
            "industry": state.get("industry"),
            "competitors_clean": state.get("competitors_clean", []),
            "competitor_analysis": state.get("competitor_analysis", ""),
            "final_report": state.get("final_report", ""),
            "errors": state.get("errors", []),
        },
    })


# ── Background worker ────────────────────────────────────────────

async def pipeline_worker_task(task_id: str, business_name: str, address: str, industry: str) -> None:
    # FIX: KHÔNG gọi _db_create_task ở đây — router đã tạo row rồi
    # Chỉ cần đảm bảo row tồn tại (trường hợp server restart)
    await _db_create_task(task_id, business_name, address, industry)

    seq = 0
    try:
        async for event_str in run_pipeline_stream(business_name, address, industry):
            TASK_STORE[task_id]["events"].append(event_str)
            asyncio.create_task(_db_append_event(task_id, seq, event_str))
            seq += 1

            if '"node": "FINISHED"' in event_str:
                TASK_STORE[task_id]["status"] = "completed"
                try:
                    result_data = json.loads(event_str.removeprefix("data: ").strip()).get("data", {})
                except Exception:
                    result_data = {}
                asyncio.create_task(_db_save_result(task_id, result_data))
                asyncio.create_task(_db_finish_task(task_id, "completed", result=result_data))

    except Exception as e:
        TASK_STORE[task_id]["status"] = "failed"
        error_payload = {
            "node": "ERROR",
            "label": "❌ Thất bại",
            "status": "failed",
            "progress": 0,
            "message": str(e),
            "data": {},
        }
        error_str = f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        TASK_STORE[task_id]["events"].append(error_str)
        asyncio.create_task(_db_append_event(task_id, seq, error_str))
        asyncio.create_task(_db_finish_task(task_id, "failed", error=str(e)))