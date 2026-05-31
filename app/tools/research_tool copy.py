# app/tools/research_tool.py

import logging
import os
import subprocess
import time
import re
from dataclasses import dataclass
from typing import List, Dict
from urllib.parse import quote_plus

import nodriver as uc
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

logger = logging.getLogger(__name__)

# ── Xvfb ── Giữ nguyên exact code gốc
subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1920x1080x24"])
os.environ["DISPLAY"] = ":99"


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str = ""


class ResearchTool:
    """Giữ nguyên cơ chế headless=False + Xvfb như code gốc đã test OK."""

    SKIP = ("google", "youtube", "facebook", "twitter", "instagram")

    def __init__(self, wait: float = 3.0, retries: int = 2):
        self.wait = wait
        self.retries = retries

    def _parse(self, html: str) -> List[SearchResult]:
        """Giữ nguyên logic parse từ code gốc."""
        soup = BeautifulSoup(html, "html.parser")
        seen = set()
        links = []
        
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if (
                href.startswith("http")
                and not any(s in href for s in self.SKIP)
                and href not in seen
                and text
            ):
                seen.add(href)
                links.append(SearchResult(url=href, title=text))
        
        return links

    async def search(self, query: str, n: int = 5) -> List[SearchResult]:
        """Giữ nguyên exact flow: start -> get -> wait -> content -> stop."""
        url = f"https://www.google.com/search?q={quote_plus(query.strip())}"
        
        for i in range(1, self.retries + 1):
            try:
                # ⚠️ Exact như code gốc: headless=False
                browser = await uc.start(headless=False)
                page = await browser.get(url)
                await page.wait(self.wait)
                html = await page.get_content()
                browser.stop()
                
                results = self._parse(html)[:n]
                logger.info(f"Search '{query}': {len(results)} results")
                return results
                
            except Exception as e:
                logger.warning(f"Attempt {i} failed: {e}")
                if i == self.retries:
                    raise
        
        return []

    def _clean(self, text: str) -> str:
        """Làm sạch markdown cho LLM."""
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # Bỏ image links
            if line.startswith("![") and "](" in line:
                continue
            
            # Bỏ HTML tags
            if line.startswith("<") and ">" in line:
                continue
            
            # Bỏ navigation patterns
            skip = (
                "trang chủ", "home", "menu", "danh mục", "giỏ hàng", "đăng nhập",
                "liên hệ", "©", "privacy", "terms", "cookie", "sitemap",
                "xem tại", "dtv search", "xu hướng tìm kiếm", "banner",
                "thay pin", "thay màn hình", "sửa điện thoại", "sửa laptop",
                "linh kiện", "phụ kiện", "thu cũ", "đặt lịch", "tìm kiếm",
                "điện thoại", "iphone", "macbook", "samsung", "airpods",
                "apple watch", "máy tính bảng", "máy cũ", "laptop cũ",
                "back-to-school", "header", "footer", "sidebar",
            )
            if any(p in line.lower() for p in skip):
                continue
            
            # Bỏ lines quá ngắn
            if len(line) < 20 and not line.startswith("#"):
                continue
            
            # Bỏ URLs đứng một mình
            if re.match(r'^https?://\S+$', line):
                continue
            
            # Bỏ breadcrumb
            if "›" in line and len(line) < 50:
                continue
            
            lines.append(line)
        
        return "\n".join(lines)[:10000] if lines else ""

    async def crawl(self, urls: List[str]) -> List[Dict]:
        docs = []
        async with AsyncWebCrawler() as crawler:
            for result in await crawler.arun_many(urls=urls):
                if result.success and result.markdown:
                    clean = self._clean(result.markdown)
                    if clean:
                        docs.append({"url": result.url, "content": clean})
                else:
                    logger.warning(f"Crawl failed: {result.url}")
        return docs

    async def run(self, query: str, n_results: int = 5, n_crawl: int = 3) -> Dict:
        results = await self.search(query, n_results)
        if not results:
            return {"query": query, "sources": [], "content": ""}

        urls = [r.url for r in results[:n_crawl]]
        docs = await self.crawl(urls)

        sources = [f"{i+1}. {r.title} — {r.url}" for i, r in enumerate(results)]

        content_parts = []
        for doc in docs:
            content_parts.append(f"---\nSource: {doc['url']}\n{doc['content']}\n")

        return {
            "query": query,
            "sources": sources,
            "content": "\n".join(content_parts),
        }


async def research(query: str, n_results: int = 5, n_crawl: int = 3) -> Dict:
    return await ResearchTool().run(query, n_results, n_crawl)