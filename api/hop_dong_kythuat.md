
contract = """# HỢP ĐỒNG KỸ THUẬT: Agent Orchestration UI
## Dự án: Nâng cấp UI giám sát Agent LangGraph

---

## 1. TỔNG QUAN

### 1.1 Mục tiêu
Xây dựng UI cho phép user **giám sát và kiểm tra chi tiết từng node agent** theo thời gian thực, với cảm giác như **trao đổi trong khung làm việc quen thuộc** — giống nói chuyện với agent bên kia.

### 1.2 Nguyên tắc cốt lõi
- **BE stream raw data (JSON)**, FE tự render UI
- **Chat UX quen thuộc** nhưng bên dưới là **workflow orchestration**
- **Agent tự quyết kế hoạch** → báo user số bước → thực thi từng bước → báo kết quả từng bước
- **Real-time per-node updates** — user thấy agent "đang nghĩ", "đang làm việc"

### 1.3 Stack hiện tại
| Layer | Tech |
|-------|------|
| Backend | FastAPI + LangGraph (main_v7) + SQLAlchemy |
| Frontend | React + TanStack Router + AI Elements + shadcn/ui |
| Streaming | SSE (Server-Sent Events) |
| State | Zustand (đề xuất) hoặc useState |

---

## 2. CẤU TRÚC DỮ LIỆU LANGGRAPH

### 2.1 State Structure
```json
{
  "values": {
    "user_input": "string",
    "language": "vi",
    "budget_limit": 2.0,
    
    // Mỗi node là key trong values
    "input_guard": {
      "execution_id": "UUID",
      "trace_id": "UUID",
      "node_id": "input_guard",
      "payload": {
        "status": "SUCCESS | FAILED",
        "text": "output text",
        "state": { /* node-specific state */ },
        "metrics": { /* performance metrics */ }
      },
      "timestamp": 1780410088.537616
    },
    
    "heuristic_router": { /* ... */ },
    "cache_read": { /* ... */ },
    "final_response": { /* ... */ },
    "errors": []
  },
  "next": [],
  "tasks": [],
  "config": {
    "configurable": {
      "thread_id": "bench-002",
      "checkpoint_id": "..."
    }
  }
}
```

### 2.2 Node Payload Standard
```typescript
interface NodePayload {
  status: "SUCCESS" | "FAILED" | "PENDING";
  text: string;           // Output text
  state: Record<string, any>;  // Node-specific state
  metrics: {
    latency_ms?: number;
    model?: string;
    input_tokens?: number;
    output_tokens?: number;
    node_path?: string[];
    cache_tier?: "L1" | "L2";
    similarity_score?: number;
  };
}
```

### 2.3 Key Fields by Node Type
| Node | Key State Fields | Key Metrics |
|------|-----------------|-------------|
| input_guard | `is_safe`, `sanitized_text`, `risk_category` | - |
| heuristic_router | `route_to`, `process_completed` | `matched_keyword` |
| cache_read | `cache_status` (hit/miss), `query` | `cache_tier`, `similarity_score` |
| knowledgebase | `retrieved_docs`, `query` | `retrieval_latency` |
| generation | `generated_text`, `finish_reason` | `model`, `tokens` |
| final_response | `answer_source`, `confidence`, `finish_reason` | `latency_ms`, `node_path` |

---

## 3. API CONTRACT (Backend → Frontend)

### 3.1 Endpoint
```
POST /chat/stream
Content-Type: application/json
Accept: text/event-stream

Body: {
  "message": "string",
  "session_id": "string",
  "conversation_id": "UUID",
  "msg_id": "string (optional)"
}

Response: SSE stream (text/event-stream)
```

### 3.2 SSE Event Types (Chronological Order)

#### 3.2.1 `agent_start` — Bắt đầu xử lý
```json
{
  "event": "agent_start",
  "run_id": "bench-002",
  "timestamp": 1780410088.500000,
  "data": {
    "message": "Đang phân tích yêu cầu của bạn...",
    "user_input": "quy định nghỉ phép năm 2025"
  }
}
```
**Timing:** Emit ngay khi nhận request, trước khi chạy node đầu tiên.
**FE Action:** Tạo assistant message "thinking" với animation.

---

#### 3.2.2 `agent_plan` — Kế hoạch từ heuristic_router
```json
{
  "event": "agent_plan",
  "run_id": "bench-002",
  "timestamp": 1780410088.520000,
  "data": {
    "message": "Đã phân tích yêu cầu. Tôi sẽ thực hiện 5 bước:",
    "steps": [
      {"id": "input_guard", "label": "Kiểm duyệt đầu vào", "order": 1},
      {"id": "heuristic_router", "label": "Định tuyến", "order": 2},
      {"id": "cache_read", "label": "Đọc cache", "order": 3},
      {"id": "knowledgebase", "label": "Knowledge", "order": 4},
      {"id": "final_response", "label": "Hoàn tất", "order": 5}
    ],
    "route_to": "rag_knowledge"
  }
}
```
**Timing:** Emit sau khi heuristic_router chạy xong, trước khi chạy các node tiếp theo.
**Source:** Từ `heuristic_router.payload.state.route_to` + danh sách nodes sẽ chạy.
**FE Action:** Tạo planning message với danh sách bước (pending/running/done).

---

#### 3.2.3 `step_start` — Bắt đầu node
```json
{
  "event": "step_start",
  "run_id": "bench-002",
  "timestamp": 1780410088.530000,
  "data": {
    "step_id": "input_guard",
    "step_label": "Kiểm duyệt đầu vào",
    "order": 1,
    "input": "quy định nghỉ phép năm 2025"
  }
}
```
**Timing:** Emit khi node bắt đầu chạy (trước xử lý).
**FE Action:** Update step status từ "pending" → "running".

---

#### 3.2.4 `step_progress` — Tiến độ node (optional)
```json
{
  "event": "step_progress",
  "run_id": "bench-002",
  "timestamp": 1780410088.535000,
  "data": {
    "step_id": "knowledgebase",
    "progress": 0.6,
    "log": "Đang tìm trên 12 nguồn...",
    "detail": {
      "current_source": "Bloomberg",
      "items_found": 7
    }
  }
}
```
**Timing:** Emit trong quá trình node chạy (nếu node hỗ trợ).
**FE Action:** Update progress bar, append log.

---

#### 3.2.5 `node_detail` — Chi tiết node (từ chunk trực tiếp)
```json
{
  "event": "node_detail",
  "run_id": "bench-002",
  "timestamp": 1780410088.537616,
  "data": {
    "node_id": "input_guard",
    "node_label": "Kiểm duyệt đầu vào",
    "order": 1,
    "status": "SUCCESS",
    "text": "quy định nghỉ phép năm 2025",
    "state": {
      "is_safe": true,
      "sanitized_text": "quy định nghỉ phép năm 2025",
      "risk_category": "NONE"
    },
    "metrics": {},
    "duration_ms": 7.6,
    "route_to": null,
    "cache_status": null
  }
}
```
**Timing:** Emit khi node hoàn thành (từ chunk, không cần aget_state).
**Source:** Trích xuất trực tiếp từ `chunk[node_id].payload`.
**FE Action:** Update step status → "done", merge detail vào step.

---

#### 3.2.6 `step_done` — Hoàn thành node (ngầm hoặc rõ ràng)
```json
{
  "event": "step_done",
  "run_id": "bench-002",
  "timestamp": 1780410088.537616,
  "data": {
    "step_id": "input_guard",
    "order": 1,
    "status": "SUCCESS",
    "output_text": "quy định nghỉ phép năm 2025",
    "duration_ms": 7.6
  }
}
```
**Timing:** Emit khi node xong.
**Note:** Có thể merge vào `node_detail` hoặc giữ riêng. Quyết định: **merge vào `node_detail`** để giảm số event.

---

#### 3.2.7 `step_result` — Kết quả từng bước (message riêng)
```json
{
  "event": "step_result",
  "run_id": "bench-002",
  "timestamp": 1780410088.540000,
  "data": {
    "step_id": "cache_read",
    "step_label": "Đọc cache",
    "order": 3,
    "content": "Tìm thấy trong cache L1 (similarity: 1.0)",
    "output": {
      "text": "Từ ngày 01/01/2026...",
      "state": {"cache_status": "hit", "query": "..."},
      "metrics": {"cache_tier": "L1", "similarity_score": 1.0}
    }
  }
}
```
**Timing:** Emit khi node quan trọng hoàn thành (ví dụ: research, generation).
**FE Action:** Tạo message mới trong conversation — "Bước X hoàn thành — [Label]".

---

#### 3.2.8 `result` — Kết quả cuối
```json
{
  "event": "result",
  "run_id": "bench-002",
  "timestamp": 1780410088.543950,
  "data": {
    "status": "success",
    "text": "Từ ngày 01/01/2026, nhà giáo...",
    "answer_source": "cache",
    "confidence": 1.0,
    "sources": [],
    "metrics": {
      "latency_ms": 0.0,
      "model": "",
      "input_tokens": 0,
      "output_tokens": 0,
      "node_path": ["cache_read"]
    },
    "error": null,
    "node_history": [
      {
        "node_id": "input_guard",
        "node_label": "Kiểm duyệt đầu vào",
        "status": "SUCCESS",
        "text": "...",
        "state": {...},
        "metrics": {},
        "timestamp": 1780410088.537616,
        "duration_ms": 7.6
      }
      // ... các node khác
    ]
  }
}
```
**Timing:** Emit khi toàn bộ graph hoàn thành.
**FE Action:** Update final message content, mark run as done.

---

#### 3.2.9 `error` — Lỗi
```json
{
  "event": "error",
  "run_id": "bench-002",
  "timestamp": 1780410088.550000,
  "data": {
    "step_id": "knowledgebase",
    "code": "API_TIMEOUT",
    "message": "API timeout sau 30s",
    "retryable": true,
    "fallback_action": "fallback_search"
  }
}
```
**Timing:** Emit khi node hoặc graph gặp lỗi.
**FE Action:** Mark step as error, hiển thị retry button.

---

#### 3.2.10 `done` — Stream kết thúc
```json
{
  "event": "done",
  "run_id": "bench-002",
  "timestamp": 1780410088.550000,
  "data": {}
}
```
**Timing:** Emit cuối cùng, đóng stream.
**FE Action:** Mark stream as complete, enable input.

---

### 3.3 Event Flow Timeline (Ví dụ)

```
T+0.0s   User gửi: "quy định nghỉ phép năm 2025"
T+0.1s   → agent_start      → FE: "Đang phân tích..."
T+0.3s   → agent_plan       → FE: Hiển thị 5 bước (tất cả "Chờ")
T+0.5s   → step_start (1)   → FE: Bước 1 → "Đang chạy..."
T+0.8s   → node_detail (1)  → FE: Bước 1 → "✓ Xong" (7.6ms)
T+0.9s   → step_start (2)   → FE: Bước 2 → "Đang chạy..."
T+1.0s   → node_detail (2)  → FE: Bước 2 → "✓ Xong" (route: rag_knowledge)
T+1.1s   → step_start (3)   → FE: Bước 3 → "Đang chạy..."
T+1.2s   → step_progress (3) → FE: Progress 60%, log "Đang tìm..."
T+1.5s   → node_detail (3)  → FE: Bước 3 → "✓ Xong" (cache hit L1)
T+1.6s   → step_result (3)  → FE: Message mới "Bước 3 hoàn thành — Đọc cache"
T+1.7s   → step_start (4)   → FE: Bước 4 → "Đang chạy..."
T+2.0s   → node_detail (4)  → FE: Bước 4 → "✓ Xong"
T+2.1s   → step_start (5)   → FE: Bước 5 → "Đang chạy..."
T+2.2s   → node_detail (5)  → FE: Bước 5 → "✓ Xong"
T+2.3s   → result           → FE: Final message + update planning
T+2.3s   → done             → FE: Stream complete
```

---

## 4. FRONTEND STATE CONTRACT

### 4.1 Unified Message Types
```typescript
// Base
type MessageRole = "user" | "assistant";

// User message
interface UserMessage {
  id: string;
  role: "user";
  type: "user";
  content: string;
  timestamp: number;
}

// Agent planning message
interface AgentPlanMessage {
  id: string;
  role: "assistant";
  type: "agent_plan";
  content: string;  // "Đã phân tích... 5 bước"
  steps: Array<{
    id: string;
    label: string;
    order: number;
    status: "pending" | "running" | "done" | "error";
    input?: any;
    output?: any;
    logs: string[];
    startedAt?: number;
    completedAt?: number;
    durationMs?: number;
    metrics?: Record<string, any>;
  }>;
  routeTo?: string;
  timestamp: number;
  isExpanded: boolean;
}

// Step result message (intermediate)
interface StepResultMessage {
  id: string;
  role: "assistant";
  type: "step_result";
  stepId: string;
  stepLabel: string;
  order: number;
  content: string;  // Output text
  output: {
    text: string;
    state: Record<string, any>;
    metrics: Record<string, any>;
  };
  timestamp: number;
}

// Final result message
interface AgentResultMessage {
  id: string;
  role: "assistant";
  type: "agent_result";
  content: string;  // Final text
  status: "success" | "fallback" | "review" | "error";
  answerSource: string;
  confidence: number;
  sources: any[];
  metrics: {
    latencyMs: number;
    model: string;
    inputTokens: number;
    outputTokens: number;
    nodePath: string[];
  };
  error: {
    code: string;
    message: string;
    retryable: boolean;
  } | null;
  timestamp: number;
}

type ChatMessage = UserMessage | AgentPlanMessage | StepResultMessage | AgentResultMessage;
```

### 4.2 State Shape
```typescript
interface ChatState {
  messages: ChatMessage[];
  status: "idle" | "streaming" | "done" | "error";
  currentRunId: string | null;
  error: string | null;
  
  // Derived (computed, không lưu)
  activePlan: AgentPlanMessage | null;
  runningSteps: Array<{ id: string; label: string; order: number }>;
  completedSteps: Array<{ id: string; label: string; order: number }>;
}
```

### 4.3 Transform Logic (Hook)
```typescript
// Event → Message mapping
function transformEvent(event: SSEEvent, state: ChatState): ChatState {
  switch (event.event) {
    case "agent_start":
      return addMessage(state, {
        id: `plan-${event.run_id}`,
        role: "assistant",
        type: "agent_plan",
        content: event.data.message,
        steps: [],
        timestamp: event.timestamp,
        isExpanded: true
      });

    case "agent_plan":
      return updateMessage(state, `plan-${event.run_id}`, msg => ({
        ...msg,
        content: event.data.message,
        steps: event.data.steps.map((s, i) => ({
          id: s.id,
          label: s.label,
          order: s.order || i + 1,
          status: "pending",
          logs: []
        })),
        routeTo: event.data.route_to
      }));

    case "step_start":
      return updateMessage(state, `plan-${event.run_id}`, msg => ({
        ...msg,
        steps: msg.steps.map(s =>
          s.id === event.data.step_id
            ? { ...s, status: "running", startedAt: event.timestamp, input: event.data.input }
            : s
        )
      }));

    case "step_progress":
      return updateMessage(state, `plan-${event.run_id}`, msg => ({
        ...msg,
        steps: msg.steps.map(s =>
          s.id === event.data.step_id
            ? { ...s, logs: [...s.logs, event.data.log] }
            : s
        )
      }));

    case "node_detail":
      return updateMessage(state, `plan-${event.run_id}`, msg => ({
        ...msg,
        steps: msg.steps.map(s =>
          s.id === event.data.node_id
            ? {
                ...s,
                status: event.data.status === "SUCCESS" ? "done" : "error",
                output: {
                  text: event.data.text,
                  state: event.data.state,
                  metrics: event.data.metrics
                },
                completedAt: event.timestamp,
                durationMs: event.data.duration_ms
              }
            : s
        )
      }));

    case "step_result":
      return addMessage(state, {
        id: `result-${event.data.step_id}-${event.timestamp}`,
        role: "assistant",
        type: "step_result",
        stepId: event.data.step_id,
        stepLabel: event.data.step_label,
        order: event.data.order,
        content: event.data.content,
        output: event.data.output,
        timestamp: event.timestamp
      });

    case "result":
      return addMessage(state, {
        id: `final-${event.run_id}`,
        role: "assistant",
        type: "agent_result",
        content: event.data.text,
        status: event.data.status,
        answerSource: event.data.answer_source,
        confidence: event.data.confidence,
        sources: event.data.sources,
        metrics: event.data.metrics,
        error: event.data.error,
        timestamp: event.timestamp
      });

    case "error":
      return {
        ...state,
        status: "error",
        error: event.data.message
      };

    case "done":
      return { ...state, status: "done" };

    default:
      return state;
  }
}
```

---

## 5. UI RENDER CONTRACT

### 5.1 Message Rendering Rules

| Message Type | Component | Position | Behavior |
|-------------|-----------|----------|----------|
| `user` | `Message from="user"` | In `Conversation` | Static, right-aligned |
| `agent_plan` | Custom `AgentPlanCard` | In `Conversation` | Collapsible, auto-expand on new steps |
| `step_result` | `Message from="assistant"` + `StepResultBadge` | In `Conversation` | Green checkmark + step label |
| `agent_result` | `Message from="assistant"` + `MessageResponse` | In `Conversation` | Final answer, markdown support |

### 5.2 Agent Plan Card Spec
```
┌─────────────────────────────────────────┐
│ 🤖 Agent                                │
│                                         │
│ "Đã phân tích yêu cầu. Tôi sẽ thực hiện│
│  5 bước:"                               │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ ① Kiểm duyệt đầu vào    ✓ Xong    │ │  // bg-emerald-50, text-emerald-600
│ │ ② Định tuyến            ✓ Xong    │ │  // bg-emerald-50
│ │ ③ Đọc cache             ▶ Đang...  │ │  // bg-blue-50, text-blue-600, animate-pulse
│ │ ④ Knowledge             ○ Chờ     │ │  // bg-slate-50, text-slate-400
│ │ ⑤ Hoàn tất              ○ Chờ     │ │  // bg-slate-50
│ └─────────────────────────────────────┘ │
│                                         │
│ 14:32:08 • Hệ thống đã lập kế hoạch    │
└─────────────────────────────────────────┘
```

**Step Status Colors:**
| Status | BG | Text | Badge | Icon |
|--------|-----|------|-------|------|
| pending | slate-50 | slate-400 | "○ Chờ" | Circle (gray) |
| running | blue-50 | blue-600 | "▶ Đang..." | Play (blue, pulse) |
| done | emerald-50 | emerald-600 | "✓ Xong" | Check (green) |
| error | red-50 | red-600 | "✗ Lỗi" | X (red) |

### 5.3 Step Result Message Spec
```
┌─────────────────────────────────────────┐
│ ✅ Bước 3 hoàn thành — Đọc cache        │
│                                         │
│ Tìm thấy trong cache L1 (similarity: 1.0)│
│                                         │
│ [Xem chi tiết ▼]                        │
│ ┌─────────────────────────────────────┐ │
│ │ Output: "Từ ngày 01/01/2026..."   │ │
│ │ State: {cache_status: "hit"}       │ │
│ │ Metrics: {cache_tier: "L1"}        │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 5.4 Right Sidebar Spec (Real-time)
```
┌─────────────────────────────────────────┐
│ Trạng thái hệ thống                     │
│ ┌─────────────────────────────────────┐ │
│ │ Hiệu năng                          │ │
│ │ Latency: 1.2s ✓                   │ │  // Từ result.metrics.latency_ms
│ │ Model: gpt-4o                      │ │  // Từ result.metrics.model
│ │ Tokens: 1,234 in / 567 out         │ │  // Từ result.metrics
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ Nhật ký thực thi                  │ │
│ │ [14:32:05] ▶ Kiểm duyệt đầu vào   │ │  // Từ step_start
│ │ [14:32:06] ✓ Kiểm duyệt xong (7ms)│ │  // Từ node_detail
│ │ [14:32:07] ▶ Đọc cache            │ │  // Từ step_start
│ │ [14:32:08] ✓ Cache hit L1         │ │  // Từ node_detail
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ Nguồn dữ liệu                      │ │
│ │ ✓ Cache L1 (hit)                  │ │  // Từ cache_read state
│ │ ✓ Knowledge Base                  │ │  // Từ knowledgebase state
│ │ ○ Web Search (chưa dùng)          │ │  // Từ route_to
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

## 6. IMPLEMENTATION PHASES

### Phase 1: Backend SSE Events (BE)
**File:** `app/chat/service.py`
**Tasks:**
1. [ ] Thêm `agent_start` event (trước loop)
2. [ ] Thêm `agent_plan` event (sau heuristic_router)
3. [ ] Thêm `step_start` event (khi node bắt đầu)
4. [ ] Tối ưu `node_detail` — trích xuất từ chunk thay vì `aget_state`
5. [ ] Thêm `duration_ms` vào `node_detail`
6. [ ] Thêm `route_to` và `cache_status` vào `node_detail`
7. [ ] Thêm `step_result` event (cho node quan trọng)
8. [ ] Test với nhiều scenario (cache hit, cache miss, error, review)

**Acceptance Criteria:**
- SSE stream có đủ 7 event types
- Event order đúng: agent_start → agent_plan → step_start → node_detail → step_result → result → done
- `duration_ms` chính xác (±10ms)
- Không dùng `aget_state` trong loop

---

### Phase 2: Frontend Hook Refactor (FE)
**File:** `src/hooks/useChatStream.ts`
**Tasks:**
1. [ ] Restructure state: `messages[]` unified với `AgentPlanMessage`, `StepResultMessage`, `AgentResultMessage`
2. [ ] Implement transform logic cho 7 event types
3. [ ] Thêm `currentRunId` tracking
4. [ ] Thêm `activePlan` derived state
5. [ ] Update `hydrate` function cho DB history
6. [ ] Test với mock SSE events

**Acceptance Criteria:**
- State shape đúng theo contract
- Transform logic xử lý đúng tất cả event types
- Không có state tách rời (nodes[], nodeDetails[] riêng)
- Hydrate từ DB không crash

---

### Phase 3: Frontend UI Components (FE)
**Files:** `src/components/`, `src/routes/index.tsx`
**Tasks:**
1. [ ] Tạo `AgentPlanCard` component (danh sách bước với status)
2. [ ] Tạo `StepResultMessage` component (checkmark + content)
3. [ ] Tạo `StepDetailPanel` (collapsible detail)
4. [ ] Update `ChatPage` render logic cho 4 message types
5. [ ] Connect Right Sidebar với real-time data
6. [ ] Add animation: pulse cho running, fade-in cho done
7. [ ] Test responsive (mobile sidebar, desktop 3-panel)

**Acceptance Criteria:**
- UI giống screenshot mẫu (±10%)
- Animation mượt (60fps)
- Mobile: sidebar ẩn, swipe mở
- Desktop: 3-panel layout (left chat, main conversation, right inspector)

---

### Phase 4: Integration & Polish
**Files:** Tất cả
**Tasks:**
1. [ ] End-to-end test: gửi request → thấy plan → thấy steps → thấy results
2. [ ] Test error scenario: node fail → retry button
3. [ ] Test resume scenario: human-in-the-loop
4. [ ] Test switch conversation: state reset đúng
5. [ ] Performance: 1000 messages không lag
6. [ ] Accessibility: keyboard navigation, screen reader
7. [ ] i18n: tiếng Việt labels

**Acceptance Criteria:**
- E2E flow hoàn chỉnh trong <3s
- Error recovery hoạt động
- Switch conversation không leak state
- Lighthouse score >90

---

## 7. TESTING SCENARIOS

### Scenario 1: Cache Hit (Nhanh)
```
Input: "quy định nghỉ phép năm 2025"
Expected: 
- 5 steps, tất cả xong trong <2s
- Bước 3 (cache_read) có "Cache hit L1"
- Final answer từ cache
```

### Scenario 2: Cache Miss (Chậm hơn)
```
Input: "xu hướng AI 2026"
Expected:
- 5+ steps, có thể thêm fallback_search
- Bước 3 (cache_read) có "Cache miss"
- Bước knowledgebase chạy lâu hơn
- Có step_progress events
```

### Scenario 3: Error (API timeout)
```
Input: "phân tích dữ liệu lớn"
Expected:
- Node fail với error message
- FE hiển thị retry button
- Các node sau không chạy
```

### Scenario 4: Review (Human-in-the-loop)
```
Input: "viết email quan trọng"
Expected:
- Graph interrupt tại output_guard
- FE hiển thị draft + approve/reject buttons
- Resume với action + feedback
```

---

## 8. RISK & MITIGATION

| Risk | Impact | Mitigation |
|------|--------|------------|
| BE `agent_plan` không lấy được từ heuristic_router | High | Fallback: emit plan với node list từ config |
| FE animation lag với nhiều steps | Medium | Virtualize step list, dùng React.memo |
| SSE reconnect mất state | Medium | Buffer events trong BE, FE request resume |
| Mobile 3-panel không vừa | Medium | Collapse left/right, dùng tabs |
| DB history không có step data | Low | Hydrate chỉ cần final result, steps từ cache |

---

## 9. APPENDIX

### A. Node Label Mapping (BE)
```python
NODE_LABELS = {
    "input_guard":      "Kiểm duyệt đầu vào",
    "heuristic_router": "Định tuyến",
    "cache_read":       "Đọc cache",
    "knowledgebase":    "Knowledge",
    "relevance_check":  "Đánh giá",
    "generation":       "Sinh câu trả lời",
    "fallback_search":  "Tìm kiếm dự phòng",
    "output_guard":     "Kiểm duyệt đầu ra",
    "final_response":   "Hoàn tất",
}
```

### B. Color Tokens (FE)
```css
--step-pending-bg: #f8fafc;      /* slate-50 */
--step-pending-text: #94a3b8;    /* slate-400 */
--step-running-bg: #eff6ff;      /* blue-50 */
--step-running-text: #2563eb;    /* blue-600 */
--step-done-bg: #f0fdf4;         /* emerald-50 */
--step-done-text: #059669;       /* emerald-600 */
--step-error-bg: #fef2f2;         /* red-50 */
--step-error-text: #dc2626;      /* red-600 */
```

### C. Animation Tokens (FE)
```css
--pulse-duration: 2s;
--fade-in-duration: 0.3s;
--slide-in-duration: 0.2s;
```

---

**Ngày tạo:** 2026-06-03
**Phiên bản:** 1.0
**Người tạo:** AI Assistant + Thành
**Trạng thái:** Draft — chờ review và approve

---

## CHECKLIST TRƯỚC KHI BẮT ĐẦU

- [ ] Mày đã đọc và hiểu toàn bộ contract
- [ ] Mày đã approve event flow (Section 3.3)
- [ ] Mày đã approve state shape (Section 4)
- [ ] Mày đã approve UI spec (Section 5)
- [ ] Mày đã chọn phase để bắt đầu (Section 6)
- [ ] Mày đã lưu file này để dùng cho conversations sau

**Khi chuyển sang conversation mới:**
1. Gửi link file này
2. Nói "Tiếp tục dự án Agent Orchestration UI, làm Phase X"
3. Tôi sẽ đọc lại contract và tiếp tục từ đó
"""

with open('/mnt/agents/output/technical_contract_agent_ui_v1.md', 'w', encoding='utf-8') as f:
    f.write(contract)

print("✅ Đã tạo hợp đồng kỹ thuật")
print(f"📄 File: /mnt/agents/output/technical_contract_agent_ui_v1.md")
print(f"📊 Kích thước: {len(contract)} ký tự")





Phương án C: "Phased Incremental" — Chia 3 giai đoạn nhỏ
Mô tả:
Phase 1 (Week 1): BE thêm agent_start + agent_plan. FE thêm AgentPlanCard. Test.
Phase 2 (Week 2): BE thêm step_start + tối ưu node_detail. FE thêm real-time step status (running/done). Test.
Phase 3 (Week 3): BE thêm step_result + step_progress. FE thêm StepResultMessage + Right Sidebar real-time. Test.
Tech Lead (Alex): "Best of both worlds. Mỗi phase có deliverable chạy được, rollback dễ. Nhưng cần discipline — không scope creep giữa phase."
Backend (Binh): "Phase 1: 2 giờ. Phase 2: 4 giờ. Phase 3: 6 giờ. Tổng 12 giờ BE, chia 3 tuần."
Frontend (Chi): "Phase 1: thêm component. Phase 2: update hook state. Phase 3: restructure render. Mỗi phase FE có thể test độc lập."
UX (Dung): "Mỗi phase UX tốt hơn — user thấy tiến bộ. Phase 1: có plan. Phase 2: thấy running. Phase 3: thấy chi tiết. Gradual delight."
QA (Em): "Test từng phase, không accumulate. Phase 1: 5 case. Phase 2: 10 case. Phase 3: 15 case. Tổng 30, nhưng chia nhỏ."
