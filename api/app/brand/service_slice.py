
# ═══════════════════════════════════════════════════
# CELL 1: IMPORTS
# ═══════════════════════════════════════════════════
import json, asyncio, re, logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.llm_clients import call_groq

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Strip zero-width spaces / non-breaking spaces / BOM that can corrupt prompts
# or break downstream regex parsing on certain runtimes (Linux/Docker).
_INVISIBLE_CHARS_PATTERN = re.compile(r'[\xa0\u200b\u200c\u200d\ufeff]')


def _strip_invisible(text: str) -> str:
    """Remove hidden/zero-width characters that can break parsing or cause
    unexpected SyntaxError-like issues when content is later embedded in code/templates."""
    if not text:
        return text
    return _INVISIBLE_CHARS_PATTERN.sub(' ', text)


# ─── Language guard: detect if a response is predominantly Vietnamese ───
_VN_CHARS = re.compile(
    r'[ăâđêôơưĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ'
    r'ÁÀẢÃẠẤẦẨẪẬẮẰẲẴẶÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ]'
)

# Các stopword phổ biến của tiếng Anh — nếu văn bản chứa nhiều từ này,
# gần như chắc chắn câu văn được viết bằng tiếng Anh, bất kể có bao nhiêu
# tên riêng tiếng Việt (brand, địa danh) chen vào.
_EN_STOPWORDS = {
    "the", "is", "are", "was", "were", "and", "or", "of", "in", "on",
    "for", "with", "to", "this", "that", "these", "those", "likely",
    "appears", "seems", "include", "includes", "including", "such",
    "as", "customers", "users", "people", "individuals", "searching",
    "particularly", "various", "information", "about",
}


def _is_vietnamese(text: str, min_ratio: float = 0.06, max_en_stopword_ratio: float = 0.06) -> bool:
    """Heuristic check kết hợp 2 tín hiệu:
    1) Tỷ lệ ký tự có dấu tiếng Việt trên tổng số ký tự chữ cái.
    2) Tỷ lệ từ trùng stopword tiếng Anh trên tổng số từ.

    Chỉ dựa vào (1) là không đủ, vì tên riêng brand/địa danh tiếng Việt
    (vd: "Đà Nẵng", "Mộc Quán") có thể kéo tỷ lệ dấu lên dù toàn bộ câu
    văn thực chất là tiếng Anh. Kết hợp thêm (2) để bắt đúng trường hợp
    này: nếu văn bản có nhiều stopword tiếng Anh, coi là lệch ngôn ngữ
    dù tỷ lệ dấu có vượt ngưỡng.
    """
    if not text:
        return False

    letters = sum(1 for ch in text if ch.isalpha())
    if letters == 0:
        return False

    vn_hits = len(_VN_CHARS.findall(text))
    vn_ratio = vn_hits / letters
    if vn_ratio < min_ratio:
        return False

    words = re.findall(r"[a-zA-Z']+", text.lower())
    if not words:
        return True  # không có từ Latin nào để nghi ngờ -> coi là tiếng Việt

    en_hits = sum(1 for w in words if w in _EN_STOPWORDS)
    en_ratio = en_hits / len(words)
    if en_ratio >= max_en_stopword_ratio:
        return False

    return True


async def _call_with_language_guard(prompt_builder, i, max_tokens, label, retries=1):
    """Call the LLM and force one retry with a stronger Vietnamese reminder
    if the response comes back predominantly in English."""
    prompt = prompt_builder(i)
    result = _strip_invisible(call_groq(prompt, max_tokens=max_tokens))

    attempt = 0
    while not _is_vietnamese(result) and attempt < retries:
        attempt += 1
        logger.warning(f"[{label}] Response looks like English, retrying ({attempt}/{retries})...")
        forced_prompt = (
            prompt
            + "\n\n<constraints>\n"
              "Câu trả lời trước của bạn bị lệch sang tiếng Anh. Lần này hãy viết lại "
              "TOÀN BỘ câu trả lời bằng tiếng Việt có dấu đầy đủ (ă, â, đ, ê, ô, ơ, ư...).\n"
              "</constraints>"
        )
        result = _strip_invisible(call_groq(forced_prompt, max_tokens=max_tokens))

    if not _is_vietnamese(result):
        logger.error(f"[{label}] Still English after {retries} retries, keeping anyway.")
    return result


def _extract_locations_deterministic(intro_text: str, phones: list) -> list:
    """
    Trích xuất địa chỉ 100% bằng regex, KHÔNG qua LLM — đảm bảo không sai lệch
    hoặc bịa thông tin. Neo vào "Vietnam" (Facebook luôn thêm vào cuối dòng
    địa chỉ đầy đủ). Chọn dòng có nhiều dấu phẩy nhất trong các dòng chứa
    "Vietnam" để tránh nhầm với caption ngắn kiểu "Da Nang, Vietnam".
    """
    lines = [l.strip() for l in intro_text.split('\n') if l.strip()]
    candidates = [l for l in lines if re.search(r'\bvietnam\b', l, re.IGNORECASE)]
    if not candidates:
        return []

    best = max(candidates, key=lambda l: l.count(','))
    if best.count(',') < 2:
        return []  # dòng kiểu "Da Nang, Vietnam" — không đủ tin cậy để là địa chỉ đầy đủ

    address_clean = re.sub(r',\s*\d{4,6}\s*$', '', best).strip()          # bỏ mã bưu chính cuối dòng nếu có
    address_clean = re.sub(r',\s*vietnam\s*$', '', address_clean, flags=re.IGNORECASE).strip()

    city_map = {
        "da nang": "Đà Nẵng", "đà nẵng": "Đà Nẵng",
        "nha trang": "Nha Trang",
        "ho chi minh": "Hồ Chí Minh", "hồ chí minh": "Hồ Chí Minh", "hcm": "Hồ Chí Minh",
        "ha noi": "Hà Nội", "hà nội": "Hà Nội",
    }
    low = address_clean.lower()
    city = next((v for k, v in city_map.items() if k in low), "")

    return [{
        "address": address_clean,
        "city": city,
        "hotline": phones[0] if phones else ""
    }]

def _resolve_business_name(data_result: dict, fallback_from_task: str = "") -> str:
    """Suy luận business_name khi input gốc rỗng/rác (vd: 'string' do test API).
    Ưu tiên: task input thật > <h1> từ trang Facebook (page_name) > <title> đã làm sạch > SERP title.
    """
    def _is_garbage(name: str) -> bool:
        if not name or not name.strip():
            return True
        return name.strip().lower() in {"string", "test", "n/a", "unknown", "null"}

    def _clean_page_title(title: str) -> str:
        if not title:
            return ""
        title = re.split(r'\s*[\|\-–]\s*Facebook\s*$', title, flags=re.IGNORECASE)[0]
        title = re.split(r'\s*[\|\-–]\s*(Da Nang|Ha Noi|Ho Chi Minh)\s*$', title, flags=re.IGNORECASE)[0]
        return title.strip()

    if not _is_garbage(fallback_from_task):
        return fallback_from_task.strip()

    page_info = data_result.get("fb_brand", {}).get("page_info", {})

    # 1. Ưu tiên cao nhất: <h1> (page_name) — tên hiển thị thật, không đuôi
    h1_name = page_info.get("page_name", "")
    if not _is_garbage(h1_name):
        logger.warning(f"[_resolve_business_name] Dùng page_name (H1): '{h1_name}'")
        return h1_name

    # 2. Tiếp theo: <title>, cần làm sạch đuôi "| Facebook", "| Da Nang"
    cleaned = _clean_page_title(page_info.get("title", ""))
    if not _is_garbage(cleaned):
        logger.warning(f"[_resolve_business_name] Dùng page title đã làm sạch: '{cleaned}'")
        return cleaned

    # 3. Cuối cùng: SERP title
    top_urls = data_result.get("serp_data", {}).get("top_urls", [])
    if top_urls:
        serp_title = _clean_page_title(top_urls[0].get("title", ""))
        if not _is_garbage(serp_title):
            logger.warning(f"[_resolve_business_name] Dùng SERP title: '{serp_title}'")
            return serp_title

    logger.error("[_resolve_business_name] Không tìm được business_name hợp lệ.")
    return "Thương hiệu"


# ═══════════════════════════════════════════════════
# CELL 1B: GENERIC LABEL PARSERS
# Dùng để đọc section "LABEL:\n..." từ output thô của LLM, RỒI render lại
# thành "# HEADER" Markdown — không build JSON lồng nhau, không mapping
# phức tạp.
# ═══════════════════════════════════════════════════

def parse_section(text, section):
    p = rf"{section}:[ \t]*\n?(.*?)(?=\n[ \t]*[A-Z_]+:|\Z)"
    m = re.search(p, text, re.S)
    return m.group(1).strip() if m else ""


def parse_list(text, section):
    content = parse_section(text, section)
    items = []
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("-"):
            items.append(line[1:].strip())
    return items


def safe_int(v, default=50):
    try:
        if v is None:
            return default
        if isinstance(v, int):
            return max(0, min(100, v))
        s = str(v).strip()
        if not s:
            return default
        m = re.search(r"\d+", s)
        if not m:
            return default
        return max(0, min(100, int(m.group())))
    except Exception:
        return default


def _bullets(items: List[str]) -> str:
    """Render 1 list Python -> bullet list Markdown. Rỗng -> chuỗi rỗng."""
    if not items:
        return ""
    return "\n".join(f"- {x}" for x in items)


def _render_markdown(blocks: List[tuple]) -> str:
    """blocks: list[(header, content)] -> 1 Markdown document hoàn chỉnh.
    Section rỗng bị bỏ qua (không in '# HEADER' rỗng)."""
    parts = []
    for header, content in blocks:
        content = (content or "").strip()
        if not content:
            continue
        parts.append(f"# {header.upper()}\n\n{content}")
    return "\n\n".join(parts).strip()


# ═══════════════════════════════════════════════════
# CELL 2A: SLICER — Helper functions
# ═══════════════════════════════════════════════════

def _k1_posts(posts):
    result = sorted(posts, key=lambda p: len(p.get("content", "")), reverse=True)[:5]
    logger.info(f"[_k1_posts] Selected {len(result)} longest posts")
    for p in result:
        logger.debug(f"  Post ID {p['id']}: {len(p.get('content',''))} chars")
    return result


def _k2_posts(posts):
    def cls(p):
        c = p.get("content", "").lower()
        if "michelin" in c:
            return 0
        if any(x in c for x in ["diff", "pháo hoa", "sự kiện"]):
            return 1
        if any(x in c for x in ["giao hàng", "tận nhà", "delivery", "take-away"]):
            return 2
        return 3

    b = [[], [], [], []]
    for p in posts:
        b[cls(p)].append(p)
    r = []
    for bucket in b:
        r.extend(bucket[:2])
    if len(r) < 8:
        used = {p["id"] for p in r}
        for p in posts:
            if p["id"] not in used:
                r.append(p)
            if len(r) >= 8:
                break
    logger.info(
        f"[_k2_posts] Selected {len(r[:8])} posts "
        f"(michelin={len(b[0])}, events={len(b[1])}, delivery={len(b[2])}, other={len(b[3])})"
    )
    return r[:8]


def _k3_posts(posts):
    minimal = []
    for p in posts:
        c = p.get("content", "")
        s = [x.strip() for x in c.replace("!", ".").replace("?", ".").split(".") if x.strip()]
        minimal.append({
            "id": p["id"], "first": s[0][:100] if s else "",
            "last": s[-1][:100] if len(s) > 1 else "", "wc": len(c.split()),
            "emoji": any(ord(ch) > 10000 for ch in c),
            "hash": "#" in c, "bi": "----------" in c, "bull": c.count("\n-")
        })
    logger.info(f"[_k3_posts] Built metadata for {len(minimal)} posts, full samples: {len(posts[:2])}")
    return minimal, posts[:2]


def _k4_posts(posts):
    m = ["Hotline:", "CS1", "Đặt bàn", "Inbox", "Gọi điện"]
    r = [p for p in posts if any(x in p.get("content", "") for x in m)]
    result = r if len(r) >= 3 else posts[-4:]
    logger.info(f"[_k4_posts] Selected {len(result)} posts with CTA keywords (matched {len(r)})")
    return result


def _clean_fb_intro(raw_intro: str) -> str:
    """Filter UI noise from the fb intro, keeping only useful information."""
    if not raw_intro:
        logger.warning("[_clean_fb_intro] Empty raw_intro!")
        return ""
    raw_intro = _strip_invisible(raw_intro)
    lines = raw_intro.split("\n")
    skip = {
        "Facebook", "Active Status indicator", "followers", "following",
        "Posts", "About", "Reels", "Photos", "More", "Intro", "Page",
        "Privacy", "Terms", "Advertising", "Ad choices", "Cookies",
        "Online status indicator", "Active", "is at", "Shared with Public",
        "See All Photos", "·", "", "Open now", "Delivery", "Takeaway", "Dine in",
        "Price range", "Photos"
    }
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped in skip:
            continue
        if stripped.startswith("·"):
            continue
        cleaned.append(stripped)
    result = "\n".join(cleaned)
    logger.info(f"[_clean_fb_intro] Cleaned from {len(raw_intro)} to {len(result)} chars")
    logger.debug(f"[_clean_fb_intro] Preview: {result[:200]}...")
    return result


# ═══════════════════════════════════════════════════
# CELL 2B: SLICER — prepare_kien_inputs
# ═══════════════════════════════════════════════════

def prepare_kien_inputs(data):
    logger.info("[prepare_kien_inputs] Starting...")
    posts = data.get("posts", [])
    comments = data.get("comments", [])
    
    # Lấy chính xác cụm kết quả từ JSON bạn đã đưa
    result_node = data.get("result", {})
    serp = result_node.get("serp_data", {})
    suggestions_tagged = result_node.get("suggestions_tagged", {})
    suggestions_raw = result_node.get("suggestions_raw", [])

    mc = [c for c in comments if len(c.get("comment", "")) > 20 and c.get("author") != "Ẩn danh"]
    m3, f3 = _k3_posts(posts)
    fb_clean = _clean_fb_intro(result_node.get("fb_brand", {}).get("intro", ""))

    result = {
        "k1": {
            "posts": _k1_posts(posts),
            "fb": fb_clean[:2000],
            "name": data.get("task", {}).get("business_name", "")
        },

        "k2": {
            "posts": _k2_posts(posts),
            "comments": mc[:15],
            "name": data.get("task", {}).get("business_name", ""),
            # ➕ BỔ SUNG: Đưa từ khóa tag để K2 hiểu Intent/Nỗi đau của khách hàng khi tìm kiếm
            "suggestions_tagged": suggestions_tagged 
        },

        "k3": {
            "posts": posts[:10],
            "keyword_cluster": serp.get("keyword_cluster", []),
            "competitor_pattern": serp.get("competitor_pattern", []),
            "content_angle": serp.get("content_angle", []),
            "intent": serp.get("intent", []),
            "top_urls": serp.get("top_urls", [])[:5] # Lấy top 5 đối thủ hàng đầu
        },

        "k4": {
            "posts": _k4_posts(posts),
            "bc": [c for c in mc if any(x in c.get("comment", "").lower() for x in ["đặt bàn", "menu", "hotline", "giá"])][:10]
        },

        "k5": {
            "posts": posts[:5],
            "fb": fb_clean[:1500],
            "intro": result_node.get("fb_brand", {}).get("intro", ""),
            "phones": result_node.get("fb_brand", {}).get("phones", []),
            "emails": result_node.get("fb_brand", {}).get("emails", []),
            "domains": result_node.get("fb_brand", {}).get("domains", []),
            "business_facts": result_node.get("fb_brand", {}).get("business_facts", {}),
            "name": data.get("task", {}).get("business_name", "")
        },

        "k6": {
            "posts": posts[:20],
            "comments": mc[:20],
            "name": data.get("task", {}).get("business_name", "")
        },

        "k7": {
            "posts": posts[:20],
            "comments": mc[:20],
            "name": data.get("task", {}).get("business_name", ""),
            "suggestions_raw": suggestions_raw[:30] # Giới hạn top 30 từ khóa thô phổ biến nhất để tránh tràn ngữ cảnh
        }
    }
    return result

# ═══════════════════════════════════════════════════
# CELL 3A: PROMPT BUILDERS — K1 & K2
#
# Design: English is used for the structural scaffolding (<system>, <task>,
# <constraints> tags + task description) because the model was instruction-
# tuned mostly on English data and parses structure/instructions more
# reliably in English. Vietnamese is used as a "language anchor" planted at
# two strategic points: right after <task> opens (sets the dominant language
# channel early) and as the very LAST line of the prompt. All parsing
# anchors (PURPOSE:, AUDIENCE:, etc.) are kept verbatim — they're consumed
# by parse_section/parse_list below to build the K1-K7 Markdown documents,
# so the labels must never change without updating the corresponding
# _build_kN_markdown() function.
# ═══════════════════════════════════════════════════
def _pk1(i):
    fb_text = _strip_invisible(i.get("fb", ""))[:500]

    pt = "\n\n---\n".join(
        f"ID:{p['id']}\n{_strip_invisible(p.get('content',''))[:800]}"
        for p in i.get("posts", [])
    )

    return f"""
ROLE

Brand DNA Extraction Agent

MISSION

Extract brand identity from observable evidence.

DATA

FACEBOOK_INTRO:
{fb_text}

POSTS:
{pt}

RULES

- Use only provided data.
- No assumptions.
- No explanations.
- No markdown.
- No XML.
- No JSON.
- Return exact schema only.

OUTPUT

PURPOSE:
(one sentence)

PERSONALITY:
(one paragraph)

MAIN_TOPICS:
- item

PRODUCTS_SERVICES:
- item

REPEATED_PHRASES:
- item

TAGLINES:
- item

EVIDENCE:
- item

END
"""


def _pk2(i):
    pt = "\n\n---\n".join(
        f"ID:{p['id']}\n{_strip_invisible(p.get('content',''))[:500]}"
        for p in i.get("posts", [])
    )

    ct = "\n".join(
        f"- {c['author']}: {_strip_invisible(c.get('comment',''))[:200]}"
        for c in i.get("comments", [])
    )

    # Biến đổi dict thành chuỗi văn bản cho LLM đọc
    tagged = i.get("suggestions_tagged", {})
    st_text = "\n".join(f"Cụm từ [{k.upper()}]: {', '.join(v)}" for k, v in tagged.items() if v)

    return f"""
ROLE
Audience Extraction Agent

MISSION
Identify audience, customer intent, and search patterns.

DATA
BRAND POSTS:
{pt}

COMMENTS FROM FANPAGE:
{ct}

SEARCH_SUGGESTIONS_BY_INTENT:
{st_text}

RULES
- Analyze posts, fanpage comments, and target search phrases together.
- Link search phrases to actual customer needs.
- No assumptions. No explanations.
- Return exact schema only.
- BẮT BUỘC: toàn bộ nội dung OUTPUT phải viết bằng tiếng Việt có dấu đầy đủ
  (ă, â, đ, ê, ô, ơ, ư). Không viết bằng tiếng Anh, kể cả khi dữ liệu đầu
  vào có chứa tiếng Anh.

OUTPUT
AUDIENCE:
(một câu tiếng Việt, mô tả khách hàng mục tiêu kết hợp cả hành vi trên
mạng xã hội và ý định tìm kiếm)

CUSTOMER_TOPICS:
- Ví dụ: Địa điểm quán, thực đơn, giá cả

CUSTOMER_SENTIMENT:
- Ví dụ: Mong muốn tìm được lựa chọn hợp túi tiền và chất lượng tốt

CUSTOMER_REQUESTS:
- Ví dụ: Tìm địa chỉ, đặt bàn, xem đánh giá

PAIN_POINTS:
- item (Dựa trên search suggestions, ví dụ: tìm kiếm quán 'rẻ nhất', 'gần thanh khê', 'đánh giá michelin')

EVIDENCE:
- item
END
"""



def _pk3(i):
    pt = "\n\n---\n".join(
        f"ID:{p['id']}\n{_strip_invisible(p.get('content',''))[:600]}"
        for p in i.get("posts", [])
    )
    
    urls_text = "\n".join(f"- {u.get('title')} ({u.get('domain')})" for u in i.get("top_urls", []))
    clusters = ", ".join(i.get("keyword_cluster", []))
    angles = ", ".join(i.get("content_angle", []))
    intents = ", ".join(i.get("intent", []))

    return f"""
ROLE
Content System Agent

MISSION
Extract content system and detect content gaps against market competitors.

DATA
CURRENT BRAND POSTS:
{pt}

MARKET SERP COMPETITORS:
{urls_text}

SEO_KEYWORD_CLUSTERS: {clusters}
EXPECTED_CONTENT_ANGLES: {angles}
USER_SEARCH_INTENTS: {intents}

RULES
- Evaluate if current posts cover the SEO_KEYWORD_CLUSTERS and USER_SEARCH_INTENTS.
- Identify what angles competitors are using that this brand is missing.
- Return exact schema only.

OUTPUT
CONTENT_TOPICS:
- item

CONTENT_PATTERNS:
- item

CONTENT_FORMATS:
- item

COMMON_CTA:
- item

FORMAT_RULES:
- emoji=yes/no
- hashtag=yes/no
- bullet=yes/no

EVIDENCE:
- item (Trích dẫn điểm yếu/điểm mạnh so với môi trường SERP)
END
"""



def _pk4(i):

    pt = "\n\n---\n".join(
        f"ID:{p['id']}\n{_strip_invisible(p.get('content',''))[:500]}"
        for p in i.get("posts", [])
    )

    bc = "\n".join(
        f"- {c['author']}: {_strip_invisible(c.get('comment',''))[:200]}"
        for c in i.get("bc", [])
    )

    return f"""
ROLE

CTA & Behaviour Rules Agent

MISSION

Extract how the brand asks readers to take action (CTA behaviour rules).

DATA

POSTS:
{pt}

CUSTOMER_QUESTIONS_ABOUT_BOOKING_MENU_PRICE:
{bc}

RULES

- Exact extraction only.
- Use customer questions to validate which contact actions actually work.
- No assumptions.
- No explanations.
- Return exact schema only.

OUTPUT

CTA_STYLE:
direct|soft|mixed

CTA_PHRASES:
- item

CONTACT_ACTIONS:
- item

MOST_REPEATED_CTA:
(one line)

EVIDENCE:
- item

END
"""



def _pk5(i: dict) -> dict:
    """
    Làm sạch sơ bộ và đóng gói trọn vẹn dữ liệu từ bản ghi Fanpage thô.
    Đảm bảo KHÔNG LÀM MẤT trường intro và bổ sung thêm cấu trúc LOCATIONS nếu quét trúng.
    """
    fb_brand_data = i.get("fb_brand") or i if isinstance(i, dict) else {}
    fb_intro = fb_brand_data.get("intro", "")

    locations = []

    if fb_intro:
        # Sử dụng Regex linh hoạt hơn: Bắt mọi khối bắt đầu bằng dấu ghim 📍
        blocks = re.findall(r"(📍.*?)(?=📍|Page|About|Open now|$)", fb_intro, re.DOTALL)

        for block in blocks:
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if not lines:
                continue

            addr_line = lines[0]
            # Loại bỏ linh hoạt các tiền tố như "📍 Cơ sở 1:", "📍 Địa chỉ:", "📍 CS1:"
            addr_clean = re.sub(r"^📍\s*(?:Cơ sở|Địa chỉ|CS)?\s*\d*\s*:?\s*", "", addr_line, flags=re.I).strip()

            city = ""
            if any(kw in addr_clean.lower() for kw in ["đà nẵng", "da nang"]):
                city = "Đà Nẵng"
            elif "nha trang" in addr_clean.lower():
                city = "Nha Trang"
            elif "hồ chí minh" in addr_clean.lower() or "hcm" in addr_clean.lower():
                city = "Hồ Chí Minh"

            hotline_clean = ""
            # Nếu dòng tiếp theo chứa dấu hiệu của số điện thoại liên hệ
            if len(lines) > 1 and any(kw in lines[1].lower() for kw in ["hotline", "sđt", "liên hệ", "tel"]):
                hotline_match = re.search(r"(?:hotline|sđt|liên hệ)\s*[^:]*:\s*(.*)", lines[1], re.I)
                hotline_clean = hotline_match.group(1).strip() if hotline_match else lines[1].strip()

            locations.append({
                "city": city,
                "address": addr_clean,
                "hotline": hotline_clean
            })

    def _clean_list(lst):
        if not lst: return []
        return list(sorted(set([str(item).strip() for item in lst if item])))

    # 🚨 QUAN TRỌNG: Trả về đầy đủ cả key viết hoa lẫn trường intro gốc để tầng dưới xài
    return {
        "intro": fb_intro,  # <--- BẮT BUỘC PHẢI GIỮ LẠI TRƯỜNG NÀY!
        "locations": locations,
        "phones": _clean_list(fb_brand_data.get("phones", [])),
        "emails": _clean_list(fb_brand_data.get("emails", [])),
        "domains": _clean_list(fb_brand_data.get("domains", [])),
        "og_image": fb_brand_data.get("og_image", "")
    }

def _pk6(i):
    pt = "\n\n---\n".join(
        _strip_invisible(p.get("content",""))[:300]
        for p in i.get("posts", [])
    )

    return f"""ROLE
Tone Analysis Agent

MISSION
Analyze brand tone from posts.

DATA
{pt}

RULES
- TONE_BASE: 3-5 descriptive Vietnamese words
- TONE_TRAITS: 3-5 personality traits in Vietnamese
- 4 SLIDER values: integers 0-100
- No explanations

OUTPUT
TONE_BASE:
- Thân thiện
- Nhiệt huyết
- Gần gũi

TONE_TRAITS:
- Chân thành
- Tự tin
- Năng động

FUNNY_SERIOUS: 20
FORMAL_CASUAL: 70
RESPECTFUL_IRREVERENT: 90
ENTHUSIASTIC_MATTER_OF_FACT: 75
END"""


def _pk7(i):
    def _strip_hashtags(text: str) -> str:
        return re.compile(r'#\S+').sub('', text).strip()

    # Chỉ lấy top 3 posts dài nhất
    posts_sorted = sorted(
        i.get("posts", []),
        key=lambda p: len(p.get("content", "")),
        reverse=True
    )[:3]
    
    pt = "\n\n---\n".join(
        _strip_hashtags(_strip_invisible(p.get("content", "")))[:400]
        for p in posts_sorted
    )
    
    # Giới hạn 15 từ khóa quan trọng nhất
    raw_keywords = i.get("suggestions_raw", [])[:15]
    keywords_text = ", ".join(raw_keywords)

    return f"""ROLE
Vocabulary System Agent

MISSION
Extract brand vocabulary from posts and cross-reference with search keywords.

DATA
BRAND POSTS:
{pt}

SEARCH KEYWORDS:
{keywords_text}

RULES
- Extract natural words/phrases from posts.
- Cross-reference with search keywords for SEO alignment.
- No hashtags, no emojis as vocabulary.
- Each item: 1-3 words, Vietnamese only.
- STRICT OUTPUT RULE: DO NOT include any introductory text, explanatory text, or conversational filler (e.g., "Here are the results..."). 
- STRICT FORMAT RULE: Output headers exactly as written below. DO NOT wrap headers in markdown bold formatting (like ** stars) or any other markdown decorations.

OUTPUT
WORDS_TO_USE
- item

WORDS_TO_AVOID
- item

PHRASES_TO_USE
- item

PHRASES_TO_AVOID
- item
END"""


# ═══════════════════════════════════════════════════
# CELL 4: RUN 7 KIENS IN PARALLEL
# K1-K4, K6, K7 go through the Vietnamese language guard. K5 is a
# structured local-extraction (regex on FB intro), no LLM/guard needed.
# ═══════════════════════════════════════════════════

async def _k1(i):
    logger.info("[_k1] Calling LLM...")
    result = await _call_with_language_guard(_pk1, i, 1500, "_k1")
    logger.info(f"[_k1] LLM response length: {len(result)}")
    logger.debug(f"[_k1] Response preview: {result[:200]}...")
    return result


async def _k2(i):
    logger.info("[_k2] Calling LLM...")
    result = await _call_with_language_guard(_pk2, i, 1500, "_k2")
    logger.info(f"[_k2] LLM response length: {len(result)}")
    return result


async def _k3(i):
    logger.info("[_k3] Calling LLM...")
    result = await _call_with_language_guard(_pk3, i, 1500, "_k3")
    logger.info(f"[_k3] LLM response length: {len(result)}")
    return result


async def _k4(i):
    logger.info("[_k4] Calling LLM...")
    result = await _call_with_language_guard(_pk4, i, 1200, "_k4")
    logger.info(f"[_k4] LLM response length: {len(result)}")
    return result


async def _k5(i):
    """
    Business facts — local extraction từ dữ liệu thô Fanpage, không cần LLM.
    Kết quả trả về chuỗi JSON dump của toàn bộ object fb_brand để hàm parse tầng dưới xử lý động.
    """
    try:
        # Giả định _pk5(i) trả về dict chứa thông tin page cào về (gồm cả intro, phones, domains,...)
        extracted_data = _pk5(i) or {}
        
        # Nhét toàn bộ dict dữ liệu thô này vào JSON String để đảm bảo đồng bộ pipeline lưu trữ
        simulated_llm_response = json.dumps(extracted_data, ensure_ascii=False)

        logger.info(f"[_k5] Local extraction complete. Text length: {len(simulated_llm_response)}")
        return simulated_llm_response

    except Exception as e:
        logger.error(f"[_k5] Error during local extraction: {str(e)}. Using safe fallback.")
        # Fallback trả về chuỗi JSON của một dict rỗng để không làm lỗi tầng json.loads phía sau
        return "{}"


async def _k6(i):
    logger.info("[_k6] Calling LLM...")
    result = await _call_with_language_guard(_pk6, i, 1000, "_k6")
    return result


async def _k7(i):
    logger.info("[_k7] Calling LLM...")
    result = await _call_with_language_guard(_pk7, i, 1000, "_k7")
    logger.info(f"[_k7] LLM response _k7: {result}")
    return result


async def run_kiens(data):
    logger.info("[run_kiens] === STARTING 7 KIENS ===")
    inp = prepare_kien_inputs(data)
    logger.info(
        f"[run_kiens] K1:{len(inp['k1']['posts'])} "
        f"K2:{len(inp['k2']['posts'])}+{len(inp['k2']['comments'])} "
        f"K3:{len(inp['k3']['posts'])} "
        f"K4:{len(inp['k4']['posts'])}+{len(inp['k4']['bc'])} "
        f"K5:{len(inp['k5']['posts'])}"
    )

    r = await asyncio.gather(
        _k1(inp["k1"]),
        _k2(inp["k2"]),
        _k3(inp["k3"]),
        _k4(inp["k4"]),
        _k5(inp["k5"]),
        _k6(inp["k6"]),
        _k7(inp["k7"])
    )

    result = {
        "k1": r[0],
        "k2": r[1],
        "k3": r[2],
        "k4": r[3],
        "k5": r[4],
        "k6": r[5],
        "k7": r[6],
        "k5_input": inp["k5"],
    }

    logger.info("[run_kiens] === ALL 7 KIENS COMPLETE ===")
    for k in ["k1", "k2", "k3", "k4", "k5", "k6", "k7"]:
        logger.info(
            f"[run_kiens] {k} output type={type(result[k])}, "
            f"length={len(result[k]) if isinstance(result[k], str) else 'N/A'}"
        )

    return result


# ═══════════════════════════════════════════════════
# CELL 5: BUSINESS FACTS PARSER (cột JSON riêng, không phải K-doc)
# ═══════════════════════════════════════════════════
import re
import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

def _parse_business_context(k5_text: str, k5_input: dict = None) -> dict:
    """
    Nguồn dữ liệu business_facts đã được lọc sạch, deterministic ngay từ
    bước research (fb_brand.business_facts) — 100% regex, không qua LLM,
    không thể bịa. Vì vậy hàm này BÊ NGUYÊN business_facts khi nó tồn tại
    và không bị đánh dấu _needs_manual_review, KHÔNG tái tạo/regex lại.
    Chỉ fallback sang tự parse intro khi business_facts thực sự không có
    (thiếu hẳn ở tầng research) hoặc bị đánh dấu cần review thủ công.
    """
    logger.info("[_parse_business_context] Bắt đầu trích xuất động dữ liệu từ Fanpage.")

    result = {
        "locations": [], "hours": "", "usp": [], "menu_highlights": [],
        "phones": [], "emails": [], "domains": []
    }

    if not (k5_input and isinstance(k5_input, dict)):
        logger.warning("[_parse_business_context] Không có k5_input, fallback sang regex parser.")
        return _fallback_regex_parser(k5_text, result)

    result["domains"] = [d.strip() for d in k5_input.get("domains", []) if d.strip()]
    intro_text = k5_input.get("intro") or k5_input.get("fb") or ""

    business_facts = k5_input.get("business_facts")
    needs_review = bool(business_facts) and business_facts.get("_needs_manual_review", False)

    if business_facts and not needs_review:
        # Bê nguyên - dữ liệu đã được chuẩn hóa sẵn (city/hotline tách riêng,
        # địa chỉ đầy đủ) từ bước research, KHÔNG tự chế/regex lại.
        logger.info("[_parse_business_context] Dùng nguyên business_facts từ research (deterministic).")
        result["locations"] = business_facts.get("locations", []) or []
        result["hours"] = business_facts.get("hours", "") or ""
        result["usp"] = list(business_facts.get("usp") or [])
        result["menu_highlights"] = list(business_facts.get("menu_highlights") or [])
        result["phones"] = [str(p).strip() for p in business_facts.get("phones", []) if str(p).strip()]
        result["emails"] = [e.strip() for e in business_facts.get("emails", []) if e.strip()]
    else:
        if needs_review:
            logger.warning("[_parse_business_context] business_facts bị đánh dấu _needs_manual_review=True, fallback tự parse intro.")
        else:
            logger.info("[_parse_business_context] Không có business_facts ở tầng research, fallback tự parse intro.")

        result["phones"] = [str(p).strip() for p in k5_input.get("phones", []) if str(p).strip()]
        result["emails"] = [e.strip() for e in k5_input.get("emails", []) if e.strip()]

        if k5_input.get("locations"):
            result["locations"] = k5_input["locations"]
        elif intro_text:
            result["locations"] = _extract_locations_deterministic(intro_text, result["phones"])

        if intro_text:
            for pattern in (
                r'(?:⏰|⏳)\s*(?:Giờ mở cửa|Giờ phục vụ|Opening hours)?:\s*([^\n]+)',
                r'(?:Giờ mở cửa|Giờ phục vụ):\s*([^\n]+)',
            ):
                m = re.search(pattern, intro_text, re.IGNORECASE)
                if m:
                    result["hours"] = m.group(1).strip()
                    break

    for domain in result["domains"]:
        dl = domain.lower()
        if "guide.michelin.com" in dl:
            result["usp"].append("Thương hiệu đạt chứng nhận danh giá từ tổ chức Michelin Guide.")
        if "tripadvisor.com" in dl:
            result["usp"].append("Nằm trong danh sách các địa điểm có lượt đề xuất cao trên TripAdvisor.")
    if intro_text and not (business_facts and business_facts.get("usp")):
        m = re.search(r'(\d+%\s*recommend[^\n(]*(?:\([^\n)]*\))?)', intro_text, re.IGNORECASE)
        if m:
            result["usp"].append(m.group(1).strip())

    if needs_review:
        logger.warning("[_parse_business_context] business_facts bị đánh dấu _needs_manual_review=True — đã bỏ qua hours/locations, dùng fallback.")

    logger.info(
        f"[_parse_business_context] Hoàn tất. Phát hiện {len(result['locations'])} chi nhánh, "
        f"hours='{result['hours']}', usp={len(result['usp'])} mục."
    )
    return result


def _fallback_regex_parser(k5_text: str, default_struct: dict) -> dict:
    if not k5_text:
        return default_struct
    try:
        parsed = json.loads(k5_text)
        default_struct["locations"] = parsed.get("locations", [])
        default_struct["phones"] = parsed.get("phones", [])
        default_struct["emails"] = parsed.get("emails", [])
        default_struct["domains"] = parsed.get("domains", [])
    except Exception:
        pass
    return default_struct


def _channels(k3_raw: str, k4_raw: str) -> List[str]:
    t = (k3_raw + k4_raw).lower()
    ch = []
    if any(w in t for w in ["facebook", "fanpage", "social", "fb"]):
        ch.append("social")
    if any(w in t for w in ["blog", "website", "web"]):
        ch.append("blog")
    if any(w in t for w in ["email", "newsletter"]):
        ch.append("email")
    if any(w in t for w in ["tiktok", "video", "reels"]):
        ch.append("video")
    return ch or ["social", "blog"]


# ═══════════════════════════════════════════════════
# CELL 6: K1 → K7 MARKDOWN BUILDERS
# Mỗi hàm nhận raw LLM output (label-based) và trả về 1 Markdown document
# hoàn chỉnh — KHÔNG build JSON lồng nhau, KHÔNG mapping field phức tạp.
# ═══════════════════════════════════════════════════

def _build_k1_markdown(k1_raw: str) -> tuple:
    """K1 — Brand Foundation: PURPOSE / PERSONALITY / PRODUCTS / TAGLINES."""
    purpose = parse_section(k1_raw, "PURPOSE")
    personality = parse_section(k1_raw, "PERSONALITY")
    products = parse_list(k1_raw, "PRODUCTS_SERVICES")
    taglines = parse_list(k1_raw, "TAGLINES")

    md = _render_markdown([
        ("PURPOSE", purpose),
        ("PERSONALITY", personality),
        ("PRODUCTS", _bullets(products)),
        ("TAGLINES", _bullets(taglines)),
    ])
    return md, purpose, taglines


def _build_k2_markdown(k2_raw: str) -> tuple:
    """K2 — Customer Insights: AUDIENCE / PAIN POINTS / CUSTOMER REQUESTS."""
    audience = parse_section(k2_raw, "AUDIENCE")
    pain_points = parse_list(k2_raw, "PAIN_POINTS")
    customer_requests = parse_list(k2_raw, "CUSTOMER_REQUESTS")
    customer_topics = parse_list(k2_raw, "CUSTOMER_TOPICS")
    customer_sentiment = parse_list(k2_raw, "CUSTOMER_SENTIMENT")

    md = _render_markdown([
        ("AUDIENCE", audience),
        ("PAIN POINTS", _bullets(pain_points)),
        ("CUSTOMER REQUESTS", _bullets(customer_requests)),
        ("CUSTOMER TOPICS", _bullets(customer_topics)),
        ("CUSTOMER SENTIMENT", _bullets(customer_sentiment)),
    ])
    return md, audience


def _build_k3_markdown(k3_raw: str) -> str:
    """K3 — Content Patterns: CONTENT TOPICS / CTA PATTERNS / CONTENT FORMATS."""
    content_topics = parse_list(k3_raw, "CONTENT_TOPICS")
    cta_patterns = parse_list(k3_raw, "COMMON_CTA")
    content_formats = parse_list(k3_raw, "CONTENT_FORMATS")
    content_patterns = parse_list(k3_raw, "CONTENT_PATTERNS")
    format_rules = parse_section(k3_raw, "FORMAT_RULES")

    return _render_markdown([
        ("CONTENT TOPICS", _bullets(content_topics)),
        ("CTA PATTERNS", _bullets(cta_patterns)),
        ("CONTENT FORMATS", _bullets(content_formats)),
        ("CONTENT PATTERNS", _bullets(content_patterns)),
        ("FORMAT RULES", format_rules),
    ])


def _build_k4_markdown(k4_raw: str) -> str:
    """K4 — Behavior Rules: cách brand kêu gọi hành động (CTA behaviour)."""
    cta_style = parse_section(k4_raw, "CTA_STYLE")
    cta_phrases = parse_list(k4_raw, "CTA_PHRASES")
    contact_actions = parse_list(k4_raw, "CONTACT_ACTIONS")
    most_repeated = parse_section(k4_raw, "MOST_REPEATED_CTA")

    return _render_markdown([
        ("CTA STYLE", cta_style),
        ("CTA PHRASES", _bullets(cta_phrases)),
        ("CONTACT ACTIONS", _bullets(contact_actions)),
        ("MOST REPEATED CTA", most_repeated),
    ])


def _build_k5_examples_markdown(posts: list, max_examples: int = 5) -> str:
    """K5 — Examples: lấy NGUYÊN VĂN các post tiêu biểu nhất của brand làm
    ví dụ thật, không qua LLM (tránh bịa nội dung không có thật)."""
    chosen = _k1_posts(posts)[:max_examples]
    if not chosen:
        return ""

    parts = ["# EXAMPLES"]
    for idx, p in enumerate(chosen, start=1):
        content = _strip_invisible(p.get("content", "")).strip()
        if not content:
            continue
        parts.append(f"\n## Example {idx}\n\n{content}")

    return "\n".join(parts).strip()


def _build_k6_markdown(k6_raw: str) -> tuple:
    """K6 — Tone Analysis: TONE_BASE / TONE_TRAITS / 4 trục slider."""
    tone_base = parse_list(k6_raw, "TONE_BASE")
    tone_traits = parse_list(k6_raw, "TONE_TRAITS")

    funny_serious = safe_int(parse_section(k6_raw, "FUNNY_SERIOUS"))
    formal_casual = safe_int(parse_section(k6_raw, "FORMAL_CASUAL"))
    respectful_irreverent = safe_int(parse_section(k6_raw, "RESPECTFUL_IRREVERENT"))
    enthusiastic_matter_of_fact = safe_int(parse_section(k6_raw, "ENTHUSIASTIC_MATTER_OF_FACT"))

    sliders_md = (
        f"- Funny ↔ Serious: {funny_serious}\n"
        f"- Formal ↔ Casual: {formal_casual}\n"
        f"- Respectful ↔ Irreverent: {respectful_irreverent}\n"
        f"- Enthusiastic ↔ Matter-of-fact: {enthusiastic_matter_of_fact}"
    )

    md = _render_markdown([
        ("TONE BASE", _bullets(tone_base)),
        ("TONE TRAITS", _bullets(tone_traits)),
        ("TONE SLIDERS", sliders_md),
    ])

    sliders = {
        "tone_funny_serious": funny_serious,
        "tone_formal_casual": formal_casual,
        "tone_respectful_irreverent": respectful_irreverent,
        "tone_enthusiastic_matter_of_fact": enthusiastic_matter_of_fact,
    }
    return md, tone_base, sliders


def _build_k7_markdown(k7_raw: str) -> str:
    """K7 — Vocabulary Rules: WORDS_TO_USE / WORDS_TO_AVOID / PHRASES_*."""
    words_to_use = parse_list(k7_raw, "WORDS_TO_USE")
    words_to_avoid = parse_list(k7_raw, "WORDS_TO_AVOID")
    phrases_to_use = parse_list(k7_raw, "PHRASES_TO_USE")
    phrases_to_avoid = parse_list(k7_raw, "PHRASES_TO_AVOID")

    return _render_markdown([
        ("WORDS TO USE", _bullets(words_to_use)),
        ("WORDS TO AVOID", _bullets(words_to_avoid)),
        ("PHRASES TO USE", _bullets(phrases_to_use)),
        ("PHRASES TO AVOID", _bullets(phrases_to_avoid)),
    ])


# ═══════════════════════════════════════════════════
# CELL 7: AGGREGATOR — Brand Markdown-first schema
# ═══════════════════════════════════════════════════

def aggregate(
    k1, k2, k3, k4, k5, k6, k7,
    bid, bname,
    fb=None,
    k5_input=None,
    posts=None,
) -> Dict[str, Any]:
    """Build dict đúng schema Brand mới: K1-K7 Markdown + field có cấu trúc
    (purpose/target_audience/desired_tone/channels/taglines/business_facts/
    4 trục tone). Không build JSON lồng nhau cho voice (personality/style/
    vocabulary/format_rules/cta_style/examples) — các field đó đã bị xoá."""
    logger.info("[aggregate] === STARTING AGGREGATION (Markdown-first) ===")

    fb = fb or {}
    posts = posts or []
    now = datetime.now(timezone.utc).isoformat()

    # ── K1: Brand Foundation (parse để lấy purpose/taglines dùng riêng) ──
    k1_md, purpose, taglines = _build_k1_markdown(k1)

    # ── K2: Customer Insights (parse để lấy audience dùng riêng) ────────
    k2_md, audience = _build_k2_markdown(k2)

    # ── K3: Content Patterns — raw, không parse lại (không cần extract field riêng)
    k3_md = _strip_invisible(k3 or "").strip()

    # ── K4: Behavior Rules — raw, không parse lại ────────────────────────
    k4_md = _strip_invisible(k4 or "").strip()

    # ── K5: Examples (verbatim post thật, không qua LLM) ─────────────────
    k5_md = _build_k5_examples_markdown(posts)

    # ── K6: Tone Analysis + 4 trục slider (parse để lấy sliders dùng riêng)
    k6_md, tone_base, sliders = _build_k6_markdown(k6)

    # ── K7: Vocabulary Rules — raw, không parse lại ──────────────────────
    k7_md = _strip_invisible(k7 or "").strip()

    # ── Business facts (JSON field riêng, không phải K-doc) ──────────────
    fb_business_facts = fb.get("business_facts")
    if fb_business_facts and not fb_business_facts.get("_needs_manual_review", False):
        business_facts = {
            "locations": fb_business_facts.get("locations", []) or [],
            "hours": fb_business_facts.get("hours", "") or "",
            "usp": list(fb_business_facts.get("usp") or []),
            "menu_highlights": list(fb_business_facts.get("menu_highlights") or []),
            "phones": fb_business_facts.get("phones", []) or [],
            "emails": fb_business_facts.get("emails", []) or [],
            "domains": fb.get("domains", []) or [],
        }
    else:
        business_facts = _parse_business_context(k5, k5_input)  # fallback duy nhất khi fb không có business_facts

    # ── Channels (dựa trên raw text K3 + K4, giữ logic cũ) ────────────────
    channels = _channels(k3, k4)

    # ── desired_tone: tóm tắt ngắn từ TONE_BASE (K6) ───────────────────────
    desired_tone = ", ".join(tone_base[:3]) if tone_base else "Chuyên nghiệp"

    fb_name = fb.get("page_info")

    result = {
        "business_id": bid,
        "name": fb_name.get("page_name", "") or "",

        # ── Structured fields (giữ lại) ───────────────────────────────
        "purpose": purpose or "Tăng trưởng kinh doanh và nhận diện thương hiệu",
        "target_audience": audience or "Khách hàng mục tiêu",
        "desired_tone": desired_tone,
        "channels": channels,
        "taglines": taglines,
        "business_facts": business_facts,

        "website_url": fb.get("url"),

        # ── K1 → K7: AI Knowledge Base (Markdown) ─────────────────────
        "k1_brand_foundation": k1_md or None,
        "k2_customer_insights": k2_md or None,
        "k3_content_patterns": k3_md or None,
        "k4_behavior_rules": k4_md or None,
        "k5_examples": k5_md or None,
        "k6_tone_analysis": k6_md or None,
        "k7_vocabulary_rules": k7_md or None,

        # ── 4 trục tone (Radar & Sliders) ──────────────────────────────
        **sliders,

        # ── System ──────────────────────────────────────────────────────
        "is_default": "0",
        "created_at": now,
        "updated_at": now,
    }

    logger.info("[aggregate] === AGGREGATION COMPLETE (Markdown-first) ===")
    logger.info(f"[aggregate] purpose={result['purpose'][:100]}")
    logger.info(f"[aggregate] target_audience={result['target_audience'][:100]}")
    logger.info(f"[aggregate] channels={result['channels']}")
    logger.info(
        f"[aggregate] K-docs lengths: "
        f"k1={len(k1_md)} k2={len(k2_md)} k3={len(k3_md)} k4={len(k4_md)} "
        f"k5={len(k5_md)} k6={len(k6_md)} k7={len(k7_md)}"
    )
    logger.info(f"[aggregate] sliders={sliders}")

    return result

# ═══════════════════════════════════════════════════
# CELL 8: MAIN — Run from data → Brand fields (K1-K7 Markdown)
# ═══════════════════════════════════════════════════

async def extract_brand_voice(research_record):
    logger.info("[extract_brand_voice] === STARTING ===")

    result = research_record["result"]
    logger.info(f"[extract_brand_voice] result type={type(result)}")
    raw_business_name = result.get("business_name") if isinstance(result, dict) else getattr(result, 'business_name', None)

    data = {
        "task": {
            "business_id": result.get("business_id") if isinstance(result, dict) else getattr(result, 'business_id', None),
            "business_name": _resolve_business_name(
                result if isinstance(result, dict) else {},
                raw_business_name
            ),
        },
        "result": {
            "serp_data": result.get("serp_data") if isinstance(result, dict) else getattr(result, 'serp_data', {}),
            "fb_brand": result.get("fb_brand") if isinstance(result, dict) else getattr(result, 'fb_brand', {}),
            "final_report": result.get("final_report") if isinstance(result, dict) else getattr(result, 'final_report', None),
            "suggestions_tagged": result.get("suggestions_tagged") if isinstance(result, dict) else getattr(result, 'suggestions_tagged', {}),
            "suggestions_raw": result.get("suggestions_raw") if isinstance(result, dict) else getattr(result, 'suggestions_raw', []),
        },
        "posts": [
            {
                "id": p.get("id") if isinstance(p, dict) else getattr(p, 'id', None),
                "content": p.get("content") if isinstance(p, dict) else getattr(p, 'content', ''),
                "attachments": p.get("attachments") if isinstance(p, dict) else getattr(p, 'attachments', []),
            }
            for p in research_record.get("posts", [])
        ],
        "comments": [
            {
                "author": c.get("author") if isinstance(c, dict) else getattr(c, 'author', ''),
                "time": c.get("time") if isinstance(c, dict) else getattr(c, 'time', ''),
                "comment": c.get("comment") if isinstance(c, dict) else getattr(c, 'comment', ''),
                "replies": c.get("replies") if isinstance(c, dict) else getattr(c, 'replies', []),
            }
            for c in research_record.get("comments", [])
        ],
    }

    logger.info(f"[extract_brand_voice] Data prepared: {len(data['posts'])} posts, {len(data['comments'])} comments")

    ko = await run_kiens(data)
    logger.info("[extract_brand_voice] Kiens complete, aggregating...")

    st = aggregate(
        ko["k1"], ko["k2"], ko["k3"], ko["k4"], ko["k5"], ko["k6"], ko["k7"],
        data["task"]["business_id"],
        data["task"]["business_name"],
        data["result"].get("fb_brand", {}),
        ko.get("k5_input"),
        data["posts"],
    )

    logger.info("[extract_brand_voice] === COMPLETE ===")
    logger.info(
        f"[extract_brand_voice] Sliders: "
        f"f={st['tone_funny_serious']} fo={st['tone_formal_casual']} "
        f"r={st['tone_respectful_irreverent']} e={st['tone_enthusiastic_matter_of_fact']}"
    )

    return st