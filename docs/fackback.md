Mục tiêu 1: Prompt 7/10 → 9/10
Bước 1 — Thu hẹp Agent

Hiện tại:

1 Agent
↓
4 nhiệm vụ

Ví dụ:

Topics
Products
Phrases
Evidence

Tách thành:

Topic Agent
Product Agent
Phrase Agent

=> Mỗi agent chỉ làm 1 việc.

Bước 2 — Evidence First

Thay vì:

TOPIC
- Hải sản

Bắt agent:

TOPIC
- Hải sản

EVIDENCE
- ...
- ...

=> Giảm hallucination.

Bước 3 — Output Contract cố định

Không XML.

Không JSON.

Dùng:

TOPICS

- ...

EVIDENCE

- ...

=> Scout ổn định hơn.

Bước 4 — Cấm suy luận

Thêm:

Do not infer.
Do not explain.
Do not summarize.
Extract only.

=> Chỉ lấy dữ liệu.

Prompt cuối cùng
IDENTITY
DATA
TASK
RULES
OUTPUT

Ngắn càng tốt.

Mục tiêu 2: Logic 4/10 → 9/10
Sai hiện tại
Facebook
↓
K1
↓
Purpose

Facebook
↓
K2
↓
Audience

Facebook
↓
K3
↓
Personality

=> Sai tầng.

Đúng phải là
Tầng 1: Extraction
Facebook
↓
Topic Agent

Facebook
↓
Customer Agent

Facebook
↓
CTA Agent

Output:

{
  "topics": [],
  "products": [],
  "customer_requests": [],
  "cta_phrases": []
}

Chỉ facts.

Tầng 2: Normalize

Code xử lý:

Remove duplicates
Clean text
Merge topics
Count frequency

Không dùng LLM.

Tầng 3: Brand Synthesizer

Input:

{
  "topics": [],
  "products": [],
  "customer_requests": [],
  "cta_phrases": []
}

LLM mới tạo:

{
  "purpose": "",
  "audience": "",
  "personality": "",
  "voice": ""
}
Tầng 4: Brand Voice Builder

Input:

Brand Profile

Output:

Writing Style
Tone
Vocabulary
CTA Style
Examples
Kế hoạch thực hiện ngắn gọn
PHASE 1

Sửa Prompt

- 1 agent = 1 nhiệm vụ
- Evidence First
- Extract Only
- Output Contract cố định

================================

PHASE 2

Sửa Logic

Facebook
↓
Extraction Agents
↓
Research JSON
↓
Normalizer
↓
Brand Synthesizer
↓
Brand Profile
↓
Brand Voice Builder

================================

PHASE 3

Giảm LLM

Phone
Email
Address
Hours
Domain

=> Regex / Code

KHÔNG dùng LLM

================================

PHASE 4

Chỉ dùng LLM cho:

Purpose
Audience
Personality
Voice

Nếu làm theo đúng thứ tự này thì tao đánh giá:

Hiện tại:
Prompt 7/10
Logic 4/10

Sau khi sửa:
Prompt 8.5-9/10
Logic 8-9/10

mà vẫn dùng nguyên Scout 17B, không cần đổi model.