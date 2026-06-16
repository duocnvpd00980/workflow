PROMPT cho LLM:

"Đọc kỹ đoạn text sau. Đây là content từ thương hiệu [Brand Name].
Phân tích và trích xuất:

1. PERSONALITY: AI nên đóng vai gì? 
   (vd: 'chuyên gia tư vấn', 'người bạn đồng hành', 'nhà lãnh đạo tư tưởng')

2. TONE: Cảm xúc chính? 
   (vd: 'tự tin', 'thân thiện', 'hài hước', 'nghiêm túc')

3. STYLE: Đặc điểm cấu trúc câu?
   (vd: 'câu ngắn', 'câu chủ động', 'dùng số liệu', 'hỏi đáp')

4. VOCABULARY POSITIVE: Từ/cụm từ đặc trưng hay xuất hiện?
   (vd: 'đột phá', 'bứt phá', 'tiên phong')

5. VOCABULARY NEGATIVE: Từ/cụm từ KHÔNG BAO GIỜ xuất hiện?
   (vd: 'rất', 'cực kỳ', 'tuyệt vời')

6. FORMAT PATTERNS: Cấu trúc đoạn văn?
   (vd: 'mở đầu bằng câu hỏi', 'đoạn 2-3 câu', 'kết bằng CTA')

7. CTA STYLE: Kêu gọi hành động kiểu gì?
   (vd: 'trực tiếp', 'mềm mại', 'tạo urgency')

8. EXAMPLES: Trích 3-5 đoạn text điển hình nhất làm few-shot"



===========================================================

{
  "personality": "Bạn là chuyên gia marketing 10 năm kinh nghiệm, nói chuyện như mentor thân thiện",
  "tone": {
    "base": ["confident", "friendly"],
    "overrides": {
      "social": ["energetic", "trendy"],
      "email": ["professional", "respectful"],
      "blog": ["conversational", "helpful"]
    }
  },
  "style": {
    "sentenceLength": "short",
    "voice": "active",
    "perspective": "second"
  },
  "vocabulary": {
    "wordsToUse": ["đột phá", "tiên phong", "bứt phá"],
    "wordsToAvoid": ["rất", "cực kỳ", "tuyệt vời"],
    "phrasesToUse": ["Hãy cùng...", "Đừng bỏ lỡ..."],
    "phrasesToAvoid": ["Xin chào quý khách", "Kính gửi"]
  },
  "formatRules": {
    "paragraphMaxSentences": 3,
    "useEmoji": true,
    "useHashtags": true,
    "bulletPointStyle": "dash"
  },
  "ctaStyle": {
    "style": "direct",
    "phrases": ["Tìm hiểu ngay", "Bắt đầu miễn phí"]
  },
  "examples": [
    {
      "input": "Giới thiệu sản phẩm mới",
      "output": "Sản phẩm X đã đến. Không chờ đợi. Không lý do.",
      "contentType": "social"
    }
  ]
}

========================================


┌─────────────────────────────────────────────────────────────┐
│  CÁCH 1: UPLOAD FILE                                         │
│  Input: PDF, DOCX, TXT                                       │
│  Process: Parse → Clean → Analyze → Extract 8 fields        │
│  Best for: Brand guideline, báo cáo, tài liệu nội bộ         │
├─────────────────────────────────────────────────────────────┤
│  CÁCH 2: PASTE TEXT                                          │
│  Input: Text trực tiếp                                       │
│  Process: Clean → Analyze → Extract 8 fields                 │
│  Best for: Test nhanh, 1-2 bài viết mẫu                     │
├─────────────────────────────────────────────────────────────┤
│  CÁCH 3: CRAWL WEBSITE (MẠNH NHẤT)                          │
│  Input: URL website                                          │
│  Process: Crawl nhiều trang → Extract text → Analyze         │
│  Best for: Brand đã có website, muốn voice chính xác nhất   │
└─────────────────────────────────────────────────────────────┘



============================


┌─────────────────────────────────────────────────────────────┐
│  BRAND VOICE OBJECT (đã lưu trong DB)                        │
│  ├── personality                                             │
│  ├── tone (base + overrides)                                │
│  ├── style                                                    │
│  ├── vocabulary (use/avoid)                                   │
│  ├── formatRules                                              │
│  ├── ctaStyle                                                 │
│  └── examples (filtered by contentType)                       │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  TEMPLATE ENGINE                                              │
│  ├── Layer 1: Core Brand Voice (luôn inject)                 │
│  ├── Layer 2: Contextual Override (theo contentType)        │
│  └── Layer 3: Few-Shot Examples (max 3, cùng contentType)   │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  SYSTEM PROMPT (gửi cho LLM)                                 │
│                                                              │
│  # BRAND VOICE                                                │
│  ## Identity: Bạn là...                                       │
│  ## Tone: ...                                                 │
│  ## Style: ...                                                │
│  ## Vocabulary Rules: ...                                     │
│  ## Format: ...                                               │
│  ## CTA: ...                                                  │
│  ## Contextual Tone for [social]: ...                        │
│  ## Examples: ...                                             │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  LLM API CALL                                                 │
│  ├── System: Prompt vừa tạo                                   │
│  ├── User: Template của loại content + User Input             │
│  └── → Output: Content đúng Brand Voice                      │
└─────────────────────────────────────────────────────────────┘





=================


User tạo Brand Voice
    │
    ├── Bước 1: Nhập thông tin NHẬN DIỆN THƯƠNG HIỆU
    │           (tên công ty, ngành, sản phẩm, đối tượng...)
    │
    ├── Bước 2: Chọn/chỉ định TÌNH HUỐNG SỬ DỤNG
    │           (bán gì? cho ai? kênh nào?)
    │
    └── Bước 3: Upload tài liệu RAG
                (website, file, text mẫu)
                → LLM đọc cả 3 → tạo Voice phù hợp




================================

┌─────────────────────────────────────────────────────────────┐
│  USER INPUT (3 field duy nhất)                               │
│  ├── business_name: "Sontras Sea Hotel"                     │
│  ├── address: "41 Hoàng Sa..."                              │
│  └── industry: "Hotel"                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  RESEARCH AGENT (đã có — chạy ngầm)                         │
│  ├── Tìm competitors                                        │
│  ├── Phân tích đối thủ (giá, điểm mạnh/yếu)               │
│  ├── Tạo personas (3-5 khách hàng tiềm năng)                │
│  └── Đề xuất chiến lược + kênh tiếp cận                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  BRAND VOICE FORM — TỰ ĐỘNG ĐIỀN + GỢI Ý                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📋 PHẦN A: SHOP PROFILE (✅ Auto-filled, user review)   │
│  ├── Tên công ty: Sontras Sea Hotel ✅                     │
│  ├── Ngành: Hotel / Beachfront Resort ✅                    │
│  ├── Địa chỉ: 41 Hoàng Sa Road... ✅                       │
│  ├── Sản phẩm: [Khách sạn bãi biển, phòng nghỉ, nhà hàng] ✅│
│  ├── Đối tượng: [Gia đình, cặp đôi, solo traveler] ✅       │
│  ├── Giá positioning: Trung cấp (3 sao) ✅                 │
│  └── Đối thủ chính: [Natalie Indochine, BlueSun...] ✅     │
│                                                             │
│  🎨 PHẦN B: VOICE CONFIG (💡 Gợi ý, user chọn/sửa)        │
│  ├── Tên voice: [Sontra Sea — Beachfront 💡] [✏️ Sửa]       │
│  ├── Mục đích: [Thu hút gia đình nghỉ dưỡng 💡] [✏️ Sửa]   │
│  ├── Kênh: ☑ Facebook ☑ Instagram ☐ TikTok ☐ Google Ads    │
│  ├── Tone: [Dropdown: warm & family-friendly 💡]           │
│  └── Đối tượng voice: [Gia đình có trẻ em, 30-45 tuổi 💡]   │
│                                                             │
│  📎 PHẦN C: RAG SOURCE (🔗 Auto + user bổ sung)            │
│  ├── Website: [sontraseahotel.com 💡] [✏️ Sửa]             │
│  ├── Upload file: [📎 Chọn file]                            │
│  └── Paste text: [textarea]                                 │
│                                                             │
│              [🚀 TẠO BRAND VOICE]                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  LLM EXTRACT 8 FIELDS                                       │
│  (Đọc cả 3 phần + RAG content → output JSON)               │
└─────────────────────────────────────────────────────────────┘










========================================================












┌─────────────────────────────────────────────────────────────────────┐
│  BƯỚC 0: RESEARCH AGENT                                             │
├─────────────────────────────────────────────────────────────────────┤
│  👤 USER NHẬP:                                                      │
│  ├── business_name: "Sontras Sea Hotel"                            │
│  ├── address: "41 Hoàng Sa Road, Sơn Trà, Đà Nẵng"               │
│  └── industry: "Hotel / Hospitality"                                │
│                                                                       │
│  🤖 SYSTEM TỰ ĐỘNG:                                                 │
│  ├── Crawl web tìm website, social media                              │
│  ├── Phân tích đối thủ (25 competitors)                             │
│  ├── Tạo 3-5 customer personas                                      │
│  ├── Đề xuất chiến dịch 30 ngày                                     │
│  └── Extract: sản phẩm, giá, đối tượng, kênh...                     │
│                                                                       │
│  → Lưu vào DB dạng research_data{}                                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BƯỚC 1: TẠO BUSINESS (1 lần duy nhất)                              │
├─────────────────────────────────────────────────────────────────────┤
│  🤖 SYSTEM TỰ ĐỘNG ĐIỀN:                                            │
│  ├── Tên công ty: "Sontras Sea Hotel" ← từ research input           │
│  ├── Ngành nghề: "Hotel / Beachfront Resort" ← từ research         │
│  ├── Địa chỉ: "41 Hoàng Sa Road..." ← từ research input            │
│  ├── Sản phẩm/Dịch vụ: ["Khách sạn bãi biển", "Phòng nghỉ",        │
│  │                      "Nhà hàng", "Hồ bơi"] ← từ research         │
│  ├── Đối tượng chính: "Gia đình, cặp đôi honeymoon,               │
│  │                      du khách solo" ← từ personas                │
│  ├── Giá positioning: "Trung cấp (3 sao), cạnh tranh với          │
│  │                      BlueSun, M Hotel" ← từ competitor analysis  │
│  └── Đối thủ chính: ["Natalie Indochine", "BDR Pool Villas",       │
│                      "BlueSun", "M Hotel"] ← từ competitors_clean   │
│                                                                       │
│  👤 USER LÀM GÌ:                                                    │
│  ├── ✅ Review tất cả — sửa nếu sai                                 │
│  ├── ✅ Thêm/bớt sản phẩm nếu cần                                   │
│  └── ✅ [💾 Lưu Business]                                          │
│                                                                       │
│  ❌ KHÔNG NHẬP TAY — chỉ review & edit                              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BƯỚC 2: TẠO BRAND VOICE (Nhiều lần)                               │
├─────────────────────────────────────────────────────────────────────┤
│  PHẦN A — BUSINESS INFO                                               │
│  🤖 SYSTEM TỰ ĐỘNG ĐIỀN:                                            │
│  ├── Thương hiệu: Sontras Sea Hotel ✅                              │
│  ├── Ngành: Hotel / Beachfront Resort ✅                             │
│  └── Tất cả info từ Business đã lưu ✅                               │
│                                                                       │
│  👤 USER LÀM GÌ:                                                    │
│  ├── ✅ [✏️ Sửa business] nếu cần (mở popup)                        │
│  └── ✅ Hoặc [▼ Chọn business khác] nếu có nhiều                   │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│  PHẦN B — VOICE CONFIG                                                │
│  🤖 SYSTEM GỢI Ý (từ research_data):                                │
│  ├── 💡 Tên voice: "Sontra Sea — Gia Đình"                         │
│  │   (gợi ý từ persona 1: Nguyễn Thị Mai, gia đình)                 │
│  ├── 💡 Mục đích: "Thu hút gia đình nghỉ dưỡng biển"               │
│  │   (gợi ý từ persona goal)                                        │
│  ├── 💡 Kênh: ☑ Facebook ☑ Google Ads ☐ TikTok                     │
│  │   (gợi ý từ chiến lược tiếp cận persona 1)                       │
│  ├── 💡 Tone: "warm, family-friendly"                               │
│  │   (gợi ý từ đối tượng gia đình + ngành khách sạn)                │
│  └── 💡 Đối tượng voice: "Gia đình có trẻ em, 30-45 tuổi,           │
│       thu nhập 20tr/tháng" (gợi ý từ persona chi tiết)               │
│                                                                       │
│  👤 USER NHẬP / CHỌN:                                               │
│  ├── ✅ Tên voice: Chọn gợi ý HOẶC tự đặt                          │
│  ├── ✅ Mục đích: Chọn gợi ý HOẶC tự nhập                          │
│  ├── ✅ Kênh: Tick/bỏ tick theo gợi ý                               │
│  ├── ✅ Tone: Chọn từ dropdown (có gợi ý sẵn)                      │
│  └── ✅ Đối tượng: Chọn gợi ý HOẶC tự nhập                          │
│                                                                       │
│  ❌ KHÔNG để trống — phải chọn/nhập                                 │
│  ✅ Có thể bỏ qua gợi ý, tự nhập hoàn toàn                          │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│  PHẦN C — RAG SOURCE                                                  │
│  🤖 SYSTEM TỰ ĐỘNG ĐIỀN:                                            │
│  ├── 💡 Website: "sontraseahotel.com" ← từ research crawl           │
│                                                                       │
│  👤 USER NHẬP / UPLOAD:                                             │
│  ├── ✅ Website: Sửa URL nếu sai HOẶC nhập nếu system không tìm     │
│  ├── ✅ Upload file: 📎 PDF, DOCX, TXT (tùy chọn)                   │
│  └── ✅ Paste text: textarea (tùy chọn)                             │
│                                                                       │
│  ❌ Ít nhất 1 trong 3: URL / File / Paste (tối thiểu 300 từ)       │
│                                                                       │
│              [🚀 TẠO BRAND VOICE]                                    │
│              → LLM Extract 8 fields                                  │
│              → Preview UI → User edit → Save                         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BƯỚC 3: LƯU BRAND VOICE (8 fields JSON)                            │
├─────────────────────────────────────────────────────────────────────┤
│  🤖 SYSTEM TỰ ĐỘNG:                                                 │
│  ├── Extract personality, tone, style, vocabulary...                  │
│  ├── Generate few-shot examples từ RAG source                       │
│  └── Tạo JSON chuẩn                                                 │
│                                                                       │
│  👤 USER LÀM GÌ:                                                    │
│  ├── ✅ Review 8 fields trong UI (dạng form)                        │
│  ├── ✅ Sửa từng field nếu không đúng ý                            │
│  └── ✅ [💾 Lưu Brand Voice]                                        │
│                                                                       │
│  ❌ Không thể bỏ qua — phải review trước khi save                    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BƯỚC 4: TẠO CONTENT (Mỗi lần generate)                             │
├─────────────────────────────────────────────────────────────────────┤
│  👤 USER NHẬP / CHỌN:                                               │
│  ├── ✅ Chọn loại content: Blog / Email / Social / ...               │
│  ├── ✅ Chọn Brand Voice: [▼ Nike Sporty / Nike Lifestyle / ...]     │
│  └── ✅ Nhập user_input theo loại:                                  │
│      ├── Blog: topic, keywords, audience, productName                │
│      ├── Email: recipientName, productName, painPoint, ctaAction      │
│      └── Social: topic, productName, visualDescription, ctaType      │
│                                                                       │
│  🤖 SYSTEM TỰ ĐỘNG:                                                 │
│  ├── Đọc BrandVoice JSON từ DB theo voiceId                         │
│  ├── Render Jinja2 template (.j2 file)                              │
│  │   ├── Core Brand Voice (8 fields)                                │
│  │   ├── Contextual Tone (theo contentType)                         │
│  │   ├── Template Instructions (Blog/Email/Social)                  │
│  │   └── Few-Shot Examples (filter by contentType)                  │
│  └── Tạo System Prompt hoàn chỉnh                                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BƯỚC 5: GỬI LLM → OUTPUT                                           │
├─────────────────────────────────────────────────────────────────────┤
│  🤖 SYSTEM TỰ ĐỘNG:                                                 │
│  ├── Gửi System Prompt + User Input → LLM API                      │
│  ├── Nhận output content                                             │
│  └── Hiển thị cho user                                               │
│                                                                       │
│  👤 USER LÀM GÌ:                                                    │
│  ├── ✅ Đọc output                                                   │
│  ├── ✅ [🔄 Regenerate] nếu không thích                              │
│  ├── ✅ [✏️ Edit] trực tiếp                                          │
│  └── ✅ [💾 Save] hoặc [📋 Copy]                                      │
└─────────────────────────────────────────────────────────────────────┘