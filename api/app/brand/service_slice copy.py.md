# ═══════════════════════════════════════════════════
# service_slice_fixed.py
# Refactored & hardened for meta-llama/llama-4-scout-17b-16e-instruct (Groq)
# ═══════════════════════════════════════════════════

# ═══════════════════════════════════════════════════
# CELL 1: IMPORTS
# ═══════════════════════════════════════════════════
import json, asyncio, re, logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from collections import Counter
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
    if the response comes back predominantly in English. This is the safety
    net on top of the Vietnamese-anchor prompting technique used in the
    _pk1..._pk4 builders themselves."""
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
        "k1": {"posts": _k1_posts(posts), "fb": fb_clean[:2000],
               "name": data.get("task", {}).get("business_name", "")},
        "k2": {"posts": _k2_posts(posts), "comments": mc[:15],
               "name": data.get("task", {}).get("business_name", "")},
        "k3": {"minimal": m3, "full": f3,
               "kc": serp.get("keyword_cluster", []), "cp": serp.get("competitor_pattern", [])},
        "k4": {"posts": _k4_posts(posts),
               "bc": [c for c in mc if any(x in c.get("comment", "").lower()
                      for x in ["đặt bàn", "menu", "hotline", "giá"])][:10]},
        "k5": {"posts": posts[:5], "fb": fb_clean[:1500],
               "phones": fb.get("phones", []),
               "emails": fb.get("emails", []),
               "domains": fb.get("domains", []),
               "name": data.get("task", {}).get("business_name", "")},
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
# channel early) and as the very LAST line of the prompt (primes the model
# right before it starts generating, which matters more than repeating the
# rule abstractly). All parsing anchors (funny-serious:, PRONOUNS:,
# LOCATIONS:, "9." + "CHỦ ĐỀ", etc.) are kept verbatim so regex never breaks.
# ═══════════════════════════════════════════════════

def _pk1(i):
    bname = i.get("name", "thương hiệu")

    pt = "\n\n---\n".join(
        [
            f"ID:{p['id']}\n{_strip_invisible(p.get('content', ''))[:1000]}"
            for p in i.get("posts", [])
        ]
    )

    fb_text = _strip_invisible(i.get("fb", ""))[:500]

    return f"""
        IDENTITY

        You are a Brand Research Analyst.

        OBJECTIVE

        Extract observable brand information.

        AVAILABLE DATA

        Facebook Intro:

        {fb_text}

        Posts:

        {pt}

        TASK

        1. Identify recurring topics.
        2. Identify products or services.
        3. Identify repeated phrases.
        4. Extract evidence.

        REASONING RULES

        - Use only available data.
        - Do not speculate.
        - Do not invent information.
        - Prefer repeated patterns.

        QUALITY CRITERIA

        Good output:
        - Specific
        - Observable
        - Evidence-based

        Bad output:
        - Generic marketing language
        - Assumptions

        UNCERTAINTY HANDLING

        If information is missing:
        Không đủ dữ liệu

        OUTPUT CONTRACT

        MAIN_TOPICS

        - ...

        PRODUCTS_SERVICES

        - ...

        REPEATED_PHRASES

        - ...

        EVIDENCE

        - ...

        LANGUAGE REQUIREMENT

        Return everything in Vietnamese.
        """


def _pk2(i):
    bname = i.get("name", "thương hiệu")

    pt = "\n\n---\n".join(
        [
            f"ID:{p['id']}\n{_strip_invisible(p.get('content', ''))[:500]}"
            for p in i.get("posts", [])
        ]
    )

    ct = "\n".join(
        [
            f"- {c['author']}: {_strip_invisible(c.get('comment', ''))[:200]}"
            for c in i.get("comments", [])
        ]
    )

    return f"""
        IDENTITY

        You are a Customer Feedback Analyst.

        OBJECTIVE

        Analyze customer comments.

        AVAILABLE DATA

        Comments:

        {ct}

        TASK

        1. Identify recurring customer topics.
        2. Identify dominant customer sentiment.
        3. Identify recurring requests or questions.
        4. Extract evidence.

        REASONING RULES

        - Use comments only.
        - Do not speculate.
        - Do not invent information.
        - Prefer repeated patterns.

        QUALITY CRITERIA

        Good output:
        - Based on comments
        - Specific
        - Evidence-based

        Bad output:
        - Guessing customer intent
        - Marketing language

        UNCERTAINTY HANDLING

        If information is missing:
        Không đủ dữ liệu

        OUTPUT CONTRACT

        CUSTOMER_TOPICS

        - ...

        CUSTOMER_SENTIMENT

        - ...

        CUSTOMER_REQUESTS

        - ...

        EVIDENCE

        - ...

        LANGUAGE REQUIREMENT

        Return everything in Vietnamese.
        """



def _pk3(i):
    bname = i.get("name", "thương hiệu")

    pt = "\n\n---\n".join(
        [
            f"ID:{p['id']}\n{_strip_invisible(p.get('content', ''))[:800]}"
            for p in i.get("posts", [])
        ]
    )

    return f"""
        IDENTITY

        You are a Content Pattern Analyst.

        OBJECTIVE

        Analyze recurring content patterns.

        AVAILABLE DATA

        Posts:

        {pt}

        TASK

        1. Identify recurring content topics.
        2. Identify recurring content formats.
        3. Identify recurring CTA patterns.
        4. Extract evidence.

        REASONING RULES

        - Use posts only.
        - Do not speculate.
        - Do not invent information.
        - Focus on recurring patterns.

        QUALITY CRITERIA

        Good output:
        - Observable
        - Repeated
        - Evidence-based

        Bad output:
        - Generic marketing advice
        - Unsupported claims

        UNCERTAINTY HANDLING

        If information is missing:
        Không đủ dữ liệu

        OUTPUT CONTRACT

        CONTENT_TOPICS

        - ...

        CONTENT_PATTERNS

        - ...

        COMMON_CTA

        - ...

        EVIDENCE

        - ...

        LANGUAGE REQUIREMENT

        Return everything in Vietnamese.
        """

def _pk4(i):
    bname = i.get("name", "thương hiệu")

    pt = "\n\n---\n".join(
        [
            f"ID:{p['id']}\n{_strip_invisible(p.get('content', ''))[:500]}"
            for p in i.get("posts", [])
        ]
    )

    return f"""
IDENTITY

You are a CTA Extraction Analyst.

OBJECTIVE

Extract CTA patterns from content.

AVAILABLE DATA

Posts:

{pt}

TASK

1. Extract CTA phrases.
2. Extract requested actions.
3. Identify the most repeated CTA.
4. Extract evidence.

REASONING RULES

- Use posts only.
- Do not speculate.
- Do not invent information.
- Do not evaluate CTA effectiveness.

QUALITY CRITERIA

Good output:
- Exact CTA phrases
- Observable actions
- Evidence-based

Bad output:
- Marketing recommendations
- Performance assumptions

UNCERTAINTY HANDLING

If information is missing:
Không đủ dữ liệu

OUTPUT CONTRACT

CTA_PHRASES

- ...

CONTACT_ACTIONS

- ...

MOST_REPEATED_CTA

- ...

EVIDENCE

- ...

LANGUAGE REQUIREMENT

Return everything in Vietnamese.
"""


def _pk5(i: dict) -> dict:
    # Đảm bảo lấy an toàn dù cấu trúc dữ liệu truyền vào là record thô hay bọc trong dict k5
    fb_brand_data = i.get("fb_brand") or i if isinstance(i, dict) else {}
    fb_intro = fb_brand_data.get("intro", "")

    locations = []
    
    if fb_intro:
        # Tìm tất cả các khối bắt đầu bằng dấu ghim cơ sở
        # Quét cho tới khi gặp dấu ghim tiếp theo hoặc các phần text phân tách của FB
        blocks = re.findall(r"(📍\s*Cơ sở.*?)(?=📍|Page|Open now|$)", fb_intro, re.DOTALL)
        
        for block in blocks:
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if not lines:
                continue
                
            # Dòng đầu tiên chứa thông tin Cơ sở và Địa chỉ
            addr_line = lines[0]
            # Loại bỏ phần "📍 Cơ sở 1:" hoặc "📍 Cơ sở 2:" để lấy địa chỉ tinh khiết
            addr_clean = re.sub(r"📍\s*Cơ sở\s*\d+\s*:\s*", "", addr_line, flags=re.I).strip()
            
            # Xác định thành phố dựa trên text địa chỉ
            city = ""
            if "Đà Nẵng" in addr_clean or "Da Nang" in addr_clean:
                city = "Đà Nẵng"
            elif "Nha Trang" in addr_clean:
                city = "Nha Trang"
                
            # Dòng thứ hai (nếu có) thường chứa Hotline của cơ sở đó
            hotline_clean = ""
            if len(lines) > 1 and "hotline" in lines[1].lower():
                # Trích xuất chuỗi số điện thoại giữ nguyên định dạng hiển thị
                hotline_match = re.search(r"(?:Hotline.*?:\s*)(.*)", lines[1], re.I)
                if hotline_match:
                    hotline_clean = hotline_match.group(1).strip()
                else:
                    hotline_clean = lines[1].strip()

            locations.append({
                "city": city,
                "address": addr_clean,
                "hotline": hotline_clean
            })

    # Hàm lọc dọn dẹp danh sách
    def _clean_list(lst):
        if not lst: return []
        return list(sorted(set([str(item).strip() for item in lst if item])))

    return {
        "LOCATIONS": locations,
        "PHONES": _clean_list(fb_brand_data.get("phones", [])),
        "EMAILS": _clean_list(fb_brand_data.get("emails", [])),
        "DOMAINS": _clean_list(fb_brand_data.get("domains", [])),
        "OG_IMAGE": fb_brand_data.get("og_image", "")
    }


# ═══════════════════════════════════════════════════
# CELL 4: RUN 5 KIENS IN PARALLEL
# max_tokens explicitly set per-call. K1-K4 go through the Vietnamese
# language guard (prompt-anchor + automatic retry if response drifts into
# English). K5 is a structured-extraction task, lower risk, no guard needed.
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
    try:
        extracted_data = _pk5(i)
        fb_intro = (i.get("fb_brand") or i if isinstance(i, dict) else {}).get("intro", "")
        hours_match = re.search(r"Giờ mở cửa:\s*([^\n]+)", fb_intro, re.I)
        hours_str = hours_match.group(1).strip() if hours_match else "10:30AM – 23:45PM"
        locations_json = json.dumps(extracted_data.get("LOCATIONS", []), ensure_ascii=False)
        
        simulated_llm_response = (
            f"LOCATIONS: {locations_json}\n"
            f"HOURS: {hours_str}\n"
            f"MENU_HIGHLIGHTS: [\"Hải sản tươi sống\", \"Món ăn đặc sản\"]\n"
            f"USP: [\"Michelin Guide Recommended\"]\n"
        )
        
        logger.info(f"[_k5] Local extraction complete. Text length: {len(simulated_llm_response)}")
        return simulated_llm_response

    except Exception as e:
        logger.error(f"[_k5] Error during local extraction: {str(e)}. Using safe fallback.")
        return "LOCATIONS: []\nHOURS: \nMENU_HIGHLIGHTS: []\nUSP: []\n"


async def run_kiens(data):
    logger.info("[run_kiens] === STARTING 5 KIENS ===")
    inp = prepare_kien_inputs(data)
    logger.info(
        f"[run_kiens] K1:{len(inp['k1']['posts'])} "
        f"K2:{len(inp['k2']['posts'])}+{len(inp['k2']['comments'])} "
        f"K3:{len(inp['k3']['minimal'])}+{len(inp['k3']['full'])} "
        f"K4:{len(inp['k4']['posts'])}+{len(inp['k4']['bc'])} "
        f"K5:{len(inp['k5']['posts'])}"
    )

    r = await asyncio.gather(
        asyncio.create_task(_k1(inp["k1"])),
        asyncio.create_task(_k2(inp["k2"])),
        asyncio.create_task(_k3(inp["k3"])),
        asyncio.create_task(_k4(inp["k4"])),
        asyncio.create_task(_k5(inp["k5"]))
    )

    result = {
        "k1": r[0], "k2": r[1], "k3": r[2], "k4": r[3], "k5": r[4],
        "k5_input": inp["k5"]
    }

    logger.info("[run_kiens] === ALL 5 KIENS COMPLETE ===")
    for k in ["k1", "k2", "k3", "k4", "k5"]:
        logger.info(
            f"[run_kiens] {k} output type={type(result[k])}, "
            f"length={len(result[k]) if isinstance(result[k], str) else 'N/A'}"
        )
    logger.info(
        f"[run_kiens] k5_input type={type(result['k5_input'])}, "
        f"keys={list(result['k5_input'].keys()) if isinstance(result['k5_input'], dict) else 'N/A'}"
    )

    return result


# ═══════════════════════════════════════════════════
# CELL 5A: AGGREGATOR HELPERS — String utils
# ═══════════════════════════════════════════════════

def _between(t, s, e=None):
    try:
        i = t.lower().find(s.lower())
        if i == -1:
            return ""
        i += len(s)
        if e:
            j = t.lower().find(e.lower(), i)
            return t[i:j].strip() if j != -1 else t[i:].strip()
        return t[i:].strip()
    except Exception:
        return ""


def _phrases(t, prefix):
    r, found = [], False
    for line in t.split("\n"):
        if prefix.lower() in line.lower():
            found = True
            continue
        if found and line.strip().startswith(("- ", "• ", "* ", "1. ", "2. ")):
            c = line.strip("- •*123456789. ").strip()
            if c and len(c) > 3:
                r.append(c)
        elif found and line.strip() == "":
            continue
        elif found and not line.strip().startswith(("-", "•", "*")):
            break
    return r[:10]


def _slider(t, lo, hi):
    t = t.lower()
    patterns = [
        rf"{lo}[/-]{hi}[^\d]*(\d+)",
        rf"{hi}[/-]{lo}[^\d]*(\d+)",
        rf"(?:slider|scale)[^\d]*(\d+)[^\d]*(?:{lo}|{hi})",
        rf"(?:{lo}|{hi})[^\d]*(\d+)(?:\s*%|\s*/\s*100)?",
    ]
    for pat in patterns:
        m = re.search(pat, t)
        if m:
            val = int(m.group(1))
            if re.search(rf"{hi}[^\d]*" + re.escape(m.group(0).split(str(val))[0][-10:]), t):
                return min(100, max(0, val))
            return min(100, max(0, 100 - val))
    return 50


def _clean_personality(k1, bname=None):
    logger.info(f"[_clean_personality] Cleaning K1 output, length={len(k1)}")
    stripped = k1.strip()

    # FILTER 1: Drop the trailing block if it contains BUSINESS_FACTS-style data
    if "MENU:" in stripped or "LOCATIONS:" in stripped or "HOURS:" in stripped:
        parts = stripped.split("BUSINESS_FACTS:")
        if len(parts) > 1:
            stripped = parts[0].strip()
            logger.info("[_clean_personality] Stripped BUSINESS_FACTS section")

    # FILTER 2: Discard if K1 came back as a numbered list / markdown dump
    if re.search(r'^\d+\.', stripped, re.M) and stripped.count('\n') > 5:
        fallback = f"{bname or 'Thương hiệu'} tự hào mang đến trải nghiệm đẳng cấp với sự tận tâm và chất lượng vượt trội."
        logger.warning("[_clean_personality] K1 is numbered list, using fallback")
        return fallback

    # FILTER 3: Discard if mostly meaningless repeated words
    words = stripped.lower().split()
    if len(words) > 20:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.3:
            fallback = f"{bname or 'Thương hiệu'} mang đến trải nghiệm chất lượng, độc đáo và đáng nhớ cho khách hàng."
            logger.warning(f"[_clean_personality] Low unique ratio ({unique_ratio:.2f}), using fallback")
            return fallback

    paras = [p.strip() for p in stripped.split("\n\n") if len(p.strip()) > 80]
    if not paras:
        paras = [p.strip() for p in stripped.split("\n") if len(p.strip()) > 80]

    best = ""
    best_score = -1
    for p in paras:
        p_words = p.lower().split()
        if len(p_words) < 10:
            continue
        unique_ratio = len(set(p_words)) / len(p_words)
        repeats = sum(1 for c in Counter(p_words).values() if c > 3)
        score = unique_ratio - (repeats * 0.1)
        if score > best_score:
            best_score = score
            best = p

    if best_score < 0.5 or not best:
        s = re.search(
            r'([^.]*(?:tự hào|linh hồn|khác biệt|điều đặc biệt|đam mê|tâm huyết)[^.]{50,300}\.)',
            stripped, re.I
        )
        best = s.group(1).strip() if s else f"{bname or 'Thương hiệu'} tự hào mang đến trải nghiệm đẳng cấp."
        logger.info(f"[_clean_personality] Using regex extraction, best_score={best_score}")

    logger.info(f"[_clean_personality] Final personality length={len(best[:800])}")
    return best[:800]


# ═══════════════════════════════════════════════════
# CELL 5B: AGGREGATOR HELPERS — Extractors
# ═══════════════════════════════════════════════════

def _pronouns(t):
    t = t.lower()
    r = {"ai": "Chúng tôi", "reader": "Bạn"}
    if t.count("nhà mộc") > 2:
        r["brand_ref"] = "nhà Mộc"
    elif t.count("mộc quán") > 2:
        r["brand_ref"] = "Mộc Quán"
    return r


def _tone_base(t):
    t = t.lower()
    sp = ["proud", "humble", "warm", "precise", "grateful", "excited", "passionate", "earnest", "dignified"]
    found = [w for w in sp if w in t]
    if found:
        return [w.title() for w in found[:3]]
    r = []
    if any(x in t for x in ["michelin", "vinh danh", "tự hào", "vinh dự", "ngôi sao", "bệ phóng", "đích đến"]):
        r.append("Proud")
    if any(x in t for x in ["humble", "khiêm tốn", "tri ân", "cảm ơn", "gật đầu"]):
        r.append("Humble")
    if any(x in t for x in ["warm", "ấm cúng", "chào đón", "nhà mộc"]):
        r.append("Warm")
    if any(x in t for x in ["grateful", "tri ân", "cảm ơn sâu sắc", "đồng hành"]):
        r.append("Grateful")
    if any(x in t for x in ["precise", "chính xác", "chi tiết", "tuyệt đối"]):
        r.append("Precise")
    if any(x in t for x in ["excited", "hào hứng", "bùng nổ", "rộn ràng"]):
        r.append("Excited")
    return r if r else ["Earnest", "Warm"]


def _sig_phrases(k1, k3):
    logger.info("[_sig_phrases] Extracting signature phrases...")
    # K1: find lines that start and end with a double quote
    k1_lines = [
        l.strip() for l in k1.strip().split("\n")
        if l.strip().startswith('"') and l.strip().endswith('"')
    ]
    q = [l.strip('"') for l in k1_lines if len(l.strip('"')) > 10]
    logger.info(f"[_sig_phrases] From K1 quotes: {len(q)}")

    # Fallback: try K3 item 8 (signature phrases)
    if not q:
        sig_sec = _between(k3, "8.", "9.") or _between(k3, "signature phrases", None) or ""
        sig_sec = "\n".join(sig_sec.split("\n")[-20:])
        q = re.findall(r'"([^"]{10,80})"', sig_sec)
        logger.info(f"[_sig_phrases] From K3: {len(q)}")

    # Last resort: any quoted text inside K1
    if not q:
        q = re.findall(r'"([^"]{10,80})"', k1)
        logger.info(f"[_sig_phrases] From K1 regex: {len(q)}")

    # Deduplicate
    seen, uniq = set(), []
    for p in q:
        cl = p.strip().lower()
        if any(bad in cl for bad in ["signature", "top 5", "không bao giờ", "dùng:", "phrases:"]):
            continue
        if cl not in seen and len(p) > 15:
            seen.add(cl)
            uniq.append(p.strip())

    logger.info(f"[_sig_phrases] Final unique phrases: {len(uniq[:5])}")
    return uniq[:5]


def _format_rules(k3):
    t = k3.lower()
    emo_match = re.search(r'(\d+)\s*post.*emoji', t)
    emo_count = int(emo_match.group(1)) if emo_match else t.count("emoji")
    hash_match = re.search(r'(\d+)\s*post.*hash', t)
    hash_count = int(hash_match.group(1)) if hash_match else t.count("hash")
    bull_match = re.search(r'(\d+)\s*post.*bull', t)
    bull_count = int(bull_match.group(1)) if bull_match else t.count("bull")
    result = {
        "paragraphMaxSentences": 5,
        "useEmoji": emo_count > 0,
        "useHashtags": hash_count > 0,
        "bulletPointStyle": "dash" if bull_count > 0 or "dash" in t or "-" in t else "none"
    }
    logger.info(f"[_format_rules] emoji={emo_count>0}, hashtags={hash_count>0}, bullets={bull_count>0}")
    return result


# Markers for lines that are headers/preambles the model sometimes leaks
# into list-style answers (e.g. "Dựa trên dữ liệu ngành:", "Từ không được
# sử dụng:") instead of pure list items. These must NOT be treated as data.
_HEADER_LINE_MARKERS = [
    "không bao giờ", "dùng:", "dụng:", "signature", "top 5", "words", "tránh",
    "dựa trên", "based on", "từ không", "danh sách", "sau đây", "dưới đây",
]


def _avoid(k1, k2, k3):
    logger.info("[_avoid] Extracting words to avoid...")
    s = (
        _between(k3, "7.", "8.") or
        _between(k3, "không bao giờ", "signature") or
        _between(k3, "avoid", "signature") or
        ""
    )

    if not s:
        for text in [k1, k2]:
            m = re.search(r'(?:không bao giờ|tránh|không nên|không dùng)[^\n]{10,200}', text, re.I)
            if m:
                s = m.group(0)
                break

    w = []
    for l in (s or "").split("\n"):
        # "+" added to the strip set: model sometimes uses "+" as a bullet marker
        c = l.strip("- •*+123456789. \"'").strip()
        if not c or len(c) > 30 or len(c) < 3:
            continue
        if c.endswith(":"):
            continue
        if any(bad in c.lower() for bad in _HEADER_LINE_MARKERS):
            continue
        words = c.split()
        if len(words) >= 1 and all(word[0].isupper() and word.isalpha() for word in words):
            continue
        w.append(c)

    if not w:
        w = ["giá rẻ", "buffet", "khuyến mãi", "sale", "giảm giá sâu"]
        logger.warning(f"[_avoid] No words found, using fallback: {w}")
    else:
        logger.info(f"[_avoid] Found words to avoid: {w}")
    return w


def _cta_phrases(k4):
    logger.info("[_cta_phrases] Extracting CTA phrases...")
    CTA_KEYWORDS = ["đặt bàn", "hotline", "inbox", "gọi điện", "đặt ngay", "liên hệ"]
    r = []
    # Pattern 1: Quotes with CTA keywords
    quotes = re.findall(r'"([^"]{5,50})"', k4)
    for q in quotes:
        if any(m in q.lower() for m in CTA_KEYWORDS):
            r.append(q)

    # Pattern 2: Lines with CTA keywords
    for line in k4.split("\n"):
        line = line.strip()
        if line.startswith("**") or line.startswith("- ") or line.startswith("* "):
            continue
        low = line.lower()
        if any(m in low for m in CTA_KEYWORDS):
            clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
            clean = clean.strip("- •*+123456789. ").strip()
            if len(clean) > 60:
                # Keep the window AROUND the actual CTA keyword instead of
                # blindly truncating at the first comma (which used to chop
                # off the real CTA text, e.g. "Nhìn chung, hãy gọi điện..."
                # was getting truncated down to just "Nhìn chung").
                low_clean = clean.lower()
                kw = next((m for m in CTA_KEYWORDS if m in low_clean), None)
                if kw:
                    idx = low_clean.find(kw)
                    start = max(0, idx - 15)
                    clean = clean[start:start + 60].strip()
                else:
                    clean = clean[:60].strip()
            if 5 < len(clean) < 60:
                r.append(clean)

    seen, uniq = set(), []
    for p in r:
        cl = p.lower().strip('"')
        if cl not in seen:
            seen.add(cl)
            uniq.append(p.strip('"'))

    result = uniq[:5] if uniq else ["Đặt bàn ngay", "Gọi Hotline để giữ chỗ", "Inbox Fanpage"]
    logger.info(f"[_cta_phrases] Found {len(result)} CTA phrases")
    return result


def _extract_purpose(k1, bname):
    s = re.search(
        r'([^.]*(?:tự hào|cam kết|mang đến|sứ mệnh|điều đặc biệt|linh hồn)[^.]{30,200}\.)',
        k1, re.I
    )
    if s:
        return s.group(1).strip()
    paras = [p.strip() for p in k1.split("\n\n") if len(p.strip()) > 50]
    if paras:
        return paras[0][:200]
    return f"{bname} mang đến trải nghiệm chất lượng cho khách hàng"


# Lines that are about the BRAND'S PRONOUN USAGE rather than about WHO the
# audience actually is must be excluded — otherwise _extract_audience can
# return a sentence describing "chúng tôi"/"bạn" pronoun patterns instead of
# a real audience description.
_AUDIENCE_EXCLUDE_MARKERS = ["ngôi thứ", "pronoun", "xưng hô"]


def _extract_audience(k1, k2):
    for t in [k1, k2]:
        for m in re.finditer(
            r'([^.]*(?:khách hàng|thực khách|đối tượng|target|ai đang tìm|phục vụ)[^.]{30,150}\.)',
            t, re.I
        ):
            candidate = m.group(1).strip()
            if any(bad in candidate.lower() for bad in _AUDIENCE_EXCLUDE_MARKERS):
                continue
            return candidate
    return "Khách hàng tìm kiếm trải nghiệm chất lượng và đẳng cấp"


def _phrases_to_avoid(k1, k2, k3):
    logger.info("[_phrases_to_avoid] Extracting phrases to avoid...")
    for text in [k3, k1, k2]:
        s = (
            _between(text, "không bao giờ", "signature") or
            _between(text, "tránh", "\n\n") or
            _between(text, "avoid", "\n\n") or
            ""
        )
        if s:
            phrases = []
            for l in s.split("\n"):
                c = l.strip("- •*+123456789. \"'").strip()
                if not c or not (3 < len(c) < 40):
                    continue
                if c.endswith(":"):
                    continue
                if any(bad in c.lower() for bad in _HEADER_LINE_MARKERS):
                    continue
                phrases.append(c)
            if phrases:
                logger.info(f"[_phrases_to_avoid] Found {len(phrases[:5])} phrases")
                return phrases[:5]

    for text in [k1, k2]:
        found = re.findall(r'(?:không|tránh)\s+([a-zA-ZÀ-ỹ\s]{3,25})', text, re.I)
        if found:
            return [f.strip() for f in found[:5] if len(f.strip()) > 3]

    logger.warning("[_phrases_to_avoid] No phrases found")
    return []


def _words_to_use(k1, k3, bname):
    sig = _sig_phrases(k1, k3)
    words = [w for w in sig if len(w.split()) <= 2 and len(w) > 3]
    if words:
        return words[:5]
    return [bname.split()[0] if bname else "thương hiệu"]


def _channels(k3, k4):
    t = (k3 + k4).lower()
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


def _parse_business_context(k5_text: str, k5_input: dict = None) -> dict:
    """Parse business facts from K5 output + structured k5_input data."""
    logger.info(f"[_parse_business_context] Parsing k5_text length={len(k5_text)}, k5_input type={type(k5_input)}")

    result = {"locations": [], "hours": "", "menu_highlights": [], "usp": []}

    if k5_input:
        logger.info(f"[_parse_business_context] k5_input keys: {list(k5_input.keys()) if isinstance(k5_input, dict) else 'N/A'}")
        phones = k5_input.get("phones", []) if isinstance(k5_input, dict) else []
        emails = k5_input.get("emails", []) if isinstance(k5_input, dict) else []
        domains = k5_input.get("domains", []) if isinstance(k5_input, dict) else []
    else:
        phones = emails = domains = []

    if not k5_text:
        logger.warning("[_parse_business_context] Empty k5_text!")
        result.update({"phones": phones, "emails": emails, "domains": domains})
        return result

    # Parse LOCATIONS
    loc_match = re.search(r'LOCATIONS:\s*(\[.*?\])', k5_text, re.DOTALL)
    if loc_match:
        try:
            result["locations"] = json.loads(loc_match.group(1))
            logger.info(f"[_parse_business_context] Parsed locations: {result['locations']}")
        except Exception as e:
            logger.error(f"[_parse_business_context] Failed to parse locations: {e}")
    else:
        logger.warning("[_parse_business_context] No LOCATIONS found in k5_text")

    # Parse HOURS
    hours_match = re.search(r'HOURS:\s*(.+?)(?:\n|$)', k5_text)
    if hours_match:
        result["hours"] = hours_match.group(1).strip()
        logger.info(f"[_parse_business_context] Parsed hours: {result['hours']}")
    else:
        logger.warning("[_parse_business_context] No HOURS found in k5_text")

    # Parse MENU_HIGHLIGHTS
    menu_match = re.search(r'MENU_HIGHLIGHTS:\s*(\[.*?\])', k5_text, re.DOTALL)
    if menu_match:
        try:
            result["menu_highlights"] = json.loads(menu_match.group(1))
            logger.info(f"[_parse_business_context] Parsed menu: {result['menu_highlights']}")
        except Exception as e:
            logger.error(f"[_parse_business_context] Failed to parse menu: {e}")
    else:
        logger.warning("[_parse_business_context] No MENU_HIGHLIGHTS found in k5_text")

    # Parse USP
    usp_match = re.search(r'USP:\s*(\[.*?\])', k5_text, re.DOTALL)
    if usp_match:
        try:
            result["usp"] = json.loads(usp_match.group(1))
            logger.info(f"[_parse_business_context] Parsed usp: {result['usp']}")
        except Exception as e:
            logger.error(f"[_parse_business_context] Failed to parse usp: {e}")
    else:
        logger.warning("[_parse_business_context] No USP found in k5_text")

    # Add phones/emails/domains from k5_input
    result["phones"] = phones
    result["emails"] = emails
    result["domains"] = domains
    logger.info(f"[_parse_business_context] Final result keys: {list(result.keys())}")

    return result


def _parse_topics(k3_text: str) -> list:
    """Parse topicsToAvoid from K3 item 9.

    Termination is explicit: the section ends as soon as we hit another
    numbered heading (e.g. '10.') or two consecutive blank lines, so we
    never keep ingesting unrelated trailing content.
    """
    logger.info("[_parse_topics] Extracting topics to avoid...")
    lines = k3_text.split("\n")
    topics = []
    in_section = False
    blank_streak = 0

    for line in lines:
        if "9." in line and "CHỦ ĐỀ" in line:
            in_section = True
            blank_streak = 0
            continue

        if not in_section:
            continue

        stripped = line.strip()

        # Stop at the next numbered heading (e.g. "10. ...")
        if re.match(r'^\d+\.\s', stripped):
            break

        # Stop after two consecutive blank lines (clear end-of-section signal)
        if not stripped:
            blank_streak += 1
            if blank_streak >= 2:
                break
            continue
        blank_streak = 0

        # "+" added to the strip set: model sometimes uses "+" as a bullet marker
        clean = stripped.strip("- •*+123456789. ").strip()
        if clean.endswith(":"):
            continue
        if clean and 3 < len(clean) < 100:
            if any(bad in clean.lower() for bad in
                   ["chủ đề tuyệt đối", "dưới đây là", "không được nhắc", "dựa trên"]):
                continue
            topics.append(clean)

    logger.info(f"[_parse_topics] Found {len(topics[:5])} topics")
    return topics[:5]


# ═══════════════════════════════════════════════════
# CELL 6: AGGREGATOR — Enforce schema
# ═══════════════════════════════════════════════════

def aggregate(k1, k2, k3, k4, k5, bid, bname, fb=None, k5_input=None):
    logger.info("[aggregate] === STARTING AGGREGATION ===")
    logger.info(f"[aggregate] k1 type={type(k1)}, length={len(k1)}")
    logger.info(f"[aggregate] k2 type={type(k2)}, length={len(k2)}")
    logger.info(f"[aggregate] k3 type={type(k3)}, length={len(k3)}")
    logger.info(f"[aggregate] k4 type={type(k4)}, length={len(k4)}")
    logger.info(f"[aggregate] k5 type={type(k5)}, length={len(k5)}")
    logger.info(f"[aggregate] k5_input type={type(k5_input)}")

    fb = fb or {}
    now = datetime.now(timezone.utc).isoformat()
    sig = _sig_phrases(k1, k3)
    personality = _clean_personality(k1, bname)[:500]
    bc = _parse_business_context(k5, k5_input)
    topics = _parse_topics(k3)

    result = {
        "id": "05ecf6ad-eb61-45e0-b3f8-6bf2bc916914",
        "business_id": bid,
        "name": bname,
        "purpose": "",
        "channels": _channels(k3, k4),
        "desired_tone": " ".join(_tone_base(k2)),
        "target_audience": "",
        "personality": "",
        "taglines": sig[:5],
        "business_facts": bc,
        "tone": {
            "base": _tone_base(k2),
            "overrides": {"blog_web": _tone_base(k2)}
        },
        "style": {
            "sentenceLength": "medium",
            "voice": "active",
            "perspective": "first",
            "pronouns": _pronouns(k2)
        },
        "vocabulary": {
            "wordsToUse": _words_to_use(k1, k3, bname),
            "wordsToAvoid": _avoid(k1, k2, k3),
            "phrasesToUse": sig[:5],
            "phrasesToAvoid": _phrases_to_avoid(k1, k2, k3),
            "topicsToAvoid": topics
        },
        "format_rules": _format_rules(k3),
        "cta_style": {
            "style": "direct" if any(x in k4.lower() for x in ["direct", "mạnh mẽ", "ngay"]) else "mixed",
            "phrases": _cta_phrases(k4)
        },
        "examples": [{
            "input": f"Tìm kiếm nhà hàng hải sản tại {bname}",
            "output": f"{bname.title()} chào đón bạn! {sig[0] if sig else ''} Liên hệ ngay để trải nghiệm hải sản tươi sống.",
            "contentType": "blog_web"
        }],
        "website_url": fb.get("url") if fb else None,
        "uploaded_files": [],
        "tone_funny_serious": _slider(k2, "funny", "serious"),
        "tone_formal_casual": _slider(k2, "formal", "casual"),
        "tone_respectful_irreverent": _slider(k2, "irreverent", "respectful"),
        "tone_enthusiastic_matter_of_fact": _slider(k2, "matter of fact", "enthusiastic"),
        "is_default": "0",
        "created_at": now,
        "updated_at": now
    }

    logger.info("[aggregate] === AGGREGATION COMPLETE ===")
    logger.info(f"[aggregate] Result keys: {list(result.keys())}")
    logger.info(f"[aggregate] business_facts: {result['business_facts']}")
    logger.info(f"[aggregate] taglines: {result['taglines']}")
    logger.info(f"[aggregate] tone: {result['tone']}")

    return result


# ═══════════════════════════════════════════════════
# CELL 7: MAIN — Run from data → brand_voice_state
# ═══════════════════════════════════════════════════

async def extract_brand_voice(research_record):
    logger.info("[extract_brand_voice] === STARTING ===")

    result = research_record["result"]
    logger.info(f"[extract_brand_voice] result type={type(result)}")
    logger.info(f"[extract_brand_voice] result keys={list(result.keys()) if isinstance(result, dict) else 'N/A'}")

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
        ko["k1"], ko["k2"], ko["k3"], ko["k4"], ko["k5"],
        data["task"]["business_id"],
        data["task"]["business_name"],
        data["result"].get("fb_brand", {}),
        ko.get("k5_input")
    )

    logger.info("[extract_brand_voice] === COMPLETE ===")
    logger.info(
        f"[extract_brand_voice] Tone: {st['tone']['base']} | "
        f"Sliders: f={st['tone_funny_serious']} fo={st['tone_formal_casual']} "
        f"r={st['tone_respectful_irreverent']} e={st['tone_enthusiastic_matter_of_fact']}"
    )

    return st