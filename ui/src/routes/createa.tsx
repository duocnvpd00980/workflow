"use client";

import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useRef, useCallback } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  Plus, Sparkles, ArrowRight, ArrowLeft, Send, Check, History,
  Eye, Play, Pause, Loader2, AlertCircle, X, Bell, DollarSign,
  Zap, Search, FileText, Megaphone, Lightbulb, ChevronRight,
  MoreHorizontal, RefreshCw,
} from "lucide-react";
import { BASE_URL, API_BASE } from "@/config";

// ==========================================
// TYPES
// ==========================================
type WorkflowStatus = "running" | "paused" | "completed" | "error";

interface WorkflowResponse {
  session_id: string;
  status: WorkflowStatus;
  draft: { content: string; metadata: Record<string, unknown>; version: number } | null;
  publish_status: string | null;
  approved: boolean | null;
  usage: { total_tokens: number; calls: unknown[] } | null;
  error: string | null;
}

interface Version {
  version: number;
  content: string;
  created_at?: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface InlineSuggestion {
  original: string;
  suggestion: string;
  changes?: string;
  selectionStart: number;
  selectionEnd: number;
}

interface Toast {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}

// ==========================================
// API LAYER (unchanged)
// ==========================================
const api = {
  createSession: async (): Promise<{ session_id: string }> => {
    const res = await fetch(`${BASE_URL}/session`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to create session");
    return res.json();
  },
  getBrands: async (ownerId: string = "string"): Promise<{ brands: any[]; total: number }> => {
    const res = await fetch(`${API_BASE}/brand-profile?owner_id=${ownerId}&limit=10&offset=0`, {
      headers: { "accept": "application/json" }
    });
    if (!res.ok) throw new Error("Failed to fetch brands");
    return res.json();
  },
  startWorkflow: async (body: { request: string; brand_id: string; auto_mode?: boolean }): Promise<WorkflowResponse> => {
    const res = await fetch(`${BASE_URL}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("Failed to start workflow");
    return res.json();
  },
  getWorkflow: async (sessionId: string): Promise<WorkflowResponse> => {
    const res = await fetch(`${BASE_URL}/${sessionId}`);
    if (!res.ok) throw new Error("Failed to fetch workflow");
    return res.json();
  },
  resumeWorkflow: async (
    sessionId: string,
    body: { action: "approve" | "edit" | "reject"; content?: string }
  ): Promise<WorkflowResponse> => {
    const res = await fetch(`${BASE_URL}/${sessionId}/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("Failed to resume workflow");
    return res.json();
  },
  publishWorkflow: async (sessionId: string): Promise<{ publish_status: string }> => {
    const res = await fetch(`${BASE_URL}/${sessionId}/publish`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to publish");
    return res.json();
  },
  deleteSession: async (sessionId: string): Promise<{ ok: boolean }> => {
    const res = await fetch(`${BASE_URL}/session/${sessionId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete session");
    return res.json();
  },
  chatEdit: async (body: { draft: string; instruction: string }): Promise<{ draft: string; usage: unknown }> => {
    const res = await fetch(`${BASE_URL}/chat/edit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("Chat edit failed");
    return res.json();
  },
  chatInline: async (body: {
    paragraph: string;
    instruction: string;
    context: string;
  }): Promise<{ draft: string; usage: unknown; changes: string }> => {
    const res = await fetch(`${BASE_URL}/chat/inline`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("Inline edit failed");
    return res.json();
  },
  getVersions: async (sessionId: string): Promise<{
    session_id: string;
    versions: Version[];
    current_version: number;
  }> => {
    const res = await fetch(`${BASE_URL}/${sessionId}/versions`);
    if (!res.ok) throw new Error("Failed to fetch versions");
    return res.json();
  },
};

// ==========================================
// SESSION STORAGE
// ==========================================
const SESSION_KEY = "content_engine_session_id";
const getStoredSessionId = () =>
  typeof window !== "undefined" ? localStorage.getItem(SESSION_KEY) : null;
const setStoredSessionId = (id: string) => localStorage.setItem(SESSION_KEY, id);

// ==========================================
// TOAST
// ==========================================
function ToastContainer({ toasts, onRemove }: { toasts: Toast[]; onRemove: (id: string) => void }) {
  return (
    <div className="fixed bottom-20 left-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-xs font-medium text-white shadow-lg pointer-events-auto ${
            t.type === "success" ? "bg-emerald-600" : t.type === "error" ? "bg-red-600" : "bg-slate-800"
          }`}
        >
          {t.type === "success" && <Check className="w-3.5 h-3.5 shrink-0" />}
          {t.type === "error" && <AlertCircle className="w-3.5 h-3.5 shrink-0" />}
          <span className="flex-1">{t.message}</span>
          <button onClick={() => onRemove(t.id)} className="opacity-60 hover:opacity-100 ml-1">
            <X className="w-3 h-3" />
          </button>
        </div>
      ))}
    </div>
  );
}

function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const add = useCallback((message: string, type: Toast["type"] = "info") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((p) => [...p, { id, message, type }]);
    setTimeout(() => setToasts((p) => p.filter((t) => t.id !== id)), 4000);
  }, []);
  const remove = useCallback((id: string) => setToasts((p) => p.filter((t) => t.id !== id)), []);
  return { toasts, add, remove };
}

// ==========================================
// ROUTE
// ==========================================
export const Route = createFileRoute("/createa")({
  component: ContentEngineWorkspace,
});

// ==========================================
// ROOT
// ==========================================
export default function ContentEngineWorkspace() {
  const [screen, setScreen] = useState<1 | 2 | 3 | 4 | 5>(1);
  const [sessionId, setSessionId] = useState<string | null>(getStoredSessionId());
  const [currentDraft, setCurrentDraft] = useState("");
  const { toasts, add: addToast, remove: removeToast } = useToast();

  const handleSessionCreated = (id: string, draft: string, isAuto: boolean) => {
    setSessionId(id);
    setStoredSessionId(id);
    setCurrentDraft(draft);
    setScreen(isAuto ? 5 : 3);
  };

  return (
    <div className="min-h-screen bg-stone-50 flex flex-col">
      <div className="flex-1 w-full max-w-md mx-auto flex flex-col">
        {screen === 1 && (
          <Dashboard onCreateContent={() => setScreen(2)} onGoAuto={() => setScreen(5)} />
        )}
        {screen === 2 && (
          <CreateContent
            onBack={() => setScreen(1)}
            onSessionCreated={handleSessionCreated}
            addToast={addToast}
          />
        )}
        {screen === 3 && sessionId && (
          <Workspace
            sessionId={sessionId}
            initialDraft={currentDraft}
            onDraftUpdate={setCurrentDraft}
            onGoToReview={() => setScreen(4)}
            onGoToAuto={() => setScreen(5)}
            onBack={() => setScreen(1)}
            addToast={addToast}
          />
        )}
        {screen === 4 && sessionId && (
          <ReviewMode
            sessionId={sessionId}
            onBack={() => setScreen(3)}
            addToast={addToast}
          />
        )}
        {screen === 5 && (
          <AutoMode
            sessionId={sessionId}
            onBack={() => setScreen(sessionId ? 3 : 1)}
            onSessionCreated={handleSessionCreated}
            addToast={addToast}
          />
        )}
      </div>
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}

// ==========================================
// SHARED COMPONENTS
// ==========================================
function TopBar({
  title,
  onBack,
  right,
}: {
  title: string;
  onBack?: () => void;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-center h-12 px-4 border-b border-stone-200 bg-white shrink-0">
      {onBack ? (
        <button onClick={onBack} className="w-8 h-8 flex items-center justify-center -ml-1 mr-2 rounded-lg text-stone-500 hover:bg-stone-100 active:bg-stone-200 transition">
          <ArrowLeft className="w-4 h-4" />
        </button>
      ) : (
        <div className="w-6 mr-2" />
      )}
      <span className="flex-1 font-semibold text-sm text-stone-900 tracking-tight">{title}</span>
      {right}
    </div>
  );
}

function BottomNav({
  active,
  onHome,
  onAuto,
}: {
  active: "home" | "auto" | "profile";
  onHome: () => void;
  onAuto: () => void;
}) {
  const items = [
    { key: "home", label: "Trang chủ", icon: <FileText className="w-5 h-5" />, action: onHome },
    { key: "auto", label: "Auto Mode", icon: <Zap className="w-5 h-5" />, action: onAuto },
    { key: "profile", label: "Hồ sơ", icon: <MoreHorizontal className="w-5 h-5" />, action: () => {} },
  ] as const;

  return (
    <div className="shrink-0 border-t border-stone-200 bg-white flex">
      {items.map((item) => (
        <button
          key={item.key}
          onClick={item.action}
          className={`flex-1 flex flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium transition ${
            active === item.key ? "text-indigo-600" : "text-stone-400 hover:text-stone-600"
          }`}
        >
          <span className={active === item.key ? "text-indigo-600" : "text-stone-400"}>
            {item.icon}
          </span>
          {item.label}
        </button>
      ))}
    </div>
  );
}

// ==========================================
// SCREEN 1 — DASHBOARD
// ==========================================
const RECENT_PROJECTS = [
  { name: "Bánh mì ABC – Tháng 6", type: "Facebook", time: "2 giờ trước", status: "Đã đăng", cls: "bg-emerald-50 text-emerald-700" },
  { name: "Khuyến mãi cuối tuần", type: "Blog", time: "1 ngày trước", status: "Bản nháp", cls: "bg-amber-50 text-amber-700" },
  { name: "Campaign mùa hè", type: "Multi-channel", time: "2 ngày trước", status: "Đang xử lý", cls: "bg-indigo-50 text-indigo-700" },
];

const CONTENT_TYPES = [
  { label: "Facebook Post", icon: <Megaphone className="w-4 h-4" /> },
  { label: "Blog SEO", icon: <FileText className="w-4 h-4" /> },
  { label: "Quảng cáo Ads", icon: <Search className="w-4 h-4" /> },
  { label: "Ý tưởng", icon: <Lightbulb className="w-4 h-4" /> },
];

function Dashboard({ onCreateContent, onGoAuto }: { onCreateContent: () => void; onGoAuto: () => void }) {
  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Header */}
      <div className="px-4 pt-5 pb-4 bg-white border-b border-stone-200 shrink-0">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-stone-400 font-medium">Chào buổi sáng</p>
            <h1 className="text-xl font-bold text-stone-900 tracking-tight mt-0.5">Minh 👋</h1>
          </div>
          <div className="relative">
            <button className="w-9 h-9 rounded-full bg-stone-100 flex items-center justify-center text-stone-500 hover:bg-stone-200 transition">
              <Bell className="w-4 h-4" />
            </button>
            <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-indigo-600 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
              11
            </span>
          </div>
        </div>

        {/* CTA */}
        <button
          onClick={onCreateContent}
          className="mt-4 w-full flex items-center justify-between bg-stone-900 text-white rounded-xl px-4 py-3 hover:bg-stone-800 active:bg-stone-700 transition"
        >
          <div className="flex items-center gap-2.5">
            <Plus className="w-4 h-4" />
            <span className="text-sm font-semibold">Tạo content mới</span>
          </div>
          <ChevronRight className="w-4 h-4 opacity-60" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Content types */}
        <div className="px-4 pt-4 pb-2">
          <p className="text-[11px] font-semibold text-stone-400 uppercase tracking-wider mb-3">Loại nội dung</p>
          <div className="grid grid-cols-2 gap-2">
            {CONTENT_TYPES.map((ct) => (
              <button
                key={ct.label}
                onClick={onCreateContent}
                className="flex items-center gap-2.5 bg-white rounded-xl border border-stone-200 px-3.5 py-3 text-left hover:border-stone-300 hover:shadow-sm active:bg-stone-50 transition"
              >
                <span className="text-stone-500 shrink-0">{ct.icon}</span>
                <span className="text-xs font-medium text-stone-800">{ct.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Auto mode banner */}
        <div className="px-4 py-2">
          <button
            onClick={onGoAuto}
            className="w-full flex items-center gap-3 bg-indigo-50 border border-indigo-100 rounded-xl px-4 py-3 hover:bg-indigo-100 active:bg-indigo-200 transition text-left"
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-indigo-900">Auto Campaign Mode</p>
              <p className="text-[11px] text-indigo-600 mt-0.5">AI tự động từ nghiên cứu đến đăng bài</p>
            </div>
            <ChevronRight className="w-4 h-4 text-indigo-400 shrink-0" />
          </button>
        </div>

        {/* Recent */}
        <div className="px-4 pt-2 pb-4">
          <p className="text-[11px] font-semibold text-stone-400 uppercase tracking-wider mb-3">Gần đây</p>
          <div className="bg-white rounded-xl border border-stone-200 divide-y divide-stone-100">
            {RECENT_PROJECTS.map((p, i) => (
              <div key={i} className="flex items-center justify-between px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-stone-900 truncate">{p.name}</p>
                  <p className="text-[11px] text-stone-400 mt-0.5">{p.type} · {p.time}</p>
                </div>
                <span className={`ml-3 shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded-full ${p.cls}`}>
                  {p.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <BottomNav active="home" onHome={() => {}} onAuto={onGoAuto} />
    </div>
  );
}

// ==========================================
// SCREEN 2 — CREATE CONTENT
// ==========================================
const TAGS = ["Bánh mì ABC", "Tone vui vẻ", "Facebook", "Quảng cáo", "Thêm CTA"];

function CreateContent({
  onBack,
  onSessionCreated,
  addToast,
}: {
  onBack: () => void;
  onSessionCreated: (id: string, draft: string, isAuto: boolean) => void;
  addToast: (m: string, t?: Toast["type"]) => void;
}) {
  const [request, setRequest] = useState("");
  const [autoMode, setAutoMode] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [audience, setAudience] = useState("Dân văn phòng");
  const [promo, setPromo] = useState("Tặng kèm nước ngọt");
  const [selectedBrandId, setSelectedBrandId] = useState("");
  const { data: brandsData, isLoading: isLoadingBrands } = useQuery({
    queryKey: ["brands"],
    queryFn: () => api.getBrands("string"),
  });
  useEffect(() => {
    if (brandsData?.brands?.length && !selectedBrandId) {
      setSelectedBrandId(brandsData.brands[0].id);
    }
  }, [brandsData, selectedBrandId]);
  const startMutation = useMutation({
    mutationFn: async () => {
      const fullRequest = [
        request,
        selectedTags.length ? `Tags: ${selectedTags.join(", ")}` : "",
        `Đối tượng: ${audience}`,
        `Ưu đãi: ${promo}`,
      ]
        .filter(Boolean)
        .join(". ");
      
      // 4. 🔥 TRUYỀN BRAND_ID ĐỘNG TỪ STATE VÀO ĐÂY
      return api.startWorkflow({ 
        request: fullRequest, 
        brand_id: selectedBrandId, 
        auto_mode: autoMode 
      });
    },
    onSuccess: (data) => {
      onSessionCreated(data.session_id, data.draft?.content ?? "", autoMode);
      addToast("Đã tạo content thành công!", "success");
    },
    onError: (err: Error) => addToast(`Lỗi: ${err.message}`, "error"),
  });

  const toggleTag = (tag: string) =>
    setSelectedTags((p) => (p.includes(tag) ? p.filter((t) => t !== tag) : [...p, tag]));

  const canSubmit = request.trim().length > 0 && selectedBrandId && !startMutation.isPending;

  return (
    <div className="flex flex-col flex-1 min-h-0 bg-white">
      <TopBar
        title="Tạo content mới"
        onBack={onBack}
        right={
          <div className="flex gap-1 items-center">
            {[1, 2, 3].map((s) => (
              <div key={s} className={`rounded-full transition-all ${s === 1 ? "w-5 h-1.5 bg-stone-900" : "w-1.5 h-1.5 bg-stone-200"}`} />
            ))}
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-5">
        {/* Request textarea */}

        <div>
    <label className="block text-xs font-semibold text-stone-700 mb-2">Chọn thương hiệu áp dụng</label>
    {isLoadingBrands ? (
      <div className="flex items-center gap-2 text-xs text-stone-400 py-2">
        <Loader2 className="w-3.5 h-3.5 animate-spin" /> Đang tải danh sách thương hiệu...
      </div>
    ) : (
      <select
        className="w-full px-3 py-2.5 text-sm text-stone-900 border border-stone-200 rounded-xl bg-stone-50 outline-none focus:border-stone-400 transition"
        value={selectedBrandId}
        onChange={(e) => setSelectedBrandId(e.target.value)}
      >
        <option value="" disabled>-- Vui lòng chọn thương hiệu --</option>
        {brandsData?.brands?.map((brand) => (
          <option key={brand.id} value={brand.id}>
            {brand.name === "string" ? `Mặc định (${brand.id.slice(0,6)})` : brand.name}
          </option>
        ))}
      </select>
    )}
  </div>

        <div>
          <label className="block text-xs font-semibold text-stone-700 mb-2">Yêu cầu nội dung</label>
          <div className="border border-stone-200 rounded-xl overflow-hidden focus-within:border-stone-400 transition">
            <textarea
              className="w-full px-3.5 pt-3 pb-2 text-sm text-stone-900 placeholder:text-stone-300 outline-none resize-none bg-white leading-relaxed"
              placeholder="Ví dụ: Viết bài Facebook quảng cáo bánh mì thịt nướng mới, tone vui vẻ, có CTA kêu gọi ghé cửa hàng..."
              rows={5}
              value={request}
              onChange={(e) => setRequest(e.target.value)}
            />
            <div className="flex items-center justify-between px-3.5 py-2.5 border-t border-stone-100 bg-stone-50">
              <button
                onClick={() => setAutoMode((v) => !v)}
                className={`flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-lg border transition ${
                  autoMode
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "bg-white text-stone-500 border-stone-200 hover:border-stone-300"
                }`}
              >
                <Zap className="w-3 h-3" />
                {autoMode ? "Auto: Bật" : "Auto: Tắt"}
              </button>
              <span className="text-[11px] text-stone-400">{request.trim().split(/\s+/).filter(Boolean).length} từ</span>
            </div>
          </div>
        </div>

        {/* Tags */}
        <div>
          <label className="block text-xs font-semibold text-stone-700 mb-2">Gắn nhãn nhanh</label>
          <div className="flex flex-wrap gap-2">
            {TAGS.map((tag) => (
              <button
                key={tag}
                onClick={() => toggleTag(tag)}
                className={`text-[11px] font-medium px-3 py-1.5 rounded-full border transition ${
                  selectedTags.includes(tag)
                    ? "bg-stone-900 text-white border-stone-900"
                    : "bg-white text-stone-600 border-stone-200 hover:border-stone-400"
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* AI clarification */}
        <div className="bg-stone-50 rounded-xl border border-stone-200 p-4 space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-stone-900 flex items-center justify-center">
              <Sparkles className="w-3 h-3 text-white" />
            </div>
            <span className="text-xs font-semibold text-stone-700">Gợi ý tối ưu từ AI</span>
          </div>

          <div className="space-y-3">
            {/* Audience */}
            <div>
              <p className="text-[11px] text-stone-500 mb-1.5">Đối tượng mục tiêu?</p>
              <div className="flex gap-2">
                {["Học sinh, sinh viên", "Dân văn phòng"].map((opt) => (
                  <button
                    key={opt}
                    onClick={() => setAudience(opt)}
                    className={`text-[11px] font-medium px-3 py-1.5 rounded-lg border transition ${
                      audience === opt
                        ? "bg-white text-stone-900 border-stone-400 shadow-sm"
                        : "bg-transparent text-stone-500 border-stone-200 hover:border-stone-300"
                    }`}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>

            {/* Promo */}
            <div>
              <p className="text-[11px] text-stone-500 mb-1.5">Ưu đãi đi kèm?</p>
              <div className="flex gap-2">
                {["Giảm giá 20%", "Tặng kèm nước ngọt"].map((opt) => (
                  <button
                    key={opt}
                    onClick={() => setPromo(opt)}
                    className={`text-[11px] font-medium px-3 py-1.5 rounded-lg border transition ${
                      promo === opt
                        ? "bg-white text-stone-900 border-stone-400 shadow-sm"
                        : "bg-transparent text-stone-500 border-stone-200 hover:border-stone-300"
                    }`}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom action */}
      <div className="shrink-0 p-4 border-t border-stone-100 bg-white space-y-2">
        <button
          onClick={() => startMutation.mutate()}
          disabled={!canSubmit}
          className="w-full flex items-center justify-center gap-2 bg-stone-900 text-white rounded-xl py-3.5 text-sm font-semibold hover:bg-stone-800 active:bg-stone-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          {startMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Sparkles className="w-4 h-4" />
          )}
          {startMutation.isPending ? "Đang tạo..." : "Tạo nội dung"}
        </button>
      </div>
    </div>
  );
}

// ==========================================
// SCREEN 3 — WORKSPACE
// ==========================================
type WorkspaceTab = "draft" | "copilot" | "history";

function Workspace({
  sessionId,
  initialDraft,
  onDraftUpdate,
  onGoToReview,
  onGoToAuto,
  onBack,
  addToast,
}: {
  sessionId: string;
  initialDraft: string;
  onDraftUpdate: (d: string) => void;
  onGoToReview: () => void;
  onGoToAuto: () => void;
  onBack: () => void;
  addToast: (m: string, t?: Toast["type"]) => void;
}) {
  const [draft, setDraft] = useState(initialDraft);
  const [tab, setTab] = useState<WorkspaceTab>("draft");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [inlineSuggestion, setInlineSuggestion] = useState<InlineSuggestion | null>(null);
  const [showInlineInput, setShowInlineInput] = useState(false);
  const [inlineInstruction, setInlineInstruction] = useState("");
  const [selection, setSelection] = useState<{ start: number; end: number; text: string } | null>(null);
  const [isApproved, setIsApproved] = useState(false);
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const { data: workflow } = useQuery({
    queryKey: ["workflow", sessionId],
    queryFn: () => api.getWorkflow(sessionId),
    enabled: !!sessionId && !initialDraft,
  });

  useEffect(() => {
    if (workflow?.draft?.content && !initialDraft) setDraft(workflow.draft.content);
  }, [workflow, initialDraft]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const updateDraft = (d: string) => {
    setDraft(d);
    onDraftUpdate(d);
  };

  const chatMutation = useMutation({
    mutationFn: (instruction: string) => api.chatEdit({ draft, instruction }),
    onSuccess: (data) => {
      updateDraft(data.draft);
      setChatMessages((p) => [
        ...p,
        { role: "assistant", content: `Đã cập nhật theo yêu cầu. ${data.draft.slice(0, 60)}…` },
      ]);
    },
    onError: (err: Error) => addToast(`Lỗi: ${err.message}`, "error"),
  });

  const inlineMutation = useMutation({
    mutationFn: ({ paragraph, instruction }: { paragraph: string; instruction: string }) =>
      api.chatInline({ paragraph, instruction, context: draft }),
    onSuccess: (data, vars) => {
      if (!selection) return;
      setInlineSuggestion({
        original: vars.paragraph,
        suggestion: data.draft,
        changes: data.changes,
        selectionStart: selection.start,
        selectionEnd: selection.end,
      });
      setShowInlineInput(false);
    },
    onError: (err: Error) => addToast(`Lỗi: ${err.message}`, "error"),
  });

  const approveMutation = useMutation({
    mutationFn: () => api.resumeWorkflow(sessionId, { action: "approve", content: draft }),
    onSuccess: () => {
      setIsApproved(true);
      addToast("Đã duyệt! Bấm Đăng bài để xuất bản.", "info");
    },
    onError: (err: Error) => addToast(`Lỗi: ${err.message}`, "error"),
  });

  const publishMutation = useMutation({
    mutationFn: () => api.publishWorkflow(sessionId),
    onSuccess: (data) => {
      addToast(`Đã đăng thành công! ${data.publish_status}`, "success");
      setIsApproved(false);
    },
    onError: (err: Error) => addToast(`Lỗi: ${err.message}`, "error"),
  });

  const sendChat = () => {
    if (!chatInput.trim()) return;
    setChatMessages((p) => [...p, { role: "user", content: chatInput }]);
    chatMutation.mutate(chatInput);
    setChatInput("");
  };

  const handleTextSelect = () => {
    const el = editorRef.current;
    if (!el) return;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const text = draft.slice(start, end);
    if (text.trim().length > 10) {
      setSelection({ start, end, text });
      setShowInlineInput(true);
    }
  };

  const handleInlineSubmit = () => {
    if (!selection || !inlineInstruction.trim()) return;
    inlineMutation.mutate({ paragraph: selection.text, instruction: inlineInstruction });
    setInlineInstruction("");
  };

  const acceptInline = () => {
    if (!inlineSuggestion) return;
    const newDraft =
      draft.slice(0, inlineSuggestion.selectionStart) +
      inlineSuggestion.suggestion +
      draft.slice(inlineSuggestion.selectionEnd);
    updateDraft(newDraft);
    setInlineSuggestion(null);
    setSelection(null);
    addToast("Đã áp dụng gợi ý", "success");
  };

  const wordCount = draft.trim().split(/\s+/).filter(Boolean).length;
  const estimatedCost = ((wordCount * 1.3) / 1_000_000 * 3).toFixed(4);

  const QUICK_ACTIONS = [
    { label: "Tối ưu SEO", instruction: "Tối ưu hóa bài viết chuẩn SEO" },
    { label: "Rút gọn", instruction: "Rút ngắn nội dung, giữ ý chính" },
    { label: "Thêm CTA", instruction: "Thêm lời kêu gọi hành động mạnh hơn" },
    { label: "Đổi tone", instruction: "Đổi văn phong sang vui vẻ, gần gũi hơn" },
  ];

  return (
    <div className="flex flex-col flex-1 min-h-0 bg-white">
      {/* TopBar */}
      <div className="flex items-center h-12 px-4 border-b border-stone-200 shrink-0 bg-white gap-2">
        <button onClick={onBack} className="w-8 h-8 flex items-center justify-center rounded-lg text-stone-500 hover:bg-stone-100 -ml-1 shrink-0">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <span className="flex-1 font-semibold text-sm text-stone-900 truncate">Bản thảo</span>
        <span className="text-[11px] text-stone-400 font-medium shrink-0">v{workflow?.draft?.version ?? 1}</span>
        <button onClick={onGoToReview} className="p-1.5 rounded-lg text-stone-400 hover:bg-stone-100 hover:text-stone-700 shrink-0">
          <Eye className="w-4 h-4" />
        </button>
        <button onClick={onGoToAuto} className="p-1.5 rounded-lg text-stone-400 hover:bg-stone-100 hover:text-stone-700 shrink-0">
          <Play className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-stone-200 bg-white shrink-0">
        {(["draft", "copilot", "history"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2.5 text-xs font-semibold border-b-2 transition ${
              tab === t ? "text-stone-900 border-stone-900" : "text-stone-400 border-transparent hover:text-stone-600"
            }`}
          >
            {t === "draft" ? "Bản thảo" : t === "copilot" ? "Copilot" : "Lịch sử"}
          </button>
        ))}
      </div>

      {/* TAB: DRAFT */}
      {tab === "draft" && (
        <>
          {/* Quick chips */}
          <div className="shrink-0 px-4 py-2.5 border-b border-stone-100 flex gap-2 overflow-x-auto bg-stone-50">
            {QUICK_ACTIONS.map(({ label, instruction }) => (
              <button
                key={label}
                onClick={() => {
                  setChatMessages((p) => [...p, { role: "user", content: instruction }]);
                  chatMutation.mutate(instruction);
                  setTab("copilot");
                }}
                disabled={chatMutation.isPending}
                className="shrink-0 text-[11px] font-medium px-3 py-1.5 bg-white border border-stone-200 rounded-full text-stone-700 hover:border-stone-400 disabled:opacity-40 transition whitespace-nowrap"
              >
                {label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
            {/* Inline suggestion */}
            {inlineSuggestion && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 space-y-2">
                <p className="text-[11px] font-semibold text-amber-800">Gợi ý chỉnh sửa</p>
                <div className="text-xs text-red-700 line-through bg-red-50 px-2.5 py-2 rounded-lg leading-relaxed">
                  {inlineSuggestion.original}
                </div>
                <div className="text-xs text-emerald-800 bg-emerald-50 px-2.5 py-2 rounded-lg leading-relaxed font-medium">
                  {inlineSuggestion.suggestion}
                </div>
                {inlineSuggestion.changes && (
                  <p className="text-[11px] text-stone-400 italic">{inlineSuggestion.changes}</p>
                )}
                <div className="flex gap-2">
                  <button onClick={acceptInline} className="text-[11px] font-semibold px-3 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 flex items-center gap-1">
                    <Check className="w-3 h-3" /> Chấp nhận
                  </button>
                  <button onClick={() => { setInlineSuggestion(null); setSelection(null); }} className="text-[11px] font-semibold px-3 py-1.5 bg-white border border-stone-200 text-stone-600 rounded-lg hover:bg-stone-50 flex items-center gap-1">
                    <X className="w-3 h-3" /> Từ chối
                  </button>
                  <button
                    onClick={() => selection && inlineMutation.mutate({ paragraph: selection.text, instruction: inlineInstruction || "Viết lại" })}
                    className="text-[11px] font-semibold px-3 py-1.5 bg-stone-100 text-stone-700 rounded-lg hover:bg-stone-200 flex items-center gap-1"
                  >
                    {inlineMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                  </button>
                </div>
              </div>
            )}
            
            {/* Inline input */}
            {showInlineInput && !inlineSuggestion && (
              <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-3 space-y-2">
                <p className="text-[11px] font-semibold text-indigo-800">Chỉnh sửa đoạn đã chọn</p>
                <p className="text-[11px] text-indigo-600 line-clamp-2 italic">"{selection?.text}"</p>
                <div className="flex gap-2">
                  <input
                    autoFocus
                    value={inlineInstruction}
                    onChange={(e) => setInlineInstruction(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleInlineSubmit()}
                    className="flex-1 border border-indigo-200 rounded-lg px-3 py-2 text-xs bg-white outline-none focus:border-indigo-400 text-stone-900"
                    placeholder="Ngắn gọn hơn, thêm CTA..."
                  />
                  <button onClick={handleInlineSubmit} disabled={inlineMutation.isPending} className="px-3 py-2 bg-indigo-600 text-white rounded-lg text-xs hover:bg-indigo-700 disabled:opacity-50">
                    {inlineMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowRight className="w-3.5 h-3.5" />}
                  </button>
                  <button onClick={() => { setShowInlineInput(false); setSelection(null); }} className="p-2 bg-white border border-stone-200 rounded-lg text-stone-500 hover:bg-stone-50">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="flex gap-1.5 flex-wrap">
                  {["Ngắn gọn hơn", "Tăng độ hài hước", "Thêm CTA"].map((s) => (
                    <button key={s} onClick={() => setInlineInstruction(s)} className="text-[10px] px-2 py-1 rounded-md bg-white border border-indigo-200 text-indigo-700 hover:bg-indigo-100">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Editor */}
            <textarea
              ref={editorRef}
              value={draft}
              onChange={(e) => updateDraft(e.target.value)}
              onMouseUp={handleTextSelect}
              onKeyUp={handleTextSelect}
              className="w-full text-sm text-stone-800 leading-relaxed outline-none resize-none border-0 bg-transparent min-h-[280px]"
              placeholder="Nội dung bản thảo xuất hiện ở đây..."
            />
          </div>

          {/* Stats + actions */}
          <div className="shrink-0 border-t border-stone-100">
            <div className="flex items-center gap-3 px-4 py-2 bg-stone-50 border-b border-stone-100">
              <span className="text-[11px] text-stone-400 flex items-center gap-1">
                <FileText className="w-3 h-3" /> {wordCount} từ
              </span>
              <span className="text-stone-200">·</span>
              <span className="text-[11px] text-stone-400 flex items-center gap-1">
                <DollarSign className="w-3 h-3" /> ~${estimatedCost}
              </span>
              <span className="ml-auto text-[10px] text-stone-300 italic">Bôi đen để chỉnh sửa inline</span>
            </div>
            <div className="flex gap-2 p-3">
              {!isApproved ? (
                <button
                  onClick={() => approveMutation.mutate()}
                  disabled={approveMutation.isPending}
                  className="flex-1 flex items-center justify-center gap-1.5 py-3 rounded-xl bg-amber-500 text-white text-xs font-semibold hover:bg-amber-600 active:bg-amber-700 disabled:opacity-50 transition"
                >
                  {approveMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                  Duyệt nội dung
                </button>
              ) : (
                <button
                  onClick={() => publishMutation.mutate()}
                  disabled={publishMutation.isPending}
                  className="flex-1 flex items-center justify-center gap-1.5 py-3 rounded-xl bg-stone-900 text-white text-xs font-semibold hover:bg-stone-800 active:bg-stone-700 disabled:opacity-50 transition"
                >
                  {publishMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  Lưu vào kho
                </button>
              )}
            </div>
          </div>
        </>
      )}

      {/* TAB: COPILOT */}
      {tab === "copilot" && (
        <>
          <div className="shrink-0 px-4 py-2.5 border-b border-stone-100 bg-stone-50">
            <p className="text-[11px] text-stone-500">
              Brand profile: <span className="font-semibold text-stone-700">Bánh mì ABC</span>
            </p>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
            {chatMessages.length === 0 && (
              <div className="text-center py-8 space-y-4">
                <Sparkles className="w-8 h-8 mx-auto text-stone-300" />
                <p className="text-xs text-stone-400">Hỏi Copilot để chỉnh sửa bản thảo</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {["Tối ưu SEO", "Rút gọn nội dung", "Thêm CTA mạnh hơn"].map((p) => (
                    <button
                      key={p}
                      onClick={() => {
                        setChatMessages((prev) => [...prev, { role: "user", content: p }]);
                        chatMutation.mutate(p);
                      }}
                      className="text-[11px] bg-stone-50 border border-stone-200 text-stone-700 px-3 py-1.5 rounded-full hover:bg-stone-100 transition"
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {chatMessages.map((msg, i) => (
              <div key={i} className={`flex gap-2 items-start ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                {msg.role === "assistant" && (
                  <div className="w-6 h-6 rounded-full bg-stone-900 text-white text-[9px] font-bold flex items-center justify-center shrink-0">
                    AI
                  </div>
                )}
                <div
                  className={`px-3 py-2 rounded-2xl max-w-[82%] text-xs leading-relaxed ${
                    msg.role === "user"
                      ? "bg-stone-900 text-white rounded-tr-sm"
                      : "bg-stone-100 text-stone-800 rounded-tl-sm"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {chatMutation.isPending && (
              <div className="flex gap-2 items-center text-stone-400 text-xs">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Đang xử lý...
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          <div className="shrink-0 flex gap-2 px-4 py-3 border-t border-stone-100">
            <input
              className="flex-1 border border-stone-200 rounded-xl px-3.5 py-2.5 text-xs outline-none focus:border-stone-400 bg-white text-stone-900"
              placeholder="Nhập yêu cầu chỉnh sửa..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendChat()}
            />
            <button
              onClick={sendChat}
              disabled={chatMutation.isPending || !chatInput.trim()}
              className="w-10 h-10 bg-stone-900 text-white rounded-xl flex items-center justify-center disabled:opacity-40 hover:bg-stone-800 transition shrink-0"
            >
              {chatMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </>
      )}

      {/* TAB: HISTORY */}
      {tab === "history" && (
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
          <p className="text-xs text-stone-400 text-center py-4">Lịch sử phiên làm việc hiện tại</p>
          {chatMessages
            .filter((m) => m.role === "user")
            .map((msg, i) => (
              <div key={i} className="bg-stone-50 border border-stone-200 rounded-xl p-3">
                <p className="text-[10px] text-stone-400 font-medium mb-1">Yêu cầu #{i + 1}</p>
                <p className="text-xs text-stone-800">{msg.content}</p>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

// ==========================================
// SCREEN 4 — REVIEW MODE
// ==========================================
function ReviewMode({
  sessionId,
  onBack,
  addToast,
}: {
  sessionId: string;
  onBack: () => void;
  addToast: (m: string, t?: Toast["type"]) => void;
}) {
  const { data: versionsData, isLoading, error } = useQuery({
    queryKey: ["versions", sessionId],
    queryFn: () => api.getVersions(sessionId),
    enabled: !!sessionId,
  });

  const approveMutation = useMutation({
    mutationFn: () => api.resumeWorkflow(sessionId, { action: "approve" }),
    onSuccess: () => {
      addToast(`Đã phê duyệt bản v${versionsData?.current_version}`, "success");
      onBack();
    },
    onError: (err: Error) => addToast(`Lỗi: ${err.message}`, "error"),
  });

  const versions = versionsData?.versions ?? [];
  const currentVersion = versionsData?.current_version ?? 0;
  const prevVersion = versions.find((v) => v.version === currentVersion - 1);
  const currVersion = versions.find((v) => v.version === currentVersion);

  return (
    <div className="flex flex-col flex-1 min-h-0 bg-white">
      <TopBar
        title={`So sánh phiên bản`}
        onBack={onBack}
        right={
          <span className="text-xs text-stone-400 font-medium">
            v{currentVersion - 1} → v{currentVersion}
          </span>
        }
      />

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {isLoading && (
          <div className="flex items-center justify-center py-12 gap-2 text-stone-400 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" /> Đang tải...
          </div>
        )}
        {error && (
          <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded-xl p-3">
            <AlertCircle className="w-4 h-4 shrink-0" /> Không tải được lịch sử. Hiển thị dữ liệu mẫu.
          </div>
        )}

        {/* Old version */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-semibold text-stone-400 uppercase tracking-wider">v{currentVersion - 1} — Cũ</span>
          </div>
          <div className="bg-stone-50 border border-stone-200 rounded-xl p-4 text-xs text-stone-600 leading-relaxed">
            {prevVersion?.content ?? (
              <>
                <p className="font-medium text-stone-800">🥖 Bánh mì ABC</p>
                <p className="mt-2">Hệ thống cửa hàng Bánh mì ABC chuyên cung cấp các bữa ăn sáng tiện lợi.</p>
                <p className="mt-1 line-through text-red-500">Hãy ghé qua mua ăn thử nếu bạn rảnh vào tuần này nhé!</p>
              </>
            )}
          </div>
        </div>

        {/* New version */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wider">v{currentVersion} — Đề xuất mới</span>
          </div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-xs text-stone-700 leading-relaxed">
            {currVersion?.content ?? (
              <>
                <p className="font-medium text-stone-800">🥖 Bánh mì ABC — Ngày mới vui hơn!</p>
                <p className="mt-2">Hệ thống cửa hàng Bánh mì ABC chuyên cung cấp các bữa ăn sáng tiện lợi.</p>
                <p className="mt-1 text-emerald-800 font-medium">✨ Ghé ngay 123 Nguyễn Văn Linh — Mua 1 tặng 1 trong khung giờ vàng!</p>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="shrink-0 p-4 border-t border-stone-100 space-y-2">
        <button
          onClick={() => approveMutation.mutate()}
          disabled={approveMutation.isPending}
          className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-stone-900 text-white text-sm font-semibold hover:bg-stone-800 disabled:opacity-50 transition"
        >
          {approveMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
          Phê duyệt v{currentVersion}
        </button>
        <button className="w-full py-3 rounded-xl bg-stone-50 border border-stone-200 text-sm font-medium text-stone-600 hover:bg-stone-100 transition">
          Khôi phục về v{currentVersion - 1}
        </button>
      </div>
    </div>
  );
}

// ==========================================
// SCREEN 5 — AUTO MODE
// ==========================================
const AUTO_STEPS = [
  { label: "Nghiên cứu", desc: "Quét từ khóa xu hướng ngành F&B", time: "~2s" },
  { label: "Tạo nội dung", desc: "Khởi tạo cấu trúc bản thảo bài đăng", time: "~15s" },
  { label: "Tạo hình AI", desc: "Sinh ảnh bằng DALL-E 3", time: "~30s" },
  { label: "Xuất bản", desc: "Đăng tự động qua Graph API", time: "~5s" },
] as const;

function AutoMode({
  sessionId: existingSessionId,
  onBack,
  onSessionCreated,
  addToast,
}: {
  sessionId: string | null;
  onBack: () => void;
  onSessionCreated: (id: string, draft: string, isAuto: boolean) => void;
  addToast: (m: string, t?: Toast["type"]) => void;
}) {
  const [isPaused, setIsPaused] = useState(false);
  const [sessionId, setSessionId] = useState(existingSessionId);
  const [request, setRequest] = useState("");
  const [started, setStarted] = useState(!!existingSessionId);


  // 🔥 1. THÊM STATE VÀ USEQUERY VÀO ĐÂY
  const [selectedBrandId, setSelectedBrandId] = useState("");

  const { data: brandsData, isLoading: isLoadingBrands } = useQuery({
    queryKey: ["brands-auto"],
    queryFn: () => api.getBrands("string"), // Gọi API lấy list brand
    enabled: !existingSessionId, // Chỉ gọi API nếu đây là campaign mới (chưa có sessionId)
  });

  // Tự động chọn brand đầu tiên khi load xong danh sách
  useEffect(() => {
    if (brandsData?.brands?.length && !selectedBrandId) {
      setSelectedBrandId(brandsData.brands[0].id);
    }
  }, [brandsData, selectedBrandId]);

  const startMutation = useMutation({
    // 🔥 2. SỬA CHỖ NÀY: Truyền selectedBrandId từ state vào API
    mutationFn: (req: string) => api.startWorkflow({ request: req, brand_id: selectedBrandId, auto_mode: true }),
    onSuccess: (data) => {
      setSessionId(data.session_id);
      setStoredSessionId(data.session_id);
      setStarted(true);
      onSessionCreated(data.session_id, data.draft?.content ?? "", true);
    },
    onError: (err: Error) => addToast(`Lỗi: ${err.message}`, "error"),
  });

  const { data: workflow } = useQuery({
    queryKey: ["workflow-auto", sessionId],
    queryFn: () => api.getWorkflow(sessionId!),
    enabled: !!sessionId && started && !isPaused,
    refetchInterval: (q) => (q.state.data?.status === "running" ? 3000 : false),
  });

  const status = workflow?.status ?? "running";
  const totalTokens = workflow?.usage?.total_tokens ?? 0;
  const estimatedCost = ((totalTokens / 1_000_000) * 3).toFixed(4);

  useEffect(() => {
    if (status === "completed") addToast("Hoàn tất! Đã đăng bài thành công.", "success");
    if (status === "error") addToast(`Lỗi: ${workflow?.error}`, "error");
  }, [status]);

  // Derive step status
  const getStepStatus = (idx: number): "done" | "active" | "wait" => {
    if (status === "completed") return "done";
    if (status === "error") return idx === 0 ? "done" : "wait";
    if (idx === 0) return "done";
    if (idx === 1) return status === "running" ? "active" : "done";
    return "wait";
  };

  if (!started) {
    return (
      <div className="flex flex-col flex-1 min-h-0 bg-white">
        <TopBar title="Auto Campaign Mode" onBack={onBack} />
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5">
          <div className="flex items-center gap-3 bg-stone-50 border border-stone-200 rounded-xl p-4">
            <div className="w-9 h-9 rounded-xl bg-stone-900 flex items-center justify-center shrink-0">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-stone-900">Chạy tự động hoàn toàn</p>
              <p className="text-xs text-stone-500 mt-0.5">AI lo từ nghiên cứu đến đăng bài</p>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-2">Yêu cầu nội dung</label>
            <textarea
              className="w-full border border-stone-200 rounded-xl px-3.5 pt-3 pb-2 text-sm text-stone-900 placeholder:text-stone-300 outline-none resize-none bg-white focus:border-stone-400 transition leading-relaxed"
              rows={5}
              placeholder="Nhập yêu cầu content, AI sẽ tự nghiên cứu, viết và đăng bài..."
              value={request}
              onChange={(e) => setRequest(e.target.value)}
            />
          </div>

          {/* Steps preview */}
          <div>
            <p className="text-[11px] font-semibold text-stone-400 uppercase tracking-wider mb-3">Quy trình tự động</p>
            <div className="space-y-2">
              {AUTO_STEPS.map((step, i) => (
                <div key={i} className="flex items-center gap-3 px-3.5 py-3 bg-stone-50 border border-stone-200 rounded-xl">
                  <div className="w-6 h-6 rounded-full bg-stone-200 text-stone-500 flex items-center justify-center text-[11px] font-bold shrink-0">
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-stone-700">{step.label}</p>
                    <p className="text-[11px] text-stone-400 truncate">{step.desc}</p>
                  </div>
                  <span className="text-[10px] text-stone-400 shrink-0">{step.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="shrink-0 p-4 border-t border-stone-100">
          <button
            onClick={() => startMutation.mutate(request)}
            disabled={!request.trim() || startMutation.isPending}
            className="w-full flex items-center justify-center gap-2 py-3.5 bg-stone-900 text-white rounded-xl text-sm font-semibold hover:bg-stone-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
          >
            {startMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {startMutation.isPending ? "Đang khởi động..." : "Bắt đầu Auto Mode"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Dark header */}
      <div className="bg-stone-900 text-white px-4 py-3.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <span
            className={`w-2.5 h-2.5 rounded-full shrink-0 ${
              status === "running" ? "bg-emerald-400 animate-pulse" : status === "completed" ? "bg-emerald-400" : "bg-amber-400"
            }`}
          />
          <span className="text-xs font-semibold">
            {status === "running" ? "Đang chạy tự động..." : status === "completed" ? "Hoàn tất!" : status === "paused" ? "Đã tạm dừng" : "Đã xảy ra lỗi"}
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setIsPaused((p) => !p)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-medium transition"
          >
            {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            {isPaused ? "Tiếp tục" : "Tạm dừng"}
          </button>
          <button onClick={onBack} className="px-3 py-1.5 rounded-lg bg-white text-stone-900 text-xs font-semibold hover:bg-stone-100 transition">
            Thoát
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-white px-4 py-5 space-y-5">
        {/* Steps */}
        <div className="space-y-2">
          {AUTO_STEPS.map((step, idx) => {
            const stepStatus = getStepStatus(idx);
            return (
              <div key={idx} className="flex items-center gap-3 px-3.5 py-3 bg-stone-50 border border-stone-200 rounded-xl">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold shrink-0 transition ${
                    stepStatus === "done"
                      ? "bg-emerald-100 text-emerald-700"
                      : stepStatus === "active"
                      ? "bg-indigo-100 text-indigo-700"
                      : "bg-stone-200 text-stone-400"
                  } ${stepStatus === "active" ? "animate-pulse" : ""}`}
                >
                  {stepStatus === "done" ? <Check className="w-3.5 h-3.5" /> : idx + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-xs font-semibold ${stepStatus === "wait" ? "text-stone-400" : "text-stone-800"}`}>
                    {step.label}
                  </p>
                  <p className="text-[11px] text-stone-400 truncate">{step.desc}</p>
                </div>
                <span className="text-[10px] text-stone-400 shrink-0">{step.time}</span>
              </div>
            );
          })}
        </div>

        {/* Log */}
        <div className="bg-stone-50 border border-stone-200 rounded-xl p-4 space-y-2">
          <p className="text-[11px] font-semibold text-stone-500 mb-3">Nhật ký tiến trình</p>
          {[
            { done: true, text: "Hoàn tất quét dữ liệu từ khóa xu hướng F&B." },
            { done: status !== "running", active: status === "running", text: "Khởi tạo cấu trúc bản thảo bài đăng." },
            { done: status === "completed", text: "Tạo hình ảnh AI bằng DALL-E 3." },
            { done: status === "completed", text: `Xuất bản bài viết${workflow?.publish_status ? ` — ${workflow.publish_status}` : ""}.` },
          ].map((log, i) => (
            <div key={i} className={`flex items-start gap-2 text-xs ${log.done ? "text-emerald-700" : log.active ? "text-indigo-600" : "text-stone-400"}`}>
              {log.done ? (
                <Check className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              ) : log.active ? (
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse mt-1.5 shrink-0" />
              ) : (
                <div className="w-1.5 h-1.5 rounded-full bg-stone-300 mt-1.5 shrink-0" />
              )}
              <span className="leading-relaxed">{log.text}</span>
            </div>
          ))}
        </div>

        {/* Error */}
        {status === "error" && workflow?.error && (
          <div className="flex items-start gap-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded-xl p-3">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            {workflow.error}
          </div>
        )}

        {/* Cost */}
        {totalTokens > 0 && (
          <div className="flex items-center justify-center gap-1.5 text-[11px] text-stone-400">
            <DollarSign className="w-3 h-3" />
            <span>{totalTokens.toLocaleString()} tokens — ~${estimatedCost}</span>
          </div>
        )}
      </div>
    </div>
  );
}