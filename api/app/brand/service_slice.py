
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


def _is_vietnamese(text: str, min_ratio: float = 0.01) -> bool:
    """Heuristic check: real Vietnamese prose should contain a noticeable
    share of diacritic characters. Pure English text will have ~0."""
    if not text:
        return False
    letters = sum(1 for ch in text if ch.isalpha())
    if letters == 0:
        return False
    vn_hits = len(_VN_CHARS.findall(text))
    return (vn_hits / letters) >= min_ratio


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


# ═══════════════════════════════════════════════════
# CELL 1B: GENERIC LABEL PARSERS
# Dùng để đọc section "LABEL:\n..." từ output thô của LLM, RỒI render lại
# thành "# HEADER" Markdown — không build JSON lồng nhau, không mapping
# phức tạp.
# ═══════════════════════════════════════════════════

def parse_section(text, section):
    p = rf"{section}:\s*(.*?)(?=\n[A-Z_]+:|\Z)"
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
    serp = data.get("result", {}).get("serp_data", {})
    fb = data.get("result", {}).get("fb_brand", {})

    logger.info(f"[prepare_kien_inputs] Raw data: {len(posts)} posts, {len(comments)} comments")
    logger.info(f"[prepare_kien_inputs] fb_brand keys: {list(fb.keys())}")
    logger.info(f"[prepare_kien_inputs] phones: {fb.get('phones', [])}")
    logger.info(f"[prepare_kien_inputs] emails: {fb.get('emails', [])}")
    logger.info(f"[prepare_kien_inputs] domains: {fb.get('domains', [])}")

    mc = [c for c in comments if len(c.get("comment", "")) > 20 and c.get("author") != "Ẩn danh"]
    logger.info(f"[prepare_kien_inputs] Filtered comments (>20 chars, not anonymous): {len(mc)}/{len(comments)}")

    m3, f3 = _k3_posts(posts)
    fb_clean = _clean_fb_intro(fb.get("intro", ""))

    result = {
        "k1": {
            "posts": _k1_posts(posts),
            "fb": fb_clean[:2000],
            "name": data.get("task", {}).get("business_name", "")
        },

        "k2": {
            "posts": _k2_posts(posts),
            "comments": mc[:15],
            "name": data.get("task", {}).get("business_name", "")
        },

        "k3": {
            "posts": posts[:10],
            "minimal": m3,
            "full": f3,
            "kc": serp.get("keyword_cluster", []),
            "cp": serp.get("competitor_pattern", [])
        },

        "k4": {
            "posts": _k4_posts(posts),
            "bc": [
                c for c in mc
                if any(
                    x in c.get("comment", "").lower()
                    for x in ["đặt bàn", "menu", "hotline", "giá"]
                )
            ][:10]
        },

        "k5": {
            "posts": posts[:5],
            "fb": fb_clean[:1500],
            "phones": fb.get("phones", []),
            "emails": fb.get("emails", []),
            "domains": fb.get("domains", []),
            "name": data.get("task", {}).get("business_name", "")
        },

        "k6": {
            "posts": posts[:20],
            "comments": mc[:20],
            "name": data.get("task", {}).get("business_name", "")
        },

        "k7": {
            "posts": posts[:20],
            "fb": fb_clean[:1000],
            "name": data.get("task", {}).get("business_name", "")
        }
    }

    logger.info("[prepare_kien_inputs] Kien inputs built:")
    for k, v in result.items():
        if isinstance(v, dict):
            logger.info(f"  {k}: keys={list(v.keys())}")
            if "posts" in v:
                logger.info(f"    posts count={len(v['posts'])}")
            if "comments" in v:
                logger.info(f"    comments count={len(v['comments'])}")
            if "phones" in v:
                logger.info(f"    phones={v['phones']}")
            if "emails" in v:
                logger.info(f"    emails={v['emails']}")
            if "domains" in v:
                logger.info(f"    domains={v['domains']}")

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

    ct = "\n".join(
        f"- {c['author']}: {_strip_invisible(c.get('comment',''))[:200]}"
        for c in i.get("comments", [])
    )

    return f"""
ROLE

Audience Extraction Agent

MISSION

Identify audience and customer intent.

DATA

COMMENTS:
{ct}

RULES

- Use comments only.
- No assumptions.
- No explanations.
- Return exact schema only.

OUTPUT

AUDIENCE:
(one sentence)

CUSTOMER_TOPICS:
- item

CUSTOMER_SENTIMENT:
- item

CUSTOMER_REQUESTS:
- item

PAIN_POINTS:
- item

EVIDENCE:
- item

END
"""

def _pk3(i):

    pt = "\n\n---\n".join(
        f"ID:{p['id']}\n{_strip_invisible(p.get('content',''))[:600]}"
        for p in i.get("posts", [])
    )

    return f"""
ROLE

Content System Agent

MISSION

Extract content system.

DATA

POSTS:
{pt}

RULES

- Use posts only.
- No assumptions.
- No explanations.
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
- item

END
"""

def _pk4(i):

    pt = "\n\n---\n".join(
        f"ID:{p['id']}\n{_strip_invisible(p.get('content',''))[:500]}"
        for p in i.get("posts", [])
    )

    return f"""
ROLE

CTA & Behaviour Rules Agent

MISSION

Extract how the brand asks readers to take action (CTA behaviour rules).

DATA

POSTS:
{pt}

RULES

- Exact extraction only.
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


import re

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

    return f"""
ROLE

Tone Analysis Agent

MISSION

Measure brand tone.

DATA

{pt}

RULES

- Return numbers only.
- Integer only.
- 0-100.
- No ranges.
- No explanations.

OUTPUT

TONE_BASE:
- item

TONE_TRAITS:
- item

FUNNY_SERIOUS: 20

FORMAL_CASUAL: 70

RESPECTFUL_IRREVERENT: 90

ENTHUSIASTIC_MATTER_OF_FACT: 75

END
"""

def _pk7(i):

    pt = "\n\n---\n".join(
        _strip_invisible(p.get("content",""))[:500]
        for p in i.get("posts", [])
    )

    return f"""
ROLE

Vocabulary System Agent

MISSION

Extract vocabulary system.

DATA

{pt}

RULES

- Extract only.
- No writing.
- No explanations.
- No examples.
- No markdown.

OUTPUT

WORDS_TO_USE:
- item

WORDS_TO_AVOID:
- item

PHRASES_TO_USE:
- item

PHRASES_TO_AVOID:
- item

END
"""


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
    return result


async def run_kiens(data):
    logger.info("[run_kiens] === STARTING 7 KIENS ===")
    inp = prepare_kien_inputs(data)
    logger.info(
        f"[run_kiens] K1:{len(inp['k1']['posts'])} "
        f"K2:{len(inp['k2']['posts'])}+{len(inp['k2']['comments'])} "
        f"K3:{len(inp['k3']['minimal'])}+{len(inp['k3']['full'])} "
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
    Chắt lọc động 100% dữ liệu từ thuộc tính của fb_brand (k5_input).
    Tuyệt đối không hardcode, tự động thích ứng theo text thô của từng Fanpage.
    """
    logger.info("[_parse_business_context] Bắt đầu trích xuất động dữ liệu từ Fanpage.")

    # Khởi tạo khung dữ liệu chuẩn cho Jinja2 prompt
    result = {
        "locations": [],
        "hours": "",
        "usp": [],
        "menu_highlights": [],
        "phones": [],
        "emails": [],
        "domains": []
    }

    # Đảm bảo đồng bộ mớ dữ liệu phẳng có sẵn từ metadata hệ thống cào về trước
    if k5_input and isinstance(k5_input, dict):
        result["phones"] = [str(p).strip() for p in k5_input.get("phones", []) if str(p).strip()]
        result["emails"] = [e.strip() for e in k5_input.get("emails", []) if e.strip()]
        result["domains"] = [d.strip() for d in k5_input.get("domains", []) if d.strip()]
        intro_text = k5_input.get("intro", "")
    else:
        intro_text = ""

    if not intro_text:
        logger.warning("[_parse_business_context] Thuộc tính 'intro' của Fanpage trống!")
        # Nếu không có intro, quay về parse từ k5_text thô dự phòng
        return _fallback_regex_parser(k5_text, result)

    # 1. ⏰ TRÍCH XUẤT ĐỘNG GIỜ MỞ CỬA (Bóc theo emoji hoặc từ khóa chung)
    # Quét dòng chứa biểu tượng đồng hồ hoặc cụm từ 'Giờ mở cửa', 'Giờ phục vụ', 'Open'
    hours_patterns = [
        r'(?:⏰|⏳)\s*(?:Giờ mở cửa|Giờ phục vụ|Opening hours)?:\s*([^\n]+)',
        r'(?:Giờ mở cửa|Giờ phục vụ):\s*([^\n]+)'
    ]
    for pattern in hours_patterns:
        hours_match = re.search(pattern, intro_text, re.IGNORECASE)
        if hours_match:
            result["hours"] = hours_match.group(1).strip()
            # Kiểm tra xem dòng ngay tiếp theo có phải là note bổ sung trong ngoặc đơn không
            next_line_match = re.search(re.escape(hours_match.group(0)) + r'\n\s*(\([^\n\)]+\))', intro_text)
            if next_line_match:
                result["hours"] += f" {next_line_match.group(1).strip()}"
            break

    # 2. 📍 TRÍCH XUẤT ĐỘNG DANH SÁCH CHI NHÁNH VÀ HOTLINE ĐI KÈM
    # Tách đoạn intro thành từng dòng để duyệt tuyến tính, tránh đè lấn địa chỉ lên nhau
    lines = [line.strip() for line in intro_text.split('\n') if line.strip()]
    
    current_location = None

    for i, line in enumerate(lines):
        # Dấu hiệu nhận biết một dòng Địa chỉ (Bắt đầu bằng emoji ghim vị trí hoặc từ khóa Cơ sở)
        if line.startswith('📍') or re.match(r'^(?:Cơ sở|Địa chỉ|CS)\s*\d*\s*:', line, re.IGNORECASE):
            # Làm sạch tiền tố
            address_clean = re.sub(r'^(?:📍|Cơ sở|Địa chỉ|CS)\s*\d*\s*:?\s*', '', line, flags=re.IGNORECASE).strip()
            
            # Cố gắng phán đoán thành phố từ chuỗi địa chỉ
            city = "Đà Nẵng" if "Đà Nẵng" in address_clean else ("Nha Trang" if "Nha Trang" in address_clean else "Hồ Chí Minh" if "Hồ Chí Minh" in address_clean else "")
            
            current_location = {
                "address": address_clean,
                "city": city,
                "hotline": ""
            }
            result["locations"].append(current_location)
            continue
        
        # Nếu dòng hiện tại chứa từ khóa Hotline và ngay trước đó vừa tìm thấy một địa chỉ
        if current_location and ("hotline" in line.lower() or "sđt" in line.lower() or "liên hệ" in line.lower()):
            phone_numbers = re.sub(r'^(?:Hotline|SĐT|Liên hệ)\s*[^:]*:\s*', '', line, flags=re.IGNORECASE).strip()
            current_location["hotline"] = phone_numbers
            # Xử lý xong thì giải phóng biến tạm để tránh dòng hotline phía dưới bám nhầm vào chi nhánh cũ
            current_location = None

    # Nếu quét theo dòng thất bại (do định dạng page không dùng emoji chuẩn), bóc thô dòng Page Vị Trí của FB
    if not result["locations"]:
        # Tìm dòng có định dạng: [Số nhà, Tên đường], [Tên Thành Phố], Vietnam
        geo_match = re.search(r'([^\n,]+,\s*[^\n,]+),\s*([^\n,]+),\s*Vietnam', intro_text, re.IGNORECASE)
        if geo_match:
            result["locations"].append({
                "address": geo_match.group(1).strip(),
                "city": geo_match.group(2).strip(),
                "hotline": result["phones"][0] if result["phones"] else ""
            })

    # 3. 🌐 TỰ ĐỘNG THIẾT LẬP USP TỪ DANH TIẾNG DOMAIN CÀO VỀ
    # AI sẽ dựa vào các chứng chỉ uy tín từ tên miền để tăng sức thuyết phục cho bài viết
    for domain in result["domains"]:
        if "guide.michelin.com" in domain.lower():
            result["usp"].append("Thương hiệu đạt chứng nhận danh giá từ tổ chức Michelin Guide.")
        if "tripadvisor.com" in domain.lower():
            result["usp"].append("Nằm trong danh sách các địa điểm có lượt đề xuất cao trên TripAdvisor.")

    # 4. BÓC TÁCH ĐỘNG CÁC ĐỀ XUẤT/RATING (Nếu có)
    recommend_match = re.search(r'(\d+%\s*recommend[^\n]*)', intro_text, re.IGNORECASE)
    if recommend_match:
        result["usp"].append(recommend_match.group(1).strip())

    logger.info(f"[_parse_business_context] Trích xuất động hoàn tất. Phát hiện {len(result['locations'])} chi nhánh.")
    return result


def _fallback_regex_parser(k5_text: str, default_struct: dict) -> dict:
    """Bộ bóc tách dự phòng từ k5_text nếu cục json thô bị lỗi cấu trúc hoàn toàn."""
    if not k5_text:
        return default_struct
    try:
        loc_match = re.search(r'LOCATIONS:\s*(\[.*?\])', k5_text, re.DOTALL)
        if loc_match:
            default_struct["locations"] = json.loads(loc_match.group(1))
        usp_match = re.search(r'USP:\s*(\[.*?\])', k5_text, re.DOTALL)
        if usp_match:
            default_struct["usp"] = json.loads(usp_match.group(1))
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

    # ── K1: Brand Foundation ────────────────────────────────────────
    k1_md, purpose, taglines = _build_k1_markdown(k1)

    # ── K2: Customer Insights ───────────────────────────────────────
    k2_md, audience = _build_k2_markdown(k2)

    # ── K3: Content Patterns ─────────────────────────────────────────
    k3_md = _build_k3_markdown(k3)

    # ── K4: Behavior Rules ───────────────────────────────────────────
    k4_md = _build_k4_markdown(k4)

    # ── K5: Examples (verbatim post thật, không qua LLM) ─────────────
    k5_md = _build_k5_examples_markdown(posts)

    # ── K6: Tone Analysis + 4 trục slider ────────────────────────────
    k6_md, tone_base, sliders = _build_k6_markdown(k6)

    # ── K7: Vocabulary Rules ──────────────────────────────────────────
    k7_md = _build_k7_markdown(k7)

    # ── Business facts (JSON field riêng, không phải K-doc) ──────────
    business_facts = _parse_business_context(k5, k5_input)

    # ── Channels (dựa trên raw text K3 + K4, giữ logic cũ) ────────────
    channels = _channels(k3, k4)

    # ── desired_tone: tóm tắt ngắn từ TONE_BASE (K6) ──────────────────
    desired_tone = ", ".join(tone_base[:3]) if tone_base else "Chuyên nghiệp"

    result = {
        "business_id": bid,
        "name": bname,

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

    data = {
        "task": {
            "business_id": result.get("business_id") if isinstance(result, dict) else getattr(result, 'business_id', None),
            "business_name": result.get("business_name") if isinstance(result, dict) else getattr(result, 'business_name', None),
        },
        "result": {
            "serp_data": result.get("serp_data") if isinstance(result, dict) else getattr(result, 'serp_data', {}),
            "fb_brand": result.get("fb_brand") if isinstance(result, dict) else getattr(result, 'fb_brand', {}),
            "final_report": result.get("final_report") if isinstance(result, dict) else getattr(result, 'final_report', None),
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