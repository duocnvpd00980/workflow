from langgraph.graph import StateGraph, END
from app.research.models import HotelResearchState
from app.research.nodes import (
    node_screenshot_google, node_screenshot_booking,
    node_ocr_images, node_llm_clean_hotels,
    node_find_websites, node_crawl_websites,
    node_analyze_competitors, node_collect_social_data,
    node_scrape_tiktok_html, node_extract_tiktok_content,
    node_scrape_tiktok_comments, node_parse_tiktok_comments,
    node_final_strategy_report,
)


# Thứ tự + % tiến độ mỗi node
NODE_META = [
    ("screenshot_google",       "📸 Chụp Google Hotels",          7),
    ("screenshot_booking",      "📸 Chụp Booking.com",            14),
    ("ocr_images",              "🔍 OCR ảnh",                     21),
    ("llm_clean_hotels",        "🤖 Làm sạch tên hotel",          30),
    ("find_websites",           "🌐 Tìm website đối thủ",         40),
    ("crawl_websites",          "🕷️ Crawl website",               52),
    ("analyze_competitors",     "📊 Phân tích đối thủ",           63),
    ("collect_social_data",     "📈 Thu thập Google Trends",      70),
    ("scrape_tiktok_html",      "📱 Lấy HTML TikTok",             76),
    ("extract_tiktok_content",  "🔤 Extract nội dung TikTok",     82),
    ("scrape_tiktok_comments",  "💬 Scrape comments TikTok",      88),
    ("parse_tiktok_comments",   "🔎 Parse comments",              93),
    ("final_strategy_report",   "📝 Tạo báo cáo chiến lược",     100),
]

def build_graph():
    graph = StateGraph(HotelResearchState)

    graph.add_node("screenshot_google",      node_screenshot_google)
    graph.add_node("screenshot_booking",     node_screenshot_booking)
    graph.add_node("ocr_images",             node_ocr_images)
    graph.add_node("llm_clean_hotels",       node_llm_clean_hotels)
    graph.add_node("find_websites",          node_find_websites)
    graph.add_node("crawl_websites",         node_crawl_websites)
    graph.add_node("analyze_competitors",    node_analyze_competitors)
    graph.add_node("collect_social_data",    node_collect_social_data)
    graph.add_node("scrape_tiktok_html",     node_scrape_tiktok_html)
    graph.add_node("extract_tiktok_content", node_extract_tiktok_content)
    graph.add_node("scrape_tiktok_comments", node_scrape_tiktok_comments)
    graph.add_node("parse_tiktok_comments",  node_parse_tiktok_comments)
    graph.add_node("final_strategy_report",  node_final_strategy_report)

    graph.set_entry_point("screenshot_google")
    graph.add_edge("screenshot_google",      "screenshot_booking")
    graph.add_edge("screenshot_booking",     "ocr_images")
    graph.add_edge("ocr_images",             "llm_clean_hotels")
    graph.add_edge("llm_clean_hotels",       "find_websites")
    graph.add_edge("find_websites",          "crawl_websites")
    graph.add_edge("crawl_websites",         "analyze_competitors")
    graph.add_edge("analyze_competitors",    "collect_social_data")
    graph.add_edge("collect_social_data",    "scrape_tiktok_html")
    graph.add_edge("scrape_tiktok_html",     "extract_tiktok_content")
    graph.add_edge("extract_tiktok_content", "scrape_tiktok_comments")
    graph.add_edge("scrape_tiktok_comments", "parse_tiktok_comments")
    graph.add_edge("parse_tiktok_comments",  "final_strategy_report")
    graph.add_edge("final_strategy_report",  END)

    return graph.compile()


