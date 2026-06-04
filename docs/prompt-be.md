# ROLE

Bạn là Staff Backend Engineer + Principal AI Systems Architect.

Nhiệm vụ:

THIẾT KẾ + CODE HOÀN CHỈNH backend production-ready.

Không viết proposal.

Không giải thích.

Không brainstorm.

Trả về kiến trúc + source code + cấu trúc dự án có thể chạy.

---

# CONTEXT

Tôi sẽ upload:

1. Product Spec
2. UI Spec

Backend đã tồn tại:

* Python
* FastAPI
* LangGraph
* PostgreSQL
* Redis
* RAG stack (đã hoàn thiện)
* Docker

KHÔNG được thiết kế lại sản phẩm.

KHÔNG thay đổi UX.

Backend phải phục vụ đúng UI.

---

# PRODUCT PRINCIPLE

Đây KHÔNG phải chatbot.

Đây là:

Content Workspace
+
AI Copilot

Flow:

Dashboard
↓

Create
↓

Clarify
↓

Generate
↓

Review
↓

Approve
↓

Publish

↓

History

---

# CORE RULE

KHÔNG dùng:

* multi-agent
* supervisor
* planner loop
* autonomous routing
* self-learning
* dynamic graph

Dùng:

# LangGraph

deterministic workflow engine

# Workers

execution units

---

# TARGET ARCHITECTURE

React
↓

FastAPI
↓

LangGraph

↓

Workers

↓

Providers

↓

Storage

Workers KHÔNG gọi nhau.

Graph điều phối.

---

# IMPLEMENT THESE WORKFLOWS

## ROOT GRAPH

START

↓

SESSION_INIT

↓

LOAD_CONTEXT

↓

CLASSIFY_REQUEST

↓

CLARIFY

↓

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

---

# LANGGRAPH STATE

Implement strongly typed state.

Fields:

session_id

workspace_id

user_id

request

template

clarification

context

retrieved_docs

outline

draft

images

edits

approved

publish_status

usage

error

---

# TEMPLATE 1 — SOCIAL

PREPARE

↓

WRITE

↓

OPTIONAL_IMAGE

↓

ASSEMBLE

↓

DONE

---

# TEMPLATE 2 — BLOG

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

---

# TEMPLATE 3 — IMAGE

PREPARE

↓

PROMPT

↓

IMAGE

↓

DONE

---

# TEMPLATE 4 — RESEARCH

QUERY

↓

SEARCH

↓

RERANK

↓

REPORT

---

# TEMPLATE 5 — CAMPAIGN

PREPARE

↓

RESEARCH

↓

PLAN

↓

PARALLEL

BLOG

ADS

IMAGE

SOCIAL

↓

ASSEMBLE

↓

DONE

---

# API

Implement exactly.

POST /session

POST /workflow/start

POST /workflow/resume

GET /workflow/status/{id}

PATCH /draft/{id}

POST /draft/review

POST /publish

GET /workspace

GET /history

DELETE /session/{id}

---

# REQUIRED OUTPUT

Generate COMPLETE PROJECT.

Output order:

1 Folder tree

2 Dependencies

3 Environment variables

4 Database schema

5 LangGraph implementation

6 Workers

7 FastAPI routes

8 Services

9 Queue

10 Tests

11 Docker

12 Run instructions

---

# IMPLEMENTATION RULES

Code only.

No placeholders.

No TODO.

No pseudo.

No stubs.

No fake implementation.

Every endpoint runnable.

Every graph executable.

Every state serializable.

Every worker injectable.

Every dependency wired.

---

# QUALITY RULES

Use:

Pydantic v2

Async SQLAlchemy

Dependency Injection

Typed configs

Structured logging

Retry

Timeout

OpenTelemetry hooks

Healthcheck

Graceful shutdown

---

# PERFORMANCE

Support:

100 concurrent users

Average:

<5s draft generation

<500ms API response

Queue for long tasks

---

# FAILURE RULES

If node fails:

retry

persist state

resume

no duplicate publish

---

# FINAL OUTPUT

Return code incrementally.

Start from:

folder tree

then generate files one by one.

Never skip files.

Stop only after backend is fully implemented.
