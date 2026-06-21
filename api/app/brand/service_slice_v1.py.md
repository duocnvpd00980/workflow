# ═══════════════════════════════════════════════════
# CELL 1: IMPORTS
# ═══════════════════════════════════════════════════
import json, asyncio, re
from typing import Dict, Any, List
from datetime import datetime, timezone
from app.llm_clients import call_groq


import re


# ═══════════════════════════════════════════════════
# CELL 2A: SLICER — Hàm phụ
# ═══════════════════════════════════════════════════

def _k1_posts(posts): 
    return sorted(posts, key=lambda p: len(p.get("content","")), reverse=True)[:5]

def _k2_posts(posts):
    def cls(p):
        c = p.get("content","").lower()
        if "michelin" in c: return 0
        if any(x in c for x in ["diff","pháo hoa","sự kiện"]): return 1
        if any(x in c for x in ["giao hàng","tận nhà","delivery","take-away"]): return 2
        return 3
    b = [[],[],[],[]]
    for p in posts: b[cls(p)].append(p)
    r = []
    for bucket in b: r.extend(bucket[:2])
    if len(r) < 8:
        used = {p["id"] for p in r}
        for p in posts:
            if p["id"] not in used: r.append(p)
            if len(r) >= 8: break
    return r[:8]

def _k3_posts(posts):
    minimal = []
    for p in posts:
        c = p.get("content","")
        s = [x.strip() for x in c.replace("!",".").replace("?",".").split(".") if x.strip()]
        minimal.append({
            "id": p["id"], "first": s[0][:100] if s else "",
            "last": s[-1][:100] if len(s)>1 else "", "wc": len(c.split()),
            "emoji": any(ord(ch)>10000 for ch in c),
            "hash": "#" in c, "bi": "----------" in c, "bull": c.count("\n-")
        })
    return minimal, posts[:2]

def _k4_posts(posts):
    m = ["Hotline:","CS1","Đặt bàn","Inbox","Gọi điện"]
    r = [p for p in posts if any(x in p.get("content","") for x in m)]
    return r if len(r)>=3 else posts[-4:]


def _clean_fb_intro(raw_intro: str) -> str:
    """Lọc UI noise từ fb intro, chỉ giữ thông tin hữu ích."""
    if not raw_intro:
        return ""
    lines = raw_intro.split("\n")
    # Bỏ các dòng UI noise
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
    return "\n".join(cleaned)



# ═══════════════════════════════════════════════════
# CELL 2B: SLICER — prepare_kien_inputs
# ═══════════════════════════════════════════════════

def prepare_kien_inputs(data):
    posts = data.get("posts",[])
    comments = data.get("comments",[])
    serp = data.get("result",{}).get("serp_data",{})
    fb = data.get("result",{}).get("fb_brand",{})
    mc = [c for c in comments if len(c.get("comment",""))>20 and c.get("author")!="Ẩn danh"]
    m3, f3 = _k3_posts(posts)
    fb_clean = _clean_fb_intro(fb.get("intro",""))
    return {
        "k1": {"posts": _k1_posts(posts), "fb": fb_clean[:2000],
               "name": data.get("task",{}).get("business_name","")},
        "k2": {"posts": _k2_posts(posts), "comments": mc[:15],
               "name": data.get("task",{}).get("business_name","")},
        "k3": {"minimal": m3, "full": f3,
               "kc": serp.get("keyword_cluster",[]), "cp": serp.get("competitor_pattern",[])},
        "k4": {"posts": _k4_posts(posts),
               "bc": [c for c in mc if any(x in c.get("comment","").lower() 
                      for x in ["đặt bàn","menu","hotline","giá"])][:10]},
        "k5": {"posts": posts[:5], "fb": fb_clean[:1500],
               "phones": fb.get("phones", []),
               "emails": fb.get("emails", []),
               "domains": fb.get("domains", []),
               "name": data.get("task",{}).get("business_name","")},
    }



# ═══════════════════════════════════════════════════
# CELL 3A: PROMPT BUILDERS — K1 & K2
# ═══════════════════════════════════════════════════

def _pk1(i):
    pt = "\n\n---\n".join([f"ID:{p['id']}\n{p.get('content','')[:3000]}" for p in i["posts"]])
    return f"""Bạn là chuyên gia brand DNA. Đọc bài viết và viết PHÂN TÍCH TỰ NHIÊN.

FB INTRO:
{i["fb"][:1500]}

BÀI VIẾT:
{pt}

Viết 1 đoạn văn liền mạch 200-400 từ: brand tự hào điều gì NHẤT? Không bao giờ làm gì vì tiền? 3 metaphor tự mô tả? Khác biệt đối thủ?

QUY TẮC TUYỆT ĐỐI:
- CHỈ 1 đoạn văn liền mạch, KHÔNG đánh số, KHÔNG bullet
- KHÔNG dùng markdown header
- KHÔNG dùng từ "thân thiện", "chuyên nghiệp", "chất lượng"

KẾT THÚC bằng EXACTLY 5 dòng, mỗi dòng 1 SIGNATURE PHRASE trong ngoặc kép:
"phrase 1"
"phrase 2"
"phrase 3"
"phrase 4"
"phrase 5"
"""



def _pk2(i):
    pt = "\n\n---\n".join([f"[{p['id']}]\n{p.get('content','')[:2500]}" for p in i["posts"]])
    ct = "\n".join([f"- {c['author']}: {c.get('comment','')[:200]}" for c in i["comments"]])
    return f"""Bạn là linguist phân tích tone & style của {i["name"]}. Đọc bài viết và comments, viết PHÂN TÍCH TỰ NHIÊN.

BÀI VIẾT:
{pt}

COMMENTS:
{ct}

Viết 1 đoạn 200-400 từ: emotional arc? Tone chính (CHỌN 2-3 TỪ CỤ THỂ)? Pronoun pattern? Bilingual strategy?

KHÔNG JSON. Viết như báo cáo phân tích.

KẾT THÚC bằng EXACTLY 4 dòng:
funny-serious: [0-100, 100=serious max]
formal-casual: [0-100, 100=casual max]
respectful-irreverent: [0-100, 100=respectful max]
enthusiastic-matter_of_fact: [0-100, 100=matter-of-fact max]

Và 1 dòng:
PRONOUNS: brand="..." reader="..." brand_ref="..." """


# ═══════════════════════════════════════════════════
# CELL 3B: PROMPT BUILDERS — K3 & K4 & K5
# ═══════════════════════════════════════════════════

def _pk3(i):
    mt = "\n".join([f"P{m['id']}: first='{m['first']}' last='{m['last']}' wc={m['wc']} emo={m['emoji']} hash={m['hash']} bi={m['bi']} bull={m['bull']}" for m in i["minimal"]])
    ft = "\n\n---\n".join([p.get("content","")[:2000] for p in i["full"]])
    return f"""Bạn là data analyst. Đọc metadata và trả lời BẰNG SỐ LIỆU.

META 11 POSTS:
{mt}

FULL SAMPLES:
{ft}

KEYWORDS: {i['kc']}

YÊU CẦU — Trả lời CHÍNH XÁC bằng số liệu từ metadata:
1. Bao nhiêu post có emoji? (đếm từ cột emo=true)
2. Bao nhiêu post có hashtag? (đếm từ cột hash=true)
3. Hashtag ở đầu hay cuối post?
4. Bao nhiêu post có bullet points? (đếm từ cột bull>0)
5. Bullet style là gì? (dựa vào first/last line)
6. Top 10 phrases brand DÙNG NHIỀU NHẤT (từ full samples, đếm lặp lại)
7. Top 5 words KHÔNG BAO GIỜ dùng (so với keywords ngành)
8. 5 SIGNATURE PHRASES — đặt trong ngoặc kép, mỗi phrase 1 dòng
9. Top 5 CHỦ ĐỀ TUYỆT ĐỐI KHÔNG ĐƯỢC NHẮC trong content (dựa trên positioning và đối thủ):

KHÔNG phân tích. KHÔNG suy đoán. Chỉ trả lời 9 câu trên."""


def _pk4(i):
    pt = "\n\n---\n".join([f"[{p['id']}]\n{p.get('content','')[-1500:]}" for p in i["posts"]])
    bt = "\n".join([f"- {c['author']}: {c.get('comment','')[:150]}" for c in i["bc"]])
    return f"""Bạn là conversion strategist phân tích CTA.

CTA SECTIONS:
{pt}

BOOKING COMMENTS:
{bt}

Viết 1 đoạn 150-300 từ: CTA style direct/soft? Top 5 phrases? Urgency framing? Conversion triggers? CTA components? Response pattern?

KHÔNG JSON. Audit report."""


def _pk5(i):
    pt = "\n\n---\n".join([f"ID:{p['id']}\n{p.get('content','')[:2000]}" for p in i["posts"]])
    fb_intro = i.get("fb", "")[:1500]
    phones = ", ".join(i.get("phones", []))
    emails = ", ".join(i.get("emails", []))
    domains = ", ".join(i.get("domains", []))
    return f"""Bạn là data extractor. Chỉ trích xuất thông tin, KHÔNG viết văn, KHÔNG phân tích.

FB INTRO:
{fb_intro}

DỮ LIỆU ĐÃ TRÍCH XUẤT:
- Phones: {phones}
- Emails: {emails}
- Domains: {domains}

BÀI VIẾT:
{pt}

Trả lời CHÍNH XÁC theo format sau (KHÔNG thêm giải thích):

LOCATIONS: [{{"city":"...","address":"...","hotline":"..."}}]
HOURS: ...
MENU_HIGHLIGHTS: ["...","...","..."]  # Chỉ các món được nhắc đến trong posts
USP: ["...","..."]"""



# ═══════════════════════════════════════════════════
# CELL 4: RUN 5 KIENS SONG SONG
# ═══════════════════════════════════════════════════

async def _k1(i): return call_groq(_pk1(i), 1500)
async def _k2(i): return call_groq(_pk2(i), 1500)
async def _k3(i): return call_groq(_pk3(i), 1500)
async def _k4(i): return call_groq(_pk4(i), 1200)
async def _k5(i): return call_groq(_pk5(i), 1200)


async def run_kiens(data):
    inp = prepare_kien_inputs(data)
    print(f"K1:{len(inp['k1']['posts'])} K2:{len(inp['k2']['posts'])}+{len(inp['k2']['comments'])} K3:{len(inp['k3']['minimal'])}+{len(inp['k3']['full'])} K4:{len(inp['k4']['posts'])}+{len(inp['k4']['bc'])} K5:{len(inp['k5']['posts'])}")
    r = await asyncio.gather(
        asyncio.create_task(_k1(inp["k1"])),
        asyncio.create_task(_k2(inp["k2"])),
        asyncio.create_task(_k3(inp["k3"])),
        asyncio.create_task(_k4(inp["k4"])),
        asyncio.create_task(_k5(inp["k5"]))
    )
    return {
        "k1": r[0], "k2": r[1], "k3": r[2], "k4": r[3], "k5": r[4],
        "k5_input": inp["k5"]
    }



# ═══════════════════════════════════════════════════
# CELL 5A: AGGREGATOR HELPERS — String utils
# ═══════════════════════════════════════════════════

def _between(t, s, e=None):
    try:
        i = t.lower().find(s.lower())
        if i==-1: return ""
        i += len(s)
        if e:
            j = t.lower().find(e.lower(), i)
            return t[i:j].strip() if j!=-1 else t[i:].strip()
        return t[i:].strip()
    except: return ""

def _phrases(t, prefix):
    r, found = [], False
    for line in t.split("\n"):
        if prefix.lower() in line.lower(): found=True; continue
        if found and line.strip().startswith(("- ","• ","* ","1. ","2. ")):
            c = line.strip("- •*123456789. ").strip()
            if c and len(c)>3: r.append(c)
        elif found and line.strip()=="": continue
        elif found and not line.strip().startswith(("-","•","*")): break
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
    stripped = k1.strip()
    
    # FILTER 1: Bỏ nếu toàn từ lặp hoặc chứa BUSINESS_FACTS
    if "MENU:" in stripped or "LOCATIONS:" in stripped or "HOURS:" in stripped:
        # Tìm đoạn văn trước BUSINESS_FACTS
        parts = stripped.split("BUSINESS_FACTS:")
        if len(parts) > 1:
            stripped = parts[0].strip()
    
    # FILTER 2: Bỏ nếu K1 trả về dạng list số hoặc markdown
    if re.search(r'^\d+\.', stripped, re.M) and stripped.count('\n') > 5:
        return f"{bname or 'Thương hiệu'} tự hào mang đến trải nghiệm đẳng cấp với sự tận tâm và chất lượng vượt trội."
    
    # FILTER 3: Bỏ nếu toàn từ lặp vô nghĩa
    words = stripped.lower().split()
    if len(words) > 20:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.3:
            return f"{bname or 'Thương hiệu'} mang đến trải nghiệm chất lượng, độc đáo và đáng nhớ cho khách hàng."
    
    # Thử lấy đoạn văn dài nhất từ K1 (trước khi có BUSINESS_FACTS)
    paras = [p.strip() for p in stripped.split("\n\n") if len(p.strip()) > 80]
    if not paras:
        paras = [p.strip() for p in stripped.split("\n") if len(p.strip()) > 80]
    
    # Tìm paragraph có ít repetition nhất
    best = ""
    best_score = -1
    for p in paras:
        p_words = p.lower().split()
        if len(p_words) < 10:
            continue
        unique_ratio = len(set(p_words)) / len(p_words)
        from collections import Counter
        repeats = sum(1 for c in Counter(p_words).values() if c > 3)
        score = unique_ratio - (repeats * 0.1)
        if score > best_score:
            best_score = score
            best = p
    
    # Nếu vẫn tệ, extract từ K1
    if best_score < 0.5 or not best:
        s = re.search(r'([^.]*(?:tự hào|linh hồn|khác biệt|điều đặc biệt|đam mê|tâm huyết)[^.]{50,300}\.)', stripped, re.I)
        best = s.group(1).strip() if s else f"{bname or 'Thương hiệu'} tự hào mang đến trải nghiệm đẳng cấp."
    
    return best[:800]



# ═══════════════════════════════════════════════════
# CELL 5B: AGGREGATOR HELPERS — Extractors
# ═══════════════════════════════════════════════════

def _pronouns(t):
    t = t.lower()
    r = {"ai": "Chúng tôi", "reader": "Bạn"}
    if t.count("nhà mộc") > 2: r["brand_ref"] = "nhà Mộc"
    elif t.count("mộc quán") > 2: r["brand_ref"] = "Mộc Quán"
    return r

def _tone_base(t):
    t = t.lower()
    sp = ["proud","humble","warm","precise","grateful","excited","passionate","earnest","dignified"]
    found = [w for w in sp if w in t]
    if found: return [w.title() for w in found[:3]]
    r = []
    if any(x in t for x in ["michelin","vinh danh","tự hào","vinh dự","ngôi sao","bệ phóng","đích đến"]):
        r.append("Proud")
    if any(x in t for x in ["humble","khiêm tốn","tri ân","cảm ơn","gật đầu"]):
        r.append("Humble")
    if any(x in t for x in ["warm","ấm cúng","chào đón","nhà mộc"]):
        r.append("Warm")
    if any(x in t for x in ["grateful","tri ân","cảm ơn sâu sắc","đồng hành"]):
        r.append("Grateful")
    if any(x in t for x in ["precise","chính xác","chi tiết","tuyệt đối"]):
        r.append("Precise")
    if any(x in t for x in ["excited","hào hứng","bùng nổ","rộn ràng"]):
        r.append("Excited")
    return r if r else ["Earnest","Warm"]


def _sig_phrases(k1, k3):
    # K1: tìm dòng bắt đầu bằng " và kết thúc bằng "
    k1_lines = [l.strip() for l in k1.strip().split("\n") 
                if l.strip().startswith('"') and l.strip().endswith('"')]
    q = [l.strip('"') for l in k1_lines if len(l.strip('"')) > 10]
    
    # Nếu K1 không có, thử K3 signature phrases
    if not q:
        sig_sec = _between(k3, "8.", "9.") or _between(k3, "signature phrases", None) or ""
        sig_sec = "\n".join(sig_sec.split("\n")[-20:])
        q = re.findall(r'"([^"]{10,80})"', sig_sec)
    
    # Nếu vẫn không có, extract từ K1 các câu trong ngoặc kép
    if not q:
        q = re.findall(r'"([^"]{10,80})"', k1)
    
    # Deduplicate
    seen, uniq = set(), []
    for p in q:
        cl = p.strip().lower()
        if any(bad in cl for bad in ["signature", "top 5", "không bao giờ", "dùng:", "phrases:"]):
            continue
        if cl not in seen and len(p) > 15:
            seen.add(cl); uniq.append(p.strip())
    
    return uniq[:5]


def _format_rules(k3):
    t = k3.lower()
    emo_match = re.search(r'(\d+)\s*post.*emoji', t)
    emo_count = int(emo_match.group(1)) if emo_match else t.count("emoji")
    hash_match = re.search(r'(\d+)\s*post.*hash', t)
    hash_count = int(hash_match.group(1)) if hash_match else t.count("hash")
    bull_match = re.search(r'(\d+)\s*post.*bull', t)
    bull_count = int(bull_match.group(1)) if bull_match else t.count("bull")
    return {
        "paragraphMaxSentences": 5,
        "useEmoji": emo_count > 0,
        "useHashtags": hash_count > 0,
        "bulletPointStyle": "dash" if bull_count > 0 or "dash" in t or "-" in t else "none"
    }
def _avoid(k1, k2, k3):
    # Thử K3 trước
    s = (_between(k3, "7.", "8.") or 
         _between(k3, "không bao giờ", "signature") or 
         _between(k3, "avoid", "signature") or
         "")
    
    # Nếu K3 rỗng, thử tìm trong K1/K2 các từ "không bao giờ", "tránh"
    if not s:
        for text in [k1, k2]:
            m = re.search(r'(?:không bao giờ|tránh|không nên|không dùng)[^\n]{10,200}', text, re.I)
            if m:
                s = m.group(0)
                break
    
    w = []
    for l in (s or "").split("\n"):
        c = l.strip("- •*123456789. \"'").strip()
        if not c or len(c) > 30 or len(c) < 3:
            continue
        if any(bad in c.lower() for bad in ["không bao giờ", "dùng:", "signature", "top 5", "words", "tránh"]):
            continue
        # Skip proper nouns
        words = c.split()
        if len(words) >= 1 and all(w[0].isupper() and w.isalpha() for w in words):
            continue
        w.append(c)
    
    # Fallback nếu vẫn rỗng
    if not w:
        w = ["giá rẻ", "buffet", "khuyến mãi", "sale", "giảm giá sâu"]
    return w


def _cta_phrases(k4):
    r = []
    # Pattern 1: Tìm text trong ngoặc kép có chứa CTA keywords
    quotes = re.findall(r'"([^"]{5,50})"', k4)
    for q in quotes:
        if any(m in q.lower() for m in ["đặt bàn","hotline","inbox","gọi điện","đặt ngay","liên hệ"]):
            r.append(q)
    
    # Pattern 2: Tìm dòng bắt đầu bằng action verb + object
    for line in k4.split("\n"):
        line = line.strip()
        # Skip markdown
        if line.startswith("**") or line.startswith("- ") or line.startswith("* "):
            continue
        # Extract nếu chứa CTA keyword ở đầu câu
        if any(m in line.lower() for m in ["đặt bàn","hotline","inbox","gọi điện"]):
            # Clean markdown bold
            clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
            clean = clean.strip("- •*123456789. ").strip()
            # Chỉ lấy phần trước dấu phẩy hoặc ngoặc đơn nếu dài
            if len(clean) > 60:
                clean = clean.split(",")[0].split("(")[0].strip()
            if 5 < len(clean) < 60:
                r.append(clean)
    
    # Deduplicate
    seen, uniq = set(), []
    for p in r:
        cl = p.lower().strip('"')
        if cl not in seen:
            seen.add(cl); uniq.append(p.strip('"'))
    return uniq[:5] if uniq else ["Đặt bàn ngay","Gọi Hotline để giữ chỗ","Inbox Fanpage"]

def _extract_purpose(k1, bname):
    s = re.search(r'([^.]*(?:tự hào|cam kết|mang đến|sứ mệnh|điều đặc biệt|linh hồn)[^.]{30,200}\.)', k1, re.I)
    if s:
        return s.group(1).strip()
    
    # Fallback: tìm đoạn dài nhất có ý nghĩa
    paras = [p.strip() for p in k1.split("\n\n") if len(p.strip()) > 50]
    if paras:
        return paras[0][:200]
    
    return f"{bname} mang đến trải nghiệm chất lượng cho khách hàng"

def _extract_audience(k1, k2):
    for t in [k1, k2]:
        s = re.search(r'([^.]*(?:khách hàng|thực khách|đối tượng|target|ai đang tìm|phục vụ)[^.]{30,150}\.)', t, re.I)
        if s:
            return s.group(1).strip()
    return "Khách hàng tìm kiếm trải nghiệm chất lượng và đẳng cấp"

def _phrases_to_avoid(k1, k2, k3):
    # Tìm section "tránh", "không dùng", "không bao giờ" trong cả 3 kiến
    for text in [k3, k1, k2]:
        s = (_between(text, "không bao giờ", "signature") or 
             _between(text, "tránh", "\n\n") or
             _between(text, "avoid", "\n\n") or
             "")
        if s:
            phrases = []
            for l in s.split("\n"):
                c = l.strip("- •*123456789. \"'").strip()
                if c and 3 < len(c) < 40 and not any(bad in c.lower() for bad in ["signature", "top 5", "words", "phrases:"]):
                    phrases.append(c)
            if phrases:
                return phrases[:5]
    
    # Fallback: tìm từ đơn/cụm ngắn được nhấn mạnh là "không"
    for text in [k1, k2]:
        found = re.findall(r'(?:không|tránh)\s+([a-zA-ZÀ-ỹ\s]{3,25})', text, re.I)
        if found:
            return [f.strip() for f in found[:5] if len(f.strip()) > 3]
    
    return []

def _words_to_use(k1, k3, bname):
    # Chỉ lấy từ sig phrases (từ đơn/cụm ngắn), KHÔNG từ K1 raw (tránh lấy nhầm business facts)
    sig = _sig_phrases(k1, k3)
    words = [w for w in sig if len(w.split()) <= 2 and len(w) > 3]
    
    if words:
        return words[:5]
    
    # Fallback: brand name
    return [bname.split()[0] if bname else "thương hiệu"]


def _channels(k3, k4):
    t = (k3 + k4).lower()
    ch = []
    if any(w in t for w in ["facebook", "fanpage", "social", "fb"]): ch.append("social")
    if any(w in t for w in ["blog", "website", "web"]): ch.append("blog")
    if any(w in t for w in ["email", "newsletter"]): ch.append("email")
    if any(w in t for w in ["tiktok", "video", "reels"]): ch.append("video")
    return ch or ["social", "blog"]


def _parse_business_context(k5_text: str, k5_input: dict = None) -> dict:
    """Parse business facts từ K5 output + k5_input structured data."""
    result = {"locations": [], "hours": "", "menu_highlights": [], "usp": []}
    
    # Ưu tiên dùng phones/emails từ k5_input nếu có
    if k5_input:
        phones = k5_input.get("phones", [])
        emails = k5_input.get("emails", [])
        domains = k5_input.get("domains", [])
    else:
        phones = emails = domains = []
    
    if not k5_text:
        return result
    
    # Parse LOCATIONS
    loc_match = re.search(r'LOCATIONS:\s*(\[.*?\])', k5_text, re.DOTALL)
    if loc_match:
        try:
            result["locations"] = json.loads(loc_match.group(1))
        except:
            pass
    
    # Parse HOURS
    hours_match = re.search(r'HOURS:\s*(.+?)(?:\n|$)', k5_text)
    if hours_match:
        result["hours"] = hours_match.group(1).strip()
    
    # Parse MENU_HIGHLIGHTS
    menu_match = re.search(r'MENU_HIGHLIGHTS:\s*(\[.*?\])', k5_text, re.DOTALL)
    if menu_match:
        try:
            result["menu_highlights"] = json.loads(menu_match.group(1))
        except:
            pass
    
    # Parse USP
    usp_match = re.search(r'USP:\s*(\[.*?\])', k5_text, re.DOTALL)
    if usp_match:
        try:
            result["usp"] = json.loads(usp_match.group(1))
        except:
            pass
    
    # Thêm phones/emails/domains từ k5_input
    result["phones"] = phones
    result["emails"] = emails
    result["domains"] = domains
    
    return result



def _parse_topics(k3_text: str) -> list:
    """Parse topicsToAvoid từ K3 câu 9."""
    # Tìm section câu 9
    lines = k3_text.split("\n")
    topics = []
    in_section = False
    
    for line in lines:
        if "9." in line and "CHỦ ĐỀ" in line:
            in_section = True
            continue
        if in_section:
            clean = line.strip("- •*123456789. ").strip()
            if clean and len(clean) > 3 and len(clean) < 100:
                # Skip header lines
                if any(bad in clean.lower() for bad in ["chủ đề tuyệt đối", "dưới đây là", "không được nhắc"]):
                    continue
                topics.append(clean)
    
    return topics[:5]





# ═══════════════════════════════════════════════════
# CELL 6: AGGREGATOR — Ép schema
# ═══════════════════════════════════════════════════

def aggregate(k1, k2, k3, k4, k5, bid, bname, fb=None, k5_input=None): 
    now = datetime.now(timezone.utc).isoformat()
    sig = _sig_phrases(k1, k3)
    personality = _clean_personality(k1)[:500]
    bc = _parse_business_context(k5, k5_input)  # ĐỔI: parse từ k5 + k5_input
    topics = _parse_topics(k3)
    
    return {
        "id": "05ecf6ad-eb61-45e0-b3f8-6bf2bc916914",
        "business_id": bid, "name": bname,
        "purpose": _extract_purpose(k1, bname),
        "channels": _channels(k3, k4),
        "desired_tone": " ".join(_tone_base(k2)),
        "target_audience": _extract_audience(k1, k2),
        "personality": personality,
        "taglines": sig[:5],
        "business_facts": bc,  # Giờ lấy từ k5 + k5_input
        "tone": {"base": _tone_base(k2), "overrides": {"blog_web": _tone_base(k2)}},
        "style": {"sentenceLength":"medium","voice":"active","perspective":"first","pronouns":_pronouns(k2)},
        "vocabulary": {
            "wordsToUse": _words_to_use(k1, k3, bname),
            "wordsToAvoid": _avoid(k1, k2, k3),
            "phrasesToUse": sig[:5], 
            "phrasesToAvoid": _phrases_to_avoid(k1, k2, k3),
            "topicsToAvoid": topics  # ĐÃ THÊM
        },
        "format_rules": _format_rules(k3),
        "cta_style": {
            "style": "direct" if any(x in k4.lower() for x in ["direct","mạnh mẽ","ngay"]) else "mixed",
            "phrases": _cta_phrases(k4)
        },
        "examples": [{
            "input": f"Tìm kiếm nhà hàng hải sản tại {bname}",
            "output": f"{bname.title()} chào đón bạn! {sig[0] if sig else ''} Liên hệ ngay để trải nghiệm hải sản tươi sống.",
            "contentType": "blog_web"
        }],
        "website_url": fb.get("url") if fb else None,
        "uploaded_files": [],
        "tone_funny_serious": _slider(k2,"funny","serious"),
        "tone_formal_casual": _slider(k2,"formal","casual"),
        "tone_respectful_irreverent": _slider(k2,"irreverent","respectful"),
        "tone_enthusiastic_matter_of_fact": _slider(k2,"matter of fact","enthusiastic"),
        "is_default": "0", "created_at": now, "updated_at": now
    }




# ═══════════════════════════════════════════════════
# CELL 7: MAIN — Chạy từ data → brand_voice_state
# ═══════════════════════════════════════════════════

async def extract_brand_voice(research_record):
    print("🔬 Slicing...")

    result = research_record["result"]

    data = {
        "task": {
            "business_id": result.get("business_id"),
            "business_name": result.get("business_name"),
        },

        "result": {
            "serp_data": result.get("serp_data"),
            "fb_brand": result.get("fb_brand"),
            "final_report": result.get("final_report"),
        },

        "posts": [
            {
                "id": p.get("id"),
                "content": p.get("content"),
                "attachments": p.get("attachments"),
            }
            for p in research_record.get("posts", [])
        ],

        "comments": [
            {
                "author": c.get("author"),
                "time": c.get("time"),
                "comment": c.get("comment"),
                "replies": c.get("replies"),
            }
            for c in research_record.get("comments", [])
        ],
    }

    ko = await run_kiens(data)
    print("✅ 5 kiến xong. Aggregating...")
    st = aggregate(ko["k1"], ko["k2"], ko["k3"], ko["k4"], ko["k5"],
      data["task"]["business_id"],
      data["task"]["business_name"],
      data["result"].get("fb_brand", {}),
      ko.get("k5_input"))  # ← SỬA: dùng k5_input thay vì k5
    
    print(f"Tone: {st['tone']['base']} | Sliders: f={st['tone_funny_serious']} fo={st['tone_formal_casual']} r={st['tone_respectful_irreverent']} e={st['tone_enthusiastic_matter_of_fact']}")
    
    return st