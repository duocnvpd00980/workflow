"use client";

import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Plus, Sparkles, ArrowRight, ArrowLeft, Send, Check, History, Eye, 
  Play, Pause, Loader2, AlertCircle, X, Bell, DollarSign, Zap
} from 'lucide-react';
import { BASE_URL } from "@/config";

// ==========================================
// CONSTANTS & TYPES
// ==========================================

const PRIMARY_COLOR = "bg-slate-900 text-white hover:bg-slate-800";

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
  role: 'user' | 'assistant';
  content: string;
}

interface InlineSuggestion {
  original: string;
  suggestion: string;
  changes?: string;
  selectionStart: number;
  selectionEnd: number;
}

// ==========================================
// API LAYER
// ==========================================
const api = {
  createSession: async (): Promise<{ session_id: string }> => {
    const res = await fetch(`${BASE_URL}/session`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to create session');
    return res.json();
  },
  startWorkflow: async (body: { request: string; auto_mode?: boolean }): Promise<WorkflowResponse> => {
    const res = await fetch(`${BASE_URL}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('Failed to start workflow');
    return res.json();
  },
  getWorkflow: async (sessionId: string): Promise<WorkflowResponse> => {
    const res = await fetch(`${BASE_URL}/${sessionId}`);
    if (!res.ok) throw new Error('Failed to fetch workflow');
    return res.json();
  },
  resumeWorkflow: async (sessionId: string, body: { action: 'approve' | 'edit' | 'reject'; content?: string }): Promise<WorkflowResponse> => {
    const res = await fetch(`${BASE_URL}/${sessionId}/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('Failed to resume workflow');
    return res.json();
  },
  publishWorkflow: async (sessionId: string): Promise<{ publish_status: string }> => {
    const res = await fetch(`${BASE_URL}/${sessionId}/publish`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to publish');
    return res.json();
  },
  deleteSession: async (sessionId: string): Promise<{ ok: boolean }> => {
    const res = await fetch(`${BASE_URL}/session/${sessionId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete session');
    return res.json();
  },
  chatEdit: async (body: { draft: string; instruction: string }): Promise<{ draft: string; usage: unknown }> => {
    const res = await fetch(`${BASE_URL}/chat/edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('Chat edit failed');
    return res.json();
  },
  chatInline: async (body: { paragraph: string; instruction: string; context: string }): Promise<{ draft: string; usage: unknown; changes: string }> => {
    const res = await fetch(`${BASE_URL}/chat/inline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('Inline edit failed');
    return res.json();
  },
  getVersions: async (sessionId: string): Promise<{ session_id: string; versions: Version[]; current_version: number }> => {
    const res = await fetch(`${BASE_URL}/${sessionId}/versions`);
    if (!res.ok) throw new Error('Failed to fetch versions');
    return res.json();
  },
};

// ==========================================
// SESSION STORAGE HELPERS
// ==========================================
const SESSION_KEY = 'content_engine_session_id';
const getStoredSessionId = () => {
  if (typeof window !== 'undefined') return localStorage.getItem(SESSION_KEY);
  return null;
};
const setStoredSessionId = (id: string) => localStorage.setItem(SESSION_KEY, id);

// ==========================================
// TOAST COMPONENT
// ==========================================
interface Toast { id: string; message: string; type: 'success' | 'error' | 'info'; }

function ToastContainer({ toasts, onRemove }: { toasts: Toast[]; onRemove: (id: string) => void }) {
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map(t => (
        <div key={t.id} className={`flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-xs font-medium text-white animate-in slide-in-from-right ${
          t.type === 'success' ? 'bg-emerald-600' : t.type === 'error' ? 'bg-red-600' : 'bg-slate-800'
        }`}>
          {t.type === 'success' && <Check className="w-3.5 h-3.5" />}
          {t.type === 'error' && <AlertCircle className="w-3.5 h-3.5" />}
          <span>{t.message}</span>
          <button onClick={() => onRemove(t.id)} className="ml-2 opacity-70 hover:opacity-100">
            <X className="w-3 h-3" />
          </button>
        </div>
      ))}
    </div>
  );
}

function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const add = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = Math.random().toString(36).slice(2);
    setToasts(p => [...p, { id, message, type }]);
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 4000);
  }, []);
  const remove = useCallback((id: string) => setToasts(p => p.filter(t => t.id !== id)), []);
  return { toasts, add, remove };
}

// ==========================================
// ROUTE SETUP
// ==========================================
export const Route = createFileRoute('/')({
  component: ContentEngineWorkspace,
});

// ==========================================
// MAIN COMPONENT
// ==========================================
export default function ContentEngineWorkspace() {
  const [currentScreen, setCurrentScreen] = useState<1 | 2 | 3 | 4 | 5 | 6>(1);
  const [sessionId, setSessionId] = useState<string | null>(getStoredSessionId());
  const [currentDraft, setCurrentDraft] = useState<string>('');
  const { toasts, add: addToast, remove: removeToast } = useToast();

  const handleSessionCreated = (id: string, draft: string, isAuto: boolean) => {
    setSessionId(id);
    setStoredSessionId(id);
    setCurrentDraft(draft);
    setCurrentScreen(isAuto ? 5 : 3);
  };

  const handleDraftUpdate = (draft: string) => setCurrentDraft(draft);

  return (
    <div >
      <>
        {currentScreen === 1 && (
          <ScreenDashboard onCreateContent={() => setCurrentScreen(2)} />
        )}
        {currentScreen === 2 && (
          <ScreenCreateContent
            onBack={() => setCurrentScreen(1)}
            onSessionCreated={handleSessionCreated}
            addToast={addToast}
          />
        )}
        {currentScreen === 3 && sessionId && (
          <ScreenWorkspace
            onGoToReview={() => setCurrentScreen(4)}
            onGoToAuto={() => setCurrentScreen(5)}
            sessionId={sessionId}
            initialDraft={currentDraft}
            onDraftUpdate={handleDraftUpdate}
            addToast={addToast}
          />
        )}
        {currentScreen === 4 && sessionId && (
          <ScreenReviewMode
            onBack={() => setCurrentScreen(3)}
            sessionId={sessionId}
            addToast={addToast}
          />
        )}
        {currentScreen === 5 && (
          <ScreenAutoMode
            onBack={() => setCurrentScreen(3)}
            sessionId={sessionId}
            onSessionCreated={handleSessionCreated}
            addToast={addToast}
          />
        )}
        {currentScreen === 6 && (
          <ScreenMobileView draft={currentDraft} />
        )}
      </>

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}

// ==========================================
// SCREEN 1 — DASHBOARD
// ==========================================
function ScreenDashboard({ onCreateContent }: { onCreateContent: () => void }) {
  const [showNotifTooltip, setShowNotifTooltip] = useState(false);

  const recentProjects = [
    { name: "Bánh mì ABC - Tháng 6", type: "Facebook Post", time: "2 giờ trước", status: "Đã đăng", color: "bg-emerald-50 text-emerald-700" },
    { name: "Khuyến mãi cuối tuần", type: "Blog Post", time: "1 ngày trước", status: "Bản nháp", color: "bg-amber-50 text-amber-700" },
    { name: "Campaign mùa hè 2024", type: "Multi-channel", time: "2 ngày trước", status: "Đang xử lý", color: "bg-indigo-50 text-indigo-700" },
  ];

  const notifBreakdown = [
    { label: "Bình luận chờ phản hồi", count: 5 },
    { label: "Bản nháp chờ duyệt", count: 3 },
    { label: "Chiến dịch hoàn thành", count: 3 },
  ];

  return (
    <div className="flex">
      <div className="md:col-span-3 space-y-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div>
              <h2 className="text-xl font-bold tracking-tight text-slate-900">Chào buổi sáng, Minh! 👋</h2>
              <p className="text-xs text-slate-500 mt-1">Hôm nay bạn muốn tối ưu hóa chiến dịch và tạo nội dung gì?</p>
            </div>
            <div className="relative">
              <button
                className="relative flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 transition"
                onMouseEnter={() => setShowNotifTooltip(true)}
                onMouseLeave={() => setShowNotifTooltip(false)}
                aria-label="11 thông báo"
              >
                <Bell className="w-4 h-4 text-slate-600" />
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-indigo-600 text-white text-[10px] font-bold rounded-full flex items-center justify-center">11</span>
              </button>
              {showNotifTooltip && (
                <div className="absolute top-10 left-0 z-10 bg-white border border-slate-200 rounded-xl shadow-lg p-3 w-52 text-xs space-y-2">
                  <p className="font-semibold text-slate-700 mb-1">11 thông báo mới</p>
                  {notifBreakdown.map(n => (
                    <div key={n.label} className="flex justify-between text-slate-600">
                      <span>{n.label}</span>
                      <span className="font-semibold text-slate-900">{n.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          <button onClick={onCreateContent} className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg shadow-sm transition ${PRIMARY_COLOR}`}>
            <Plus className="w-4 h-4" /> Tạo content mới
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {["Bài đăng Facebook", "Blog bài viết SEO", "Quảng cáo Ads", "Ý tưởng nội dung"].map((action, idx) => (
            <button key={idx} onClick={onCreateContent}
              className="bg-white p-4 rounded-xl border border-slate-200 text-left hover:border-indigo-500 transition hover:shadow-sm space-y-2">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-sm">0{idx + 1}</div>
              <div className="font-semibold text-xs text-slate-900">{action}</div>
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white p-5 rounded-xl border border-slate-200 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Dự án gần đây</h3>
            <div className="divide-y divide-slate-100 text-xs">
              {recentProjects.map((proj, i) => (
                <div key={i} className="py-3 flex justify-between items-center first:pt-0 last:pb-0">
                  <div>
                    <h4 className="font-semibold text-slate-900">{proj.name}</h4>
                    <span className="text-[11px] text-slate-400">{proj.type} · {proj.time}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded font-medium ${proj.color}`}>{proj.status}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white p-5 rounded-xl border border-slate-200 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Hoạt động gần đây</h3>
            <div className="space-y-3 text-xs text-slate-600">
              <div className="flex gap-2"><div className="w-1.5 h-1.5 bg-indigo-500 rounded-full mt-1.5 shrink-0" /><p>Bạn đã xuất bản <strong>Bánh mì ngon</strong> lên Fanpage <span className="text-slate-400">· 2 giờ trước</span></p></div>
              <div className="flex gap-2"><div className="w-1.5 h-1.5 bg-amber-500 rounded-full mt-1.5 shrink-0" /><p>AI đã tạo bản nháp mới cho chiến dịch tuần mới <span className="text-slate-400">· 5 giờ trước</span></p></div>
              <div className="flex gap-2"><div className="w-1.5 h-1.5 bg-slate-300 rounded-full mt-1.5 shrink-0" /><p>Cập nhật lại cấu trúc <strong>Brand Profile</strong> <span className="text-slate-400">· 1 ngày trước</span></p></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// SCREEN 2 — CREATE CONTENT
// ==========================================
function ScreenCreateContent({
  onBack, onSessionCreated, addToast
}: {
  onBack: () => void;
  onSessionCreated: (id: string, draft: string, isAuto: boolean) => void;
  addToast: (m: string, t?: Toast['type']) => void;
}) {
  const [request, setRequest] = useState('');
  const [autoMode, setAutoMode] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedAudience, setSelectedAudience] = useState('Dân văn phòng');
  const [selectedPromo, setSelectedPromo] = useState('Tặng kèm nước ngọt');

  const startMutation = useMutation({
    mutationFn: async () => {
      const fullRequest = [
        request,
        selectedTags.length ? `Tags: ${selectedTags.join(', ')}` : '',
        `Đối tượng: ${selectedAudience}`,
        `Ưu đãi: ${selectedPromo}`,
      ].filter(Boolean).join('. ');
      return api.startWorkflow({ request: fullRequest, auto_mode: autoMode });
    },
    onSuccess: (data) => {
      const draft = data.draft?.content ?? '';
      onSessionCreated(data.session_id, draft, autoMode);
      addToast('Đã tạo content thành công!', 'success');
    },
    onError: (err: Error) => addToast(`Lỗi: ${err.message}`, 'error'),
  });

  const tags = ["Bánh mì ABC", "Tone vui vẻ", "Mạng xã hội Facebook", "Quảng cáo sản phẩm", "Thêm CTA ưu đãi"];
  const toggleTag = (tag: string) => setSelectedTags(p => p.includes(tag) ? p.filter(t => t !== tag) : [...p, tag]);

  return (
    <div className="mx-auto bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden mt-6">
      <div className="border-b border-slate-100 p-4 flex items-center justify-between text-xs font-medium text-slate-500">
        <button onClick={onBack} className="flex items-center gap-1 hover:text-slate-900"><ArrowLeft className="w-3.5 h-3.5" /> Quay lại</button>
        <div className="flex gap-4 items-center">
          <span className="text-indigo-600 font-semibold border-b-2 border-indigo-600 pb-4 pt-1">1. Yêu cầu</span>
          <span className="opacity-50">2. Thông tin bổ sung</span>
          <span className="opacity-50">3. Tạo nội dung</span>
        </div>
      </div>

      <div className="p-8 space-y-6">
        <div className="text-center max-w-md mx-auto space-y-1">
          <h2 className="text-lg font-bold tracking-tight">Bạn muốn tạo nội dung gì hôm nay?</h2>
          <p className="text-xs text-slate-500">Nhập yêu cầu chi tiết của bạn, AI Engine sẽ thiết lập không gian xử lý tối ưu.</p>
        </div>

        <div className="border border-slate-200 rounded-xl p-4 bg-slate-50 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 transition relative">
          <textarea
            className="w-full bg-transparent border-0 outline-none resize-none text-sm placeholder:text-slate-400 min-h-[120px]"
            placeholder="Ví dụ: Viết bài đăng Facebook quảng cáo dòng sản phẩm bánh mì thịt nướng mới của quán ABC, yêu cầu văn phong vui vẻ, có kêu gọi hành động cuối bài..."
            value={request}
            onChange={e => setRequest(e.target.value)}
          />
          <div className="flex justify-between items-center pt-2 border-t border-slate-200 text-xs text-slate-400">
            <div className="flex items-center gap-3">
              <span>Độ dài đề xuất: 50-200 từ</span>
              <button
                onClick={() => setAutoMode(v => !v)}
                className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md transition font-medium border ${
                  autoMode
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'bg-white text-slate-500 border-slate-200 hover:border-indigo-400 hover:text-indigo-600'
                }`}
              >
                <Zap className="w-3 h-3" />
                Auto Mode {autoMode ? 'Bật' : 'Tắt'}
              </button>
            </div>
            <button
              onClick={() => startMutation.mutate()}
              disabled={!request.trim() || startMutation.isPending}
              className="bg-indigo-600 text-white p-2 rounded-lg hover:bg-indigo-700 transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed">
              {startMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <div className="space-y-2 text-xs">
          <span className="font-semibold text-slate-500">Gợi ý nhanh cấu trúc:</span>
          <div className="flex flex-wrap gap-1.5">
            {tags.map(tag => (
              <button key={tag}
                onClick={() => toggleTag(tag)}
                className={`px-2.5 py-1 rounded-md font-medium cursor-pointer transition ${selectedTags.includes(tag) ? 'bg-indigo-100 text-indigo-700 border border-indigo-300' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
                {tag}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-indigo-50/60 border border-indigo-100 rounded-xl p-4 space-y-4">
          <div className="flex items-start gap-2.5 text-xs">
            <div className="w-5 h-5 bg-indigo-600 text-white rounded-full flex items-center justify-center shrink-0 font-bold text-[10px]">AI</div>
            <div className="space-y-1">
              <h4 className="font-bold text-indigo-900">AI Clarification (Gợi ý tối ưu hóa)</h4>
              <p className="text-indigo-700">Để bản thảo đầu tiên sát nhất với mong muốn, bạn có thể chọn thêm các chi tiết sau:</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pl-7">
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">1. Đối tượng khách hàng mục tiêu?</label>
              <div className="flex gap-1.5">
                {["Học sinh, sinh viên", "Dân văn phòng"].map(opt => (
                  <button key={opt} onClick={() => setSelectedAudience(opt)}
                    className={`px-2 py-1 rounded cursor-pointer border ${selectedAudience === opt ? 'bg-white border-indigo-200 text-indigo-700 font-medium' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}>
                    {opt}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">2. Chương trình ưu đãi đi kèm?</label>
              <div className="flex gap-1.5">
                {["Giảm giá 20%", "Tặng kèm nước ngọt"].map(opt => (
                  <button key={opt} onClick={() => setSelectedPromo(opt)}
                    className={`px-2 py-1 rounded cursor-pointer border ${selectedPromo === opt ? 'bg-white border-indigo-200 text-indigo-700 font-medium' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}>
                    {opt}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="pt-2 text-right border-t border-indigo-100">
            <button
              onClick={() => startMutation.mutate()}
              disabled={!request.trim() || startMutation.isPending}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold disabled:opacity-50">
              {startMutation.isPending ? 'Đang xử lý...' : 'Bỏ qua & Tiến hành tạo nội dung ngay →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// SCREEN 3 — CONTENT WORKSPACE
// ==========================================
function ScreenWorkspace({
   onGoToReview, onGoToAuto, sessionId, initialDraft, onDraftUpdate, addToast
}: {
  onGoToReview: () => void;
  onGoToAuto: () => void;
  sessionId: string;
  initialDraft: string;
  onDraftUpdate: (d: string) => void;
  addToast: (m: string, t?: Toast['type']) => void;
}) {
  const [draftContent, setDraftContent] = useState(initialDraft);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [activeTab, setActiveTab] = useState<'copilot' | 'history'>('copilot');
  const [inlineSuggestion, setInlineSuggestion] = useState<InlineSuggestion | null>(null);
  const [inlineInstruction, setInlineInstruction] = useState('');
  const [showInlineInput, setShowInlineInput] = useState(false);
  const [selection, setSelection] = useState<{ start: number; end: number; text: string } | null>(null);
  const [isApproved, setIsApproved] = useState(false);
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const { data: workflow } = useQuery({
    queryKey: ['workflow', sessionId],
    queryFn: () => api.getWorkflow(sessionId),
    enabled: !!sessionId && !initialDraft,
  });

  useEffect(() => {
    if (workflow?.draft?.content && !initialDraft) {
      setDraftContent(workflow.draft.content);
    }
  }, [workflow, initialDraft]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const chatMutation = useMutation({
    mutationFn: (instruction: string) => api.chatEdit({ draft: draftContent, instruction }),
    onSuccess: (data) => {
      setDraftContent(data.draft);
      onDraftUpdate(data.draft);
      setChatMessages(p => [...p, { role: 'assistant', content: `Đã cập nhật bản thảo theo yêu cầu. ${data.draft.slice(0, 80)}…` }]);
    },
    onError: (err: Error) => addToast(`Chat error: ${err.message}`, 'error'),
  });

  const inlineMutation = useMutation({
    mutationFn: ({ paragraph, instruction }: { paragraph: string; instruction: string }) =>
      api.chatInline({ paragraph, instruction, context: draftContent }),
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
    onError: (err: Error) => addToast(`Inline error: ${err.message}`, 'error'),
  });

  const approveMutation = useMutation({
    mutationFn: () => api.resumeWorkflow(sessionId, { action: 'approve', content: draftContent }),
    onSuccess: () => {
      setIsApproved(true);
      addToast('Đã duyệt! Bấm "Đăng bài" để xuất bản.', 'info');
    },
    onError: (err: Error) => addToast(`Lỗi duyệt: ${err.message}`, 'error'),
  });

  const publishMutation = useMutation({
    mutationFn: () => api.publishWorkflow(sessionId),
    onSuccess: (data) => {
      addToast(`Đã đăng bài thành công! Status: ${data.publish_status}`, 'success');
      setIsApproved(false);
    },
    onError: (err: Error) => addToast(`Lỗi đăng bài: ${err.message}`, 'error'),
  });

  const handleSendChat = () => {
    if (!chatInput.trim()) return;
    setChatMessages(p => [...p, { role: 'user', content: chatInput }]);
    chatMutation.mutate(chatInput);
    setChatInput('');
  };

  const handleTextSelect = () => {
    const el = editorRef.current;
    if (!el) return;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const text = draftContent.slice(start, end);
    if (text.trim().length > 10) {
      setSelection({ start, end, text });
      setShowInlineInput(true);
    }
  };

  const handleInlineSubmit = () => {
    if (!selection || !inlineInstruction.trim()) return;
    inlineMutation.mutate({ paragraph: selection.text, instruction: inlineInstruction });
    setInlineInstruction('');
  };

  const acceptInlineSuggestion = () => {
    if (!inlineSuggestion) return;
    const before = draftContent.slice(0, inlineSuggestion.selectionStart);
    const after = draftContent.slice(inlineSuggestion.selectionEnd);
    const newDraft = before + inlineSuggestion.suggestion + after;
    setDraftContent(newDraft);
    onDraftUpdate(newDraft);
    setInlineSuggestion(null);
    setSelection(null);
    addToast('Đã áp dụng gợi ý inline', 'success');
  };

  const rejectInlineSuggestion = () => {
    setInlineSuggestion(null);
    setSelection(null);
  };

  const wordCount = draftContent.trim().split(/\s+/).filter(Boolean).length;
  const estimatedCostUSD = ((wordCount * 1.3) / 1_000_000 * 3).toFixed(4);

  const suggestedPrompts = [
    "Tối ưu hóa chuẩn SEO",
    "Rút gọn nội dung",
    "Thêm CTA mạnh hơn",
    "Đổi tone vui vẻ hơn",
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-0 border border-slate-200 rounded-xl overflow-hidden h-[calc(100vh-80px)] mt-6">
      
      {/* LEFT PANEL: Copilot (4/12) */}
      <div className="lg:col-span-4 bg-white border-r border-slate-200 flex flex-col h-full overflow-hidden">
        <div className="flex border-b border-slate-100 p-2 bg-slate-50 text-xs font-semibold shrink-0">
          <button onClick={() => setActiveTab('copilot')}
            className={`flex-1 py-1.5 text-center rounded transition ${activeTab === 'copilot' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-400 hover:text-slate-600'}`}>
            Trợ lý Copilot
          </button>
          <button onClick={() => setActiveTab('history')}
            className={`flex-1 py-1.5 text-center rounded transition ${activeTab === 'history' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-400 hover:text-slate-600'}`}>
            Lịch sử (v{workflow?.draft?.version ?? 1})
          </button>
        </div>

        {activeTab === 'copilot' && (
          <div className="shrink-0 p-3 border-b border-slate-100 bg-slate-50/50">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">Actions nhanh</p>
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { label: "Tối ưu SEO", instruction: "Tối ưu hóa bài viết này chuẩn SEO" },
                { label: "Rút gọn", instruction: "Rút ngắn nội dung, giữ ý chính" },
                { label: "Đổi tone", instruction: "Đổi văn phong sang chuyên nghiệp hơn" },
                { label: "Tạo ảnh AI", instruction: "Viết prompt hình ảnh phù hợp cho bài này" },
              ].map(({ label, instruction }) => (
                <button key={label}
                  onClick={() => {
                    setChatMessages(p => [...p, { role: 'user', content: instruction }]);
                    chatMutation.mutate(instruction);
                  }}
                  disabled={chatMutation.isPending}
                  className="text-left bg-white border border-slate-200 px-2.5 py-1.5 rounded-lg hover:border-indigo-400 text-xs font-medium text-slate-700 disabled:opacity-50 transition">
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
          {activeTab === 'copilot' ? (
            <>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-slate-500 text-center text-[11px]">
                Brand Profile đang áp dụng: <strong className="text-slate-700">Bánh mì ABC</strong>
              </div>

              {chatMessages.length === 0 && (
                <div className="text-center text-slate-400 py-4 space-y-3">
                  <Sparkles className="w-7 h-7 mx-auto text-slate-300" />
                  <p className="text-[11px]">Thử hỏi Copilot:</p>
                  <div className="flex flex-wrap gap-1.5 justify-center">
                    {suggestedPrompts.map(p => (
                      <button key={p}
                        onClick={() => {
                          setChatMessages(prev => [...prev, { role: 'user', content: p }]);
                          chatMutation.mutate(p);
                        }}
                        className="text-[11px] bg-indigo-50 text-indigo-700 border border-indigo-100 px-2 py-1 rounded-lg hover:bg-indigo-100 transition">
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex gap-2 items-start ${msg.role === 'user' ? 'justify-end' : ''}`}>
                  {msg.role === 'assistant' && (
                    <div className="w-6 h-6 bg-indigo-100 text-indigo-600 font-bold rounded-full flex items-center justify-center shrink-0 text-[10px]">AI</div>
                  )}
                  <div className={`p-3 rounded-xl max-w-[85%] leading-relaxed ${
                    msg.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-slate-100 text-slate-800 rounded-tl-none'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}

              {chatMutation.isPending && (
                <div className="flex gap-2 items-center text-slate-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>AI đang xử lý...</span>
                </div>
              )}
              <div ref={chatBottomRef} />
            </>
          ) : (
            <div className="space-y-2 text-slate-600">
              <p className="text-slate-400 text-center pt-4 text-[11px]">Lịch sử chỉnh sửa phiên làm việc hiện tại.</p>
              {chatMessages.filter(m => m.role === 'user').map((msg, i) => (
                <div key={i} className="bg-slate-50 border border-slate-100 rounded-lg p-2.5">
                  <span className="text-[10px] text-slate-400 font-medium">Yêu cầu #{i + 1}</span>
                  <p className="mt-1 text-xs">{msg.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="shrink-0 px-3 py-2 border-t border-slate-100 bg-slate-50 flex items-center gap-1.5 text-[11px] text-slate-400">
          <DollarSign className="w-3 h-3" />
          <span>{wordCount} từ · ước tính ~${estimatedCostUSD}</span>
        </div>

        <div className="shrink-0 p-3 border-t border-slate-100 flex gap-2 bg-slate-50">
          <input
            className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-indigo-500"
            placeholder="Nhập yêu cầu chỉnh sửa..."
            value={chatInput}
            onChange={e => setChatInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSendChat()}
          />
          <button onClick={handleSendChat} disabled={chatMutation.isPending || !chatInput.trim()}
            className="bg-indigo-600 text-white p-1.5 rounded-lg hover:bg-indigo-700 disabled:opacity-50">
            {chatMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* RIGHT PANEL: Editor (8/12) */}
      <div className="lg:col-span-8 bg-white flex flex-col h-full overflow-hidden">
        <div className="border-b border-slate-200 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50 shrink-0">
          <div className="flex items-center gap-2 text-xs">
            <span className="font-bold text-slate-900">Bản thảo: Bánh mì ABC</span>
            <span className="bg-slate-200 px-2 py-0.5 rounded text-[11px] font-medium text-slate-700 flex items-center gap-1">
              <History className="w-3 h-3" /> v{workflow?.draft?.version ?? 1}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onGoToReview}
              className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5">
              <Eye className="w-3.5 h-3.5" /> So sánh
            </button>
            <button onClick={onGoToAuto}
              className="px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-lg text-xs font-semibold hover:bg-indigo-100 flex items-center gap-1.5">
              <Play className="w-3.5 h-3.5" /> Auto Mode
            </button>
            {!isApproved ? (
              <button
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending}
                className="px-3 py-1.5 bg-amber-500 text-white rounded-lg text-xs font-semibold hover:bg-amber-600 flex items-center gap-1.5 disabled:opacity-50">
                {approveMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <Check className="w-3.5 h-3.5" /> Duyệt nội dung
              </button>
            ) : (
              <button
                onClick={() => publishMutation.mutate()}
                disabled={publishMutation.isPending}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition flex items-center gap-1.5 ${PRIMARY_COLOR} disabled:opacity-50`}>
                {publishMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <Send className="w-3.5 h-3.5" /> Đăng bài
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex gap-2 px-6 py-2 border-b border-slate-100 text-xs text-slate-400 font-mono items-center shrink-0">
            <span className="font-bold text-slate-800 cursor-pointer hover:bg-slate-100 px-1 rounded">H1</span>
            <span className="font-bold text-slate-800 cursor-pointer hover:bg-slate-100 px-1 rounded">H2</span>
            <span className="underline cursor-pointer hover:bg-slate-100 px-1 rounded">U</span>
            <span className="italic cursor-pointer hover:bg-slate-100 px-1 rounded">I</span>
            <span className="cursor-pointer hover:bg-slate-100 px-1 rounded">Link</span>
            <span className="cursor-pointer hover:bg-slate-100 px-1 rounded">Quote</span>
            <span className="ml-auto text-[10px] text-slate-400 font-sans italic">
              Bôi đen đoạn văn → AI sẽ gợi ý chỉnh sửa
            </span>
          </div>

          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
            {inlineSuggestion && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs space-y-2">
                <div className="font-semibold text-amber-900">✨ Gợi ý chỉnh sửa inline</div>
                <div className="space-y-1">
                  <div className="line-through text-red-600 bg-red-50 p-2 rounded">{inlineSuggestion.original}</div>
                  <div className="text-emerald-700 bg-emerald-50 p-2 rounded font-medium">{inlineSuggestion.suggestion}</div>
                  {inlineSuggestion.changes && <div className="text-slate-500 italic">{inlineSuggestion.changes}</div>}
                </div>
                <div className="flex gap-2">
                  <button onClick={acceptInlineSuggestion} className="px-3 py-1 bg-emerald-600 text-white rounded font-semibold hover:bg-emerald-700">
                    ✓ Chấp nhận
                  </button>
                  <button onClick={rejectInlineSuggestion} className="px-3 py-1 bg-white border border-slate-200 text-slate-600 rounded font-semibold hover:bg-slate-50">
                    ✗ Từ chối
                  </button>
                  <button onClick={() => {
                    if (selection) inlineMutation.mutate({ paragraph: selection.text, instruction: inlineInstruction || 'Viết lại' });
                  }} className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded font-semibold hover:bg-indigo-100 flex items-center gap-1">
                    {inlineMutation.isPending && <Loader2 className="w-3 h-3 animate-spin" />} ↻ Thử lại
                  </button>
                </div>
              </div>
            )}

            {showInlineInput && !inlineSuggestion && (
              <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-3 text-xs space-y-2">
                <div className="font-semibold text-indigo-900">✂️ Chỉnh sửa đoạn đã chọn</div>
                <div className="text-indigo-700 bg-white p-2 rounded border border-indigo-100 line-clamp-2">{selection?.text}</div>
                <div className="flex gap-2">
                  <input
                    className="flex-1 bg-white border border-indigo-200 rounded-lg px-3 py-1.5 outline-none focus:border-indigo-500"
                    placeholder="Yêu cầu chỉnh sửa... (VD: Ngắn gọn hơn, thêm CTA)"
                    value={inlineInstruction}
                    onChange={e => setInlineInstruction(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleInlineSubmit()}
                    autoFocus
                  />
                  <button onClick={handleInlineSubmit} disabled={inlineMutation.isPending}
                    className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1">
                    {inlineMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowRight className="w-3.5 h-3.5" />}
                  </button>
                  <button onClick={() => { setShowInlineInput(false); setSelection(null); }}
                    className="px-2 py-1.5 bg-white border border-slate-200 text-slate-500 rounded-lg hover:bg-slate-50">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="flex gap-1.5">
                  {["Ngắn gọn hơn", "Tăng độ hài hước", "Thêm CTA ưu đãi"].map(s => (
                    <button key={s} onClick={() => setInlineInstruction(s)}
                      className="bg-white px-2 py-0.5 rounded border border-indigo-200 text-indigo-700 text-[11px] cursor-pointer hover:bg-indigo-100">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <textarea
              ref={editorRef}
              className="w-full text-sm text-slate-800 leading-relaxed outline-none resize-none border-0 bg-transparent min-h-[400px]"
              value={draftContent}
              onChange={e => { setDraftContent(e.target.value); onDraftUpdate(e.target.value); }}
              onMouseUp={handleTextSelect}
              onKeyUp={handleTextSelect}
              placeholder="Nội dung bản thảo sẽ xuất hiện ở đây..."
            />
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// SCREEN 4 — REVIEW MODE
// ==========================================
function ScreenReviewMode({
  onBack, sessionId, addToast
}: {
  onBack: () => void;
  sessionId: string;
  addToast: (m: string, t?: Toast['type']) => void;
}) {
  const { data: versionsData, isLoading, error } = useQuery({
    queryKey: ['versions', sessionId],
    queryFn: () => api.getVersions(sessionId),
    enabled: !!sessionId,
  });

  const approveMutation = useMutation({
    mutationFn: () => api.resumeWorkflow(sessionId, { action: 'approve' }),
    onSuccess: () => addToast('Đã phê duyệt bản v' + (versionsData?.current_version ?? ''), 'success'),
    onError: (err: Error) => addToast(`Lỗi: ${err.message}`, 'error'),
  });

  const versions = versionsData?.versions ?? [];
  const currentVersion = versionsData?.current_version ?? 0;
  const prevVersion = versions.find(v => v.version === currentVersion - 1);
  const currVersion = versions.find(v => v.version === currentVersion);

  return (
    <div className="space-y-4 p-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-200">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h2 className="text-sm font-bold">So sánh và phê duyệt (Diff Review)</h2>
            <p className="text-xs text-slate-500">Xem các chỉnh sửa AI đề xuất trước khi phê duyệt.</p>
          </div>
        </div>
        <div className="flex gap-2 text-xs">
          <button className="px-4 py-2 bg-slate-100 rounded-lg font-semibold text-slate-600 hover:bg-slate-200">
            Khôi phục về v{currentVersion - 1}
          </button>
          <button
            onClick={() => approveMutation.mutate()}
            disabled={approveMutation.isPending}
            className={`px-4 py-2 rounded-lg font-semibold shadow-sm transition flex items-center gap-2 ${PRIMARY_COLOR} disabled:opacity-50`}>
            {approveMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Phê duyệt bản v{currentVersion}
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12 text-slate-400 gap-2">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Đang tải lịch sử phiên bản...</span>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4" /> Không thể tải lịch sử phiên bản. Hiển thị dữ liệu mẫu.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 relative opacity-75">
          <span className="absolute top-3 right-3 text-[10px] uppercase tracking-wider bg-slate-100 px-2 py-0.5 rounded font-bold text-slate-500">
            Bản cũ (v{currentVersion - 1})
          </span>
          <h3 className="text-sm font-bold text-slate-900 pr-24">Phiên bản cũ</h3>
          <div className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">
            {prevVersion?.content ? (
              prevVersion.content
            ) : (
              <>
                <p>🥖 BÁNH MÌ NGON - MÓN QUÀ BUỔI SÁNG</p>
                <p className="mt-2">Hệ thống cửa hàng Bánh mì ABC chuyên cung cấp các bữa ăn sáng tiện lợi cho mọi người.</p>
                <div className="bg-red-50 text-red-700 p-2.5 rounded border border-red-100 line-through mt-2">
                  Hãy ghé qua mua ăn thử nếu bạn rảnh vào tuần này nhé mọi người ơi.
                </div>
              </>
            )}
          </div>
        </div>

        <div className="bg-white border border-indigo-200 rounded-xl p-5 space-y-3 relative ring-1 ring-indigo-500/20">
          <span className="absolute top-3 right-3 text-[10px] uppercase tracking-wider bg-indigo-50 px-2 py-0.5 rounded font-bold text-indigo-600">
            Đề xuất mới (v{currentVersion})
          </span>
          <h3 className="text-sm font-bold text-slate-900 pr-24">Phiên bản mới nhất</h3>
          <div className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">
            {currVersion?.content ? (
              currVersion.content
            ) : (
              <>
                <p>🥖 BÁNH MÌ NGON - NGÀY MỚI VUI HƠN!</p>
                <p className="mt-2">Hệ thống cửa hàng Bánh mì ABC chuyên cung cấp các bữa ăn sáng tiện lợi cho mọi người.</p>
                <div className="bg-emerald-50 text-emerald-800 p-2.5 rounded border border-emerald-100 font-medium mt-2">
                  ✨ 📍 Ghé ngay cơ sở gần nhất tại 123 Nguyễn Văn Linh để được áp dụng chương trình mua 1 tặng 1 trong khung giờ vàng!
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// SCREEN 5 — AUTO MODE
// ==========================================
function ScreenAutoMode({
  onBack, sessionId: existingSessionId, onSessionCreated, addToast
}: {
  onBack: () => void;
  sessionId: string | null;
  onSessionCreated: (id: string, draft: string, isAuto: boolean) => void;
  addToast: (m: string, t?: Toast['type']) => void;
}) {
  const [isPaused, setIsPaused] = useState(false);
  const [sessionId, setSessionId] = useState(existingSessionId);
  const [request, setRequest] = useState('');
  const [started, setStarted] = useState(!!existingSessionId);

  const startMutation = useMutation({
    mutationFn: (req: string) => api.startWorkflow({ request: req, auto_mode: true }),
    onSuccess: (data) => {
      setSessionId(data.session_id);
      setStoredSessionId(data.session_id);
      setStarted(true);
      onSessionCreated(data.session_id, data.draft?.content ?? '', true);
    },
    onError: (err: Error) => addToast(`Lỗi: ${err.message}`, 'error'),
  });

  const { data: workflow } = useQuery({
    queryKey: ['workflow-auto', sessionId],
    queryFn: () => api.getWorkflow(sessionId!),
    enabled: !!sessionId && started && !isPaused,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'running' ? 3000 : false;
    },
  });

  const status = workflow?.status ?? 'running';
  const publishStatus = workflow?.publish_status;
  const totalTokens = workflow?.usage?.total_tokens ?? 0;
  const estimatedCost = ((totalTokens / 1_000_000) * 3).toFixed(4);

  useEffect(() => {
    if (status === 'completed') addToast('Hoàn tất! Đã đăng bài thành công.', 'success');
    if (status === 'error') addToast(`Lỗi: ${workflow?.error}`, 'error');
  }, [status, workflow, addToast]);

  const steps = [
    { label: "Research", timeEstimate: "~2s", status: 'complete' as const },
    { label: "Generate", timeEstimate: "~15s", status: status === 'running' || status === 'completed' ? 'complete' as const : 'active' as const },
    { label: "Image Gen", timeEstimate: "~30s", status: status === 'completed' ? 'complete' as const : status === 'running' ? 'active' as const : 'pending' as const },
    { label: "Publish", timeEstimate: "~5s", status: status === 'completed' ? 'complete' as const : 'pending' as const },
  ];

  if (!started) {
    return (
      <div className="max-w-2xl mx-auto bg-white border border-slate-200 rounded-xl shadow-sm p-8 space-y-6 mt-6">
        <h2 className="text-lg font-bold">Kích hoạt Auto Campaign Mode</h2>
        <p className="text-sm text-slate-500">Nhập yêu cầu, AI sẽ tự động hoàn thành toàn bộ quy trình từ nghiên cứu đến đăng bài.</p>
        <textarea
          className="w-full border border-slate-200 rounded-xl p-4 text-sm outline-none focus:border-indigo-500 min-h-[120px] resize-none"
          placeholder="Nhập yêu cầu content..."
          value={request}
          onChange={e => setRequest(e.target.value)}
        />
        <div className="flex gap-3">
          <button onClick={onBack} className="px-4 py-2 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50">
            Quay lại
          </button>
          <button
            onClick={() => startMutation.mutate(request)}
            disabled={!request.trim() || startMutation.isPending}
            className={`px-6 py-2 rounded-lg text-sm font-semibold shadow-sm transition flex items-center gap-2 ${PRIMARY_COLOR} disabled:opacity-50`}>
            {startMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            <Play className="w-4 h-4" /> Bắt đầu Auto Mode
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden mt-6">
      <div className="bg-slate-900 text-white p-4 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${status === 'running' ? 'bg-emerald-400 animate-pulse' : status === 'completed' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          <span className="text-xs font-semibold tracking-wide uppercase">
            {status === 'running' ? 'Hệ thống đang vận hành tự động' : status === 'completed' ? 'Hoàn tất!' : status === 'paused' ? 'Đã tạm dừng' : 'Đã xảy ra lỗi'}
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setIsPaused(p => !p)}
            className="px-3 py-1 bg-white/10 hover:bg-white/20 text-white text-xs font-medium rounded flex items-center gap-1 transition">
            {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            {isPaused ? "Tiếp tục" : "Tạm dừng"}
          </button>
          <button onClick={onBack} className="px-3 py-1 bg-white text-slate-900 text-xs font-semibold rounded hover:bg-slate-100 transition">
            Thoát về workspace
          </button>
        </div>
      </div>

      <div className="p-8 space-y-8">
        <div className="flex items-start justify-between relative max-w-2xl mx-auto">
          <div className="absolute left-0 right-0 top-[14px] h-0.5 bg-slate-200 z-0" />
          <div className={`absolute left-0 top-[14px] h-0.5 bg-indigo-600 z-0 transition-all duration-1000 ${
            status === 'completed' ? 'w-full' : 'w-[50%]'
          }`} />

          {steps.map((step, idx) => (
            <div key={idx} className="relative z-10 flex flex-col items-center space-y-1 text-center min-w-[70px]">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                step.status === 'complete' ? 'bg-indigo-600 text-white' :
                step.status === 'active' ? 'bg-indigo-50 border-2 border-indigo-600 text-indigo-600 animate-pulse' :
                'bg-white border-2 border-slate-200 text-slate-400'
              }`}>
                {step.status === 'complete' ? <Check className="w-4 h-4" /> : idx + 1}
              </div>
              <span className={`text-xs font-semibold ${step.status === 'active' ? 'text-indigo-600' : 'text-slate-500'}`}>{step.label}</span>
              <span className="text-[10px] text-slate-400">{step.timeEstimate}</span>
            </div>
          ))}
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-3 max-w-2xl mx-auto text-xs">
          <div className="flex justify-between items-center border-b border-slate-200 pb-2">
            <span className="font-bold text-slate-700">Nhật ký tiến trình thực tế</span>
            <span className="text-slate-400">
              {status === 'completed' ? 'Tiến độ: 100%' : status === 'running' ? 'Đang chạy...' : status}
            </span>
          </div>
          <div className="space-y-2 text-slate-600">
            <div className="flex gap-2 text-emerald-600"><Check className="w-3.5 h-3.5 shrink-0" /><span>[Xong] Hoàn tất quét dữ liệu từ khóa xu hướng ngành F&B Việt Nam.</span></div>
            <div className={`flex gap-2 ${status !== 'running' ? 'text-emerald-600' : 'text-indigo-600'}`}>
              {status !== 'running' ? <Check className="w-3.5 h-3.5 shrink-0" /> : <div className="w-1.5 h-1.5 rounded-full bg-indigo-600 mt-1.5 animate-ping shrink-0" />}
              <span>{status !== 'running' ? '[Xong]' : '[Đang chạy]'} Khởi tạo cấu trúc bản thảo bài đăng.</span>
            </div>
            <div className={`flex gap-2 ${status === 'completed' ? 'text-emerald-600' : 'text-slate-400'}`}>
              {status === 'completed' ? <Check className="w-3.5 h-3.5 shrink-0" /> : <div className="w-1.5 h-1.5 rounded-full bg-slate-300 mt-1.5 shrink-0" />}
              <span>{status === 'completed' ? '[Xong]' : '[Chờ]'} Tạo hình ảnh AI bằng DALL-E 3.</span>
            </div>
            <div className={`flex gap-2 ${status === 'completed' ? 'text-emerald-600' : 'text-slate-400'}`}>
              {status === 'completed' ? <Check className="w-3.5 h-3.5 shrink-0" /> : <div className="w-1.5 h-1.5 rounded-full bg-slate-300 mt-1.5 shrink-0" />}
              <span>{status === 'completed' ? `[Xong] ${publishStatus ?? 'Đã xuất bản'}` : '[Chờ] Xuất bản bài viết tự động qua Graph API.'}</span>
            </div>
          </div>
        </div>

        {totalTokens > 0 && (
          <div className="max-w-2xl mx-auto text-xs text-slate-400 text-center flex items-center justify-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5" />
            Đã sử dụng <strong className="text-slate-600">{totalTokens.toLocaleString()} tokens</strong>
            <span className="text-slate-300">·</span>
            ước tính <strong className="text-slate-600">~${estimatedCost}</strong>
          </div>
        )}

        {status === 'error' && workflow?.error && (
          <div className="max-w-2xl mx-auto bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" /> {workflow.error}
          </div>
        )}
      </div>
    </div>
  );
}

// ==========================================
// SCREEN 6 — MOBILE VIEW
// ==========================================
function ScreenMobileView({ draft }: { draft: string }) {
  const displayContent = draft || `🥖 BÁNH MÌ NGON - NGÀY MỚI VUI HƠN!\n\nBạn đã sẵn sàng để bùng nổ năng lượng cho ngày mới chưa? Ghé ngay hệ thống Bánh mì ABC để nhận trọn combo bữa sáng giòn rụm, đầy ắp năng lượng!`;

  return (
    <div className="max-w-md mx-auto bg-slate-900 p-3 rounded-[40px] shadow-2xl border-4 border-slate-800 my-8">
      <div className="bg-white rounded-[32px] overflow-hidden min-h-[640px] flex flex-col text-slate-900">
        <div className="px-4 pt-6 pb-3 border-b border-slate-100 flex justify-between items-center text-xs font-bold">
          <span className="text-slate-900">⚡ Copilot Workspace</span>
          <span className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full">Draft</span>
        </div>
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-wrap">{displayContent}</p>
          <div className="bg-slate-100 rounded-xl h-36 flex items-center justify-center border border-slate-200 text-xs text-slate-400 font-medium">
            [ Khung hiển thị Banner AI đã tạo kèm theo ]
          </div>
        </div>
        <div className="p-3 bg-slate-50 border-t border-slate-100 space-y-3">
          <div className="flex gap-1.5 text-[10px] font-bold overflow-x-auto pb-1">
            <span className="bg-white border border-slate-200 px-2.5 py-1 rounded text-slate-700 shrink-0">✨ Rút ngắn gọn</span>
            <span className="bg-white border border-slate-200 px-2.5 py-1 rounded text-slate-700 shrink-0">✨ Thêm CTA gấp</span>
            <span className="bg-white border border-slate-200 px-2.5 py-1 rounded text-slate-700 shrink-0">🔄 Đổi văn phong</span>
          </div>
          <div className="flex gap-2">
            <input className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs outline-none" placeholder="Nhập yêu cầu nhanh cho trợ lý..." />
            <button className={`px-4 py-2 rounded-lg text-xs font-bold shrink-0 shadow-sm ${PRIMARY_COLOR}`}>Đăng bài</button>
          </div>
        </div>
      </div>
    </div>
  );
}