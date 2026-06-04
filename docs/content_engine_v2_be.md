0. Triết lý
UI
↓

Session

↓

Workflow

↓

Worker

↓

Provider

↓

Storage

Worker KHÔNG gọi worker.

Graph điều phối.

1. LangGraph tổng
START

↓

SESSION_INIT

↓

LOAD_CONTEXT

↓

CLASSIFY_REQUEST

↓

CLARIFY
   │
   └── WAIT_USER
          │
          ▼

SELECT_TEMPLATE

↓

EXECUTE_TEMPLATE

↓

REVIEW

↓

APPROVE

↓

PUBLISH

↓

SAVE

↓

END

Tổng:

10 nodes
2. State
class WorkflowState:

    session_id:str

    workspace_id:str

    user_id:str

    request:str

    template:str

    clarification:list

    context:dict

    retrieved_docs:list

    outline:str

    draft:dict

    images:list

    edits:list

    approved:bool

    publish_status:str

    usage:dict

    error:str
3. NODE SPEC
NODE 1 — SESSION_INIT

Mục tiêu:

Tạo phiên làm việc.

Input:

{
"prompt":"..."
}

Output:

{
"session_id":""
}

DB:

create session

Fail:

return 503
NODE 2 — LOAD_CONTEXT

Mục tiêu:

nạp dữ liệu.

Load:

Brand Profile

Preferences

History

Credits

Output:

{
"context":{}
}

Nguồn:

Postgres
Redis

Không dùng LLM.

NODE 3 — CLASSIFY_REQUEST

Mục tiêu:

xác định loại công việc.

Input:

user request

Output:

{
"type":"BLOG"
}

Chỉ trả:

SOCIAL

BLOG

IMAGE

RESEARCH

CAMPAIGN

Không generate.

LLM nhỏ.

NODE 4 — CLARIFY

Mục tiêu:

hỏi nếu thiếu.

Logic:

missing
↓

question

Rule:

max 2 turns

Output:

{
"need_user":true
}

Nếu cần:

interrupt()

UI:

chat panel
NODE 5 — SELECT_TEMPLATE

Mục tiêu:

map loại yêu cầu.

Không dùng AI.

Mapping:

SOCIAL
↓

social_template

BLOG
↓

blog_template

IMAGE
↓

image_template

CAMPAIGN
↓

campaign_template

Output:

{
"template":"blog"
}
4. TEMPLATE GRAPH

Template mới là phần quan trọng.

TEMPLATE 1 — SOCIAL

Dùng:

caption

ads

social

Graph:

PREPARE

↓

WRITE

↓

OPTIONAL_IMAGE

↓

ASSEMBLE

↓

DONE

Node:

PREPARE

Input:

context

↓

WRITE

Worker:

writer

↓

OPTIONAL_IMAGE

Worker:

image

↓

ASSEMBLE

Output:

{
"text":"",
"image":""
}

Tổng:

4 nodes
TEMPLATE 2 — BLOG

Graph:

PREPARE

↓

RAG

↓

OUTLINE

↓

WAIT_APPROVAL

↓

WRITE

↓

POLISH

↓

DONE

PREPARE

↓

RAG

Worker:

retrieve

↓

OUTLINE

Worker:

planner

↓

WAIT_APPROVAL

interrupt

↓

WRITE

Worker:

writer

↓

POLISH

Worker:

editor

Tổng:

6 nodes
TEMPLATE 3 — IMAGE

Graph:

PREPARE

↓

PROMPT

↓

IMAGE

↓

DONE

Worker:

image

Tổng:

3 nodes
TEMPLATE 4 — RESEARCH

Graph:

QUERY

↓

SEARCH

↓

RERANK

↓

REPORT

Worker:

rag

Tổng:

4 nodes
TEMPLATE 5 — CAMPAIGN

Graph:

PREPARE

↓

RESEARCH

↓

PLAN

↓

PARALLEL
     │
     ├─ BLOG
     │
     ├─ ADS
     │
     ├─ IMAGE
     │
     └─ SOCIAL

↓

ASSEMBLE

↓

DONE

Parallel.

Tổng:

7 nodes
5. REVIEW NODE

Input:

{
"draft":""
}

Cho phép:

edit

regenerate

approve

Output:

{
"approved":true
}

Không regenerate toàn bộ.

Chỉ section.

6. PUBLISH NODE

Input:

{
"channel":"facebook"
}

Worker:

publisher

Output:

{
"url":"..."
}

Retry:

2

4

8
7. SAVE NODE

Lưu:

draft

history

usage

versions

Output:

END
8. API (đủ cho UI)

Chỉ cần khoảng:

POST /session

POST /workflow/start

POST /workflow/resume

GET /workflow/status

PATCH /draft

POST /draft/review

POST /publish

GET /workspace

GET /history

DELETE /session

≈

10 APIs
9. Mapping UI → API

Dashboard

↓

GET workspace

Create

↓

POST workflow/start

Clarify

↓

POST workflow/resume

Editor

↓

PATCH draft

Review

↓

POST review

Publish

↓

POST publish
10. Folder
backend/

api/

graph/

state.py

router.py

templates/

social.py

blog.py

campaign.py

nodes/

session.py

context.py

clarify.py

review.py

publish.py

workers/

writer.py

editor.py

image.py

research.py

publisher.py

rag/

retriever.py

rerank.py

Đây là bản tôi sẽ giao dev nếu mục tiêu là build thật bằng FastAPI + LangGraph + RAG và khớp UI vừa thiết kế.