IDENTITY

You are [ROLE_NAME].

Your responsibility is limited to the tasks defined in this prompt.

Do not perform tasks outside your role.



OBJECTIVE

Your objective is:

1. ...
2. ...
3. ...



AVAILABLE DATA

<Data>

{INPUT_DATA}

</Data>



CONTEXT

<Context>

{OPTIONAL_CONTEXT}

</Context>



TASK

Complete the following tasks:

1. ...
2. ...
3. ...



REASONING RULES

- Use only information found in AVAILABLE DATA.
- Do not invent facts.
- Do not speculate.
- Do not infer hidden motivations.
- Prefer repeated patterns over isolated mentions.
- Every conclusion must be supported by observable evidence.



QUALITY CRITERIA

Good output:

- Specific
- Observable
- Evidence-based
- Actionable

Bad output:

- Generic
- Marketing clichés
- Assumptions
- Unsupported claims



UNCERTAINTY HANDLING

If information is missing:

"Không đủ dữ liệu"

If evidence is weak:

"Chưa đủ bằng chứng"



OUTPUT CONTRACT

SECTION_1

- ...

SECTION_2

- ...

SECTION_3

- ...

EVIDENCE

- ...
- ...
- ...



LANGUAGE REQUIREMENT

Return all content in Vietnamese.

Do not use English except proper nouns.

































========================================================

1. IDENTITY
IDENTITY

You are Brand Research Analyst.
Mục đích

Trả lời:

Tôi là ai?

Nếu không có phần này:

Model dễ bị:

Researcher
↓
Copywriter
↓
Consultant
↓
Storyteller

trong cùng một câu trả lời.

Đây là nguồn gây noise lớn nhất.

2. OBJECTIVE
OBJECTIVE

1...
2...
3...
Mục đích

Trả lời:

Tôi đang cố đạt được điều gì?

Nhiều người viết:

Analyze this brand.

Quá mơ hồ.

Model sẽ tự quyết định.

Nhưng:

Identify recurring themes.
Identify products.
Identify evidence.

thì rất rõ.

3. AVAILABLE DATA
AVAILABLE DATA
Mục đích

Tạo ranh giới dữ liệu.

Model biết:

Đây là dữ liệu duy nhất được phép dùng.

Đây là kỹ thuật Anthropic dùng rất nhiều.

4. CONTEXT
CONTEXT
Mục đích

Đưa metadata.

Ví dụ:

Brand = Moc Seafood

Industry = Restaurant

Country = Vietnam

Quan trọng:

DATA ≠ CONTEXT

Sai lầm phổ biến là trộn cả hai.

5. TASK
TASK
Mục đích

Trả lời:

Tôi phải làm gì với dữ liệu?

Không viết:

Analyze deeply.

Viết:

Find recurring topics.
Find products.
Find CTA patterns.

Task càng đo được càng ổn định.

6. REASONING RULES

Đây là phần quan trọng nhất.

Do not speculate.
Do not invent facts.

Mục tiêu:

Giảm hallucination.

Đặc biệt với:

Llama 4 Scout 17B

phần này cực kỳ quan trọng.

7. QUALITY CRITERIA

Đây là thứ 90% prompt trên mạng thiếu.

Không chỉ bảo:

Làm đúng.

Mà định nghĩa:

Thế nào là đúng.

Ví dụ:

Good output:
Specific
Observable
Evidence-based

Bad output:
Generic
Marketing clichés

Khi đó model bắt đầu tự kiểm tra.

8. UNCERTAINTY HANDLING

Đây là phần cứu mạng hệ thống production.

Không có phần này:

Model sẽ:

Không biết
↓
Tự bịa

Có phần này:

Không đủ dữ liệu

Tỷ lệ hallucination giảm mạnh.

9. OUTPUT CONTRACT

Đây là thứ thay thế XML.

Không dùng:

<topics>
...
</topics>

Không dùng:

{
 "topics":[]
}

Dùng:

TOPICS

- ...

PRODUCTS

- ...

EVIDENCE

- ...

Lý do:

Model nhỏ rất ít phá format này.

10. LANGUAGE REQUIREMENT

Đặt cuối prompt.

Không đặt đầu prompt.

Sai:

TRẢ VỀ TIẾNG VIỆT.
TRẢ VỀ TIẾNG VIỆT.
TRẢ VỀ TIẾNG VIỆT.

Đúng:

LANGUAGE REQUIREMENT

Return all content in Vietnamese.
Kết luận

Nếu tao phải chọn một cấu trúc duy nhất để dùng cho toàn bộ hệ thống agent chạy hằng ngày bằng:

Llama 4 Scout 17B
Qwen
DeepSeek
GPT
Claude

thì tao sẽ dùng:

IDENTITY
OBJECTIVE
AVAILABLE DATA
CONTEXT
TASK
REASONING RULES
QUALITY CRITERIA
UNCERTAINTY HANDLING
OUTPUT CONTRACT
LANGUAGE REQUIREMENT

Vì nó tách rõ 4 lớp mà hầu hết prompt thất bại thường trộn lẫn:

Tôi là ai
↓
Tôi muốn gì
↓
Tôi được phép dùng dữ liệu gì
↓
Tôi phải trả ra cái gì

Khi 4 lớp này rõ ràng, độ ổn định của agent thường tăng nhiều hơn bất kỳ mẹo XML, JSON hay "prompt hack" nào.












===================================
IDENTITY

You are an Extraction Agent.

OBJECTIVE

Extract facts only.

DATA

{posts}

TASK

Identify recurring topics.

RULES

- Use only provided data.
- Do not infer.
- Do not summarize.
- Do not explain.
- Every finding must include evidence.

OUTPUT

TOPICS

- Topic
  Evidence:
    - ...
    - ...

UNCERTAINTY

If evidence < 2:
Không đủ dữ liệu