from typing import TypedDict, List

class HotelResearchState(TypedDict):
    business_name: str
    address: str
    industry: str

    hotel_dir: str
    screenshot_paths: list[str]
    ocr_raw_text: str
    competitors_clean: list
    competitors_with_website: list
    competitors_scraped: list
    competitor_analysis: str
    social_sources: list
    tiktok_html_path: str
    tiktok_content: str
    tiktok_comment_html_paths: list
    tiktok_comments: list
    final_report: str
    errors: list[str]