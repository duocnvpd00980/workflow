SƠ ĐỒ: ROOT GRAPH + 4 TEMPLATE SUBGRAPHS
ROOT GRAPH
plain
┌─────────────────────────────────────────────────────────────────────┐
│                         ROOT GRAPH                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   START                                                             │
│     │                                                               │
│     ▼                                                               │
│   SESSION_INIT ──► Tạo session, khởi tạo state rỗng               │
│     │                                                               │
│     ▼                                                               │
│   LOAD_CONTEXT ──► Load user profile, brand voice, history, RAG   │
│     │                                                               │
│     ▼                                                               │
│   CLASSIFY_REQUEST ──► Phân loại: social / blog / image / research│
│     │                                                               │
│     ▼                                                               │
│   CLARIFY ──► AI hỏi thêm nếu request thiếu info?                   │
│     │      (loop: hỏi → user trả lời → đủ chưa?)                   │
│     │      ┌─────────────────────────────┐                          │
│     └──────┤  Chưa đủ ──► pause, chờ resume                     │
│            └─────────────────────────────┘                          │
│            ↓ Đủ rồi                                                  │
│     ▼                                                               │
│   SELECT_TEMPLATE ──► Chọn 1 trong 4 templates                      │
│     │                                                               │
│     ▼                                                               │
│   EXECUTE_TEMPLATE ──► Chạy subgraph tương ứng                    │
│     │                    │                                          │
│     │      ┌───────────┼───────────┬───────────┐                   │
│     │      ▼           ▼           ▼           ▼                   │
│     │   [SOCIAL]   [BLOG]      [IMAGE]    [RESEARCH]              │
│     │      │           │           │           │                   │
│     │      └───────────┴───────────┴───────────┘                   │
│     │                    │                                          │
│     ▼◄───────────────────┘                                          │
│   REVIEW ──► Hiển thị draft, chờ user duyệt                        │
│     │      (RESEARCH skip qua, không cần review)                    │
│     │      ┌─────────────────────────────┐                          │
│     └──────┤  Reject ──► edits ──► quay lại EXECUTE_TEMPLATE      │
│            │  Approve ──► tiếp tục                                  │
│            └─────────────────────────────┘                          │
│            ↓ Approve                                                │
│     ▼                                                               │
│   APPROVE ──► Đánh dấu approved=true                               │
│     │                                                               │
│     ▼                                                               │
│   PUBLISH ──► Đẩy lên nền tảng (idempotent: check đã publish chưa)│
│     │                                                               │
│     ▼                                                               │
│   SAVE ──► Persist toàn bộ state, version history                  │
│     │                                                               │
│     ▼                                                               │
│   END                                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
TEMPLATE 1 — SOCIAL (nhanh, không pause giữa chừng)
plain
┌─────────────────────────────────────────┐
│           SOCIAL SUBGRAPH               │
├─────────────────────────────────────────┤
│                                         │
│   PREPARE                               │
│     │  Parse: platform, tone, length,   │
│     │  key message, CTA, hashtags       │
│     ▼                                   │
│   WRITE                                 │
│     │  Generate caption/text (LLM)    │
│     ▼                                   │
│   OPTIONAL_IMAGE?                       │
│     │  Có ──► IMAGE ──► generate ảnh │
│     │  Không ──► skip                  │
│     ▼                                   │
│   ASSEMBLE                              │
│     │  Gộp text + image URL + meta    │
│     ▼                                   │
│   DONE ──► Trả về draft ──► về REVIEW │
│                                         │
└─────────────────────────────────────────┘
TEMPLATE 2 — BLOG (có pause giữa chừng — duyệt outline)
plain
┌─────────────────────────────────────────┐
│            BLOG SUBGRAPH                │
├─────────────────────────────────────────┤
│                                         │
│   PREPARE                               │
│     │  Topic, audience, tone, length,   │
│     │  SEO keywords, style            │
│     ▼                                   │
│   RAG                                   │
│     │  Retrieve docs từ knowledge base │
│     ▼                                   │
│   OUTLINE                               │
│     │  Generate H2, H3, key points    │
│     ▼                                   │
│   WAIT_APPROVAL ◄── PAUSE POINT         │
│     │  API trả: status="paused",       │
│     │  reason="outline_approval"      │
│     │                                 │
│     │  User duyệt ──► resume          │
│     │  User reject ──► feedback ──► quay lại OUTLINE
│     ▼                                   │
│   WRITE                                 │
│     │  Generate full draft theo outline đã duyệt
│     ▼                                   │
│   POLISH                                │
│     │  Grammar, SEO, readability       │
│     ▼                                   │
│   DONE ──► Trả về draft ──► về REVIEW │
│                                         │
└─────────────────────────────────────────┘
TEMPLATE 3 — IMAGE (đơn giản nhất)
plain
┌─────────────────────────────────────────┐
│           IMAGE SUBGRAPH                │
├─────────────────────────────────────────┤
│                                         │
│   PREPARE                               │
│     │  Description, style, size,       │
│     │  brand constraints               │
│     ▼                                   │
│   PROMPT                                │
│     │  Translate → image gen prompt     │
│     ▼                                   │
│   IMAGE                                 │
│     │  Call image provider             │
│     ▼                                   │
│   DONE ──► Trả về image URL + meta    │
│            ──► về REVIEW               │
│                                         │
└─────────────────────────────────────────┘
TEMPLATE 4 — RESEARCH (khác biệt: skip REVIEW/APPPOVE/PUBLISH)
plain
┌─────────────────────────────────────────┐
│          RESEARCH SUBGRAPH              │
├─────────────────────────────────────────┤
│                                         │
│   QUERY                                 │
│     │  Parse research question,         │
│     │  scope, depth, sources           │
│     ▼                                   │
│   SEARCH                                │
│     │  Web search + internal KB + RAG  │
│     │  (parallel nếu nhiều source)    │
│     ▼                                   │
│   RERANK                                │
│     │  Score, filter, deduplicate      │
│     ▼                                   │
│   REPORT                                │
│     │  Synthesize: summary, sources,   │
│     │  key findings, confidence        │
│     ▼                                   │
│   DONE ──► Trả về report              │
│            ──► SKIP REVIEW             │
│            ──► SKIP APPROVE            │
│            ──► SKIP PUBLISH            │
│            ──► Đi thẳng SAVE ──► END   │
│                                         │
└─────────────────────────────────────────┘
TỔNG HỢP: CÁC ĐIỂM PAUSE TRÊN TOÀN HỆ THỐNG
plain
┌─────────────────┬────────────────────────┬─────────────────────────┐
│    Node         │      Lý do pause       │    Cách resume          │
├─────────────────┼────────────────────────┼─────────────────────────┤
│   CLARIFY       │ Thiếu info, cần hỏi    │ POST /workflow/resume   │
│                 │ thêm                   │ + answer                │
├─────────────────┼────────────────────────┼─────────────────────────┤
│   WAIT_APPROVAL │ Blog outline cần duyệt │ POST /workflow/resume   │
│   (trong Blog)  │ trước khi viết         │ + approve/reject        │
├─────────────────┼────────────────────────┼─────────────────────────┤
│   REVIEW        │ Draft cần duyệt        │ POST /workflow/resume   │
│                 │                        │ + approve/reject/edit   │
└─────────────────┴────────────────────────┴─────────────────────────┘
STATE FLOW QUA CÁC NODE
plain
┌─────────────────────────────────────────────────────────────────────┐
│  STATE (14 fields) ──► Mỗi node READ → process → WRITE → next      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  session_id      ──► không đổi                                     │
│  workspace_id    ──► không đổi                                     │
│  user_id         ──► không đổi                                     │
│  request         ──► không đổi (input gốc)                         │
│  template        ──► set ở SELECT_TEMPLATE                         │
│  clarification   ──► append ở CLARIFY loop                         │
│  context         ──► set ở LOAD_CONTEXT                             │
│  retrieved_docs  ──► set ở RAG / SEARCH                            │
│  outline         ──► set ở OUTLINE (Blog), clear ở others          │
│  draft           ──► set ở WRITE / ASSEMBLE / REPORT / IMAGE       │
│  images          ──► set ở OPTIONAL_IMAGE / IMAGE                  │
│  edits           ──► set ở REVIEW (nếu reject)                     │
│  approved        ──► set ở APPROVE                                  │
│  publish_status  ──► set ở PUBLISH                                  │
│  usage           ──► accumulate ở mỗi LLM call                     │
│  error           ──► set nếu fail sau retry                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘