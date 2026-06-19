"""
pipeline.py
Research Pipeline: Node 1 (Google Suggest) -> Node 2 (SERP) -> Node 3 (Facebook).

- KHÔNG còn research_service.py — mọi thứ gộp thẳng vào đây.
- Lưu DB NGAY sau mỗi node (không đợi hết pipeline) -> node sau lỗi không mất dữ liệu node trước.
- Mỗi business chỉ giữ bản mới nhất: xóa dữ liệu cũ của business_id rồi ghi mới (upsert).
- Mọi JSON lưu DB đều chạy qua safe_get() với schema cố định trong models.py
  -> brand lấy dữ liệu ra luôn đủ key, không bị None/KeyError bất ngờ.

Usage (Jupyter / script):
    from pipeline import run_research
    state = await run_research(
        business_id="moc-seafood",
        business_name="Moc Seafood",
        query="nhà hàng quán nhậu hải sản Đà Nẵng",
        fb_url="https://www.facebook.com/mocseafood/",
        db_path="research.db",
        headless=False,
    )
"""

import asyncio
import random
import re
import time
import traceback
from datetime import datetime
from urllib.parse import quote
from typing import Optional

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from .models import (
    Base,
    PipelineTask,
    PipelineEvent,
    ResearchResult,
    FbPost,
    FbComment,
    ResearchState,
    init_db,
    safe_get,
    SUGGESTIONS_TAGGED_SCHEMA,
    SERP_DATA_SCHEMA,
    FB_BRAND_SCHEMA,
    default_suggestions_tagged,
    default_serp_data,
    default_fb_brand,
)
import nodriver as uc
try:
    import nodriver as uc
    HAS_NODRIVER = True
except ImportError:
    HAS_NODRIVER = False
    uc = None

GOOGLE_SESSION = requests.Session()
GOOGLE_SESSION.headers.update({
    "Connection": "keep-alive"
})
UC_BROWSER = None

# ═══════════════════════════════════════════════════════════════════════
# DB HELPERS — upsert kiểu "xóa cũ rồi ghi mới", chỉ dùng business_id
# ═══════════════════════════════════════════════════════════════════════

def _upsert_task(session: Session, state: ResearchState):
    task = session.query(PipelineTask).filter_by(business_id=state.business_id).first()
    if task is None:
        task = PipelineTask(business_id=state.business_id)
        session.add(task)
    task.business_name = state.business_name
    task.query = state.query
    task.fb_url = state.fb_url
    task.status = state.status
    task.error = state.error
    task.updated_at = datetime.now()
    session.commit()


def _replace_events(session: Session, state: ResearchState):
    session.query(PipelineEvent).filter_by(business_id=state.business_id).delete()
    for ev in state.events:
        session.add(PipelineEvent(
            business_id=state.business_id,
            seq=ev["seq"],
            node_name=ev["node"],
            payload=ev["payload"],
        ))
    session.commit()


def _upsert_result(session: Session, state: ResearchState):
    """Lưu/ghi đè research_results — luôn ép dữ liệu qua schema cố định trước khi lưu."""
    result = session.query(ResearchResult).filter_by(business_id=state.business_id).first()
    if result is None:
        result = ResearchResult(business_id=state.business_id)
        session.add(result)

    result.business_name = state.business_name
    result.suggestions_raw = list(state.suggestions)
    result.suggestions_tagged = safe_get(state.tagged_suggestions, SUGGESTIONS_TAGGED_SCHEMA)
    result.serp_data = safe_get(state.serp_data, SERP_DATA_SCHEMA)
    result.fb_brand = safe_get(state.fb_data.get("brand"), FB_BRAND_SCHEMA)
    result.final_report = state.report.get("text") if isinstance(state.report, dict) else None
    result.updated_at = datetime.now()
    session.commit()


def _replace_fb_posts_comments(session: Session, state: ResearchState):
    """Xóa posts/comments cũ của business rồi ghi lại toàn bộ bản mới."""
    session.query(FbPost).filter_by(business_id=state.business_id).delete()
    session.query(FbComment).filter_by(business_id=state.business_id).delete()

    for content in state.fb_data.get("posts", []):
        if content:
            session.add(FbPost(business_id=state.business_id, content=content))

    for c in state.fb_data.get("comments", []):
        session.add(FbComment(
            business_id=state.business_id,
            author=c.get("author"),
            time=c.get("time"),
            comment=c.get("comment"),
            replies=list(c.get("replies", [])),
        ))
    session.commit()


def save_after_node(engine, state: ResearchState):
    """Gọi NGAY sau mỗi node — lưu tất cả những gì state đang có, kể cả khi sau đó lỗi."""
    with Session(engine) as session:
        _upsert_task(session, state)
        _replace_events(session, state)
        _upsert_result(session, state)
        _replace_fb_posts_comments(session, state)


# ═══════════════════════════════════════════════════════════════════════
# NODE 1: GOOGLE SUGGESTIONS  (giữ nguyên logic đã test ok)
# ═══════════════════════════════════════════════════════════════════════

def _get_suggestions(query: str) -> list:
    url = "https://suggestqueries.google.com/complete/search"
    params = {"client": "firefox", "hl": "vi", "q": query}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) "
            "Gecko/20100101 Firefox/109.0"
        ),
        "Accept": "application/json, text/javascript, */*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
    }
    try:
        response = GOOGLE_SESSION.get(
            url,
            params=params,
            headers=headers,
            timeout=(2,3)
        )
        if response.status_code in [429,503]:
            return []

        if response.status_code != 200:
            return []
        data = response.json()
        if isinstance(data, list) and len(data) >= 2:
            suggestions = data[1]
            if isinstance(suggestions, list):
                return [s for s in suggestions if s != query and len(s) > 3]
    except Exception as e:
        print(f"  ERROR get_suggestions: {e}")
    return []


def _expand_query(query: str) -> list:
    all_results = set()

    print(f"\n[1] Base: '{query}'")
    base = _get_suggestions(query)
    all_results.update(base)
    print(f"    → {len(base)} suggestions")
    time.sleep(
        random.uniform(
            0.8,
            1.5,
        )
    )

    print("\n[2] Alphabet expansion...")
    for char in [
        "a",
        "g",
        "n",
        "r",
        "t",
    ]:
        suggs = _get_suggestions(f"{query} {char}")
        all_results.update(suggs)
        time.sleep(
            random.uniform(
                0.4,
                0.8,
            )
        )

    print("\n[3] Number expansion...")
    for num in ["1", "3", "5"]:
        suggs = _get_suggestions(f"{query} {num}")
        all_results.update(suggs)
        time.sleep(
            random.uniform(
                0.4,
                0.8,
            )
        )

    print("\n[4] Intent words...")
    for word in ["giá", "gần", "ở", "cho", "review", "nào", "ngon", "rẻ", "đẹp"]:
        suggs = _get_suggestions(f"{query} {word}")
        all_results.update(suggs)
        time.sleep(
            random.uniform(
                0.4,
                0.8,
            )
        )

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


def node_suggest(state: ResearchState, seq: list):
    print("\n" + "=" * 60)
    print("NODE 1: GOOGLE SUGGESTIONS")
    print("=" * 60)

    state.status = "running"
    seq[0] += 1
    state.add_event(seq[0], "suggest", {"status": "started", "query": state.query})

    state.suggestions =  _expand_query(state.query)
    state.tagged_suggestions = _simple_intent_tag(state.suggestions)

    seq[0] += 1
    state.add_event(seq[0], "suggest", {"status": "done", "total": len(state.suggestions)})
    print(f"\nTOTAL: {len(state.suggestions)} unique suggestions")


# ═══════════════════════════════════════════════════════════════════════
# NODE 2: SERP  (giữ nguyên logic đã test ok)
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
    paa = paa[:5]

    related = []
    for a in soup.select("a"):
        text = _clean_serp_text(a.get_text(" ", strip=True))
        if not text:
            continue
        if any(k in text.lower() for k in ["quán", "hải sản", "đà nẵng"]):
            if len(text.split()) <= 10:
                related.append(text)
    related = list(dict.fromkeys(related))[:10]

    snippets = []
    for block in soup.select("div.g"):
        snippet_el = block.select_one("span")
        if not snippet_el:
            continue
        text = _clean_serp_text(snippet_el.get_text(" ", strip=True))
        if text and 60 < len(text) < 300:
            snippets.append({"snippet": text[:200]})
    snippets = snippets[:5]

    return {
        "top_urls": top_urls[:10],
        "people_also_ask": paa,
        "related_searches": related,
        "snippets": snippets,
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


async def node_serp(state: ResearchState, seq: list, headless: bool):
    print("\n" + "=" * 60)
    print("NODE 2: SERP SCRAPER")
    print("=" * 60)

    seq[0] += 1
    state.add_event(seq[0], "serp", {"status": "started", "query": state.query})

    if not HAS_NODRIVER:
        print("⚠️  nodriver chưa cài. Bỏ qua node SERP.")
        seq[0] += 1
        state.add_event(seq[0], "serp", {"status": "skipped", "reason": "nodriver not installed"})
        return

    global UC_BROWSER

    if UC_BROWSER is None:
        print("🚀 Start browser")
        UC_BROWSER = await uc.start(headless=headless)

    browser = UC_BROWSER
    try:
        page = await browser.get(f"https://www.google.com/search?q={quote(state.query)}&hl=vi")
        await asyncio.sleep(3)
        soup = BeautifulSoup(await page.get_content(), "html.parser")

        state.serp_data = _parse_serp(soup, state.query)

        print(f"  ✅ Top URLs: {len(state.serp_data['top_urls'])}")
        print(f"  ✅ PAA: {len(state.serp_data['people_also_ask'])}")

        seq[0] += 1
        state.add_event(seq[0], "serp", {
            "status": "done",
            "top_urls": len(state.serp_data["top_urls"]),
            "paa": len(state.serp_data["people_also_ask"]),
        })

    except Exception as e:
        state.error = f"node_serp: {e}"
        seq[0] += 1
        state.add_event(seq[0], "serp", {"status": "error", "error": str(e)})
        print(f"  ❌ Error: {e}")

    finally:
        # Đóng HẲN browser ở đây — để node_facebook mở browser MỚI TINH,
        # giống đúng điều kiện lúc test riêng (1000 lần ok), tránh tab/state cũ
        # của node_serp lẫn sang làm sai lệch quá trình tìm tab Facebook.
        if UC_BROWSER:
            print("🛑 Close browser (sau SERP, để node Facebook mở mới sạch)")
            try:
                await UC_BROWSER.stop()
            except Exception:
                pass
            UC_BROWSER = None


# ═══════════════════════════════════════════════════════════════════════
# NODE 3: FACEBOOK  (scrape giữ nguyên cơ chế cũ đã test ok; extract = gộp doc5 + doc6)
# ═══════════════════════════════════════════════════════════════════════

def _clean_fb_text(text: str) -> str:
    """Sửa lỗi mã hóa font Facebook (UTF-8 bị đọc nhầm thành Latin-1)."""
    if not text:
        return ""
    try:
        return text.encode("latin1").decode("utf-8")
    except Exception:
        return text


def _extract_brand_info(html: str) -> dict:
    """Trích page_info / intro / phones / emails / domains từ TOÀN BỘ trang FB."""
    soup = BeautifulSoup(html, "html.parser")
    raw_text = soup.get_text("\n", strip=True)

    NOISE_LINES = {
        "Like", "Comment", "Share", "See more", "View more comments",
        "All reactions:", "Online status indicator", "Active Status indicator",
        "Privacy", "Terms", "Advertising", "Ad choices", "Cookies", "More",
        "Active", "Log in", "Forgotten account?", "Chia sẻ", "Thích", "Bình luận",
    }

    clean_lines = []
    for line in raw_text.split("\n"):
        line = line.strip()
        if not line or line in NOISE_LINES:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if re.fullmatch(r"\d+:\d+", line):
            continue
        clean_lines.append(line)
    clean_text = "\n".join(clean_lines)

    # page_info
    page_info = {"title": "", "followers": "", "following": ""}
    title_tag = soup.find("title")
    if title_tag:
        page_info["title"] = title_tag.get_text(strip=True)

    m = re.search(r'([\d.,]+\s*[KMB]?)\s+(?:followers|người theo dõi)', clean_text, re.IGNORECASE)
    if m:
        page_info["followers"] = m.group(1).strip()

    m = re.search(r'([\d.,]+\s*[KMB]?)\s+(?:following|đang theo dõi)', clean_text, re.IGNORECASE)
    if m:
        page_info["following"] = m.group(1).strip()

    # intro
    intro_section = ""
    start_pos = -1
    for marker in ["Intro", "Giới thiệu", "Page ·"]:
        pos = clean_text.find(marker)
        if pos != -1:
            start_pos = pos
            break
    if start_pos != -1:
        end_pos = len(clean_text)
        for marker in ["\nPhotos", "\nPosts", "\nAbout", "\nẢnh", "\nBài viết"]:
            pos = clean_text.find(marker, start_pos)
            if pos != -1 and pos < end_pos:
                end_pos = pos
        intro_section = clean_text[start_pos:end_pos].strip()
    else:
        intro_section = clean_text[:2000].strip()

    # phones
    raw_phones = re.findall(r'(?:\+84\s?)?(?:0\d{2,3}[\s.-]?\d{3}[\s.-]?\d{3,4})', clean_text)
    phones = set()
    for phone in raw_phones:
        phone = re.sub(r"[\s.-]", "", phone)
        if phone.startswith("+84"):
            phone = "0" + phone[3:]
        phones.add(phone)

    # emails
    emails = sorted(set(re.findall(r'[\w.-]+@[\w.-]+\.\w+', clean_text)))

    # domains
    all_domains = re.findall(r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,6}\b', clean_text.lower())
    domains = sorted(set(
        d for d in all_domains if not d.endswith(("js", "css", "png", "jpg", "jpeg", "gif", "ico"))
    ))

    # posts (cắt theo mốc "Shared with Public" / "Công khai")
    posts = []
    chunks = re.split(r'Shared with Public|Chia sẻ với Công khai|Công khai', clean_text)
    for chunk in chunks:
        chunk = chunk.strip()
        if len(chunk) < 150:
            continue
        if "followers" in chunk or "người theo dõi" in chunk:
            continue
        posts.append(chunk)
    posts = posts[:10]

    return {
        "page_info": page_info,
        "intro": intro_section,
        "phones": sorted(phones),
        "emails": emails,
        "domains": domains,
        "posts_from_text": posts,
    }


def _extract_posts_comments(html: str) -> tuple:
    """Trích main_post_data + detailed_comments (kèm replies).
    Dùng cho cả facebook_page.html và popup_only.html (selector giống nhau)."""
    soup = BeautifulSoup(html, "html.parser")

    post_contents = []
    for post_div in soup.find_all("div", attrs={"data-ad-preview": "message"}):
        post_contents.append(_clean_fb_text(post_div.get_text(separator="\n", strip=True)))

    if not post_contents:
        for text_div in soup.find_all("div", class_="xdj266r"):
            if len(text_div.get_text()) > 100 and not text_div.find_parent(attrs={"role": "article"}):
                cleaned = _clean_fb_text(text_div.get_text(strip=True))
                if cleaned and cleaned not in post_contents:
                    post_contents.append(cleaned)

    comments_list = []
    for block in soup.find_all("div", attrs={"role": "article"}):
        aria_label = block.get("aria-label", "")
        author_name = "Ẩn danh"
        comment_time = "Không rõ"

        if "Comment by" in aria_label:
            meta_info = aria_label.replace("Comment by ", "")
            match = re.search(r'(.+?)\s(\d+\s\w+\sago|\d+\w+)', meta_info)
            if match:
                author_name, comment_time = match.group(1), match.group(2)
            else:
                author_name = meta_info

        comment_text = ""
        text_container = block.find("div", attrs={"dir": "auto"})
        if text_container:
            comment_text = _clean_fb_text(text_container.get_text(strip=True))
        else:
            possible_text = block.find("div", class_="xdj266r")
            if possible_text:
                comment_text = _clean_fb_text(possible_text.get_text(strip=True))

        replies = []
        parent_div = block.find_parent()
        if parent_div:
            next_sibling = parent_div.find_next_sibling()
            if next_sibling:
                reply_text = _clean_fb_text(next_sibling.get_text(separator=" ", strip=True))
                if reply_text:
                    replies.append(reply_text)

        if comment_text or author_name != "Ẩn danh":
            comments_list.append({
                "author": author_name, "time": comment_time,
                "comment": comment_text, "replies": replies,
            })

    return post_contents, comments_list




async def _scrape_facebook(fb_url: str, headless: bool, business_id: str):
    """
    HÀM CÀO FACEBOOK TỐI ƯU TỐC ĐỘ - CHỈ LẤY TOP BÀI VIẾT LÀM BRAND VOICE
    """
    browser = None

    try:
        print("🚀 Mở trình duyệt...")
        browser = await uc.start(headless=headless, icon_mode=1)

        target_url = fb_url.strip().lower()
        if not target_url.endswith("/"):
            target_url += "/"

        clean_search_url = f'"{target_url}"'
        raw_clean_url = target_url.replace("https://", "").replace("http://", "").replace("www.", "")
        search_query = f"site:{raw_clean_url}"

        print(f"🔍 Vào Google tìm kiếm nâng cao: {search_query}...")
        page = await browser.get(f"https://www.google.com/search?q={search_query}")

        # TỐI ƯU: Giảm thời gian chờ Google load
        print("⏳ Chờ 1.5 giây cho Google Search ổn định...")
        await asyncio.sleep(1.5)

        matched_href = None
        click_target = None

        links = await page.select_all("a:has(h3)")
        if not links:
            print("⚠️ Không tìm thấy kết quả hiển thị trên Google!")
            return None, None

        for link in links:
            try:
                href_attr = link["href"] if "href" in link.attrs else None
                if not href_attr:
                    continue
                
                href_lower = href_attr.strip().lower()
                if clean_search_url in f'"{href_lower}"':
                    matched_href = href_attr.strip()
                    click_target = link
                    break
            except Exception:
                pass

        if not matched_href or not click_target:
            print(f"❌ Không tìm thấy homepage khớp với từ khóa: {fb_url}")
            return None, None

        # Giãn cách ngắn trước khi click
        await asyncio.sleep(random.uniform(0.4, 0.8))

        try:
            await click_target.scroll_into_view()
        except Exception:
            pass

        print(f"🖱️ [HÀNH ĐỘNG] Click vào kết quả Facebook: {matched_href}")
        await click_target.click()

        # QUAN TRỌNG: Giữ 3 giây cố định để Facebook nhận Referer sạch từ Google
        print("⏳ Đợi 3 giây cố định để chuyển hướng an toàn...")
        await asyncio.sleep(3.0)

        # Kiểm tra Tab điều hướng
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
            print("💡 Google điều hướng trực tiếp trên TAB HIỆN TẠI.")
            fb_tab = page

        # TỐI ƯU: Giảm thời gian đợi Facebook load vì chỉ cần top bài viết
        print("⏳ Đợi 1.5 giây cho Facebook nạp DOM phần đầu trang...")
        await asyncio.sleep(1.5)

        current_url = str(fb_tab.url).lower()
        if "login" in current_url or "checkpoint" in current_url:
            print("❌ Thất bại: Facebook bắt Login!")
            return None, None

        print("🎉 Đã vào Facebook. Cuộn ngắn lấy đủ 3 bài viết đầu...")
        try:
            # TỐI ƯU: Chỉ cuộn 1 lần vừa phải (1500px) đủ để hiện 3 bài viết đầu và comment của chúng
            await fb_tab.evaluate("window.scrollBy(0, 2500);")
        except Exception:
            pass
        
        # Đợi 1.5s cho comment và bài viết dưới nạp ra
        await asyncio.sleep(1.5)

        # =====================================================
        # 👑 TỐI ƯU CLICK EXPAND: NHANH & NGẪU NHIÊN NÉ BOT
        # =====================================================
        print("📜 Đang kích hoạt JS mở rộng nội dung (See more / Xem thêm)...")
        try:
            await fb_tab.evaluate(
                """
                (() => {
                    const targets = [
                        "See more", "View more comments", "Xem thêm", "Xem thêm bình luận", "Xem phản hồi"
                    ];
                    const all = document.querySelectorAll("*");
                    let clickCount = 0;
                    for (const el of all) {
                        const text = (el.innerText || "").trim();
                        if (targets.includes(text)) {
                            try {
                                el.click();
                                clickCount++;
                                // Giới hạn không click vô tận để tiết kiệm thời gian
                                if(clickCount > 15) break; 
                            } catch(e) {}
                        }
                    }
                })();
                """
            )
        except Exception:
            pass

        # Giảm thời gian đợi sau khi expand xuống tối thiểu
        await asyncio.sleep(random.uniform(2.4, 2.8))

        print("📸 Lấy dữ liệu HTML...")
        html = await fb_tab.get_content()
        page_path = f"fb_page_{business_id}.html"

        with open(page_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"💾 Đã lưu dữ liệu phục vụ phân tích Brand Voice.")

        # Kiểm tra Dialog phụ nếu có (Không bắt buộc dữ dội nữa)
        popup_path = f"popup_{business_id}.html"
        try:
            popup_html = await fb_tab.evaluate("""
                (() => {
                    const dialogs = document.querySelectorAll('[role="dialog"]');
                    if (!dialogs.length) return "NO_DIALOG";
                    return dialogs[dialogs.length - 1].outerHTML;
                })()
            """)
            if popup_html != "NO_DIALOG":
                with open(popup_path, "w", encoding="utf-8") as f:
                    f.write(popup_html)
            else:
                popup_path = None
        except Exception:
            popup_path = None

        return page_path, popup_path

    except Exception as e:
        print("❌ Lỗi toàn cục:", e)
        traceback.print_exc()
        return None, None

    finally:
        print("⏳ Đóng trình duyệt...")
        try:
            if browser:
                await browser.stop()
        except Exception:
            pass



async def node_facebook(state: ResearchState, seq: list, headless: bool):
    print("\n" + "=" * 60)
    print("NODE 3: FACEBOOK SCRAPER")
    print("=" * 60)

    seq[0] += 1
    state.add_event(seq[0], "facebook", {"status": "started", "fb_url": state.fb_url})

    if not HAS_NODRIVER:
        print("⚠️  nodriver chưa cài. Bỏ qua node Facebook.")
        seq[0] += 1
        state.add_event(seq[0], "facebook", {"status": "skipped", "reason": "nodriver not installed"})
        return

    try:
        page_path, popup_path = await _scrape_facebook(state.fb_url, headless, state.business_id)

        if not page_path:
            raise RuntimeError("Không lấy được trang Facebook (xem log _scrape_facebook ở trên).")

        with open(page_path, "r", encoding="utf-8") as f:
            page_html = f.read()

        # Brand info luôn lấy từ trang đầy đủ
        brand = _extract_brand_info(page_html)

        # Posts/comments: ưu tiên popup (chi tiết hơn), fallback sang trang chính
        if popup_path:
            with open(popup_path, "r", encoding="utf-8") as f:
                popup_html = f.read()
            posts, comments = _extract_posts_comments(popup_html)
            if not posts and not comments:
                posts, comments = _extract_posts_comments(page_html)
        else:
            posts, comments = _extract_posts_comments(page_html)

        state.fb_data = {
            "brand": {
                "page_info": brand["page_info"],
                "intro": brand["intro"],
                "phones": brand["phones"],
                "emails": brand["emails"],
                "domains": brand["domains"],
            },
            "posts": posts if posts else brand["posts_from_text"],
            "comments": comments,
        }

        print(f"  ✅ Posts: {len(state.fb_data['posts'])}")
        print(f"  ✅ Comments: {len(state.fb_data['comments'])}")

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
        print(f"  ❌ Error: {e}")


# ═══════════════════════════════════════════════════════════════════════
# NODE 4: REPORT (tóm tắt text ngắn, không bắt buộc)
# ═══════════════════════════════════════════════════════════════════════

def node_report(state: ResearchState, seq: list):
    print("\n" + "=" * 60)
    print("NODE 4: REPORT")
    print("=" * 60)

    seq[0] += 1
    state.add_event(seq[0], "report", {"status": "started"})

    text = (
        f"Query: {state.query}\n"
        f"Business: {state.business_name} ({state.business_id})\n"
        f"Suggestions: {len(state.suggestions)}\n"
        f"SERP top urls: {len(state.serp_data.get('top_urls', []))}\n"
        f"FB posts: {len(state.fb_data.get('posts', []))}\n"
        f"FB comments: {len(state.fb_data.get('comments', []))}\n"
    )
    state.report = {"text": text}

    seq[0] += 1
    state.add_event(seq[0], "report", {"status": "done"})
    print(text)


# ═══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

async def run_research(
    business_id: str,
    query: str,
    fb_url: str,
    business_name: Optional[str] = None,
    db_path: str = "research.db",
    headless: bool = False,
) -> ResearchState:
    """
    Chạy đủ 3 node, LƯU DB NGAY sau mỗi node.
    Node sau lỗi vẫn giữ được kết quả của node trước trong DB.
    """
    engine = init_db(db_path)
    state = ResearchState(query=query, fb_url=fb_url, business_id=business_id, business_name=business_name)
    seq = [0]  # dùng list để mutate được trong các hàm node

    print("\n" + "🚀" * 30)
    print(f"RESEARCH PIPELINE — business_id={business_id}")
    print("🚀" * 30)

    # Node 1
    try:
        node_suggest(state, seq)
    except Exception as e:
        state.error = f"node_suggest: {e}"
        seq[0] += 1
        state.add_event(seq[0], "suggest", {"status": "error", "error": str(e)})
    save_after_node(engine, state)

    # Node 2
    await node_serp(state, seq, headless)
    save_after_node(engine, state)

    # Node 3
    await node_facebook(state, seq, headless)
    save_after_node(engine, state)

    # Node 4 (report) — luôn chạy, không phụ thuộc lỗi node trước
    node_report(state, seq)
    state.status = "error" if state.error else "done"
    save_after_node(engine, state)

    print("\n" + ("❌" if state.error else "✅") * 30)
    print(f"PIPELINE {'LỖI: ' + state.error if state.error else 'HOÀN TẤT'}")
    print(("❌" if state.error else "✅") * 30)

    global UC_BROWSER

    try:
        return state

    finally:
        if UC_BROWSER:
            print("🛑 Close browser")
            try:
                await UC_BROWSER.stop()
            except Exception:
                pass
            UC_BROWSER = None