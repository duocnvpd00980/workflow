# app/tools/google_search.py

import logging
from langchain_core.tools import tool

from app.tools.research_tool import research  # hàm convenience

logger = logging.getLogger(__name__)


@tool
async def google_search(query: str, max_results: int = 5) -> str:
    """Search Google and read webpage content. Input: query string."""
    result = await research(query, n_results=max_results, n_crawl=3)
    
    lines = [
        f"Query: {result['query']}\n",
        "Sources:",
    ]
    for src in result["sources"]:
        lines.append(f"  - {src}")
    
    if result["content"]:
        lines.extend(["\nContent:", result["content"][:10000]])
    
    return "\n".join(lines)


tools = [google_search]