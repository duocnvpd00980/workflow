from pathlib import Path
from typing import AsyncGenerator, Dict, Any
import json
import asyncio

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.research.models import HotelResearchState, PipelineTask, PipelineEvent, ResearchResult
from app.research.workflow import build_graph
from app.tasks import create_task, finish_task, fail_task, update_task

# ── RAM cache ───────────────────────────────────────────────────
TASK_STORE: Dict[str, Dict[str, Any]] = {}

# ── NODE_META ────────────────────────────────────────────────────
NODE_META = [
    ("screenshots",       "📸 Chụp ảnh màn hình",    10),
    ("vision_extract",    "🔍 Trích xuất dữ liệu",    25),
    ("competitor_branch", "🏆 Phân tích đối thủ",     50),
    ("social_branch",     "📱 Dữ liệu mạng xã hội",  50),
    ("merge_data",        "🔄 Tổng hợp dữ liệu",      65),
    ("final_report",      "📝 Báo cáo chiến lược",    85),
    ("cleanup",           "🧹 Dọn dẹp",               95),
]
STEPS_TOTAL = len(NODE_META)


# ── Helpers DB ───────────────────────────────────────────────────

async def _db_create_task(
    task_id: str,
    business_name: str,
    address: str,
    industry: str,
    business_id: str | None = None,   # ← thêm
) -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.get(PipelineTask, task_id)
        if existing:
            return
        session.add(PipelineTask(
            task_id=task_id,
            business_id=business_id,       # ← gán
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


async def _db_finish_task(
    task_id: str,
    status: str,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    async with AsyncSessionLocal() as session:
        task = await session.get(PipelineTask, task_id)
        if task:
            task.status = status
            task.result = result
            task.error  = error
            await session.commit()


async def _db_save_result(
    task_id: str,
    data: dict,
    business_id: str | None = None,   # ← thêm
) -> None:
    async with AsyncSessionLocal() as session:
        session.add(ResearchResult(
            task_id=task_id,
            business_id=business_id,       # ← gán
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

        events = (await session.execute(
            select(PipelineEvent)
            .where(PipelineEvent.task_id == task_id)
            .order_by(PipelineEvent.seq)
        )).scalars().all()

        TASK_STORE[task_id] = {
            "status": task.status,
            "events": [e.payload for e in events],
        }
        return True


# ── State factory ─────────────────────────────────────────────────

def create_initial_state(
    hotel_dir: str,
    business_name: str,
    address: str,
    industry: str,
    business_id: str | None = None,   # ← thêm
) -> HotelResearchState:
    return {
        "business_id":   business_id,  # ← xuyên suốt LangGraph state
        "business_name": business_name,
        "address":       address,
        "industry":      industry,
        "hotel_dir":     hotel_dir,
        "screenshot_paths":        [],
        "competitors_clean":       [],
        "competitors_with_website": [],
        "competitors_scraped":     [],
        "competitor_analysis":     "",
        "tiktok_data":             [],
        "tiktok_comments":         [],
        "social_sources":          [],
        "final_report":            "",
        "errors":                  [],
    }


def _make_config(business_name: str) -> dict:
    return {"configurable": {"thread_id": f"hotel-research-{business_name}"}}


# ── Đồng bộ ──────────────────────────────────────────────────────

async def run_pipeline(business_name: str, address: str, industry: str) -> HotelResearchState:
    hotel_dir = "hotels"
    Path(hotel_dir).mkdir(parents=True, exist_ok=True)
    graph  = build_graph()
    state  = create_initial_state(hotel_dir=hotel_dir, business_name=business_name, address=address, industry=industry)
    config = _make_config(business_name)
    return await graph.ainvoke(state, config=config)


# ── Stream generator ──────────────────────────────────────────────

async def run_pipeline_stream(
    business_name: str,
    address: str,
    industry: str,
    business_id: str | None = None,   # ← thêm
) -> AsyncGenerator[str, None]:

    hotel_dir = "hotels"
    Path(hotel_dir).mkdir(parents=True, exist_ok=True)

    state    = create_initial_state(
        hotel_dir=hotel_dir,
        business_name=business_name,
        address=address,
        industry=industry,
        business_id=business_id,
    )
    node_map = {name: (label, pct) for name, label, pct in NODE_META}
    graph    = build_graph()
    config   = _make_config(business_name)

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
                summary["sample"]       = state.get("competitors_clean", [])[:3]
            elif node_name == "competitor_branch":
                summary["with_website"] = len([h for h in state.get("competitors_with_website", []) if h.get("website")])
                summary["crawled_ok"]   = len([s for s in state.get("competitors_scraped",      []) if s.get("success")])
                summary["analysis_chars"] = len(state.get("competitor_analysis", ""))
            elif node_name == "social_branch":
                summary["comments"]      = len(state.get("tiktok_comments", []))
                summary["social_sources"] = len(state.get("social_sources", []))
            elif node_name == "final_report":
                summary["report_chars"] = len(state.get("final_report", ""))
                summary["errors"]       = state.get("errors", [])

            yield sse({
                "node":     node_name,
                "label":    label,
                "status":   "done",
                "progress": progress,
                "message":  f"{label} hoàn thành",
                "data":     summary,
            })

    yield sse({
        "node":     "FINISHED",
        "label":    "✅ Pipeline hoàn thành",
        "status":   "finished",
        "progress": 100,
        "message":  "Tất cả nodes đã chạy xong",
        "data": {
            "business_id":          state.get("business_id"),
            "business_name":        state.get("business_name"),
            "address":              state.get("address"),
            "industry":             state.get("industry"),
            "competitors_scraped":  state.get("competitors_scraped",  []),
            "tiktok_comments":      state.get("tiktok_comments",      []),
            "competitors_clean":    state.get("competitors_clean",    []),
            "competitor_analysis":  state.get("competitor_analysis",  ""),
            "final_report":         state.get("final_report",         ""),
            "errors":               state.get("errors",               []),
        },
    })


# ── Background worker ─────────────────────────────────────────────

async def pipeline_worker_task(
    task_id: str,
    business_name: str,
    address: str,
    industry: str,
    business_id: str | None = None,   # ← thêm
) -> None:
    # Idempotent — router đã tạo trước, chỉ đảm bảo tồn tại
    await _db_create_task(task_id, business_name, address, industry, business_id=business_id)

    # Tạo row trong background_tasks trung tâm
    async with AsyncSessionLocal() as db:
        bg_task = await create_task(
            db,
            source="research",
            source_id=task_id,
            title=f"Nghiên cứu: {business_name}",
            triggered_by="user",
            steps_total=STEPS_TOTAL,
            business_id=business_id,  # ← thêm nếu create_task hỗ trợ
        )
        bg_task_id = bg_task.id

    seq = 0
    steps_done = 0

    try:
        async for event_str in run_pipeline_stream(
            business_name=business_name,
            address=address,
            industry=industry,
            business_id=business_id,
        ):
            TASK_STORE[task_id]["events"].append(event_str)
            asyncio.create_task(_db_append_event(task_id, seq, event_str))
            seq += 1

            try:
                payload = json.loads(event_str.removeprefix("data: ").strip())
                if payload.get("status") == "done":
                    steps_done += 1
                    async with AsyncSessionLocal() as db:
                        await update_task(db, bg_task_id, steps_done=steps_done)
            except Exception:
                pass

            if '"node": "FINISHED"' in event_str:
                TASK_STORE[task_id]["status"] = "completed"
                try:
                    result_data = json.loads(event_str.removeprefix("data: ").strip()).get("data", {})
                except Exception:
                    result_data = {}

                asyncio.create_task(_db_save_result(task_id, result_data, business_id=business_id))
                asyncio.create_task(_db_finish_task(task_id, "completed", result=result_data))

                async with AsyncSessionLocal() as db:
                    await finish_task(db, bg_task_id, steps_done=STEPS_TOTAL)

    except Exception as e:
        TASK_STORE[task_id]["status"] = "failed"
        error_payload = {
            "node":     "ERROR",
            "label":    "❌ Thất bại",
            "status":   "failed",
            "progress": 0,
            "message":  str(e),
            "data":     {},
        }
        error_str = f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        TASK_STORE[task_id]["events"].append(error_str)
        asyncio.create_task(_db_append_event(task_id, seq, error_str))
        asyncio.create_task(_db_finish_task(task_id, "failed", error=str(e)))

        async with AsyncSessionLocal() as db:
            await fail_task(db, bg_task_id, error_message=str(e))