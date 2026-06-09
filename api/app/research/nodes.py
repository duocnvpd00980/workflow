"""
Hotel Competitor Research Pipeline — nodes.py
"""

import asyncio
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Any

import aiohttp
import cv2
import easyocr

from app.research.models import HotelResearchState
from app.config import get_settings

_s = get_settings()

# ═══════════════════════════════════════════════════════
# CONFIG & CONSTANTS
# ═══════════════════════════════════════════════════════

HUMAN_DELAYS = {
    "min": 0.8,
    "max": 2.5,
    "scroll": 1.2,
    "page_load": 3.0,
}

STEALTH_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
    "--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process",
    "--disable-site-isolation-trials",
    "--disable-setuid-sandbox",
    "--disable-infobars",
    "--window-size=1920,1080",
    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0",
]

# ═══════════════════════════════════════════════════════
# BROWSER POOL — Singleton reuse
# ═══════════════════════════════════════════════════════

@dataclass
class BrowserContext:
    browser: Any
    page: Any
    last_used: float
    lock: asyncio.Lock


class BrowserPool:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    async def _init(self):
        if self._initialized:
            return
        import nodriver as uc
        self.uc = uc
        self._contexts: List[BrowserContext] = []
        self._max_contexts = 2
        self._initialized = True

    async def acquire(self) -> BrowserContext:
        await self._init()
        async with self._lock:
            now = time.time()
            for ctx in self._contexts:
                if not ctx.lock.locked() and (now - ctx.last_used) > 1:
                    await ctx.lock.acquire()
                    ctx.last_used = now
                    return ctx

            if len(self._contexts) < self._max_contexts:
                browser = await self.uc.start(headless=True, browser_args=STEALTH_ARGS)
                page = await browser.get("about:blank")
                ctx = BrowserContext(browser=browser, page=page, last_used=now, lock=asyncio.Lock())
                await ctx.lock.acquire()
                self._contexts.append(ctx)
                return ctx

            while True:
                for ctx in self._contexts:
                    if not ctx.lock.locked():
                        await ctx.lock.acquire()
                        ctx.last_used = now
                        return ctx
                await asyncio.sleep(0.5)

    async def release(self, ctx: BrowserContext):
        ctx.last_used = time.time()
        if ctx.lock.locked():
            ctx.lock.release()

    async def close_all(self):
        for ctx in self._contexts:
            try:
                ctx.browser.stop()
            except Exception:
                pass
        self._contexts.clear()


_pool = BrowserPool()


def human_delay(min_s: float = None, max_s: float = None):
    mn = min_s or HUMAN_DELAYS["min"]
    mx = max_s or HUMAN_DELAYS["max"]
    return asyncio.sleep(random.uniform(mn, mx))


# ═══════════════════════════════════════════════════════
# LLM HELPERS — Groq
# ═══════════════════════════════════════════════════════

_groq_client = None


def get_groq_client():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=_s.GROQ_API_KEY)
    return _groq_client


def call_groq(prompt: str, max_tokens: int = 1000, temperature: float = 0.3) -> str:
    client = get_groq_client()
    try:
        resp = client.chat.completions.create(
            model=_s.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        print(f"⚠️ Groq error: {e}")
        return ""


# ═══════════════════════════════════════════════════════
# NODE 1+2: Parallel Screenshots
# ═══════════════════════════════════════════════════════

async def _screenshot_google(hotel_dir: Path) -> str:
    ctx = await _pool.acquire()
    try:
        page = ctx.page
        await page.get("https://www.google.com/travel/hotels?q=hotel%20%C4%90%C3%A0%20N%E1%BA%B5ng%20S%C6%A1n%20Tr%C3%A0")
        await asyncio.sleep(HUMAN_DELAYS["page_load"])

        for _ in range(random.randint(3, 5)):
            # FIX: tính random trong Python, truyền số vào JS string
            scroll_y = random.randint(600, 1000)
            await page.evaluate(f"window.scrollBy(0, {scroll_y})")
            await human_delay(1.0, 2.0)

        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)

        out_path = str(hotel_dir / "step1_google.png")
        await page.save_screenshot(out_path, full_page=True)
        print(f"✅ Google screenshot: {out_path}")
        return out_path
    finally:
        await _pool.release(ctx)


async def _screenshot_booking(hotel_dir: Path) -> str:
    ctx = await _pool.acquire()
    try:
        page = ctx.page
        await page.get("https://www.booking.com/searchresults.html?ss=Đà+Nẵng")
        await asyncio.sleep(HUMAN_DELAYS["page_load"] + 1)

        await page.evaluate("""
            document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="overlay"]')
                .forEach(el => el.remove());
        """)
        await human_delay(1.0, 2.0)

        for _ in range(random.randint(5, 8)):
            # FIX: tính random trong Python, truyền số vào JS string
            scroll_y = random.randint(800, 1200)
            await page.evaluate(f"window.scrollBy(0, {scroll_y})")
            await human_delay(1.5, 2.5)

        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)

        out_path = str(hotel_dir / "step1_booking.png")
        await page.save_screenshot(out_path, full_page=True)
        print(f"✅ Booking screenshot: {out_path}")
        return out_path
    finally:
        await _pool.release(ctx)


async def node_screenshots(state: HotelResearchState) -> dict:
    """Node 1+2: Chụp ảnh song song"""
    print("\n📸 [Nodes 1+2] Parallel screenshots...")
    hotel_dir = Path(state["hotel_dir"])
    hotel_dir.mkdir(exist_ok=True)

    try:
        results = await asyncio.gather(
            _screenshot_google(hotel_dir),
            _screenshot_booking(hotel_dir),
            return_exceptions=True,
        )

        paths = []
        errors = []
        for r in results:
            if isinstance(r, Exception):
                errors.append(str(r))
                print(f"❌ Screenshot error: {r}")
            else:
                paths.append(r)

        return {"screenshot_paths": paths, "errors": errors}

    except Exception as e:
        print(f"❌ Screenshots failed: {e}")
        return {"errors": [f"screenshots: {e}"]}


# ═══════════════════════════════════════════════════════
# NODE 3+4: OCR → LLM clean
# ═══════════════════════════════════════════════════════

_ocr_reader = None


def _get_ocr_reader() -> easyocr.Reader:
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = easyocr.Reader(['vi', 'en'], gpu=False)
    return _ocr_reader


def _run_ocr(image_paths: List[Path]) -> tuple[str, List[str]]:
    """Chạy OCR đồng bộ (easyocr không hỗ trợ async)."""
    reader = _get_ocr_reader()
    all_texts = []
    errors = []

    for img_path in image_paths:
        print(f"  🔍 OCR: {img_path.name}")
        img = cv2.imread(str(img_path))
        if img is None:
            errors.append(f"ocr: không đọc được {img_path.name}")
            continue

        h, w = img.shape[:2]
        if w > 1440:
            scale = 1440 / w
            img = cv2.resize(img, (1440, int(h * scale)), interpolation=cv2.INTER_AREA)

        results = reader.readtext(img, detail=0, paragraph=False, batch_size=8)
        for text in results:
            text = text.strip()
            if len(text) > 10 and any(c.isupper() for c in text[1:]):
                all_texts.append(text)

    unique_texts = list(dict.fromkeys(all_texts))
    return "\n".join(unique_texts), errors


async def node_vision_extract(state: HotelResearchState) -> dict:
    """Node 3+4: OCR ảnh → LLM clean tên hotel"""
    print("\n🔍 [Node 3+4] OCR + LLM clean hotels...")
    hotel_dir = Path(state["hotel_dir"])
    hotel_dir.mkdir(exist_ok=True)

    image_paths = [Path(p) for p in (state.get("screenshot_paths") or [])]
    if not image_paths:
        image_paths = sorted(hotel_dir.glob("step1_*.png"))

    if not image_paths:
        return {"errors": ["vision_extract: không tìm thấy ảnh"]}

    print(f"📁 {len(image_paths)} ảnh")

    # Bước 1: OCR trong thread pool
    loop = asyncio.get_event_loop()
    raw_text, ocr_errors = await loop.run_in_executor(None, _run_ocr, image_paths)

    if not raw_text.strip():
        return {"errors": ocr_errors + ["vision_extract: OCR không ra text"]}

    (hotel_dir / "competitors.txt").write_text(raw_text, encoding="utf-8")
    print(f"✅ OCR xong: {len(raw_text)} ký tự")

    # Bước 2: LLM clean
    prompt = f"""Bạn là chuyên gia du lịch Đà Nẵng. Từ đoạn text OCR lộn xộn sau, hãy trích xuất CHÍNH XÁC tên các khách sạn, resort, homestay ở khu vực Sơn Trà/Đà Nẵng.

Yêu cầu:
- Chỉ trả về tên hotel, mỗi dòng 1 tên
- Loại bỏ: giá tiền, số sao, số reviews, tiện ích (WiFi, pool...), UI text
- Sửa lỗi OCR: "LBtusS" → "Lotus", "bv" → "by", v.v.
- Giữ nguyên tên thương hiệu: "Four Points by Sheraton", "InterContinental"

TEXT OCR:
{raw_text[:8000]}

OUTPUT (chỉ tên hotel, không giải thích):"""

    try:
        result = await loop.run_in_executor(
            None, lambda: call_groq(prompt, max_tokens=4000)
        )
        hotels = [h.strip() for h in result.splitlines() if h.strip()]
    except Exception as e:
        return {"errors": ocr_errors + [f"vision_extract LLM: {e}"]}

    (hotel_dir / "competitors_clean.txt").write_text("\n".join(hotels), encoding="utf-8")
    print(f"✅ {len(hotels)} hotel → competitors_clean.txt")

    return {
        "competitors_clean": hotels,
        **({"errors": ocr_errors} if ocr_errors else {}),
    }


# ═══════════════════════════════════════════════════════
# NODE 4: Find Websites
# ═══════════════════════════════════════════════════════

_ddgs_instance = None


def get_ddgs():
    global _ddgs_instance
    if _ddgs_instance is None:
        from ddgs import DDGS
        _ddgs_instance = DDGS()
    return _ddgs_instance


async def _find_one_website(name: str, sem: asyncio.Semaphore) -> dict:
    async with sem:
        try:
            loop = asyncio.get_event_loop()
            ddgs = get_ddgs()

            def _search():
                return list(ddgs.text(f"{name} official website Đà Nẵng", max_results=3))

            search_list = await asyncio.wait_for(
                loop.run_in_executor(None, _search), timeout=10.0
            )

            website = None
            for r in search_list:
                url = r.get('href', '')
                if any(x in url.lower() for x in ['booking.com', 'tripadvisor', 'agoda', 'expedia']):
                    continue
                if url.startswith('http'):
                    website = url
                    break

            print(f"  ✅ {name}: {website or 'N/A'}")
            return {
                "name": name,
                "website": website,
                "search_results": [r.get('href', '') for r in search_list[:3]],
            }

        except asyncio.TimeoutError:
            print(f"  ⏱️ {name}: timeout")
            return {"name": name, "website": None, "search_results": []}
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            return {"name": name, "website": None, "search_results": []}


async def node_find_websites(state: HotelResearchState) -> dict:
    """Node 4: Tìm website"""
    print("\n🌐 [Node 4] Finding websites...")
    hotel_dir = Path(state["hotel_dir"])
    hotels = state.get("competitors_clean") or []

    if not hotels:
        return {"errors": ["find_websites: no hotels"]}

    sem = asyncio.Semaphore(5)
    tasks = [_find_one_website(name, sem) for name in hotels[:15]]
    results = await asyncio.gather(*tasks)

    (hotel_dir / "competitors_with_website.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    found = sum(1 for r in results if r["website"])
    print(f"✅ {found}/{len(results)} websites found")

    return {"competitors_with_website": list(results)}


# ═══════════════════════════════════════════════════════
# NODE 5: Crawl Websites
# ═══════════════════════════════════════════════════════

async def _crawl_one(hotel: dict, session: aiohttp.ClientSession, sem: asyncio.Semaphore) -> dict:
    name, url = hotel["name"], hotel.get("website")
    if not url:
        return {"name": name, "url": None, "content": "", "success": False}

    async with sem:
        try:
            jina_url = f"https://r.jina.ai/{url}"
            async with session.get(jina_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    success = len(text) > 200
                    print(f"  ✅ {name}: {len(text)} chars")
                    return {
                        "name": name, "url": url,
                        "content": text[:3000] if success else "Too short",
                        "success": success,
                    }

            # Fallback: direct request
            ua = random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            ])
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10),
                                   headers={"User-Agent": ua}) as resp2:
                text = await resp2.text()
                from trafilatura import extract
                clean = extract(text, output_format="txt") or ""
                success = len(clean) > 200
                return {
                    "name": name, "url": url,
                    "content": clean[:3000] if success else "Empty",
                    "success": success,
                }

        except Exception as e:
            print(f"  ❌ {name}: {str(e)[:60]}")
            return {"name": name, "url": url, "content": f"Error: {str(e)[:80]}", "success": False}


async def node_crawl_websites(state: HotelResearchState) -> dict:
    """Node 5: Crawl websites"""
    print("\n🕷️ [Node 5] Crawling websites...")
    hotel_dir = Path(state["hotel_dir"])
    data = state.get("competitors_with_website", [])
    hotels = [h for h in data if h.get("website")]

    if not hotels:
        return {"errors": ["crawl: no websites"]}

    sem = asyncio.Semaphore(5)
    connector = aiohttp.TCPConnector(limit=10, limit_per_host=3)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [_crawl_one(h, session, sem) for h in hotels]
        scraped = await asyncio.gather(*tasks)

    (hotel_dir / "competitors_scraped.json").write_text(
        json.dumps(scraped, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    ok = sum(1 for s in scraped if s["success"])
    print(f"✅ {ok}/{len(scraped)} crawled successfully")

    return {"competitors_scraped": list(scraped)}


# ═══════════════════════════════════════════════════════
# NODE 6: Analyze Competitors
# ═══════════════════════════════════════════════════════

async def node_analyze_competitors(state: HotelResearchState) -> dict:
    """Node 6: Phân tích đối thủ"""
    print("\n📊 [Node 6] Analyzing competitors...")
    hotel_dir = Path(state["hotel_dir"])
    scraped = state.get("competitors_scraped", [])

    successful = [s for s in scraped if s.get("success")][:10]
    if not successful:
        return {"errors": ["analyze: no data"]}

    content_summary = ""
    for h in successful:
        content_summary += f"\n\n### {h['name']} ({h['url']})\n{h['content'][:600]}"

    prompt = f"""Bạn là Marketing Analyst của Sontra Sea Hotel (3 sao, Sơn Trà, Đà Nẵng).
Phân tích dữ liệu đối thủ và tạo báo cáo:

1. PHÂN LOẠI ĐỐI THỦ (Direct/Indirect)
2. ĐỐI THỦ CHÍNH: Điểm mạnh/yếu, giá ước tính, target khách hàng
3. CHIẾN LƯỢC ĐỀ XUẤT: 3-5 hành động cụ thể

DỮ LIỆU:{content_summary[:4000]}"""

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: call_groq(prompt, max_tokens=4000))

    if not result:
        result = "Không thể phân tích đối thủ do lỗi kết nối Groq API."
        print("⚠️ Warning: call_groq returned empty!")

    (hotel_dir / "competitor_analysis.txt").write_text(result, encoding="utf-8")
    print("✅ Analysis complete")

    # FIX: chỉ trả đúng field trong HotelResearchState, bỏ node/status/errors thừa
    return {"competitor_analysis": result}


# ═══════════════════════════════════════════════════════
# NODE 7: TikTok
# ═══════════════════════════════════════════════════════

TIKTOK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


async def _tiktok_search_api(query: str, session: aiohttp.ClientSession) -> List[dict]:
    try:
        async with session.get("https://www.tiktok.com", headers=TIKTOK_HEADERS) as resp:
            _ = resp.cookies

        search_url = "https://www.tiktok.com/api/search/general/full/"
        params = {"keyword": query, "offset": 0, "count": 10, "search_source": "normal_search", "type": 1}

        async with session.get(search_url, params=params, headers=TIKTOK_HEADERS) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            videos = []
            for item in data.get("data", []):
                content = item.get("item", {})
                if content:
                    videos.append({
                        "id": content.get("id"),
                        "desc": content.get("desc", ""),
                        "author": content.get("author", {}).get("uniqueId", ""),
                        "stats": content.get("stats", {}),
                        "url": f"https://www.tiktok.com/@{content.get('author', {}).get('uniqueId', '')}/video/{content.get('id')}",
                    })
            return videos

    except Exception as e:
        print(f"⚠️ TikTok API error: {e}")
        return []


async def _tiktok_comments_api(video_id: str, session: aiohttp.ClientSession) -> List[dict]:
    try:
        url = "https://www.tiktok.com/api/comment/list/"
        params = {"aweme_id": video_id, "count": 20, "cursor": 0}

        async with session.get(url, params=params, headers=TIKTOK_HEADERS) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            comments = []
            for c in data.get("comments", []):
                text = c.get("text", "")
                if any(k in text.lower() for k in ["khách sạn", "hotel", "đà nẵng", "phòng", "giá"]):
                    comments.append({
                        "username": c.get("user", {}).get("unique_id", "unknown"),
                        "text": text,
                        "likes": c.get("digg_count", 0),
                    })
            return comments

    except Exception as e:
        print(f"⚠️ TikTok comments error: {e}")
        return []


async def node_tiktok_data(state: HotelResearchState) -> dict:
    """Node 7: TikTok API"""
    print("\n📱 [Node 7] TikTok API...")
    hotel_dir = Path(state["hotel_dir"])

    # FIX: bọc toàn bộ trong try/except, đảm bảo luôn trả dict
    try:
        connector = aiohttp.TCPConnector(limit=5, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            videos = await _tiktok_search_api("review khách sạn Đà Nẵng", session)
            print(f"  Found {len(videos)} videos")

            if not videos:
                return {"tiktok_data": [], "tiktok_comments": []}

            comment_tasks = [_tiktok_comments_api(v["id"], session) for v in videos[:3]]
            comments_results = await asyncio.gather(*comment_tasks)

            all_comments = []
            for i, comments in enumerate(comments_results):
                for c in comments:
                    c["video_index"] = i + 1
                    all_comments.append(c)

            seen = set()
            unique = []
            for c in all_comments:
                key = c["username"] + c["text"][:30]
                if key not in seen:
                    seen.add(key)
                    unique.append(c)

        (hotel_dir / "tiktok_videos.json").write_text(
            json.dumps(videos, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (hotel_dir / "tiktok_comments.json").write_text(
            json.dumps(unique, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        print(f"✅ {len(videos)} videos, {len(unique)} comments")
        return {"tiktok_data": videos, "tiktok_comments": unique}

    except Exception as e:
        print(f"❌ node_tiktok_data crashed: {e}")
        return {"tiktok_data": [], "tiktok_comments": [], "errors": [f"tiktok: {e}"]}


# ═══════════════════════════════════════════════════════
# NODE 8: Social Data
# ═══════════════════════════════════════════════════════

async def _reddit_search(query: str, session: aiohttp.ClientSession) -> List[dict]:
    try:
        params = {"q": query, "limit": 15, "sort": "relevance"}
        headers = {"User-Agent": "Mozilla/5.0 (HotelResearch/1.0)"}

        async with session.get(
            "https://www.reddit.com/search.json",
            params=params, headers=headers,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            posts = []
            for child in data.get("data", {}).get("children", []):
                p = child.get("data", {})
                posts.append({
                    "title": p.get("title", ""),
                    "text": p.get("selftext", "")[:500],
                    "subreddit": p.get("subreddit", ""),
                    "score": p.get("score", 0),
                    "url": f"https://reddit.com{p.get('permalink', '')}",
                })
            return posts

    except Exception as e:
        print(f"⚠️ Reddit error: {e}")
        return []


async def _google_trends(keywords: List[str]) -> Optional[str]:
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='vi-VN', tz=360)
        pytrends.build_payload(keywords, timeframe='today 12-m', geo='VN')
        df = pytrends.interest_over_time()
        return df.to_csv() if not df.empty else None
    except Exception as e:
        print(f"⚠️ Trends error: {e}")
        return None


async def node_social_data(state: HotelResearchState) -> dict:
    """Node 8: Reddit + Google Trends"""
    print("\n📈 [Node 8] Social data...")
    hotel_dir = Path(state["hotel_dir"])

    # FIX: bọc toàn bộ trong try/except, đảm bảo luôn trả dict
    try:
        sources = []

        connector = aiohttp.TCPConnector(limit=5)
        async with aiohttp.ClientSession(connector=connector) as session:
            reddit_posts = await _reddit_search("Da Nang hotel budget", session)
            if reddit_posts:
                (hotel_dir / "reddit_posts.json").write_text(
                    json.dumps(reddit_posts, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                sources.append(f"Reddit ({len(reddit_posts)} posts)")
                print(f"✅ Reddit: {len(reddit_posts)} posts")

        trends_csv = await _google_trends(
            ["khách sạn giá rẻ Đà Nẵng", "hotel Sơn Trà", "du lịch Đà Nẵng"]
        )
        if trends_csv:
            (hotel_dir / "google_trends.csv").write_text(trends_csv, encoding="utf-8")
            sources.append("Google Trends")
            print("✅ Trends OK")

        return {"social_sources": sources}

    except Exception as e:
        print(f"❌ node_social_data crashed: {e}")
        return {"social_sources": [], "errors": [f"social: {e}"]}


# ═══════════════════════════════════════════════════════
# NODE 9: Final Report
# ═══════════════════════════════════════════════════════

async def node_final_report(state: HotelResearchState) -> dict:
    """Node 9: Báo cáo chiến lược cuối"""
    print("\n📝 [Node 9] Final strategy report...")
    hotel_dir = Path(state["hotel_dir"])

    competitors = state.get("competitors_clean", [])
    if not competitors:
        try:
            competitors = (hotel_dir / "competitors_clean.txt").read_text(encoding="utf-8").splitlines()
        except Exception:
            pass

    analysis = state.get("competitor_analysis", "")
    if not analysis:
        try:
            analysis = (hotel_dir / "competitor_analysis.txt").read_text(encoding="utf-8")
        except Exception:
            pass

    tiktok_comments = state.get("tiktok_comments", [])
    if not tiktok_comments:
        try:
            tiktok_comments = json.loads((hotel_dir / "tiktok_comments.json").read_text(encoding="utf-8"))
        except Exception:
            pass

    comments_text = "\n".join([
        f"@{c['username']}: {c['text'][:120]}"
        for c in tiktok_comments[:25]
    ])

    prompt = f"""Bạn là Giám đốc Marketing khách sạn Sontra Sea Hotel (3 sao, view biển Sơn Trà, 41 Hoàng Sa, Đà Nẵng).

DỮ LIỆU:
1. ĐỐI THỦ: {chr(10).join(competitors[:20]) if competitors else "Không có dữ liệu"}
2. PHÂN TÍCH: {analysis[:2000] if analysis else "Không có dữ liệu"}
3. KHÁCH HÀNG TIKTOK: {comments_text[:2000] if comments_text else "Không có dữ liệu"}

YÊU CẦU:
A. CUSTOMER PERSONAS (3-5 personas)
B. CHIẾN LƯỢC TIẾP CẬN TỪNG PERSONA
C. CHIẾN DỊCH 30 NGÀY

Tiếng Việt, bullet point."""

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: call_groq(prompt, max_tokens=4000))

    if not result or not result.strip():
        result = "Không thể tạo báo cáo chiến lược do lỗi kết nối Groq API."

    (hotel_dir / "final_strategy_report.txt").write_text(result, encoding="utf-8")
    print(f"✅ Report saved")

    return {"final_report": result}


# ═══════════════════════════════════════════════════════
# CLEANUP
# ═══════════════════════════════════════════════════════

async def cleanup_browser(state: HotelResearchState) -> dict:
    """Đóng browser pool khi pipeline xong"""
    await _pool.close_all()
    return {}