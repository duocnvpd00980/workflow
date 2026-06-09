from pathlib import Path
from typing import AsyncGenerator, Dict, Any
import json
import asyncio

from app.research.models import HotelResearchState
from app.research.workflow import NODE_META, build_graph

# 📦 Bộ lưu trữ trạng thái các Task chạy ngầm trên RAM
TASK_STORE: Dict[str, Dict[str, Any]] = {}


def create_initial_state(
    hotel_dir: str,
    business_name: str,
    address: str,
    industry: str,
) -> HotelResearchState:
    return {
        "business_name": business_name,
        "address": address,
        "industry": industry,

        "hotel_dir": hotel_dir,
        "screenshot_paths": [],
        "ocr_raw_text": "",
        "competitors_clean": [],
        "competitors_with_website": [],
        "competitors_scraped": [],
        "competitor_analysis": "",
        "social_sources": [],
        "tiktok_html_path": "",
        "tiktok_content": "",
        "tiktok_comment_html_paths": [],
        "tiktok_comments": [],
        "final_report": "",
        "errors": [],
    }


async def run_pipeline(
    business_name: str,
    address: str,
    industry: str,
) -> HotelResearchState:
    
    hotel_dir = "hotels"
    Path(hotel_dir).mkdir(parents=True, exist_ok=True)

    graph = build_graph()

    return await graph.ainvoke(
        create_initial_state(
            hotel_dir=hotel_dir,
            business_name=business_name,
            address=address,
            industry=industry,
        )
    )


async def run_pipeline_stream(
    business_name: str,
    address: str,
    industry: str,
) -> AsyncGenerator[str, None]:
    hotel_dir = "hotels"
    Path(hotel_dir).mkdir(parents=True, exist_ok=True)

    state = create_initial_state(
        hotel_dir=hotel_dir,
        business_name=business_name,
        address=address,
        industry=industry,
    )

    node_map = {name: (label, pct) for name, label, pct in NODE_META}
    graph = build_graph()

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async for event in graph.astream(state, stream_mode="updates"):
        for node_name, node_state in event.items():
            label, progress = node_map.get(node_name, (node_name, 0))

            state = {**state, **node_state}

            summary = {}

            if node_name == "ocr_images":
                summary["chars"] = len(state.get("ocr_raw_text", ""))

            elif node_name == "llm_clean_hotels":
                summary["hotels_found"] = len(state.get("competitors_clean", []))
                summary["sample"] = state.get("competitors_clean", [])[:3]

            elif node_name == "find_websites":
                summary["with_website"] = len([
                    h
                    for h in state.get("competitors_with_website", [])
                    if h.get("website")
                ])

            elif node_name == "crawl_websites":
                summary["crawled_ok"] = len([
                    s
                    for s in state.get("competitors_scraped", [])
                    if s.get("success")
                ])

            elif node_name == "parse_tiktok_comments":
                summary["comments"] = len(state.get("tiktok_comments", []))

            elif node_name == "final_strategy_report":
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
            "industry": state.get("industry"),
            "competitors_clean": state.get("competitors_clean", []),
            "competitor_analysis": state.get("competitor_analysis", ""),
            "final_report": state.get("final_report", ""),
            "errors": state.get("errors", []),
        },
    })


# 🛠️ HÀM MỚI BỔ SUNG: Chạy ngầm hấp thụ data từ generator và lưu lại
async def pipeline_worker_task(task_id: str, business_name: str, address: str, industry: str):
    TASK_STORE[task_id] = {
        "status": "running",
        "events": []
    }
    try:
        async for event_str in run_pipeline_stream(business_name, address, industry):
            TASK_STORE[task_id]["events"].append(event_str)
            
            # Nếu thấy flag kết thúc từ generator thì cập nhật status tổng
            if '"node": "FINISHED"' in event_str:
                TASK_STORE[task_id]["status"] = "completed"
                
    except Exception as e:
        TASK_STORE[task_id]["status"] = "failed"
        # Bắn thêm 1 event lỗi giả lập theo cấu trúc SSE để UI React nhận diện được luôn
        error_payload = {
            "node": "ERROR",
            "label": "❌ Thất bại",
            "status": "failed",
            "progress": 0,
            "message": str(e),
            "data": {}
        }
        TASK_STORE[task_id]["events"].append(f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n")