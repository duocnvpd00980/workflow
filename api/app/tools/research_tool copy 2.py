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

# ── Xvfb ──
subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1920x1080x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
os.environ["DISPLAY"] = ":99"


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str = ""


class ResearchTool:
    SKIP = ("google", "youtube", "facebook", "twitter", "instagram")

    def __init__(self, wait: float = 3.0, retries: int = 2):
        self.wait = wait
        self.retries = retries

    def _parse(self, html: str) -> List[SearchResult]:
        soup = BeautifulSoup(html, "html.parser")
        seen = set()
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if href.startswith("http") and not any(s in href for s in self.SKIP) and href not in seen and text:
                seen.add(href)
                links.append(SearchResult(url=href, title=text))
        return links

    async def search(self, query: str, n: int = 5) -> List[SearchResult]:
        url = f"https://www.google.com/search?q={quote_plus(query.strip())}"
        for i in range(1, self.retries + 1):
            try:
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

    def _extract_article(self, html: str, url: str) -> str:
        """Extract main article content, bỏ navigation/TOC/footer."""
        soup = BeautifulSoup(html, "html.parser")
        
        # Bỏ script, style, nav, header, footer, aside
        for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        
        # Tìm main content area
        main = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"content|article|post|entry"))
        
        if not main:
            main = soup.find("body")
        
        text = main.get_text(separator="\n", strip=True) if main else ""
        
        # Clean up lines
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line or len(line) < 15:
                continue
            
            # Bỏ TOC patterns
            if re.match(r'^\d+[\.\d]*\s+\w+', line) and len(line) < 80:
                # Looks like table of contents entry
                continue
            
            # Bỏ breadcrumb
            if "›" in line or ">" in line and len(line) < 50:
                continue
            
            # Bỏ author info patterns
            if any(p in line.lower() for p in ["author", "đăng bởi", "viết bởi", "ngày đăng", "lượt xem"]):
                continue
            
            lines.append(line)
        
        # Join và giới hạn
        content = "\n".join(lines)
        return content[:12000]

    async def crawl(self, urls: List[str]) -> List[Dict]:
        docs = []
        async with AsyncWebCrawler() as crawler:
            for result in await crawler.arun_many(urls=urls):
                if result.success and result.html:
                    # Dùng BeautifulSoup extract thay vì markdown thô
                    clean = self._extract_article(result.html, result.url)
                    if len(clean) > 200:  # Chỉ giữ nếu có nội dung thực sự
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

        # Format content gọn cho LLM
        content_parts = []
        for doc in docs:
            # Truncate nếu quá dài
            text = doc["content"]
            if len(text) > 4000:
                text = text[:4000] + "...[truncated]"
            content_parts.append(f"SOURCE: {doc['url']}\n{text}\n")

        return {
            "query": query,
            "sources": sources,
            "content": "\n---\n".join(content_parts),
        }


async def research(query: str, n_results: int = 5, n_crawl: int = 3) -> Dict:
    return await ResearchTool().run(query, n_results, n_crawl)