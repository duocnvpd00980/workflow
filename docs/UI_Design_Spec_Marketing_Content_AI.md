# UI Design Spec — Marketing Content AI App

> **Stack**: React + TanStack Router + shadcn/ui  
> **Pattern**: Gmail/Jasper style — List + Detail  
> **Date**: 2026-06-13

---

## Table of Contents

1. [Navigation Structure](#1-navigation-structure)
2. [Brand Management](#2-brand-management)
3. [Task History](#3-task-history)
4. [Content (Main Feature)](#4-content-main-feature)
5. [RAG (Knowledge Base)](#5-rag-knowledge-base)
6. [Settings](#6-settings)
7. [Responsive Behavior](#7-responsive-behavior)
8. [API Mapping](#8-api-mapping)

---

## 1. Navigation Structure

```
┌────────┬─────────────────────────────────────────────┐
│ [Logo] │  [Brand: Acme ▼]    [🔔]  [⚡3]  [👤]      │
│        │                                             │
│ 📄 All │                                             │
│ 📝Blog │    [MAIN CONTENT AREA]                      │
│ 📧Email│                                             │
│ 📱Soc  │                                             │
│        │                                             │
│ ───────┤                                             │
│ 🏢 Brands              [+]                           │
│   ● Acme  ○ Brand B  ○ Brand C                     │
│        │                                             │
│ 📚 RAG  │                                             │
│ ⚡ Tasks  ←── Badge: số đang chạy                   │
│ ⚙️ Settings                                          │
└────────┴─────────────────────────────────────────────┘
```

### Top Bar
| Element | Behavior |
|---------|----------|
| `Brand: Acme ▼` | Dropdown chọn brand hiện tại. Ảnh hưởng toàn bộ app context |
| `🔔` | Notification bell — dropdown thông báo (toast + history) |
| `⚡3` | Task bell — badge số đang chạy. Click → dropdown real-time progress |
| `👤` | User menu — profile, settings, logout |

### Sidebar
| Item | Active | Navigate |
|------|--------|----------|
| 📄 All | Default | `/content` — all types |
| 📝 Blog | Filter blog | `/content?type=blog` |
| 📧 Email | Filter email | `/content?type=email` |
| 📱 Social | Filter social | `/content?type=social` |
| 🏢 Brands | Section expandable | Brand switcher + `[+]` tạo mới |
| 📚 RAG | Page | `/rag` — knowledge base |
| ⚡ Tasks | Page | `/tasks` — full task history |
| ⚙️ Settings | Page | `/settings` |

---

## 2. Brand Management

> **Pattern**: Sidebar Section (như Notion workspace)

### Brand Sidebar Section
```
┌────────┐
│ ───────┤
│ 🏢 BRANDS              [+]          │
│   ● Acme Corp        (active)       │
│   ○ StartupX                        │
│   ○ TechBrand VN                    │
│        │
│ ⚡ Tasks │
└────────┘
```

**Behavior:**
- Click brand name → switch context toàn app
- Brand active = `●`, inactive = `○`
- `[+]` → mở modal tạo brand mới
- Right-click brand → context menu: Edit / Delete / Set Default

### Brand Create/Edit Modal
```
┌─────────────────────────────────────┐
│  🏢 Tạo Brand Mới              [✕] │
├─────────────────────────────────────┤
│                                     │
│  Tên brand *                        │
│  ┌─────────────────────────────┐    │
│  │ Acme Corporation            │    │
│  └─────────────────────────────┘    │
│                                     │
│  Logo                               │
│  ┌─────────┐                        │
│  │   📷    │  [Upload / URL]       │
│  │  +Logo  │                        │
│  └─────────┘                        │
│                                     │
│  ─── Voice & Tone ───               │
│                                     │
│  Brand Voice *                      │
│  ┌─────────────────────────────┐    │
│  │ Professional, friendly,     │    │
│  │ authoritative but approachable│   │
│  └─────────────────────────────┘    │
│                                     │
│  Target Audience *                  │
│  ┌─────────────────────────────┐    │
│  │ Marketing managers, 25-45,  │    │
│  │ B2B SaaS, tech-savvy        │    │
│  └─────────────────────────────┘    │
│                                     │
│  Writing Guidelines                 │
│  ┌─────────────────────────────┐    │
│  │ - Use "you" not "we"        │    │
│  │ - Avoid jargon              │    │
│  │ - CTA always at end         │    │
│  └─────────────────────────────┘    │
│                                     │
│  ─── Visual ───                     │
│                                     │
│  Primary Color                      │
│  ┌──────┐ ┌─────────────────────┐   │
│  │ ████ │ │ #3B82F6             │   │
│  └──────┘ └─────────────────────┘   │
│                                     │
│  [Hủy]              [💾 Lưu Brand]  │
└─────────────────────────────────────┘
```

**Fields:**
| Field | Required | Type |
|-------|----------|------|
| Name | ✅ | Text |
| Logo | ❌ | Upload / URL |
| Brand Voice | ✅ | Textarea |
| Target Audience | ✅ | Textarea |
| Writing Guidelines | ❌ | Textarea |
| Primary Color | ❌ | Color picker |
| Secondary Color | ❌ | Color picker |

**API:**
- `GET /api/brands` — list
- `POST /api/brands` — create
- `PUT /api/brands/:id` — update
- `DELETE /api/brands/:id` — delete
- `PATCH /api/brands/:id/default` — set default

---

## 3. Task History

> **Pattern**: Notification Bell + Dropdown (như GitHub Actions)

### Task Bell Dropdown (Top Bar)
```
┌─────────────────────────────────────┐
│                         [🔔] [⚡3] [👤]│
│                         ┌─────────┐ │
│                         │ ⚡ Đang chạy (2) │
│                         │   • Gen blog "AI Trends"  45% │
│                         │     [████████░░░░░░░░░░]      │
│                         │     Còn ~2 phút • [Hủy]      │
│                         │                             │
│                         │   • Research thị trường VN  12%│
│                         │     [████░░░░░░░░░░░░░░]      │
│                         │     Còn ~5 phút • [Hủy]      │
│                         │ ─────────────────────────    │
│                         │ 📜 Hoàn thành (5)            │
│                         │   ✓ Gen email "Promo T6"   2p │
│                         │   ✓ Research đối thủ A     1h │
│                         │   ✓ Gen social post T6     3h │
│                         │ ─────────────────────────    │
│                         │ [Xem tất cả lịch sử →]       │
│                         └─────────┘ │
└─────────────────────────────────────┘
```

**Dropdown sections:**
1. **Đang chạy** — real-time progress bar, %, ETA, cancel button
2. **Hoàn thành gần đây** — 5 task mới nhất, click → navigate to content
3. **Footer link** → navigate to `/tasks`

### Task History Page (`/tasks`)
```
┌─────────────────────────────────────────────────────┐
│  ⚡ Lịch sử tác vụ                    [Filter ▼]   │
├─────────────────────────────────────────────────────┤
│  Tab: [Đang chạy] [Hoàn thành] [Lỗi] [Tất cả]     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ 🟡 Gen blog "AI Trends 2024"                │  │
│  │    Type: Blog  •  Brand: Acme               │  │
│  │    [████████████░░░░░░░░░░]  45%            │  │
│  │    Bắt đầu: 18:52  •  Còn ~2 phút          │  │
│  │    [Hủy]  [Xem log →]                      │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ 🟡 Research thị trường VN Q2                │  │
│  │    Type: Research  •  Brand: Acme           │  │
│  │    [████░░░░░░░░░░░░░░░░░░]  12%            │  │
│  │    Bắt đầu: 18:53  •  Còn ~5 phút          │  │
│  │    [Hủy]                                   │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
│  ─────────────────────────────────────────────────  │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ ✅ Gen email "Promo T6"                     │  │
│  │    Type: Email  •  Brand: Acme              │  │
│  │    Hoàn thành: 18:50  •  Thời gian: 2m 34s │  │
│  │    [Xem kết quả →]  [Tạo lại]              │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ 🔴 Gen social post "Flash Sale"             │  │
│  │    Type: Social  •  Brand: StartupX         │  │
│  │    Lỗi: Timeout (30s)  •  18:30            │  │
│  │    [Xem lỗi →]  [Thử lại]  [Xóa]           │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Task card states:**
| State | Badge | Actions |
|-------|-------|---------|
| Running | 🟡 | Progress bar, ETA, Cancel, View log |
| Success | ✅ | View result, Regenerate, Delete |
| Error | 🔴 | View error, Retry, Delete |
| Queued | ⏳ | Waiting, Cancel |

**API:**
- `GET /api/tasks` — list with filter (status, type, brand)
- `GET /api/tasks/:id` — detail + log
- `POST /api/tasks/:id/cancel` — cancel running
- `POST /api/tasks/:id/retry` — retry failed
- `DELETE /api/tasks/:id` — delete

---

## 4. Content (Main Feature)

### Content List (`/content`)
```
┌─────────────────────────────────────────────────────────┐
│  [☰]  All Content                    [🔍] [Filter ▼] [+ Tạo mới]│
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 🟢  Blog: "AI Trends 2024"              2h trước │   │
│  │     Brand: Acme  •  1,240 words  •  [✏️] [🗑️] │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 🟡  Email: "Promo T6 Campaign"          Đang tạo │   │
│  │     Brand: Acme  •  [████████░░] 60%  •  [✕]    │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 🟢  Social: "Flash Sale Post"           1d trước │   │
│  │     Brand: StartupX  •  280 chars  •  [✏️] [🗑️]│   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 🔴  Blog: "Research VN Q2"              Lỗi      │   │
│  │     Brand: Acme  •  Timeout  •  [↻ Thử lại]      │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**List columns:**
| Field | Display |
|-------|---------|
| Status | 🟢 Ready / 🟡 Running / 🔴 Error |
| Type | Icon + label (Blog/Email/Social) |
| Title | Truncated if long |
| Brand | Brand name |
| Length | Word count / char count |
| Time | Relative time |
| Actions | Edit, Delete, Retry (if error) |

### Content Detail (`/content/:id`)
```
┌─────────────────────────────────────────────────────────┐
│  [← Quay lại]  Blog: "AI Trends 2024"    [✏️] [🗑️] [⋯]│
├─────────────────────────────────────────────────────────┤
│  Tab: [Preview] [Edit] [Versions] [Settings]            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │                                                  │   │
│  │  The Future of AI in Marketing                   │   │
│  │                                                  │   │
│  │  Artificial intelligence is transforming...      │   │
│  │                                                  │   │
│  │  [Full content rendered here]                    │   │
│  │                                                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ─── Metadata ───                                       │
│  Brand: Acme Corp  •  Type: Blog  •  Words: 1,240       │
│  Created: Jun 13, 18:30  •  Last edited: Jun 13, 19:15   │
│                                                         │
│  [📋 Copy]  [📥 Export]  [🔄 Regenerate]  [🚀 Publish]  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Detail tabs:**
| Tab | Content |
|-----|---------|
| Preview | Rendered content (HTML/Markdown) |
| Edit | Inline editor — sửa trực tiếp |
| Versions | History các lần regenerate |
| Settings | Meta: brand, type, tone, prompt gốc |

### Create Content Flow
```
Step 1: Chọn template
┌─────────────────────────────────────────────────────┐
│  Tạo nội dung mới                              [✕]  │
├─────────────────────────────────────────────────────┤
│  Chọn loại nội dung:                                │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │   📝     │  │   📧     │  │   📱     │         │
│  │  Blog    │  │  Email   │  │  Social  │         │
│  │  Post    │  │  Campaign│  │  Post    │         │
│  │          │  │          │  │          │         │
│  │ [Chọn]   │  │ [Chọn]   │  │ [Chọn]   │         │
│  └──────────┘  └──────────┘  └──────────┘         │
│                                                     │
│  ─── Hoặc chọn template có sẵn ───                  │
│  [Blog giới thiệu sản phẩm] [Email welcome] ...     │
└─────────────────────────────────────────────────────┘

Step 2: Nhập thông tin
┌─────────────────────────────────────────────────────┐
│  📝 Tạo Blog Post                              [✕]  │
├─────────────────────────────────────────────────────┤
│  Brand: Acme Corp ▼                                 │
│                                                     │
│  Chủ đề / Prompt *                                  │
│  ┌─────────────────────────────────────────────┐    │
│  │ Viết blog về xu hướng AI trong marketing   │    │
│  │ năm 2024, tập trung vào content...         │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  Độ dài mong muốn                                    │
│  [○ Ngắn (~500 từ)]  [● Vừa (~1000 từ)]  [○ Dài]   │
│                                                     │
│  Tone giọng                                          │
│  [Professional ▼]  [Friendly ▼]  [Persuasive ▼]      │
│                                                     │
│  [Hủy]                    [⚡ Generate]              │
└─────────────────────────────────────────────────────┘
```

**API:**
- `GET /api/content` — list (filter: type, brand, status, search)
- `GET /api/content/:id` — detail
- `POST /api/content` — create (triggers background task)
- `PUT /api/content/:id` — update
- `DELETE /api/content/:id` — delete
- `POST /api/content/:id/regenerate` — regenerate

---

## 5. RAG (Knowledge Base)

> **Pattern**: Card Grid + Drawer (NOT master-detail)

### RAG List (`/rag`) — Card Grid
```
┌─────────────────────────────────────────────────────────┐
│  📚 Knowledge Base                        [+ Upload]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │    📄       │    │    📄       │    │    📄       │ │
│  │  Brand      │    │  Marketing  │    │  Competitor │ │
│  │  Guidelines │    │  Research   │    │  Analysis   │ │
│  │             │    │  Q2         │    │             │ │
│  │  🟢 Ready   │    │  🟡 Indexing│    │  🟢 Ready   │ │
│  │  12 chunks  │    │  45%        │    │  89 chunks  │ │
│  │  Sync: 2h   │    │  Started:   │    │  Sync: 1d   │ │
│  │             │    │  now        │    │             │ │
│  │ [🔄] [🗑️]  │    │ [✕ Cancel]  │    │ [🔄] [🗑️]  │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                         │
│  ┌─────────────┐    ┌─────────────┐                     │
│  │    📄       │    │    🔗       │                     │
│  │  Product    │    │  Website    │                     │
│  │  Catalog    │    │  Content    │                     │
│  │             │    │             │                     │
│  │  🔴 Error   │    │  🟢 Ready   │                     │
│  │  Failed     │    │  156 chunks │                     │
│  │             │    │  Sync: 3d   │                     │
│  │ [↻ Retry]   │    │             │                     │
│  │ [🗑️]       │    │ [🔄] [🗑️]  │                     │
│  └─────────────┘    └─────────────┘                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Card elements:**
| Element | Description |
|---------|-------------|
| File icon | PDF, DOC, TXT, URL |
| Document name | Truncated if > 2 lines |
| Status badge | 🟢 Ready / 🟡 Indexing / 🔴 Error |
| Chunk count | "X chunks" or "X%" if indexing |
| Last sync | Relative time |
| Actions | Sync (🔄), Delete (🗑️), Cancel (✕), Retry (↻) |

### RAG Detail — Drawer (click card)
```
┌────────────────────────────────────────┐
│                                        │
│    [Card Grid — mờ 50%]                │
│                                        │
│         ┌────────────────────┐ ←── Slide from right
│         │ 📄 Brand Guidelines │
│         │                     │
│         │ ┌─────────────┐     │
│         │ │ 🟢 Ready    │     │
│         │ └─────────────┘     │
│         │                     │
│         │ Type:      PDF      │
│         │ Size:      2.4 MB   │
│         │ Chunks:    12 / 12  │
│         │ Created:   Jun 11   │
│         │ Last Sync: 2h trước │
│         │                     │
│         │ ─────────────────── │
│         │ CHUNKS              │
│         │ ┌─────────────────┐ │
│         │ │ 1. Brand tone...│ │
│         │ │ 2. Target audi..│ │
│         │ │ 3. Color usage..│ │
│         │ │ ... 9 more      │ │
│         │ └─────────────────┘ │
│         │                     │
│         │ ─────────────────── │
│         │ PREVIEW             │
│         │ ┌─────────────────┐ │
│         │ │ Our brand voice │ │
│         │ │ is professional │ │
│         │ │ yet approachable..│ │
│         │ │ ...               │ │
│         │ └─────────────────┘ │
│         │                     │
│         │ [🔄 Sync Now]       │
│         │ [🗑️ Delete]         │
│         │                     │
│         │ [✕ Close]           │
│         └────────────────────┘
│                                        │
└────────────────────────────────────────┘
```

**Drawer sections:**
1. **Header**: File name + status badge
2. **Metadata**: Type, size, chunks, timestamps
3. **Chunks**: Collapsible list — xem các chunk đã split
4. **Preview**: 10-15 dòng đầu nội dung file (read-only)
5. **Actions**: Sync, Delete

**Why Drawer (not page):**
- RAG = "set & forget" — tần suất xem thấp
- Drawer giữ context (background vẫn là list)
- Không cần load trang mới, không mất scroll position
- Actions đơn giản: sync, delete — không cần edit phức tạp

**API:**
- `GET /api/rag` — list documents
- `GET /api/rag/:id` — detail + chunks
- `POST /api/rag/upload` — upload new
- `POST /api/rag/:id/sync` — re-sync
- `DELETE /api/rag/:id` — delete

---

## 6. Settings

```
┌─────────────────────────────────────────────────────────┐
│  ⚙️ Settings                                            │
├─────────────────────────────────────────────────────────┤
│  Tab: [Profile] [Team] [API Keys] [Billing] [Integrations]│
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ─── Profile ───                                        │
│  Tên:        ┌─────────────────────┐                  │
│              │ Nguyễn Văn A        │                  │
│              └─────────────────────┘                  │
│  Email:      ┌─────────────────────┐                  │
│              │ a@company.com       │                  │
│              └─────────────────────┘                  │
│                                                         │
│  ─── Team ───                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 👤 Nguyễn Văn A (Admin)  a@company.com  [Quản lý]│   │
│  │ 👤 Trần Thị B (Editor)   b@company.com  [Xóa]   │   │
│  │ 👤 Lê Văn C (Viewer)     c@company.com  [Xóa]   │   │
│  └──────────────────────────────────────────────────┘   │
│  [+ Mời thành viên]                                     │
│                                                         │
│  ─── API Keys ───                                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │ sk-abc123...xyz   Created: Jun 1  [🗑️]          │   │
│  │ sk-def456...uvw   Created: May 15 [🗑️]          │   │
│  └──────────────────────────────────────────────────┘   │
│  [+ Tạo API Key]                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Responsive Behavior

### Desktop (>1024px)
- Full layout: sidebar + content area
- RAG drawer: 400px from right
- Content detail: master-detail or page

### Tablet (768-1024px)
- Sidebar collapsible (hamburger menu)
- Content list full width
- Detail: drawer or modal

### Mobile (<768px)
- Sidebar → bottom sheet
- Content list: card list (not table)
- Detail: full screen page
- RAG drawer → bottom sheet
- Task dropdown → bottom sheet

---

## 8. API Mapping

| UI | Endpoint | Method |
|----|----------|--------|
| **Brand** | | |
| List brands | `/api/brands` | GET |
| Create brand | `/api/brands` | POST |
| Update brand | `/api/brands/:id` | PUT |
| Delete brand | `/api/brands/:id` | DELETE |
| Set default | `/api/brands/:id/default` | PATCH |
| **Content** | | |
| List content | `/api/content` | GET |
| Get content | `/api/content/:id` | GET |
| Create content | `/api/content` | POST |
| Update content | `/api/content/:id` | PUT |
| Delete content | `/api/content/:id` | DELETE |
| Regenerate | `/api/content/:id/regenerate` | POST |
| **RAG** | | |
| List documents | `/api/rag` | GET |
| Get document | `/api/rag/:id` | GET |
| Upload | `/api/rag/upload` | POST |
| Sync | `/api/rag/:id/sync` | POST |
| Delete | `/api/rag/:id` | DELETE |
| **Tasks** | | |
| List tasks | `/api/tasks` | GET |
| Get task | `/api/tasks/:id` | GET |
| Cancel | `/api/tasks/:id/cancel` | POST |
| Retry | `/api/tasks/:id/retry` | POST |
| Delete | `/api/tasks/:id` | DELETE |

---

## Summary

| Feature | Pattern | UI Type |
|---------|---------|---------|
| Brand | Notion workspace | Sidebar section + Modal |
| Task (real-time) | GitHub Actions bell | Top bar dropdown |
| Task (history) | GitHub Actions list | Page `/tasks` |
| Content List | Gmail | Table / List |
| Content Detail | Jasper | Master-detail / Page |
| Content Create | Jasper template | Modal flow |
| RAG List | Vercel projects | Card Grid |
| RAG Detail | GitHub PR drawer | Drawer (not page) |
| Settings | Standard | Tabbed page |

---

*Generated by Kimi — 2026-06-13*
