

# ═══════════════════════════════════════════════════
# CELL 1: IMPORTS
# ═══════════════════════════════════════════════════
import json, asyncio, re
from typing import Dict, Any, List
from datetime import datetime, timezone
from app.llm_clients import call_groq


import re
# Trong aggregate():

# In[17]:


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




# In[18]:


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
    return {
        "k1": {"posts": _k1_posts(posts), "fb": fb.get("intro","")[:2000],
               "name": data.get("task",{}).get("business_name","")},
        "k2": {"posts": _k2_posts(posts), "comments": mc[:15],
               "name": data.get("task",{}).get("business_name","")},
        "k3": {"minimal": m3, "full": f3,
               "kc": serp.get("keyword_cluster",[]), "cp": serp.get("competitor_pattern",[])},
        "k4": {"posts": _k4_posts(posts),
               "bc": [c for c in mc if any(x in c.get("comment","").lower() 
                      for x in ["đặt bàn","menu","hotline","giá"])][:10]}
    }



# In[19]:


# ═══════════════════════════════════════════════════
# CELL 3A: PROMPT BUILDERS — K1 & K2
# ═══════════════════════════════════════════════════

# ═══════════════════════════════════════════════════
# CELL 3A SỬA — PROMPT BUILDERS K1 (mới) & K2 (giữ cũ)
# ═══════════════════════════════════════════════════

def _pk1(i):
    pt = "\n\n---\n".join([f"ID:{p['id']}\n{p.get('content','')[:3000]}" for p in i["posts"]])
    return f"""Bạn là chuyên gia brand DNA. Đọc bài viết và viết PHÂN TÍCH TỰ NHIÊN về LINH HỒN thương hiệu {i["name"]}.

FB INTRO: {i["fb"][:1500]}

BÀI VIẾT:
{pt}

Viết 1 đoạn văn liền mạch 200-400 từ: brand tự hào điều gì NHẤT? Không bao giờ làm gì vì tiền? 3 metaphor tự mô tả? Khác biệt đối thủ?

KHÔNG dùng "thân thiện", "chuyên nghiệp", "chất lượng".

QUAN TRỌNG — KẾT THÚC bằng EXACTLY 5 dòng, mỗi dòng 1 SIGNATURE PHRASE trong ngoặc kép:
"phrase 1"
"phrase 2"
"phrase 3"
"phrase 4"
"phrase 5"

Các phrase này PHẢI là những câu brand DÙNG NHIỀU LẦN trong bài viết trên."""

def _pk2(i):
    pt = "\n\n---\n".join([f"[{p['id']}]\n{p.get('content','')[:2500]}" for p in i["posts"]])
    ct = "\n".join([f"- {c['author']}: {c.get('comment','')[:200]}" for c in i["comments"]])
    return f"""Bạn là linguist phân tích tone & style của {i["name"]}. Đọc bài viết và comments, viết PHÂN TÍCH TỰ NHIÊN.

BÀI VIẾT:
{pt}

COMMENTS:
{ct}

Viết 1 đoạn 200-400 từ: emotional arc? Tone chính (CHỌN 2-3 TỪ CỤ THỂ)? Pronoun pattern? Bilingual strategy? 4 sliders (0-100): funny-serious, formal-casual, respectful-irreverent, enthusiastic-matter_of_fact.

KHÔNG JSON. Viết như báo cáo phân tích."""

def _pk2(i):
    pt = "\n\n---\n".join([f"[{p['id']}]\n{p.get('content','')[:2500]}" for p in i["posts"]])
    ct = "\n".join([f"- {c['author']}: {c.get('comment','')[:200]}" for c in i["comments"]])
    return f"""Bạn là linguist phân tích tone & style của {i["name"]}. Đọc bài viết và comments, viết PHÂN TÍCH TỰ NHIÊN.

BÀI VIẾT:
{pt}

COMMENTS:
{ct}

Viết 1 đoạn 200-400 từ: emotional arc? Tone chính (CHỌN 2-3 TỪ CỤ THỂ)? Pronoun pattern? Bilingual strategy? 4 sliders (0-100): funny-serious, formal-casual, respectful-irreverent, enthusiastic-matter_of_fact.

KHÔNG JSON. Viết như báo cáo phân tích."""


# In[20]:


# ═══════════════════════════════════════════════════
# CELL 3B: PROMPT BUILDERS — K3 & K4
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

KHÔNG phân tích. KHÔNG suy đoán. Chỉ trả lời 8 câu trên."""


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


# In[21]:


# ═══════════════════════════════════════════════════
# CELL 4: RUN 4 KIENS SONG SONG
# ═══════════════════════════════════════════════════

async def _k1(i): return call_groq(_pk1(i), 1500)
async def _k2(i): return call_groq(_pk2(i), 1500)
async def _k3(i): return call_groq(_pk3(i), 1500)
async def _k4(i): return call_groq(_pk4(i), 1200)

async def run_kiens(data):
    inp = prepare_kien_inputs(data)
    print(f"K1:{len(inp['k1']['posts'])} K2:{len(inp['k2']['posts'])}+{len(inp['k2']['comments'])} K3:{len(inp['k3']['minimal'])}+{len(inp['k3']['full'])} K4:{len(inp['k4']['posts'])}+{len(inp['k4']['bc'])}")
    r = await asyncio.gather(
        asyncio.create_task(_k1(inp["k1"])),
        asyncio.create_task(_k2(inp["k2"])),
        asyncio.create_task(_k3(inp["k3"])),
        asyncio.create_task(_k4(inp["k4"]))
    )
    return {"k1": r[0], "k2": r[1], "k3": r[2], "k4": r[3]}


# In[22]:


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


def _clean_personality(k1, bname):
    # Thử lấy đoạn văn dài nhất từ K1 (bỏ dòng đầu/cuối nếu là header)
    paras = [p.strip() for p in k1.strip().split("\n\n") if len(p.strip()) > 80]
    if not paras:
        paras = [p.strip() for p in k1.strip().split("\n") if len(p.strip()) > 80]
    
    # Tìm paragraph có ít repetition nhất
    best = ""
    best_score = -1
    for p in paras:
        words = p.lower().split()
        if len(words) < 10:
            continue
        # Score = unique words / total words (cao = ít lặp)
        unique_ratio = len(set(words)) / len(words)
        # Penalty nếu có từ lặp >3 lần
        from collections import Counter
        repeats = sum(1 for c in Counter(words).values() if c > 3)
        score = unique_ratio - (repeats * 0.1)
        if score > best_score:
            best_score = score
            best = p
    
    # Nếu vẫn tệ, fallback
    if best_score < 0.5 or not best:
        # Extract từ K1: tìm câu có "tự hào", "linh hồn", "khác biệt"
        s = re.search(r'([^.]*(?:tự hào|linh hồn|khác biệt|điều đặc biệt)[^.]{50,300}\.)', k1, re.I)
        best = s.group(1).strip() if s else f"{bname} tự hào mang đến trải nghiệm ẩm thực đẳng cấp với hải sản tươi sống."
    
    return best[:1000]



# In[23]:


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
    k1_lines = [l.strip() for l in k1.strip().split("\n") if l.strip().startswith('"') and l.strip().endswith('"')]
    q = [l.strip('"') for l in k1_lines if len(l.strip('"')) > 10]

    sig_sec = _between(k3, "8.", None) or _between(k3, "signature phrases", None) or ""
    sig_sec = "\n".join(sig_sec.split("\n")[-20:])
    q += re.findall(r'"([^"]{10,80})"', sig_sec)
    
    seen, uniq = set(), []
    for p in q:
        cl = p.strip().lower()
        if any(bad in cl for bad in ["signature", "top 5", "không bao giờ", "words to", "phrases:"]):
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
    # Từ sig nhưng chỉ lấy từ đơn/cụm ngắn
    sig = _sig_phrases(k1, k3)
    words = [w for w in sig if len(w.split()) <= 2 and len(w) > 3]
    
    if words:
        return words[:5]
    
    # Fallback: extract từ K1 các từ được nhấn mạnh (đậm, caps, trong ngoặc kép)
    candidates = re.findall(r'"([^"]{3,20})"', k1)
    candidates += re.findall(r'\*\*([^*]{3,20})\*\*', k1)
    candidates += re.findall(r'\b([A-ZĐ][a-zđ]{2,}(?:\s+[A-ZĐ][a-zđ]{2,}){0,1})\b', k1)
    
    seen, uniq = set(), []
    for c in candidates:
        cl = c.lower().strip()
        if cl not in seen and 3 <= len(c) <= 20:
            seen.add(cl); uniq.append(c)
    
    return uniq[:5] or [bname.split()[0] if bname else "thương hiệu"]

def _channels(k3, k4):
    t = (k3 + k4).lower()
    ch = []
    if any(w in t for w in ["facebook", "fanpage", "social", "fb"]): ch.append("social")
    if any(w in t for w in ["blog", "website", "web"]): ch.append("blog")
    if any(w in t for w in ["email", "newsletter"]): ch.append("email")
    if any(w in t for w in ["tiktok", "video", "reels"]): ch.append("video")
    return ch or ["social", "blog"]


# In[24]:


# ═══════════════════════════════════════════════════
# CELL 6: AGGREGATOR — Ép schema
# ═══════════════════════════════════════════════════

def aggregate(k1, k2, k3, k4, bid, bname, fb=None):
    now = datetime.now(timezone.utc).isoformat()
    sig = _sig_phrases(k1, k3)
    personality = _clean_personality(k1)[:1000]
    return {
        "id": "05ecf6ad-eb61-45e0-b3f8-6bf2bc916914",
        "business_id": bid, "name": bname,
        "purpose": _extract_purpose(k1, bname),
        "channels": _channels(k3, k4),
        "desired_tone": " ".join(_tone_base(k2)),
        "target_audience": _extract_audience(k1, k2),
        "personality": personality,
        "tone": {"base": _tone_base(k2), "overrides": {"blog_web": _tone_base(k2)}},
        "style": {"sentenceLength":"medium","voice":"active","perspective":"first","pronouns":_pronouns(k2)},
        "vocabulary": {
            "wordsToUse": _words_to_use(k1, k3, bname),
            "wordsToAvoid": _avoid(k1, k2, k3),
            "phrasesToUse": sig[:5], 
            "phrasesToAvoid":_phrases_to_avoid(k1, k2, k3),
            "topicsToAvoid": []
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


# In[25]:



# ═══════════════════════════════════════════════════
# CELL 7: MAIN — Chạy từ data → brand_voice_state
# ═══════════════════════════════════════════════════

async def extract_brand_voice(research_record):
    print("🔬 Slicing...")

    result = research_record["result"]

    data = {
        "task": {
            "business_id": result.business_id,
            "business_name": result.business_name,
        },

        "result": {
            "serp_data": result.serp_data,
            "fb_brand": result.fb_brand,
            "final_report": result.final_report,
        },

        "posts": [
            {
                "id": p.id,
                "content": p.content,
                "attachments": p.attachments,
            }
            for p in research_record["posts"]
        ],

        "comments": [
            {
                "author": c.author,
                "time": c.time,
                "comment": c.comment,
                "replies": c.replies,
            }
            for c in research_record["comments"]
        ],
    }

    ko = await run_kiens(data)
    print("✅ 4 kiến xong. Aggregating...")
    st = aggregate(ko["k1"], ko["k2"], ko["k3"], ko["k4"],
      data["task"]["business_id"],
      data["task"]["business_name"],
      data["result"].get("fb_brand", {}))
    
    print(f"Tone: {st['tone']['base']} | Sliders: f={st['tone_funny_serious']} fo={st['tone_formal_casual']} r={st['tone_respectful_irreverent']} e={st['tone_enthusiastic_matter_of_fact']}")
    
    return st


