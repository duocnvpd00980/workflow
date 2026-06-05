Sau khi gom toàn bộ UI đã thiết kế (Dashboard, Workspace, Templates, Brand Voice, Integrations, Reports, Settings, Publish…), tôi sẽ không thiết kế kiểu REST 100 endpoint.

Mục tiêu:

1 backend
1 frontend
1–2 dev
ship được

Tôi chốt khoảng:

≈ 35–45 API

không tính:

auth
monitoring
admin
webhook nội bộ
1. AUTH (4)
POST /auth/login

POST /auth/logout

POST /auth/refresh

GET /auth/me
2. DASHBOARD (4)

UI:

Recent Projects
Credits
Suggestions
Activities

API:

GET /dashboard

GET /dashboard/recent

GET /dashboard/activity

GET /dashboard/suggestions
3. WORKSPACE (6)

UI:

create
open
resume
delete
history

API:

POST /workspaces

GET /workspaces

GET /workspaces/{id}

PATCH /workspaces/{id}

DELETE /workspaces/{id}

GET /workspaces/{id}/history
4. LANGGRAPH WORKFLOW (6)

Đây là API chính.

POST /workflow/start

POST /workflow/resume

GET /workflow/{id}

POST /workflow/cancel

GET /workflow/{id}/events

POST /workflow/retry
5. DRAFT + EDITOR (6)

UI:

editor

review

version

API:

GET /drafts/{id}

PATCH /drafts/{id}

POST /drafts/review

POST /drafts/approve

GET /drafts/{id}/versions

POST /drafts/{id}/restore
6. TEMPLATE LIBRARY (4)

UI:

templates

API:

GET /templates

GET /templates/{id}

POST /templates/custom

DELETE /templates/{id}
7. BRAND VOICE (6)

UI:

Tone

CTA

Image

Products

Reference

API:

GET /brand

PATCH /brand

POST /brand/products

DELETE /brand/products/{id}

POST /brand/reference

DELETE /brand/reference/{id}
8. CHANNEL INTEGRATION (5)

UI:

facebook

wordpress

instagram

API:

GET /channels

POST /channels/connect

POST /channels/disconnect

PATCH /channels/config

POST /channels/test
9. PUBLISH (3)

UI:

publish
status
retry

API:

POST /publish

GET /publish/{id}

POST /publish/{id}/retry
10. REPORTS (4)

UI:

metrics

usage

API:

GET /reports

GET /reports/content

GET /reports/templates

GET /reports/usage
11. SETTINGS (4)

UI:

system
limits
preferences

API:

GET /settings

PATCH /settings

POST /settings/export

DELETE /settings/reset
12. FILES (3)

UI:

upload

reference

preview

API:

POST /files

GET /files/{id}

DELETE /files/{id}
Tổng
Module	API
Auth	4
Dashboard	4
Workspace	6
Workflow	6
Draft	6
Templates	4
Brand	6
Channels	5
Publish	3
Reports	4
Settings	4
Files	3

≈

55 API

Nhưng build thật tôi sẽ chia phase:

MVP (2–4 tuần)
18–22 API
Production v1
35 API
Full như UI vừa thiết kế
50–55 API

Và quan trọng:

LangGraph thực tế chỉ chạm khoảng 6 API thôi:

POST /workflow/start

POST /workflow/resume

GET /workflow/{id}

PATCH /draft

POST /approve

POST /publish

còn lại chủ yếu CRUD cho UI.