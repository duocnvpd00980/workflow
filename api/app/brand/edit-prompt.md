1. SỬA Brand MODEL — Thêm trường + Validation
1.1 Thêm taglines (tách khỏi personality)
Python
# Thêm cột mới
taglines = Column(JSON, default=list)  # ["Chất lượng không đổi...", "Mộc hiểu rằng..."]
1.2 Thêm business_context — ngữ cảnh thực tế
Python
business_context = Column(JSON, default=dict)
# {
#   "locations": [{"city": "Đà Nẵng", "address": "26 Tô Hiến Thành", "hotline": "0905 665 058"}],
#   "hours": "10:30 - 23:45",
#   "usp": ["Michelin Selected 2026", "Hải sản tươi sống"],
#   "menu_highlights": ["Tôm hùm nướng phô mai", "Cua sốt Sing", "Sashimi"]
# }
1.3 Validation overlap phrasesToUse vs phrasesToAvoid
Python
# Trong _normalize_brand_voice() hoặc @validates
def _validate_phrases(vocab):
    overlap = set(vocab.get("phrasesToUse", [])) & set(vocab.get("phrasesToAvoid", []))
    if overlap:
        # Ưu tiên phrasesToAvoid: xóa khỏi phrasesToUse
        vocab["phrasesToUse"] = [p for p in vocab["phrasesToUse"] if p not in overlap]
    return vocab
1.4 Sửa _slider() — Bug ngược respectful_irreverent
Python
# Hiện tại: _slider(k2, "irreverent", "respectful") 
# → tìm "irreverent-respectful" nhưng K2 viết "respectful-irreverent"
# → regex không match → fallback 50

# Sửa: Đổi thứ tự parameter hoặc regex
def _slider(t, lo, hi):
    # ... giữ nguyên logic nhưng đảm bảo K2 output đúng format
    # Hoặc đơn giản: parse từ K2 theo cả 2 chiều
2. SỬA TEMPLATE brand_voice_prompt.j2 — 5 thay đổi lớn
2.1 Thêm ## NGỮ CẢNH DOANH NGHIỆP
jinja2
{% if brand_voice.business_context %}
## NGỮ CẢNH DOANH NGHIỆP
{% for loc in brand_voice.business_context.locations %}
- Cơ sở {{ loop.index }}: {{ loc.address }}, {{ loc.city }} | Hotline: {{ loc.hotline }}
{% endfor %}
- Giờ phục vụ: {{ brand_voice.business_context.hours }}
{% for usp in brand_voice.business_context.usp %}
- USP: {{ usp }}
{% endfor %}
{% endif %}
2.2 Tách personality vs taglines
jinja2
Bạn là {{ brand_voice.personality }}

{% if brand_voice.taglines %}
## SLOGAN THƯƠNG HIỆU
{% for tag in brand_voice.taglines %}
- {{ tag }}
{% endfor %}
{% endif %}
2.3 Slider directives mạnh hơn — imperative + uppercase
jinja2
{% if brand_voice.slider_directives %}
## CHỈ THỊ KHẨU KHÍ — BẮT BUỘC TUÂN THỦ
{% for directive in brand_voice.slider_directives %}
[QUAN TRỌNG] {{ directive | upper }}
{% endfor %}
{% endif %}
2.4 Thêm storytelling directive
jinja2
## CẤU TRÚC BÀI VIẾT
- Mở bài: Bắt đầu bằng insight, câu chuyện ngắn, hoặc tình huống cụ thể. KHÔNG mở bằng giới thiệu chung chung.
- Thân bài: Mỗi đoạn là 1 bước trong câu chuyện, có mục đích riêng. KHÔNG liệt kê tính năng.
- Kết bài: Kết nối lại insight mở bài + CTA có thông tin hành động cụ thể.
2.5 CTA bắt buộc thông tin cụ thể
jinja2
## CTA
- Phong cách: {{ brand_voice.cta_style.style }}
- BẮT BUỘC: Mỗi CTA phải kèm 1 trong: hotline, địa chỉ, hoặc giờ mở cửa cụ thể.
{% if brand_voice.cta_style.phrases %}
- Gợi ý: {{ brand_voice.cta_style.phrases | join(" / ") }}
{% endif %}
3. SỬA 4 PROMPT KIẾN — Để extract đúng + đủ
3.1 K1 — Thêm extract business_context
Python
def _pk1(i):
    # ... giữ nguyên phần personality
    # Thêm yêu cầu extract:
    return f"""... (giữ nguyên)

THÊM YÊU CẦU — Trích xuất thông tin doanh nghiệp:
- Địa chỉ cơ sở (thành phố, địa chỉ đầy đủ, hotline)
- Giờ mở cửa
- 3 món ăn signature
- 2 USP độc nhất (vd: Michelin, hải sản tươi sống)

Trả về ở cuối trong format:
LOCATIONS: [{"city":"...","address":"...","hotline":"..."}]
HOURS: ...
MENU: [...]
USP: [...]
"""
3.2 K2 — Fix slider format + extract pronoun chuẩn
Python
def _pk2(i):
    return f"""... (giữ nguyên)

THÊM YÊU CẦU — Trả về EXACTLY 4 dòng cuối:
funny-serious: [số]
formal-casual: [số]
respectful-irreverent: [số]  ← CHÚ Ý: 100 = respectful max, 0 = irreverent max
enthusiastic-matter_of_fact: [số]

PRONOUNS: brand="..." | reader="..." | brand_ref="..."
"""
3.3 K3 — Thêm extract topicsToAvoid
Python
def _pk3(i):
    return f"""... (giữ nguyên 8 câu)

THÊM CÂU 9:
9. Top 5 CHỦ ĐỀ TUYỆT ĐỐI KHÔNG ĐƯỢC NHẮC trong content (dựa trên brand positioning và đối thủ):
- ...
"""
3.4 K4 — Giữ nguyên nhưng thêm urgency_level
Python
def _pk4(i):
    return f"""... (giữ nguyên)

THÊM: Đánh giá urgency level (0-100): [số]
"""
4. SỬA aggregate() — Parse thêm fields mới
Python
def aggregate(k1, k2, k3, k4, bid, bname, fb=None):
    # ... giữ nguyên phần cũ
    
    # Thêm parse business_context từ K1
    bc = _parse_business_context(k1)  # regex parse LOCATIONS:, HOURS:, etc.
    
    # Thêm parse topicsToAvoid từ K3 câu 9
    topics = _parse_topics(k3)
    
    return {
        # ... giữ nguyên các field cũ
        "business_context": bc,
        "taglines": sig[:5],  # tách từ personality cũ
        "personality": _clean_personality(k1)[:500],  # rút ngắn, chỉ 1 đoạn
        "vocabulary": {
            # ... giữ nguyên
            "topicsToAvoid": topics,
        },
    }
Tóm tắt ưu tiên code:
Table
#	File	Thay đổi	Độ phức tạp
1	Brand model	Thêm taglines, business_context	Migration
2	_normalize_brand_voice()	Validation overlap + fix slider	Dễ
3	brand_voice_prompt.j2	5 section mới	Trung bình
4	_pk1 to _pk4	Thêm extract fields	Trung bình
5	aggregate()	Parse + gán fields mới	Trung bình
Muốn tôi viết code hoàn chỉnh cho cái nào trước?










==============================



📁 FILE 1: app/brand/models.py — Brand Model
Table
STT	Việc cần làm	Mô tả
1.1	Thêm cột taglines	Column(JSON, default=list) — tách slogan khỏi personality
1.2	Thêm cột business_facts	Column(JSON, default=dict) — lưu địa chỉ, giờ, hotline, menu, USP
1.3	Thêm validator phrasesToUse ∩ phrasesToAvoid == ∅	Pydantic validate trước khi save, xóa overlap khỏi phrasesToUse



📁 FILE 2: app/brand_voice/services/brand_voice_prompt.py
Table
STT	Việc cần làm	Mô tả
2.1	Sửa _normalize_brand_voice()	Đổi slider_directives → slider_mandates, prefix MANDATE:, uppercase
2.2	Sửa get_brand_prompt_by_id()	Parse business_facts từ brand, truyền vào template
2.3	Sửa fallback brand_voice_dict	Thêm taglines, business_facts vào dict default



📁 FILE 3: app/brand_voice/services/brand_voice_prompt.j2 — Template
Table
STT	Việc cần làm	Mô tả
3.1	Thêm ## FACTS ngay sau Bạn là...	Render địa chỉ, giờ, hotline, USP, menu từ business_facts
3.2	Thêm ## SLOGAN THƯƠNG HIỆU	Render taglines list, tách khỏi personality
3.3	Sửa ## CHỈ THỊ KHẨU KHÍ	Đổi bullet thành MANDATE: [DIRECTIVE_UPPERCASE]
3.4	Thêm ## CẤU TRÚC BÀI VIẾT	3-act: Hook → Body → Close. Cấm header "Về chúng tôi", "Dịch vụ"
3.5	Sửa ## CTA	Bắt buộc `MUST include [hotline	address	hours]`



📁 FILE 4: app/blog/graph.py — LangGraph Workflow (blog_prepare node)
Table
STT	Việc cần làm	Mô tả
4.1	Sửa node blog_prepare	Trước gọi get_brand_prompt_by_id(), nén research data thành 800 tokens
4.2	Truyền research nén vào user_input.additional_instructions	Để template inject ngữ cảnh thực tế vào prompt



📁 FILE 5: app/research/aggregators/brand_voice.py — 4 Kiến Extractor
Table
STT	Việc cần làm	Mô tả
5.1	Sửa _pk1()	Thêm yêu cầu extract: locations, hours, menu, USP. Parse LOCATIONS:/HOURS:/MENU:/USP:
5.2	Sửa _pk2()	Fix slider format: respectful-irreverent: [số] (100=max respectful). Thêm PRONOUNS:
5.3	Sửa _pk3()	Thêm câu 9: extract topicsToAvoid
5.4	Sửa aggregate()	Parse business_facts từ K1, topicsToAvoid từ K3. Gán taglines từ sig phrases




Tóm tắt: 5 file, 15 việc
Table
File	Số việc	Mức độ
models.py	3	Migration + validator
brand_voice_prompt.py	3	Logic normalize + parse
brand_voice_prompt.j2	5	Template structure
graph.py	2	Node enrichment
brand_voice.py (4 kiến)	4	Extract prompts + aggregate
