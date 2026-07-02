import asyncio
import random
import re
import time
import traceback
from datetime import datetime
from urllib.parse import quote
from typing import Optional
import  asyncio, re, logging
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from .models import (
    FbPhoto,
    PipelineTask,
    PipelineEvent,
    ResearchResult,
    FbPost,
    FbComment,
    ResearchState,
    safe_get,
    SUGGESTIONS_TAGGED_SCHEMA,
    SERP_DATA_SCHEMA,
    FB_BRAND_SCHEMA,
    default_suggestions_tagged,
)
import nodriver as uc
logger = logging.getLogger(__name__)

HAS_NODRIVER = uc is not None
UC_BROWSER = None

# Cấu hình Async HTTP Client chuyên dụng cho Node 1
ASYNC_HTTP_CLIENT = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=30, max_keepalive_connections=10),
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
        "Accept": "application/json, text/javascript, */*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
    },
    timeout=httpx.Timeout(3.0)
)

# ═══════════════════════════════════════════════════════════════════════
# DB HELPERS 
# ═══════════════════════════════════════════════════════════════════════
async def _upsert_task(db: AsyncSession, state: ResearchState):
    task = (
        await db.execute(
            select(PipelineTask)
            .where(PipelineTask.business_id == state.business_id)
        )
    ).scalar_one_or_none()

    if not task:
        task = PipelineTask(business_id=state.business_id)
        db.add(task)

    task.business_name = state.business_name
    task.query = state.query
    task.fb_url = state.fb_url
    task.status = state.status
    task.error = state.error
    task.updated_at = datetime.now()


async def _replace_events(db: AsyncSession, state: ResearchState):
    await db.execute(
        delete(PipelineEvent)
        .where(PipelineEvent.business_id == state.business_id)
    )

    db.add_all([
        PipelineEvent(
            business_id=state.business_id,
            seq=e["seq"],
            node_name=e["node"],
            payload=e["payload"],
        )
        for e in state.events
    ])


async def _upsert_result(db: AsyncSession, state: ResearchState):
    result = (
        await db.execute(
            select(ResearchResult)
            .where(ResearchResult.business_id == state.business_id)
        )
    ).scalar_one_or_none()

    if not result:
        result = ResearchResult(
            business_id=state.business_id
        )
        db.add(result)

    result.business_name = state.business_name
    result.suggestions_raw = state.suggestions
    result.suggestions_tagged = safe_get(
        state.tagged_suggestions,
        SUGGESTIONS_TAGGED_SCHEMA,
    )
    result.serp_data = safe_get(
        state.serp_data,
        SERP_DATA_SCHEMA,
    )
    result.fb_brand = safe_get(
        state.fb_data["brand"],
        FB_BRAND_SCHEMA,
    )
    result.final_report = state.report.get("text")
    result.updated_at = datetime.now()


async def _replace_fb_posts_comments(
    db: AsyncSession,
    state: ResearchState,
):
    await db.execute(
        delete(FbPost)
        .where(FbPost.business_id == state.business_id)
    )

    await db.execute(
        delete(FbComment)
        .where(FbComment.business_id == state.business_id)
    )

    attachments_map = state.fb_data.get("attachments_map", [])
    db.add_all([
        FbPost(
            business_id=state.business_id,
            content=p,
            attachments=attachments_map[i] if i < len(attachments_map) else [],
        )
        for i, p in enumerate(state.fb_data["posts"])
    ])

    db.add_all([
        FbComment(
            business_id=state.business_id,
            author=c.get("author"),
            time=c.get("time"),
            comment=c.get("comment"),
            replies=c.get("replies", []),
        )
        for c in state.fb_data["comments"]
    ])

async def _replace_fb_photos(db: AsyncSession, state: ResearchState):
    """Xóa cũ + ghi mới ảnh từ tab Photos và attachments."""
    
    await db.execute(
        delete(FbPhoto).where(FbPhoto.business_id == state.business_id)
    )

    # Ảnh từ tab Photos
    photo_urls = state.fb_data.get("photos", []) or []
    db.add_all([
        FbPhoto(
            business_id=state.business_id,
            url=url,
            source="tab",
        )
        for url in photo_urls if isinstance(url, str)
    ])

    # Ảnh từ attachments của posts (optional)
    attachments_map = state.fb_data.get("attachments_map", [])
    for i, attachments in enumerate(attachments_map):
        if attachments:
            db.add_all([
                FbPhoto(
                    business_id=state.business_id,
                    url=url,
                    source="post",
                    post_index=i,
                )
                for url in attachments if isinstance(url, str)
            ])


async def save_after_node(db: AsyncSession, state: ResearchState):
    await _upsert_task(db, state)
    await _replace_events(db, state)
    await _upsert_result(db, state)
    await _replace_fb_posts_comments(db, state)
    await _replace_fb_photos(db, state) 
    await db.commit()




# ═══════════════════════════════════════════════════════════════════════
# NODE 1: GOOGLE SUGGESTIONS (Concurrent Async)
# ═══════════════════════════════════════════════════════════════════════

async def _get_suggestions_async(query: str) -> list:
    url = "https://suggestqueries.google.com/complete/search"
    params = {"client": "firefox", "hl": "vi", "q": query}
    try:
        response = await ASYNC_HTTP_CLIENT.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) >= 2:
                suggestions = data[1]
                if isinstance(suggestions, list):
                    return [s for s in suggestions if s != query and len(s) > 3]
    except Exception:
        pass
    return []


async def _expand_query_async(query: str) -> list:
    all_results = set()
    
    target_queries = [query]
    target_queries.extend([f"{query} {char}" for char in ["a", "g", "n", "r", "t"]])
    target_queries.extend([f"{query} {num}" for num in ["1", "3", "5"]])
    target_queries.extend([f"{query} {word}" for word in ["giá", "gần", "ở", "cho", "review", "nào", "ngon", "rẻ", "đẹp"]])

    print(f"🔍 [Node 1] Đang cào đồng thời {len(target_queries)} nhánh gợi ý...")
    tasks = [_get_suggestions_async(q) for q in target_queries]
    outputs = await asyncio.gather(*tasks)
    
    for suggs in outputs:
        all_results.update(suggs)
        
    return list(all_results)


def _simple_intent_tag(queries: list) -> dict:
    tags = {
        "budget": ["giá", "rẻ", "tiết kiệm", "bao nhiêu", "chi phí"],
        "location": ["gần", "ở", "tại", "đường", "khu"],
        "food": ["hải sản", "món", "ăn", "nhậu", "buffet", "nướng"],
        "experience": ["review", "trải nghiệm", "ngon", "đẹp", "view"],
        "family": ["gia đình", "nhóm", "đoàn", "nhiều người"],
        "question": ["?", "là gì", "ở đâu", "có nên", "nào"],
    }
    result = default_suggestions_tagged()
    for q in queries:
        q_lower = q.lower()
        matched = False
        for tag, keywords in tags.items():
            if any(kw in q_lower for kw in keywords):
                result[tag].append(q)
                matched = True
                break
        if not matched:
            result["other"].append(q)
    return result


async def node_suggest(state: ResearchState, seq: list):
    print("\n" + "=" * 60)
    print("NODE 1: GOOGLE SUGGESTIONS")
    print("=" * 60)

    state.status = "running"
    seq[0] += 1
    state.add_event(seq[0], "suggest", {"status": "started", "query": state.query})

    state.suggestions = await _expand_query_async(state.query)
    state.tagged_suggestions = _simple_intent_tag(state.suggestions)

    seq[0] += 1
    state.add_event(seq[0], "suggest", {"status": "done", "total": len(state.suggestions)})
    print(f"🎉 Hoàn tất Node 1: {len(state.suggestions)} suggestions")


# ═══════════════════════════════════════════════════════════════════════
# NODE 2: SERP SCRAPER (Giữ vững Session)
# ═══════════════════════════════════════════════════════════════════════

def _clean_serp_text(text: str):
    if not text:
        return None
    text = " ".join(text.split())
    BAD = [
        "facebook", "tripadvisor", "đăng nhập", "chính sách",
        "hỗ trợ", "video", "youtube", "maps", "translate",
        "google", "javascript", "cookie",
    ]
    if len(text) < 5 or len(text) > 160 or any(x in text.lower() for x in BAD):
        return None
    return text


def _is_valid_url(url: str):
    if not url or not url.startswith("http"):
        return False
    BAD_URL = ["google.com/search", "googleusercontent", "webcache", "/settings", "accounts.google"]
    return not any(x in url for x in BAD_URL)


def _parse_serp(soup: BeautifulSoup, query: str) -> dict:
    top_urls = []
    seen = set()
    for a in soup.select("a"):
        h3 = a.select_one("h3")
        if not h3:
            continue
        url = a.get("href")
        title = _clean_serp_text(h3.get_text(" ", strip=True))
        if not title or not _is_valid_url(url):
            continue
        key = url.split("#")[0]
        if key in seen:
            continue
        seen.add(key)
        domain = url.split("/")[2] if "://" in url else ""
        top_urls.append({
            "position": len(top_urls) + 1, "title": title, "url": url,
            "domain": domain, "type": "organic",
        })

    paa = []
    for el in soup.select('div[jsname="N760b"]'):
        q = _clean_serp_text(el.get_text(" ", strip=True))
        if q and "?" in q:
            paa.append({"question": q, "intent": "expansion"})

    related = []
    for a in soup.select("a"):
        text = _clean_serp_text(a.get_text(" ", strip=True))
        if text and any(k in text.lower() for k in ["quán", "hải sản", "đà nẵng"]) and len(text.split()) <= 10:
            related.append(text)
    related = list(dict.fromkeys(related))[:10]

    snippets = []
    for block in soup.select("div.g"):
        snippet_el = block.select_one("span")
        if snippet_el:
            text = _clean_serp_text(snippet_el.get_text(" ", strip=True))
            if text and 60 < len(text) < 300:
                snippets.append({"snippet": text[:200]})

    return {
        "top_urls": top_urls[:10],
        "people_also_ask": paa[:5],
        "related_searches": related,
        "snippets": snippets[:5],
        "keyword_cluster": [
            "quán hải sản ngon Đà Nẵng", "hải sản giá rẻ", "gần biển Mỹ Khê",
            "Sơn Trà", "quán nhậu Đà Nẵng", "buffet hải sản",
        ],
        "content_angle": ["review", "top list", "trải nghiệm", "giá rẻ", "du lịch ăn uống"],
        "intent": ["ăn nhậu", "du lịch", "gia đình", "buffet", "hải sản tươi sống"],
        "competitor_pattern": [
            "Pasgo", "Tripadvisor", "Blog du lịch SEO", "Facebook group", "Local listing / directory",
        ],
    }

def _extract_intro_section(clean_text: str) -> str:
    """
    Trích xuất đúng khối "Intro" (giới thiệu + địa chỉ + liên hệ) của Fanpage,
    neo vào mốc cấu trúc cố định của Facebook thay vì cắt cứng theo ký tự
    (tránh vừa thiếu vừa lẫn nội dung post/comment không liên quan).
    """
    start_match = re.search(r'\b(?:Intro|Giới thiệu)\b', clean_text)
    start = start_match.end() if start_match else 0

    end_match = re.search(r'Shared with Public|Công khai', clean_text[start:])
    end = start + end_match.start() if end_match else start + 1500  # fallback an toàn

    section = clean_text[start:end].strip()
    return section if section else clean_text[:1500].strip()


async def lay_20_anh_tu_tab_photos(fb_tab):
    """
    Click vào tab "Photos" của page, kéo xuống 2 lần,
    rồi lấy 20 ảnh đầu tiên (src chứa 'scontent').
    """

    print("📷 Tìm tab Photos...")

    try:
        clicked = await fb_tab.evaluate(
            """
            (() => {
                const links = Array.from(
                    document.querySelectorAll("a")
                );

                const target = links.find((a) => {
                    const t = (a.innerText || "").trim();

                    return (
                        t === "Photos" ||
                        t === "Ảnh" ||
                        t === "Hình ảnh" ||
                        (
                            a.href &&
                            a.href.includes("/photos")
                        )
                    );
                });

                if (target) {
                    target.click();
                    return true;
                }

                return false;
            })();
            """
        )
    except Exception as e:
        print("Lỗi khi tìm tab Photos:", e)
        clicked = False

    if not clicked:
        print("❌ Không tìm thấy tab Photos.")
        return []

    print("✅ Đã click tab Photos. Đợi tải...")

    await asyncio.sleep(random.uniform(1.8, 2.6))

    print("📜 Kéo xuống 2 lần để load thêm ảnh...")

    for round_idx in range(2):
        print(f"🔄 Scroll round {round_idx + 1}/2")

        try:
            await fb_tab.evaluate(
                """
                window.scrollBy(0, 3000);
                """
            )
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.5, 2.5))

    print("🖼️ Thu thập danh sách ảnh...")

    try:
        urls = await fb_tab.evaluate(
            """
            (() => {
                const imgs = Array.from(
                    document.querySelectorAll("img")
                );

                const srcs = imgs
                    .map((img) => img.src)
                    .filter(
                        (src) =>
                            src &&
                            src.includes("scontent")
                    );

                return Array.from(
                    new Set(srcs)
                ).slice(0, 20);
            })();
            """
        )
    except Exception as e:
        print("Lỗi khi lấy ảnh:", e)
        urls = []

    urls = urls or []


    print(f"✅ Lấy được {len(urls)} ảnh.")

    return urls


async def node_serp(state: ResearchState, seq: list, headless: bool):
    print("\n" + "=" * 60)
    print("NODE 2: SERP SCRAPER")
    print("=" * 60)

    seq[0] += 1
    state.add_event(seq[0], "serp", {"status": "started", "query": state.query})

    if not HAS_NODRIVER:
        print("⚠️  nodriver chưa cài. Bỏ qua node SERP.")
        return

    global UC_BROWSER
    if UC_BROWSER is None:
        print("🚀 Khởi tạo trình duyệt dùng chung...")
        UC_BROWSER = await uc.start(headless=headless, icon_mode=1)

    try:
        page = await UC_BROWSER.get(f"https://www.google.com/search?q={quote(state.query)}&hl=vi")
        await asyncio.sleep(1.5)
        soup = BeautifulSoup(await page.get_content(), "html.parser")

        state.serp_data = _parse_serp(soup, state.query)
        print(f"  ✅ Top URLs: {len(state.serp_data['top_urls'])}")

        seq[0] += 1
        state.add_event(seq[0], "serp", {
            "status": "done",
            "top_urls": len(state.serp_data["top_urls"]),
        })

    except Exception as e:
        state.error = f"node_serp: {e}"
        seq[0] += 1
        state.add_event(seq[0], "serp", {"status": "error", "error": str(e)})
        print(f"  ❌ Error Node 2: {e}")


# ═══════════════════════════════════════════════════════════════════════
# NODE 3: FACEBOOK SCRAPER (Tối ưu Anti-bot & Expand Selector)
# ═══════════════════════════════════════════════════════════════════════

def _clean_fb_text(text: str) -> str:
    if not text:
        return ""
    try:
        return text.encode("latin1").decode("utf-8")
    except Exception:
        return text


# ── THÊM MỚI: 4 hàm dưới đây, đặt ngay tại đây ──────────────────────────

PHONE_PATTERN = r'(?:\+84\s?)?(?:0\d{2,3}[\s.-]?\d{3}[\s.-]?\d{3,4})'

def _guess_city(address: str) -> str:
    city_map = {
        "đà nẵng": "Đà Nẵng", "da nang": "Đà Nẵng",
        "nha trang": "Nha Trang",
        "hồ chí minh": "Hồ Chí Minh", "ho chi minh": "Hồ Chí Minh", "hcm": "Hồ Chí Minh",
        "hà nội": "Hà Nội", "ha noi": "Hà Nội",
    }
    low = address.lower()
    return next((v for k, v in city_map.items() if k in low), "")


def _extract_locations_multi(intro_text: str, global_phones: list) -> list:
    """Hỗ trợ cả 2 format: (A) đa chi nhánh có emoji 📍, (B) 1 chi nhánh neo 'Vietnam'."""
    locations = []

    if "📍" in intro_text:
        blocks = re.findall(r"📍(.*?)(?=📍|\Z)", intro_text, re.DOTALL)
        for block in blocks:
            parts = re.split(r'Hotline[^:]*:', block, maxsplit=1, flags=re.IGNORECASE)
            address_raw = parts[0].strip()
            address_clean = re.sub(
                r'^\s*(?:Cơ sở|Địa chỉ|CS)\s*\d*\s*:?\s*', '', address_raw, flags=re.IGNORECASE
            ).strip().rstrip(' -–—')

            if len(address_clean) < 8:
                continue

            hotline = ""
            if len(parts) > 1:
                phone_matches = re.findall(PHONE_PATTERN, parts[1])
                hotline = " – ".join(re.sub(r'[\s.-]', '', p) for p in phone_matches)

            locations.append({
                "address": address_clean,
                "city": _guess_city(address_clean),
                "hotline": hotline or (global_phones[0] if global_phones and len(locations) == 0 else "")
            })

        if locations:
            return locations

    candidates = [
        seg.strip() for seg in re.split(r'\n', intro_text)
        if re.search(r'\bvietnam\b', seg, re.IGNORECASE)
    ]
    if candidates:
        best = max(candidates, key=lambda l: l.count(','))
        if best.count(',') >= 2:
            address_clean = re.sub(r',\s*vietnam\s*$', '', best, flags=re.IGNORECASE).strip()
            locations.append({
                "address": address_clean,
                "city": _guess_city(address_clean),
                "hotline": global_phones[0] if global_phones else ""
            })

    return locations

def _extract_hours(intro_text: str) -> str:
    m = re.search(
        r'(?:⏰|⏳)\s*(?:Giờ mở cửa|Giờ phục vụ|Opening hours)?:\s*(.+?)(?=📍|\n|\Z)',
        intro_text, re.IGNORECASE
    )
    if not m:
        return ""

    hours = m.group(1).strip()

    # ✅ FIX: nếu dòng ngay sau là ghi chú bổ sung dạng "(...)" (VD: giờ order
    # cuối), nối tiếp vào — tránh mất thông tin quan trọng khi giờ mở cửa và
    # ghi chú nằm trên 2 dòng riêng.
    remainder = intro_text[m.end():]
    note_match = re.match(r'\s*\n\s*(\([^\n]*\))', remainder)
    if note_match:
        hours += " " + note_match.group(1).strip()

    return hours


def build_business_facts(intro_text: str, phones: list, emails: list) -> dict:
    locations = _extract_locations_multi(intro_text, phones)
    hours = _extract_hours(intro_text)

    if not locations:
        logger.error(
            f"[build_business_facts] KHÔNG trích xuất được địa chỉ nào — cần review thủ công. "
            f"intro preview: {intro_text[:200]!r}"
        )

    return {
        "locations": locations,
        "hours": hours,
        "phones": phones,
        "emails": emails,
        "_needs_manual_review": len(locations) == 0,
    }


def _extract_brand_info(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    raw_text = soup.get_text("\n", strip=True)
    clean_lines = [l.strip() for l in raw_text.split("\n") if l.strip() and not re.fullmatch(r"\d+", l.strip())]
    clean_text = "\n".join(clean_lines)

    page_info = {"title": soup.find("title").get_text(strip=True) if soup.find("title") else "", "followers": "", "following": ""}
    m = re.search(r'([\d.,]+\s*[KMB]?)\s+(?:followers|người theo dõi)', clean_text, re.IGNORECASE)
    if m: page_info["followers"] = m.group(1).strip()

    h1_tag = soup.find("h1")
    page_name = ""
    if h1_tag:
        page_name = h1_tag.get_text(strip=True)
        page_name = page_name.replace("\xa0", " ").strip()  # bỏ &nbsp; còn sót
    page_info["page_name"] = page_name

    intro_section = _extract_intro_section(clean_text)
    phones = set(re.sub(r"[\s.-]", "", p) for p in re.findall(PHONE_PATTERN, clean_text))
    emails = sorted(set(re.findall(r'[\w.-]+@[\w.-]+\.\w+', clean_text)))
    domains = sorted(set(d for d in re.findall(r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,6}\b', clean_text.lower()) if not d.endswith(("js", "css", "png", "jpg", "jpeg", "gif", "ico"))))

    og_image = ""
    og_tag = soup.find("meta", property="og:image")
    if og_tag:
        og_image = og_tag.get("content", "")

    posts = [c.strip() for c in re.split(r'Shared with Public|Công khai', clean_text) if len(c.strip()) > 150][:10]

    phones_sorted = sorted(list(phones))
    business_facts = build_business_facts(intro_section, phones_sorted, emails)   # ← THÊM DÒNG NÀY

    return {
        "page_info": page_info,
        "intro": intro_section,
        "phones": phones_sorted,
        "emails": emails,
        "domains": domains,
        "og_image": og_image,
        "posts_from_text": posts,
        "business_facts": business_facts,   # ← THÊM KEY NÀY
    }

def _extract_posts_comments(html: str) -> tuple:
    soup = BeautifulSoup(html, "html.parser")

    _SKIP_PATTERNS = [
        "/p40x40/", "/s40x40/", "/p50x50/", "/s50x50/",
        "profile", "avatar", "emoji", "rsrc.php", "static.xx.fbcdn",
    ]

    # ── Extract post contents ──
    post_contents = [
        _clean_fb_text(div.get_text(separator="\n", strip=True))
        for div in soup.find_all("div", attrs={"data-ad-preview": "message"})
    ]

    if not post_contents:
        for text_div in soup.find_all("div", class_="xdj266r"):
            if len(text_div.get_text()) > 100:
                cleaned = _clean_fb_text(text_div.get_text(strip=True))
                if cleaned and cleaned not in post_contents:
                    post_contents.append(cleaned)

    # ── Extract tất cả ảnh thật từ toàn bộ HTML ──
    all_imgs = []
    seen_imgs = set()
    for img in soup.find_all("img", src=True):
        src = img.get("src", "")
        if not src or src in seen_imgs:
            continue
        if "scontent" in src and "fbcdn.net" in src:
            if not any(p in src for p in _SKIP_PATTERNS):
                all_imgs.append(src)
                seen_imgs.add(src)

    # Gán ảnh vào từng post theo vị trí data-visualcompletion block
    # Vì FB tách ảnh ra div riêng, không nằm trong post block
    # → chia đều: mỗi post lấy tối đa 5 ảnh theo thứ tự
    n_posts = len(post_contents)
    attachments_map = [[] for _ in range(max(n_posts, 1))]

    if all_imgs and n_posts > 0:
        chunk_size = max(1, len(all_imgs) // n_posts)
        for i in range(n_posts):
            start = i * chunk_size
            end = start + chunk_size if i < n_posts - 1 else len(all_imgs)
            attachments_map[i] = all_imgs[start:end][:5]

    # ── Extract comments ──
    comments_list = []
    for block in soup.find_all("div", attrs={"role": "article"}):
        aria_label = block.get("aria-label", "")
        author_name, comment_time = "Ẩn danh", "Không rõ"
        if "Comment by" in aria_label:
            match = re.search(
                r'(.+?)\s(\d+\s\w+\sago|\d+\w+)',
                aria_label.replace("Comment by ", "")
            )
            if match:
                author_name, comment_time = match.group(1), match.group(2)

        container = (
            block.find("div", attrs={"dir": "auto"})
            or block.find("div", class_="xdj266r")
        )
        comment_text = _clean_fb_text(container.get_text(strip=True)) if container else ""

        replies = []
        if block.find_parent() and block.find_parent().find_next_sibling():
            reply_text = _clean_fb_text(
                block.find_parent().find_next_sibling().get_text(separator=" ", strip=True)
            )
            if reply_text:
                replies.append(reply_text)

        if comment_text or author_name != "Ẩn danh":
            comments_list.append({
                "author": author_name,
                "time": comment_time,
                "comment": comment_text,
                "replies": replies,
            })

    return post_contents, comments_list, attachments_map



async def _scrape_facebook(browser, fb_url: str, business_id: str):
    target_url = fb_url.strip().lower() + ("/" if not fb_url.strip().endswith("/") else "")
    clean_search_url = f'"{target_url}"'
    search_query = f"site:{target_url.replace('https://', '').replace('http://', '').replace('www.', '')}"
    print(search_query)
    # Dùng hàm get trực tiếp trên browser dùng chung (không close tab bậy bạ)
    page = await browser.get(f"https://www.google.com/search?q={search_query}")
    await asyncio.sleep(1.5)

    links = await page.select_all("a:has(h3)")
    matched_href, click_target = None, None
    for link in links:
        try:
            href = link["href"] if "href" in link.attrs else None
            if href and clean_search_url in f'"{href.strip().lower()}"':
                matched_href = href.strip()
                click_target = link
                break
        except Exception: 
            pass

    if not matched_href or not click_target:
        return None, None

    await asyncio.sleep(random.uniform(0.4, 0.8))
    try: 
        await click_target.scroll_into_view()
    except Exception: 
        pass

    print(f"🖱️ [HÀNH ĐỘNG] Click kết quả tìm kiếm: {matched_href}")
    await click_target.click()
    
    # Ép giãn cách 3s để nhận đúng Referer nguồn từ Google chuyển qua
    await asyncio.sleep(4.0)

    fb_tab = None
    for tab in browser.tabs:
        try:
            url = str(tab.url).lower()
            if "facebook.com" in url and url != "about:blank" and url != "":
                fb_tab = tab
                break
        except Exception: 
            pass

    if not fb_tab:
        fb_tab = page

    await asyncio.sleep(1.5)
    if "login" in str(fb_tab.url).lower() or "checkpoint" in str(fb_tab.url).lower():
        print("❌ Anti-bot chặn: Yêu cầu đăng nhập tài khoản!")
        return None, None

    # Lướt ngắn 1500px nhặt gọn 3 bài đầu
    try: 
        await fb_tab.evaluate("window.scrollBy(0, 1500);")
    except Exception: 
        pass
    await asyncio.sleep(1.5)

    # Tối ưu Selector để tăng tốc độ phân tách DOM của Chromium
    print("📜 Đang bấm Expand mở rộng text/comment...")
    try:
        await fb_tab.evaluate("""
            (() => {
                const targets = ["See more", "View more comments", "Xem thêm", "Xem thêm bình luận", "Xem phản hồi"];
                const elements = document.querySelectorAll('div[role="button"], span, a');
                let count = 0;
                for (const el of elements) {
                    if (targets.includes((el.innerText || "").trim())) {
                        try { 
                            el.click(); 
                            count++; 
                            if(count > 12) break; 
                        } catch(e){}
                    }
                }
            })();
        """)
    except Exception: 
        pass
    
    await asyncio.sleep(random.uniform(2.5, 3.0))

    html = await fb_tab.get_content()
    page_path = f"fb_page.html"
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(html)

    popup_path = f"popup_page.html"
    try:
        popup_html = await fb_tab.evaluate("""
            (() => {
                const dialogs = document.querySelectorAll('[role="dialog"]');
                return dialogs.length ? dialogs[dialogs.length - 1].outerHTML : "NO_DIALOG";
            })()
        """)
        if popup_html != "NO_DIALOG":
            with open(popup_path, "w", encoding="utf-8") as f: 
                f.write(popup_html)
        else: 
            popup_path = None
    except Exception: 
        popup_path = None

    photo_path = await lay_20_anh_tu_tab_photos(fb_tab)
    await asyncio.sleep(random.uniform(0.5, 1.0))
    

    return page_path, popup_path, photo_path


async def node_facebook(state: ResearchState, seq: list, headless: bool):
    print("\n" + "=" * 60)
    print("NODE 3: FACEBOOK SCRAPER")
    print("=" * 60)

    seq[0] += 1
    state.add_event(seq[0], "facebook", {"status": "started", "fb_url": state.fb_url})

    global UC_BROWSER
    if UC_BROWSER is None:
        UC_BROWSER = await uc.start(headless=headless, icon_mode=1)

    try:
        page_path, popup_path, photo_path = await _scrape_facebook(UC_BROWSER, state.fb_url, state.business_id)

        if not page_path:
            raise RuntimeError("Thất bại khi trích xuất dữ liệu thô Facebook.")

        with open(page_path, "r", encoding="utf-8") as f: 
            page_html = f.read()
            
        brand = _extract_brand_info(page_html)


        if popup_path:
            with open(popup_path, "r", encoding="utf-8") as f: 
                popup_html = f.read()
            posts, comments, attachments_map = _extract_posts_comments(popup_html)
            if not posts and not comments: 
                posts, comments, attachments_map = _extract_posts_comments(page_html)
        else:
            posts, comments, attachments_map = _extract_posts_comments(page_html)

        final_posts = posts if posts else brand["posts_from_text"]


        if not photo_path:
            raise RuntimeError("Thất bại khi trích xuất dữ liệu thô Facebook.")


        state.fb_data = {
            "brand": {
                "page_info": brand["page_info"], "intro": brand["intro"],
                "phones": brand["phones"], "emails": brand["emails"],
                "domains": brand["domains"], "og_image": brand.get("og_image", ""),
                "business_facts": brand["business_facts"],   # ← THÊM DÒNG NÀY
            },
            "photos": photo_path,
            "posts": final_posts,
            "attachments_map": attachments_map if posts else [[] for _ in final_posts],
            "comments": comments,
        }

        if brand["business_facts"]["_needs_manual_review"]:
            logger.warning(
                f"[node_facebook] business_id={state.business_id} — KHÔNG tìm thấy địa chỉ "
                f"trong intro, cần review thủ công."
            )
        state.add_event(seq[0] + 1, "facebook", {
            "status": "warning",
            "message": "Không trích xuất được địa chỉ — cần review thủ công.",
        })

        print(f"  ✅ Posts: {len(state.fb_data['posts'])} | Comments: {len(state.fb_data['comments'])}")

        seq[0] += 1
        state.add_event(seq[0], "facebook", {
            "status": "done",
            "posts": len(state.fb_data["posts"]),
            "comments": len(state.fb_data["comments"]),
        })

    except Exception as e:
        state.error = f"node_facebook: {e}"
        seq[0] += 1
        state.add_event(seq[0], "facebook", {"status": "error", "error": str(e)})
        print(f"  ❌ Error Node 3: {e}")


# ═══════════════════════════════════════════════════════════════════════
# NODE 4 & ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

def node_report(state: ResearchState, seq: list):
    text = (
        f"Query: {state.query}\n"
        f"Business: {state.business_name}\n"
        f"Suggestions: {len(state.suggestions)}\n"
        f"SERP urls: {len(state.serp_data.get('top_urls', []))}\n"
        f"FB photos: {len(state.fb_data.get('photos', []))}\n"
        f"FB posts: {len(state.fb_data.get('posts', []))}\n"
        f"FB comments: {len(state.fb_data.get('comments', []))}\n"
    )
    state.report = {"text": text}
    print("\n📊 BAO CAO PIPELINE:")
    print(text)

async def run_research(
    db: AsyncSession,
    business_id: str,
    query: str,
    fb_url: str,
    business_name: Optional[str]=None,
    headless=False,
)-> ResearchState:

    state = ResearchState(
        query=query,
        fb_url=fb_url,
        business_id=business_id,
        business_name=business_name,
    )

    seq = [0]

    global UC_BROWSER

    try:
        try:
            await node_suggest(state, seq)
        except Exception:
            pass

        await save_after_node(db, state)

        await node_serp(state, seq, headless)
        await save_after_node(db, state)

        await node_facebook(state, seq, headless)
        await save_after_node(db, state)

        node_report(state, seq)

        state.status = "error" if state.error else "done"

        await save_after_node(db, state)

        return state

    finally:
        if UC_BROWSER:
            print("🛑 Release browser...")

            try:
                UC_BROWSER.stop()
                await asyncio.sleep(0.5)
            except Exception:
                pass

            UC_BROWSER = None