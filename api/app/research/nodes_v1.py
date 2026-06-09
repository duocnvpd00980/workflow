"""
Hotel Competitor Research Pipeline - LangGraph nodes (optimized)

Tối ưu so với bản gốc:
- Node 5: find_websites  → asyncio.gather + Semaphore(3) thay loop tuần tự
- Node 6: crawl_websites → asyncio.gather + Semaphore(3) thay loop tuần tự
- Node 9: scrape_tiktok  → giảm scroll 5→3 lần
- Node 11: tiktok comments → asyncio.gather(3 video song song)
- workflow.py            → Node1 + Node2 chạy song song qua parallel branch
"""

import asyncio
import json
import re
from pathlib import Path

from app.research.models import HotelResearchState
from app.config import get_settings

_s = get_settings()

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_groq_client():
    from groq import Groq
    return Groq(api_key=_s.GROQ_API_KEY)

def call_groq(prompt: str, max_tokens: int = 1000) -> str:
    client = get_groq_client()
    try:
        resp = client.chat.completions.create(
            model=_s.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=max_tokens,
            temperature=0.3,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        print(f"⚠️ Groq error: {e}")
        return ""


# ─────────────────────────────────────────────
# NODE 1: Screenshot Google Hotels
# ─────────────────────────────────────────────

async def node_screenshot_google(state: HotelResearchState) -> HotelResearchState:
    print("\n📸 [Node 1] Screenshot Google Hotels...")
    hotel_dir = Path(state["hotel_dir"])
    hotel_dir.mkdir(exist_ok=True)

    try:
        import nodriver as uc
        browser = await uc.start(
            headless=True,
            browser_args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.get(
            "https://www.google.com/travel/hotels?q=hotel%20%C4%90%C3%A0%20N%E1%BA%B5ng%20S%C6%A1n%20Tr%C3%A0"
        )
        await asyncio.sleep(5)

        for _ in range(5):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(2)

        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)

        out_path = str(hotel_dir / "step1_hotels.png")
        await page.save_screenshot(out_path, full_page=True)
        print(f"✅ Google Hotels: {out_path}")
        browser.stop()

        return {"screenshot_paths": state["screenshot_paths"] + [out_path]}

    except Exception as e:
        print(f"❌ Node 1 lỗi: {e}")
        return {"errors": state["errors"] + [f"node_screenshot_google: {e}"]}


# ─────────────────────────────────────────────
# NODE 2: Screenshot Booking.com
# ─────────────────────────────────────────────

async def node_screenshot_booking(state: HotelResearchState) -> HotelResearchState:
    print("\n📸 [Node 2] Screenshot Booking.com...")
    hotel_dir = Path(state["hotel_dir"])

    try:
        import nodriver as uc
        browser = await uc.start(
            headless=False,
            browser_args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.get("https://www.booking.com/searchresults.html?ss=Đà+Nẵng")
        await asyncio.sleep(5)

        await page.evaluate("""
            const closeBtns = document.querySelectorAll('button, [role="button"]');
            for (const btn of closeBtns) {
                const text = btn.textContent || btn.getAttribute('aria-label') || '';
                if (text.includes('Close') || text.includes('×') || text.includes('✕')) {
                    btn.click(); break;
                }
            }
            document.querySelectorAll('[data-testid="modal"], [role="dialog"], .modal, [class*="modal"]')
                .forEach(m => { m.style.display='none'; m.remove(); });
            document.querySelectorAll('[data-testid="overlay"], [class*="overlay"]')
                .forEach(o => { o.style.display='none'; o.remove(); });
        """)
        await asyncio.sleep(2)

        await page.evaluate("""
            async function scrollToBottom() {
                for (let i = 0; i < 10; i++) {
                    window.scrollBy(0, 1000);
                    await new Promise(r => setTimeout(r, 1000));
                }
            }
            scrollToBottom();
        """)
        await asyncio.sleep(12)

        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)

        out_path = str(hotel_dir / "step1_booking.png")
        await page.save_screenshot(out_path, full_page=True)
        print(f"✅ Booking.com: {out_path}")
        browser.stop()

        return {"screenshot_paths": state["screenshot_paths"] + [out_path]}

    except Exception as e:
        print(f"❌ Node 2 lỗi: {e}")
        return {"errors": state["errors"] + [f"node_screenshot_booking: {e}"]}


# ─────────────────────────────────────────────
# NODE 1+2 MERGER: Gộp kết quả 2 screenshot
# Dùng sau khi cả 2 nhánh song song hoàn thành
# ─────────────────────────────────────────────

def node_merge_screenshots(state: HotelResearchState) -> HotelResearchState:
    """
    Không làm gì thêm — LangGraph tự merge state từ 2 nhánh.
    Node này chỉ là điểm hội tụ để tiếp tục pipeline.
    """
    print(f"\n🔀 [Merge] Screenshot paths: {len(state['screenshot_paths'])} ảnh")
    return state


# ─────────────────────────────────────────────
# NODE 3: OCR ảnh
# ─────────────────────────────────────────────

def node_ocr_images(state: HotelResearchState) -> HotelResearchState:
    print("\n🔍 [Node 3] OCR ảnh...")
    import easyocr
    import cv2

    hotel_dir = Path(state["hotel_dir"])
    image_paths = sorted(hotel_dir.glob("*.png")) + sorted(hotel_dir.glob("*.jpg"))

    if not image_paths:
        msg = "Không tìm thấy ảnh"
        print(f"⚠️ {msg}")
        return {"errors": state["errors"] + [f"node_ocr_images: {msg}"]}

    print(f"📁 {len(image_paths)} ảnh")
    reader = easyocr.Reader(['vi', 'en'], gpu=False)
    all_texts = []

    for img_path in image_paths:
        print(f"  🔍 OCR: {img_path.name}")
        img = cv2.imread(str(img_path))
        if img is None:
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
    output_file = hotel_dir / "competitors.txt"
    output_file.write_text("\n".join(unique_texts), encoding="utf-8")
    print(f"✅ {len(unique_texts)} texts → {output_file}")

    return {"ocr_raw_text": "\n".join(unique_texts)}


# ─────────────────────────────────────────────
# NODE 4: LLM clean tên hotel
# ─────────────────────────────────────────────

def node_llm_clean_hotels(state: HotelResearchState) -> HotelResearchState:
    print("\n🤖 [Node 4] LLM clean tên hotel...")
    hotel_dir = Path(state["hotel_dir"])
    raw_text = state["ocr_raw_text"] or (hotel_dir / "competitors.txt").read_text(encoding="utf-8")

    prompt = f"""Bạn là chuyên gia du lịch Đà Nẵng. Từ đoạn text OCR lộn xộn sau, hãy trích xuất CHÍNH XÁC tên các khách sạn, resort, homestay ở khu vực Sơn Trà/Đà Nẵng.

Yêu cầu:
- Chỉ trả về tên hotel, mỗi dòng 1 tên
- Loại bỏ: giá tiền, số sao, số reviews, tiện ích (WiFi, pool...), UI text
- Sửa lỗi OCR: "LBtusS" → "Lotus", "bv" → "by", v.v.
- Giữ nguyên tên thương hiệu: "Four Points by Sheraton", "InterContinental"

TEXT OCR:
{raw_text[:8000]}

OUTPUT (chỉ tên hotel, không giải thích):"""

    result = call_groq(prompt, max_tokens=2000)
    hotels = [h.strip() for h in result.splitlines() if h.strip()]

    output_file = hotel_dir / "competitors_clean.txt"
    output_file.write_text("\n".join(hotels), encoding="utf-8")
    print(f"✅ {len(hotels)} hotel → {output_file}")

    return {"competitors_clean": hotels}


# ─────────────────────────────────────────────
# NODE 5: Tìm website — PARALLEL với Semaphore(3)
# ─────────────────────────────────────────────

async def node_find_websites(state: HotelResearchState) -> HotelResearchState:
    print("\n🌐 [Node 5] Tìm website hotel (parallel 3)...")
    from ddgs import DDGS

    hotel_dir = Path(state["hotel_dir"])
    hotels = state["competitors_clean"] or (hotel_dir / "competitors_clean.txt").read_text(encoding="utf-8").splitlines()
    hotels = [h.strip() for h in hotels if h.strip()]

    sem = asyncio.Semaphore(3)

    async def find_one(name: str) -> dict:
        async with sem:
            try:
                # DDGS là sync → chạy trong executor để không block event loop
                loop = asyncio.get_event_loop()
                def _search():
                    ddgs = DDGS()
                    return list(ddgs.text(f"{name} official website Đà Nẵng", max_results=3))

                search_list = await loop.run_in_executor(None, _search)
                website = None
                for r in search_list:
                    url = r['href']
                    if any(x in url.lower() for x in ['booking.com', 'tripadvisor', 'agoda', 'expedia']):
                        continue
                    website = url
                    break

                print(f"  ✅ {name}: {website or 'Không tìm thấy'}")
                return {
                    "name": name,
                    "website": website,
                    "search_results": [r['href'] for r in search_list[:3]],
                }
            except Exception as e:
                print(f"  ❌ {name}: {e}")
                return {"name": name, "website": None, "search_results": []}

    results = await asyncio.gather(*[find_one(name) for name in hotels])

    output = hotel_dir / "competitors_with_website.json"
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    found = sum(1 for r in results if r["website"])
    print(f"✅ {found}/{len(results)} có website → {output}")

    return {"competitors_with_website": list(results)}


# ─────────────────────────────────────────────
# NODE 6: Crawl website — PARALLEL với Semaphore(3)
# ─────────────────────────────────────────────

async def node_crawl_websites(state: HotelResearchState) -> HotelResearchState:
    print("\n🕷️ [Node 6] Crawl website (parallel 3)...")
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
    from crawl4ai.content_filter_strategy import PruningContentFilter
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

    hotel_dir = Path(state["hotel_dir"])
    data = state["competitors_with_website"] or json.loads(
        (hotel_dir / "competitors_with_website.json").read_text(encoding="utf-8")
    )
    hotels_with_site = [h for h in data if h.get("website")]
    print(f"  Scrape {len(hotels_with_site)} website...")

    sem = asyncio.Semaphore(3)

    async def scrape_one(hotel: dict) -> dict:
        name, url = hotel["name"], hotel["website"]
        async with sem:
            try:
                browser_cfg = BrowserConfig(headless=True, extra_args=["--no-sandbox"])
                run_cfg = CrawlerRunConfig(
                    page_timeout=15000,
                    markdown_generator=DefaultMarkdownGenerator(
                        content_filter=PruningContentFilter(threshold=0.48)
                    ),
                )
                async with AsyncWebCrawler(config=browser_cfg) as crawler:
                    cr = await crawler.arun(url=url, config=run_cfg)
                    text = (
                        cr.markdown.fit_markdown
                        if hasattr(cr.markdown, "fit_markdown")
                        else str(cr.markdown)
                    )
                    success = bool(text and len(text) > 100)
                    status_icon = "✅" if success else "⚠️"
                    print(f"  {status_icon} {name}: {len(text or '')} chars | HTTP {cr.status_code}")
                    return {
                        "name": name, "url": url,
                        "content": text[:3000] if text else "Empty",
                        "status": cr.status_code,
                        "success": success,
                    }
            except Exception as e:
                print(f"  ❌ {name}: {str(e)[:80]}")
                return {"name": name, "url": url, "content": f"Error: {str(e)[:100]}", "status": 0, "success": False}

    scraped = await asyncio.gather(*[scrape_one(h) for h in hotels_with_site])

    output = hotel_dir / "competitors_scraped_all.json"
    output.write_text(json.dumps(scraped, indent=2, ensure_ascii=False), encoding="utf-8")
    ok = sum(1 for s in scraped if s["success"])
    print(f"✅ {ok}/{len(scraped)} thành công → {output}")

    return {"competitors_scraped": list(scraped)}


# ─────────────────────────────────────────────
# NODE 7: LLM phân tích đối thủ
# ─────────────────────────────────────────────

def node_analyze_competitors(state: HotelResearchState) -> HotelResearchState:
    print("\n📊 [Node 7] Phân tích đối thủ...")
    hotel_dir = Path(state["hotel_dir"])
    scraped = state["competitors_scraped"] or json.loads(
        (hotel_dir / "competitors_scraped_all.json").read_text(encoding="utf-8")
    )

    content_summary = ""
    for h in scraped[:10]:
        if h["success"]:
            content_summary += f"\n\n### {h['name']} ({h['url']})\n{h['content'][:500]}"

    prompt = f"""Bạn là Marketing Analyst của Sontra Sea Hotel (3 sao, Sơn Trà, Đà Nẵng).
Phân tích dữ liệu đối thủ dưới đây và tạo báo cáo gồm:

1. PHÂN LOẠI ĐỐI THỦ (Direct / Indirect)
2. ĐỐI THỦ CHÍNH (Direct): Mỗi đối thủ:
   - Điểm mạnh / Điểm yếu / Giá ước tính / Khách hàng mục tiêu
3. CHIẾN LƯỢC ĐỀ XUẤT: 3-5 hành động cụ thể cho Sontra Sea Hotel

KHÔNG dùng JSON. Viết dạng bullet point.

DỮ LIỆU:{content_summary[:4000]}"""

    result = call_groq(prompt, max_tokens=4000)
    output_file = hotel_dir / "competitor_analysis.txt"
    output_file.write_text(result, encoding="utf-8")
    print(f"✅ Phân tích xong → {output_file}")

    return {"competitor_analysis": result}


# ─────────────────────────────────────────────
# NODE 8: Thu thập social data
# ─────────────────────────────────────────────

def node_collect_social_data(state: HotelResearchState) -> HotelResearchState:
    print("\n📈 [Node 8] Google Trends + Reddit...")
    hotel_dir = Path(state["hotel_dir"])
    sources = []

    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='vi-VN', tz=360)
        keywords = ["khách sạn giá rẻ Đà Nẵng", "hotel Sơn Trà", "du lịch Đà Nẵng bình dân"]
        pytrends.build_payload(keywords, timeframe='today 12-m', geo='VN')
        pytrends.interest_over_time().to_csv(hotel_dir / "google_trends.csv")
        print("✅ Google Trends OK")
        sources.append("Google Trends")
    except Exception as e:
        print(f"⚠️ Google Trends: {e}")

    try:
        import praw
        reddit = praw.Reddit(
            client_id="YOUR_CLIENT_ID",
            client_secret="YOUR_SECRET",
            user_agent="hotel_research_bot",
        )
        reddit_posts = []
        for sub in ["VietNam", "travel", "solotravel", "Shoestring"]:
            for post in reddit.subreddit(sub).search("Da Nang hotel", limit=10):
                reddit_posts.append({
                    "title": post.title,
                    "text": post.selftext[:500],
                    "score": post.score,
                    "comments": post.num_comments,
                })
        (hotel_dir / "reddit_posts.json").write_text(
            json.dumps(reddit_posts, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"✅ Reddit: {len(reddit_posts)} posts")
        sources.append("Reddit")
    except Exception as e:
        print(f"⚠️ Reddit: {e}")

    return {"social_sources": sources}


# ─────────────────────────────────────────────
# NODE 9: Scrape TikTok HTML — giảm scroll 5→3
# ─────────────────────────────────────────────

async def node_scrape_tiktok_html(state: HotelResearchState) -> HotelResearchState:
    print("\n📱 [Node 9] Lấy HTML TikTok...")
    hotel_dir = Path(state["hotel_dir"])

    try:
        import nodriver as uc
        browser = await uc.start(headless=False)
        page = await browser.get("https://www.tiktok.com/search?q=review%20khách%20sạn%20Đà%20Nẵng")
        await asyncio.sleep(8)  # giảm 10→8s

        for _ in range(3):  # giảm 5→3 lần scroll
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(1.5)  # giảm 2→1.5s

        html = await page.evaluate("document.documentElement.outerHTML")
        out_path = hotel_dir / "tiktok_full_html.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"✅ HTML: {len(html)} ký tự → {out_path}")
        browser.stop()

        return {"tiktok_html_path": str(out_path)}

    except Exception as e:
        print(f"❌ Node 9 lỗi: {e}")
        return {"errors": state["errors"] + [f"node_scrape_tiktok_html: {e}"]}


# ─────────────────────────────────────────────
# NODE 10: Extract TikTok content
# ─────────────────────────────────────────────

def node_extract_tiktok_content(state: HotelResearchState) -> HotelResearchState:
    print("\n🔤 [Node 10] Extract TikTok content...")
    from trafilatura import extract

    hotel_dir = Path(state["hotel_dir"])
    html_path = state["tiktok_html_path"] or str(hotel_dir / "tiktok_full_html.html")

    try:
        html = Path(html_path).read_text(encoding="utf-8")
        text = extract(html, output_format="json", include_comments=True, include_tables=False, deduplicate=True)
        text_str = str(text) if text else "{}"

        out_path = hotel_dir / "tiktok_trafilatura.json"
        out_path.write_text(text_str, encoding="utf-8")
        print(f"✅ {len(text_str)} ký tự → {out_path}")

        return {"tiktok_content": text_str}

    except Exception as e:
        print(f"❌ Node 10 lỗi: {e}")
        return {"errors": state["errors"] + [f"node_extract_tiktok_content: {e}"]}


# ─────────────────────────────────────────────
# NODE 11: Scrape TikTok comments — PARALLEL 3 video
# ─────────────────────────────────────────────

async def node_scrape_tiktok_comments(state: HotelResearchState) -> HotelResearchState:
    print("\n💬 [Node 11] Scrape TikTok comments (parallel 3 video)...")
    hotel_dir = Path(state["hotel_dir"])
    html_path = state["tiktok_html_path"] or str(hotel_dir / "tiktok_full_html.html")

    try:
        import nodriver as uc

        html = Path(html_path).read_text(encoding="utf-8")
        video_links = list(set(re.findall(r'https://www\.tiktok\.com/@[\w.]+/video/\d+', html)))[:3]
        print(f"  {len(video_links)} video links")

        if not video_links:
            return {"tiktok_comment_html_paths": []}

        sem = asyncio.Semaphore(3)

        async def scrape_video(idx: int, link: str) -> str | None:
            async with sem:
                try:
                    browser = await uc.start(headless=False)
                    video_page = await browser.get(link)
                    await asyncio.sleep(4)  # giảm 5→4s

                    try:
                        comments_tab = await video_page.find("Comments", best_match=True)
                        await comments_tab.click()
                        await asyncio.sleep(2)
                    except Exception:
                        pass

                    for _ in range(3):  # giảm 5→3 lần
                        await video_page.evaluate("window.scrollBy(0, 800)")
                        await asyncio.sleep(1.5)

                    video_html = await video_page.evaluate("document.documentElement.outerHTML")
                    out_path = hotel_dir / f"tiktok_video_{idx}_comments.html"
                    out_path.write_text(video_html, encoding="utf-8")
                    print(f"  ✅ Video {idx}: {len(video_html)} chars → {out_path}")

                    await video_page.save_screenshot(str(hotel_dir / f"tiktok_video_{idx}.png"))
                    browser.stop()
                    return str(out_path)

                except Exception as e:
                    print(f"  ❌ Video {idx}: {e}")
                    return None

        results = await asyncio.gather(*[scrape_video(i + 1, link) for i, link in enumerate(video_links)])
        saved_paths = [p for p in results if p]

        return {"tiktok_comment_html_paths": saved_paths}

    except Exception as e:
        print(f"❌ Node 11 lỗi: {e}")
        return {"errors": state["errors"] + [f"node_scrape_tiktok_comments: {e}"]}


# ─────────────────────────────────────────────
# NODE 12: Parse TikTok comments
# ─────────────────────────────────────────────

def node_parse_tiktok_comments(state: HotelResearchState) -> HotelResearchState:
    print("\n🔎 [Node 12] Parse TikTok comments...")
    from bs4 import BeautifulSoup

    hotel_dir = Path(state["hotel_dir"])
    html_paths = state["tiktok_comment_html_paths"] or [
        str(p) for p in sorted(hotel_dir.glob("tiktok_video_*_comments.html"))
    ]

    all_comments = []
    keywords = ["khách sạn", "hotel", "đà nẵng", "phòng", "giá", "view", "biển", "sơn trà", "có", "không", "xin", "ib"]

    for i, html_path in enumerate(html_paths, 1):
        path = Path(html_path)
        if not path.exists():
            continue

        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        comments = []

        for container in soup.find_all("div", class_=re.compile(r"DivCommentContentWrapper|comment-content")):
            username_tag = container.find("p", class_=re.compile(r"TUXText.*weight-medium"))
            if not username_tag:
                username_tag = container.find("a", href=re.compile(r"/@"))
            username = username_tag.get_text(strip=True) if username_tag else "unknown"

            text = ""
            for tag in container.find_all("p", class_=re.compile(r"TUXText")):
                tag_text = tag.get_text(strip=True)
                if tag_text != username and len(tag_text) > 5:
                    text = tag_text
                    break

            if not text:
                for span in container.find_all("span"):
                    span_text = span.get_text(strip=True)
                    if len(span_text) > 10 and span_text != username:
                        text = span_text
                        break

            if username and text and len(text) > 10:
                if any(k in text.lower() for k in keywords):
                    comments.append({"video": i, "username": username, "text": text, "source": "tiktok_comment"})

        print(f"  Video {i}: {len(comments)} comments")
        all_comments.extend(comments)

    seen, unique = set(), []
    for c in all_comments:
        key = c["username"] + c["text"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(c)

    out_path = hotel_dir / "tiktok_comments_with_user.json"
    out_path.write_text(json.dumps(unique, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ {len(unique)} unique comments → {out_path}")

    return {"tiktok_comments": unique}


# ─────────────────────────────────────────────
# NODE 13: Final strategy report
# ─────────────────────────────────────────────

def node_final_strategy_report(state: HotelResearchState) -> HotelResearchState:
    print("\n📝 [Node 13] Tạo báo cáo chiến lược cuối...")
    hotel_dir = Path(state["hotel_dir"])

    competitors = "\n".join(state["competitors_clean"]) if state["competitors_clean"] else \
        (hotel_dir / "competitors_clean.txt").read_text(encoding="utf-8")

    analysis = state["competitor_analysis"] or \
        (hotel_dir / "competitor_analysis.txt").read_text(encoding="utf-8")

    tiktok = state["tiktok_comments"]
    if not tiktok:
        tiktok_path = hotel_dir / "tiktok_comments_with_user.json"
        tiktok = json.loads(tiktok_path.read_text(encoding="utf-8")) if tiktok_path.exists() else []

    comments_text = "\n".join([f"@{c['username']}: {c['text'][:100]}" for c in tiktok[:30]])

    prompt = f"""Bạn là Giám đốc Marketing khách sạn Sontra Sea Hotel (3 sao, view biển Sơn Trà, 41 Hoàng Sa, Đà Nẵng).

DỮ LIỆU ĐÃ THU THẬP:
1. ĐỐI THỦ CHÍNH:\n{competitors[:1500]}
2. PHÂN TÍCH ĐỐI THỦ:\n{analysis[:2000]}
3. KHÁCH HÀNG THẬT (TikTok):\n{comments_text[:2500]}

YÊU CẦU:
A. CUSTOMER PERSONAS (3-5 personas): Tên, Demographics, Pain points, Motivations, Kênh tiếp cận
B. CHIẾN LƯỢC TIẾP CẬN TỪNG PERSONA: Message, Offer, Kênh quảng cáo, Content format
C. ĐỀ XUẤT CHIẾN DỊCH 30 NGÀY: Tuần 1-2 Awareness, Tuần 3-4 Conversion

OUTPUT: Tiếng Việt, bullet point."""

    result = call_groq(prompt, max_tokens=4000)

    out_path = hotel_dir / "final_strategy_report.txt"
    out_path.write_text(result, encoding="utf-8")
    print(f"✅ Báo cáo → {out_path}")

    return {"final_report": result}