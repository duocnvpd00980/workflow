"use client";

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  useQuery, useMutation, useQueryClient, QueryClient, QueryClientProvider
} from '@tanstack/react-query';
import {
  LayoutDashboard, FolderKanban, FileText, UserSquare2,
  Layers, BarChart3, Settings, CreditCard, Plus, Sparkles,
  ArrowRight, ArrowLeft, Send, Check, History, Undo,
  ChevronRight, AlignLeft, Eye, EyeOff, Play, Pause,
  Smartphone, Monitor, ThumbsUp, Trash2, Loader2, AlertCircle, X
} from 'lucide-react';

// ==========================================
// CONSTANTS & TYPES
// ==========================================
const BASE_URL = "http://localhost:8000/api/v1/marketing";
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
// API LAYER (fetch-based)
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
const getStoredSessionId = () => localStorage.getItem(SESSION_KEY);
const setStoredSessionId = (id: string) => localStorage.setItem(SESSION_KEY, id);
const clearStoredSessionId = () => localStorage.removeItem(SESSION_KEY);

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
          <button onClick={() => onRemove(t.id)} className="ml-2 opacity-70 hover:opacity-100"><X className="w-3 h-3" /></button>
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
export const Route = createFileRoute('/chat')({
  component: ContentEngineApp,
});

const queryClient = new QueryClient();

function ContentEngineApp() {
  return (
    <QueryClientProvider client={queryClient}>
      <ContentEngineWorkspace />
    </QueryClientProvider>
  );
}

// ==========================================
// MAIN COMPONENT
// ==========================================
export default function ContentEngineWorkspace() {
  const [currentScreen, setCurrentScreen] = useState<1 | 2 | 3 | 4 | 5 | 6>(1);
  const [sessionId, setSessionId] = useState<string | null>(getStoredSessionId);
  const [currentDraft, setCurrentDraft] = useState<string>('');
  const [autoMode, setAutoMode] = useState(false);
  const { toasts, add: addToast, remove: removeToast } = useToast();

  const handleSessionCreated = (id: string, draft: string, isAuto: boolean) => {
    setSessionId(id);
    setStoredSessionId(id);
    setCurrentDraft(draft);
    setAutoMode(isAuto);
    setCurrentScreen(isAuto ? 5 : 3);
  };

  const handleDraftUpdate = (draft: string) => setCurrentDraft(draft);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased">
      {/* Top Nav */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-indigo-600" />
          <span className="font-bold tracking-tight text-slate-900">Content Engine V2.0</span>
          <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full font-medium">Balanced Option</span>
        </div>
        <div className="flex bg-slate-100 p-1 rounded-lg text-xs font-medium">
          {[1, 2, 3, 4, 5, 6].map(num => (
            <button key={num} onClick={() => setCurrentScreen(num as any)}
              className={`px-3 py-1.5 rounded-md transition-all ${currentScreen === num ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'}`}>
              Màn {num}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span>User: <strong>Alex</strong></span>
          {sessionId && <span className="font-mono text-[10px] text-slate-400">sid: {sessionId.slice(0, 8)}…</span>}
        </div>
      </div>

      <main className="p-6 max-w-[1600px] mx-auto">
        {currentScreen === 1 && (
          <ScreenDashboard onCreateContent={() => setCurrentScreen(2)} addToast={addToast} />
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
            onBack={() => setCurrentScreen(2)}
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
      </main>

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}

// ==========================================
// SCREEN 1 — DASHBOARD
// ==========================================
function ScreenDashboard({ onCreateContent, addToast }: { onCreateContent: () => void; addToast: (m: string, t?: Toast['type']) => void }) {
  // Mock recent projects from localStorage
  const recentProjects = [
    { name: "Bánh mì ABC - Tháng 6", type: "Facebook Post", time: "2 giờ trước", status: "Đã đăng", color: "bg-emerald-50 text-emerald-700" },
    { name: "Khuyến mãi cuối tuần", type: "Blog Post", time: "1 ngày trước", status: "Bản nháp", color: "bg-amber-50 text-amber-700" },
    { name: "Campaign mùa hè 2024", type: "Multi-channel", time: "2 ngày trước", status: "Đang xử lý", color: "bg-indigo-50 text-indigo-700" },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-start">
      {/* Sidebar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-6">
        <div className="space-y-1">
          {[
            { icon: LayoutDashboard, label: 'Tổng quan', active: true },
            { icon: FolderKanban, label: 'Dự án gần đây' },
            { icon: FileText, label: 'Templates mẫu' },
            { icon: UserSquare2, label: 'Brand Profile' },
            { icon: Layers, label: 'Tích hợp kênh' },
            { icon: BarChart3, label: 'Báo cáo hiệu quả' },
            { icon: Settings, label: 'Cài đặt hệ thống' },
          ].map(({ icon: Icon, label, active }) => (
            <button key={label} className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md ${active ? 'bg-slate-100 text-slate-900' : 'text-slate-600 hover:bg-slate-50'}`}>
              <Icon className="w-4 h-4" /> {label}
            </button>
          ))}
        </div>
        <hr className="border-slate-100" />
        <div className="bg-slate-50 p-4 rounded-lg border border-slate-100 text-xs space-y-3">
          <div className="flex justify-between items-center text-slate-600">
            <span className="flex items-center gap-1 font-medium"><CreditCard className="w-3.5 h-3.5" /> Credit còn lại</span>
            <span className="font-bold text-slate-900">182 / 500</span>
          </div>
          <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
            <div className="bg-indigo-600 h-full w-[36%]" />
          </div>
          <button className="w-full py-2 bg-white border border-slate-200 rounded text-center font-semibold text-slate-700 hover:bg-slate-50 transition">Nâng cấp gói</button>
        </div>
      </div>

      {/* Main */}
      <div className="md:col-span-3 space-y-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900">Chào buổi sáng, Minh! 👋 11</h2>
            <p className="text-xs text-slate-500 mt-1">Hôm nay bạn muốn tối ưu hóa chiến dịch và tạo nội dung gì?</p>
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
                    <span className="text-[11px] text-slate-400">{proj.type} • {proj.time}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded font-medium ${proj.color}`}>{proj.status}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white p-5 rounded-xl border border-slate-200 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Hoạt động gần đây</h3>
            <div className="space-y-3 text-xs text-slate-600">
              <div className="flex gap-2"><div className="w-1.5 h-1.5 bg-indigo-500 rounded-full mt-1.5 shrink-0" /><p>Bạn đã xuất bản <strong>Bánh mì ngon</strong> lên Fanpage</p></div>
              <div className="flex gap-2"><div className="w-1.5 h-1.5 bg-amber-500 rounded-full mt-1.5 shrink-0" /><p>AI đã tạo bản nhập mới cho chiến dịch tuần mới</p></div>
              <div className="flex gap-2"><div className="w-1.5 h-1.5 bg-slate-300 rounded-full mt-1.5 shrink-0" /><p>Cập nhật lại cấu trúc <strong>Brand Profile</strong></p></div>
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
  const [selectedAudience, setSelectedAudience] = useState('Học sinh, sinh viên');
  const [selectedPromo, setSelectedPromo] = useState('Tặng kèm nước ngọt');

  const startMutation = useMutation({
    mutationFn: async () => {
      // Build full request with clarifications
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
    onError: (err: Error) => {
      addToast(`Lỗi: ${err.message}`, 'error');
    },
  });

  const tags = ["Bánh mì ABC", "Tone vui vẻ", "Mạng xã hội Facebook", "Quảng cáo sản phẩm", "Thêm CTA ưu đãi"];
  const toggleTag = (tag: string) => setSelectedTags(p => p.includes(tag) ? p.filter(t => t !== tag) : [...p, tag]);

  return (
    <div className="max-w-3xl mx-auto bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
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
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input type="checkbox" checked={autoMode} onChange={e => setAutoMode(e.target.checked)}
                  className="w-3 h-3 accent-indigo-600" />
                <span className="text-indigo-600 font-medium">Auto Mode</span>
              </label>
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
              <span key={tag}
                onClick={() => toggleTag(tag)}
                className={`px-2.5 py-1 rounded-md font-medium cursor-pointer transition ${selectedTags.includes(tag) ? 'bg-indigo-100 text-indigo-700 border border-indigo-300' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
                {tag}
              </span>
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
                  <span key={opt} onClick={() => setSelectedAudience(opt)}
                    className={`px-2 py-1 rounded cursor-pointer border ${selectedAudience === opt ? 'bg-white border-indigo-200 text-indigo-700 font-medium' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}>
                    {opt}
                  </span>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">2. Chương trình ưu đãi đi kèm?</label>
              <div className="flex gap-1.5">
                {["Giảm giá 20%", "Tặng kèm nước ngọt"].map(opt => (
                  <span key={opt} onClick={() => setSelectedPromo(opt)}
                    className={`px-2 py-1 rounded cursor-pointer border ${selectedPromo === opt ? 'bg-white border-indigo-200 text-indigo-700 font-medium' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}>
                    {opt}
                  </span>
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
  onBack, onGoToReview, onGoToAuto, sessionId, initialDraft, onDraftUpdate, addToast
}: {
  onBack: () => void;
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
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const qc = useQueryClient();

  // Load workflow from API if draft is empty
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

  // Chat Copilot mutation
  const chatMutation = useMutation({
    mutationFn: (instruction: string) => api.chatEdit({ draft: draftContent, instruction }),
    onSuccess: (data) => {
      setDraftContent(data.draft);
      onDraftUpdate(data.draft);
      setChatMessages(p => [...p, { role: 'assistant', content: `Đã cập nhật bản thảo theo yêu cầu. ${data.draft.slice(0, 80)}…` }]);
    },
    onError: (err: Error) => addToast(`Chat error: ${err.message}`, 'error'),
  });

  // Inline suggestion mutation
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

  // Approve & publish
  const approveMutation = useMutation({
    mutationFn: () => api.resumeWorkflow(sessionId, { action: 'approve', content: draftContent }),
    onSuccess: () => {
      addToast('Đã phê duyệt! Đang đăng bài...', 'info');
      publishMutation.mutate();
    },
    onError: (err: Error) => addToast(`Lỗi phê duyệt: ${err.message}`, 'error'),
  });

  const publishMutation = useMutation({
    mutationFn: () => api.publishWorkflow(sessionId),
    onSuccess: (data) => addToast(`Đã đăng bài! Status: ${data.publish_status}`, 'success'),
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
  const tokenEstimate = Math.round(wordCount * 1.3);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* Left: Chat Copilot */}
      <div className="lg:col-span-4 bg-white border border-slate-200 rounded-xl overflow-hidden flex flex-col h-[680px]">
        <div className="flex border-b border-slate-100 p-2 bg-slate-50 text-xs font-semibold">
          <button onClick={() => setActiveTab('copilot')}
            className={`flex-1 py-1.5 text-center rounded transition ${activeTab === 'copilot' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-400 hover:text-slate-600'}`}>
            Trợ lý Copilot
          </button>
          <button onClick={() => setActiveTab('history')}
            className={`flex-1 py-1.5 text-center rounded transition ${activeTab === 'history' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-400 hover:text-slate-600'}`}>
            Lịch sử phiên (v{workflow?.draft?.version ?? 1})
          </button>
        </div>

        <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
          {activeTab === 'copilot' ? (
            <>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-slate-500 text-center">
                Hệ thống áp dụng Brand Profile: <strong>Bánh mì ABC</strong>
              </div>

              {chatMessages.length === 0 && (
                <div className="text-center text-slate-400 py-8">
                  <Sparkles className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                  <p>Nhập yêu cầu để AI chỉnh sửa nội dung</p>
                </div>
              )}

              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex gap-2 items-start ${msg.role === 'user' ? 'justify-end' : ''}`}>
                  {msg.role === 'assistant' && (
                    <div className="w-6 h-6 bg-indigo-100 text-indigo-600 font-bold rounded-full flex items-center justify-center shrink-0">AI</div>
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
              <p className="text-slate-400 text-center pt-4">Lịch sử chỉnh sửa của phiên làm việc hiện tại.</p>
              {chatMessages.filter(m => m.role === 'user').map((msg, i) => (
                <div key={i} className="bg-slate-50 border border-slate-100 rounded-lg p-2.5">
                  <span className="text-[10px] text-slate-400 font-medium">Yêu cầu #{i + 1}</span>
                  <p className="mt-1">{msg.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-3 border-t border-slate-100 flex gap-2 bg-slate-50">
          <input
            className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-indigo-500"
            placeholder="Yêu cầu AI sửa đổi nội dung văn bản..."
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

      {/* Right: Editor */}
      <div className="lg:col-span-8 bg-white border border-slate-200 rounded-xl overflow-hidden flex flex-col h-[680px]">
        <div className="border-b border-slate-200 p-4 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50">
          <div className="flex items-center gap-2 text-xs">
            <span className="font-bold text-slate-900">Bản thảo: Bánh mì ABC</span>
            <span className="bg-slate-200 px-2 py-0.5 rounded text-[11px] font-medium text-slate-700 flex items-center gap-1">
              <History className="w-3 h-3" /> v{workflow?.draft?.version ?? 1}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onGoToReview}
              className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5">
              <Eye className="w-3.5 h-3.5" /> So sánh phiên bản
            </button>
            <button onClick={onGoToAuto}
              className="px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-lg text-xs font-semibold hover:bg-indigo-100 flex items-center gap-1.5">
              <Play className="w-3.5 h-3.5" /> Auto Mode
            </button>
            <button
              onClick={() => approveMutation.mutate()}
              disabled={approveMutation.isPending || publishMutation.isPending}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition flex items-center gap-1.5 ${PRIMARY_COLOR} disabled:opacity-50`}>
              {(approveMutation.isPending || publishMutation.isPending) && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Duyệt & Đăng bài
            </button>
          </div>
        </div>

        <div className="flex-1 grid grid-cols-1 md:grid-cols-4 divide-x divide-slate-100 overflow-hidden">
          {/* Editor Area */}
          <div className="md:col-span-3 p-6 overflow-y-auto space-y-3 flex flex-col">
            <div className="flex gap-2 border-b border-slate-100 pb-2 text-xs text-slate-400 font-mono">
              <span className="font-bold text-slate-800 cursor-pointer">H1</span>
              <span className="font-bold text-slate-800 cursor-pointer">H2</span>
              <span className="underline cursor-pointer">U</span>
              <span className="italic cursor-pointer">I</span>
              <span className="cursor-pointer">Link</span>
              <span className="cursor-pointer">Quote</span>
              <span className="ml-auto text-[10px] text-slate-400 font-sans">
                💡 Bôi đen đoạn văn để chỉnh sửa inline
              </span>
            </div>

            {/* Inline suggestion banner */}
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

            {/* Inline input popup */}
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
                    <span key={s} onClick={() => setInlineInstruction(s)}
                      className="bg-white px-2 py-0.5 rounded border border-indigo-200 text-indigo-700 cursor-pointer hover:bg-indigo-100">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <textarea
              ref={editorRef}
              className="flex-1 w-full text-sm text-slate-800 leading-relaxed outline-none resize-none border-0 bg-transparent"
              value={draftContent}
              onChange={e => { setDraftContent(e.target.value); onDraftUpdate(e.target.value); }}
              onMouseUp={handleTextSelect}
              onKeyUp={handleTextSelect}
              placeholder="Nội dung bản thảo sẽ xuất hiện ở đây..."
            />
          </div>

          {/* Quick AI Actions */}
          <div className="p-4 bg-slate-50/50 space-y-3 text-xs overflow-y-auto">
            <h4 className="font-bold uppercase tracking-wider text-slate-400 text-[10px]">AI Actions nhanh</h4>
            {[
              { label: "Tối ưu hóa chuẩn SEO", instruction: "Tối ưu hóa bài viết này chuẩn SEO, thêm từ khóa phù hợp" },
              { label: "Rút gọn văn bản gốc", instruction: "Rút ngắn nội dung, giữ lại ý chính" },
              { label: "Đổi văn phong (Tone)", instruction: "Đổi văn phong sang chuyên nghiệp hơn" },
              { label: "Tự động tạo ảnh AI", instruction: "Mô tả prompt hình ảnh phù hợp cho bài viết này" },
            ].map(({ label, instruction }) => (
              <button key={label}
                onClick={() => {
                  setChatMessages(p => [...p, { role: 'user', content: instruction }]);
                  chatMutation.mutate(instruction);
                }}
                disabled={chatMutation.isPending}
                className="w-full text-left bg-white border border-slate-200 p-2.5 rounded-lg hover:border-indigo-500 font-medium flex items-center justify-between disabled:opacity-50">
                <span>{label}</span>
                <ChevronRight className="w-3.5 h-3.5 shrink-0" />
              </button>
            ))}
            <hr className="border-slate-200" />
            <div className="text-[11px] text-slate-400 space-y-1">
              <div>Độ dài: <strong>{wordCount} từ</strong></div>
              <div>Ước tính token: <strong>{tokenEstimate} tokens</strong></div>
            </div>
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
    <div className="space-y-4">
      <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-200">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50"><ArrowLeft className="w-4 h-4" /></button>
          <div>
            <h2 className="text-sm font-bold">Chế độ so sánh và phê duyệt (Diff Review)</h2>
            <p className="text-xs text-slate-500">Xem các chỉnh sửa chi tiết mà AI Copilot đã đề xuất.</p>
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
        {/* Old version */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 relative opacity-75">
          <span className="absolute top-3 right-3 text-[10px] uppercase tracking-wider bg-slate-100 px-2 py-0.5 rounded font-bold text-slate-500">
            Bản cũ (v{currentVersion - 1})
          </span>
          <h3 className="text-sm font-bold text-slate-900 pr-24">Phiên bản cũ</h3>
          <div className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">
            {prevVersion?.content ?? (
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

        {/* New version */}
        <div className="bg-white border border-indigo-200 rounded-xl p-5 space-y-3 relative ring-1 ring-indigo-500/20">
          <span className="absolute top-3 right-3 text-[10px] uppercase tracking-wider bg-indigo-50 px-2 py-0.5 rounded font-bold text-indigo-600">
            Đề xuất mới (v{currentVersion})
          </span>
          <h3 className="text-sm font-bold text-slate-900 pr-24">Phiên bản mới nhất</h3>
          <div className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">
            {currVersion?.content ?? (
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

  useEffect(() => {
    if (status === 'completed') addToast('Hoàn tất! Đã đăng bài thành công.', 'success');
    if (status === 'error') addToast(`Lỗi: ${workflow?.error}`, 'error');
  }, [status]);

  // Map status to steps
  const steps = [
    { label: "Research", status: status === 'running' ? 'active' : 'complete' },
    { label: "Generate", status: status === 'running' ? 'active' : status === 'completed' ? 'complete' : 'active' },
    { label: "Image Gen", status: status === 'completed' ? 'complete' : status === 'running' ? 'active' : 'pending' },
    { label: "Publish", status: status === 'completed' ? 'complete' : 'pending' },
  ];

  if (!started) {
    return (
      <div className="max-w-2xl mx-auto bg-white border border-slate-200 rounded-xl shadow-sm p-8 space-y-6">
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
    <div className="max-w-4xl mx-auto bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
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
          <button onClick={onBack} className="px-3 py-1 bg-white text-slate-900 text-xs font-semibold rounded hover:bg-slate-100 transition">Thoát ra</button>
        </div>
      </div>

      <div className="p-8 space-y-8">
        {/* Progress Steps */}
        <div className="flex items-center justify-between relative max-w-2xl mx-auto">
          <div className="absolute left-0 right-0 top-1/2 h-0.5 bg-slate-200 -translate-y-1/2 z-0" />
          <div className={`absolute left-0 top-1/2 h-0.5 bg-indigo-600 -translate-y-1/2 z-0 transition-all duration-1000 ${
            status === 'completed' ? 'w-full' : 'w-[50%]'
          }`} />

          {steps.map((step, idx) => (
            <div key={idx} className="relative z-10 flex flex-col items-center space-y-1 text-center">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                step.status === 'complete' ? 'bg-indigo-600 text-white' :
                step.status === 'active' ? 'bg-indigo-50 border-2 border-indigo-600 text-indigo-600 animate-pulse' :
                'bg-white border-2 border-slate-200 text-slate-400'
              }`}>
                {step.status === 'complete' ? <Check className="w-4 h-4" /> : idx + 1}
              </div>
              <span className={`text-xs font-semibold ${step.status === 'active' ? 'text-indigo-600' : 'text-slate-500'}`}>{step.label}</span>
            </div>
          ))}
        </div>

        {/* Status Logs */}
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

        {/* Usage info */}
        {workflow?.usage && (
          <div className="max-w-2xl mx-auto text-xs text-slate-400 text-center">
            Đã sử dụng tổng cộng <strong className="text-slate-600">{workflow.usage.total_tokens.toLocaleString()} tokens</strong>
          </div>
        )}

        {/* Error display */}
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
    <div className="max-w-md mx-auto bg-slate-900 p-3 rounded-[40px] shadow-2xl border-4 border-slate-800">
      <div className="bg-white rounded-[32px] overflow-hidden min-h-[640px] flex flex-col text-slate-900">
        <div className="px-4 pt-6 pb-3 border-b border-slate-100 flex justify-between items-center text-xs font-bold">
          <span className="text-slate-900">⚡ Copilot Workspace</span>
          <span className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full">Draft</span>
        </div>

        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <div className="space-y-2">
            <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-wrap">{displayContent}</p>
          </div>
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