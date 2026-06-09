from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Send

from app.research.models import HotelResearchState
from app.research.nodes import (
    node_screenshots,
    node_vision_extract,
    node_find_websites,
    node_crawl_websites,
    node_analyze_competitors,
    node_tiktok_data,
    node_social_data,
    node_final_report,
    cleanup_browser,
)

# ═══════════════════════════════════════════════════════
# CONDITIONAL EDGES
# ═══════════════════════════════════════════════════════

def should_continue_after_screenshots(state: HotelResearchState) -> str:
    if state.get("screenshot_paths"):
        return "vision_extract"
    return "final_report"


def should_continue_after_vision(state: HotelResearchState):
    """Fan-out sang 2 branches song song bằng Send API."""
    if state.get("competitors_clean"):
        return [
            Send("competitor_branch", state),
            Send("social_branch", state),
        ]
    return "final_report"


# ═══════════════════════════════════════════════════════
# SUB-GRAPHS
# ═══════════════════════════════════════════════════════

def build_competitor_branch() -> StateGraph:
    graph = StateGraph(HotelResearchState)
    graph.add_node("find_websites", node_find_websites)
    graph.add_node("crawl_websites", node_crawl_websites)
    graph.add_node("analyze_competitors", node_analyze_competitors)

    graph.add_edge(START, "find_websites")
    graph.add_edge("find_websites", "crawl_websites")
    graph.add_edge("crawl_websites", "analyze_competitors")
    graph.add_edge("analyze_competitors", END)

    return graph.compile()


def build_social_branch() -> StateGraph:
    graph = StateGraph(HotelResearchState)
    graph.add_node("tiktok_data", node_tiktok_data)
    graph.add_node("social_data", node_social_data)

    graph.add_edge(START, "tiktok_data")
    graph.add_edge(START, "social_data")
    graph.add_edge("tiktok_data", END)
    graph.add_edge("social_data", END)

    return graph.compile()


# ═══════════════════════════════════════════════════════
# MAIN GRAPH
# ═══════════════════════════════════════════════════════

def build_graph():
    graph = StateGraph(HotelResearchState)

    graph.add_node("screenshots", node_screenshots)
    graph.add_node("vision_extract", node_vision_extract)
    graph.add_node("competitor_branch", build_competitor_branch())
    graph.add_node("social_branch", build_social_branch())
    graph.add_node("merge_data", lambda state: {})
    graph.add_node("final_report", node_final_report)
    graph.add_node("cleanup", cleanup_browser)

    graph.add_edge(START, "screenshots")

    graph.add_conditional_edges(
        "screenshots",
        should_continue_after_screenshots,
        {
            "vision_extract": "vision_extract",
            "final_report": "final_report",
        }
    )

    # FIX: dùng Send API + list đích thay vì dict với value là list
    graph.add_conditional_edges(
        "vision_extract",
        should_continue_after_vision,
        ["competitor_branch", "social_branch", "final_report"],
    )

    graph.add_edge("competitor_branch", "merge_data")
    graph.add_edge("social_branch", "merge_data")

    graph.add_edge("merge_data", "final_report")
    graph.add_edge("final_report", "cleanup")
    graph.add_edge("cleanup", END)

    return graph.compile(checkpointer=MemorySaver())