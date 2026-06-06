"use client";

import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Plus, Sparkles, ArrowRight, ArrowLeft, Send, Check, History, Eye, 
  Play, Pause, Loader2, AlertCircle, X, Bell, DollarSign, Zap, LayoutDashboard, Sliders
} from 'lucide-react';
import { BASE_URL } from "@/config";

// ==========================================
// CONSTANTS & TYPES
// ==========================================

const PRIMARY_COLOR = "bg-slate-900 text-white hover:bg-slate-800 transition-colors";

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
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 max-w-sm w-full px-4 sm:px-0">
      {toasts.map(t => (
        <div key={t.id} className={`flex items-center justify-between gap-3 px-4 py-3 rounded-lg shadow-lg text-xs font-medium text-white animate-in slide-in-from-bottom-5 duration-200 ${
          t.type === 'success' ? 'bg-slate-900' : t.type === 'error' ? 'bg-red-600' : 'bg-slate-700'
        }`}>
          <div className="flex items-center gap-2">
            {t.type === 'success' && <Check className="w-4 h-4 shrink-0" />}
            {t.type === 'error' && <AlertCircle className="w-4 h-4 shrink-0" />}
            <span className="break-words line-clamp-2">{t.message}</span>
          </div>
          <button onClick={() => onRemove(t.id)} className="p-1 rounded-md hover:bg-white/20 transition">
            <X className="w-3.5 h-3.5" />
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
  const [currentScreen, setCurrentScreen] = useState<1 | 2 | 3 | 4 | 5>(1);
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
    <div className="h-screen bg-white text-slate-900 flex flex-col antialiased overflow-hidden selection:bg-slate-100">
      {/* HEADER TỐI GIẢN */}
      <div className="bg-white border-b border-slate-100 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-slate-900" />
          <span className="text-xs font-bold tracking-widest text-slate-900 uppercase">AI Content Engine</span>
        </div>
        <div className="flex items-center gap-1 text-xs font-medium">
          <button onClick={() => setCurrentScreen(1)} className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition ${currentScreen === 1 ? 'text-slate-900 bg-slate-50' : 'text-slate-500 hover:text-slate-900'}`}><LayoutDashboard className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Tổng quan</span></button>
          <button onClick={() => setCurrentScreen(2)} className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition ${currentScreen === 2 ? 'text-slate-900 bg-slate-50' : 'text-slate-500 hover:text-slate-900'}`}><Plus className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Khởi tạo</span></button>
          <button onClick={() => setCurrentScreen(3)} className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition ${currentScreen === 3 ? 'text-slate-900 bg-slate-50' : 'text-slate-500 hover:text-slate-900'}`}><Sliders className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Không gian viêt</span></button>
          <button onClick={() => setCurrentScreen(4)} className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition ${currentScreen === 4 ? 'text-slate-900 bg-slate-50' : 'text-slate-500 hover:text-slate-900'}`}><Eye className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Kiểm duyệt</span></button>
          <button onClick={() => setCurrentScreen(5)} className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition ${currentScreen === 5 ? 'text-slate-900 bg-slate-50' : 'text-slate-500 hover:text-slate-900'}`}><Zap className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Tự động</span></button>
        </div>
      </div>

      {/* VÙNG NỘI DUNG TRUNG TÂM (Loại bỏ các padding/margin thừa để workspace tràn viền) */}
      <div className={`flex-1 w-full flex flex-col justify-stretch overflow-y-auto ${currentScreen === 3 ? '' : 'max-w-5xl mx-auto p-6 lg:p-12'}`}>
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
        {currentScreen === 3 && (
          <ScreenWorkspace
            onGoToReview={() => setCurrentScreen(4)}
            onGoToAuto={() => setCurrentScreen(5)}
            sessionId={sessionId || "dummy-session-id"}
            initialDraft={currentDraft}
            onDraftUpdate={handleDraftUpdate}
            addToast={addToast}
          />
        )}
        {currentScreen === 4 && (
          <ScreenReviewMode
            onBack={() => setCurrentScreen(3)}
            sessionId={sessionId || "dummy-session-id"}
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
      </div>

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}

// ==========================================
// SCREEN 1 — DASHBOARD
// ==========================================
function ScreenDashboard({ onCreateContent }: { onCreateContent: () => void }) {
  const [showNotifTooltip, setShowNotifTooltip] = useState(false);

  const notifBreakdown = [
    { label: "Bình luận chờ phản hồi", count: 5 },
    { label: "Bản nháp chờ duyệt", count: 3 },
    { label: "Chiến dịch hoàn thành", count: 3 },
  ];

  return (
    <div className="space-y-12 w-full animate-in fade-in duration-300">
      {/* Header Tối Giản */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6 pb-6 border-b border-slate-100">
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Chào buổi sáng.</h2>
          <p className="text-sm text-slate-500">Bạn muốn khởi tạo chiến dịch nội dung gì hôm nay?</p>
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <div className="relative">
            <button
              className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-slate-50 transition"
              onClick={() => setShowNotifTooltip(!showNotifTooltip)}
              onMouseEnter={() => setShowNotifTooltip(true)}
            >
              <Bell className="w-5 h-5 text-slate-600" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-slate-900 rounded-full" />
            </button>
            {showNotifTooltip && (
              <div className="absolute top-12 right-0 z-50 bg-white border border-slate-100 rounded-lg shadow-xl p-4 w-64 text-sm space-y-3 animate-in fade-in zoom-in-95 duration-100">
                <p className="font-semibold text-slate-900 border-b border-slate-100 pb-2">Thông báo chờ</p>
                {notifBreakdown.map(n => (
                  <div key={n.label} className="flex justify-between items-center text-slate-600 text-xs">
                    <span>{n.label}</span>
                    <span className="font-medium">{n.count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <button onClick={onCreateContent} className={`flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-medium rounded-md ${PRIMARY_COLOR}`}>
            <Plus className="w-4 h-4" /> Tạo chiến dịch mới
          </button>
        </div>
      </div>

      {/* Grid Menu Không Đóng Khung */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {["Bài đăng Mạng Xã Hội", "Bài viết chuẩn SEO", "Kịch bản Quảng Cáo", "Ý tưởng & Concept"].map((action, idx) => (
          <button key={idx} onClick={onCreateContent}
            className="text-left p-6 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors group space-y-4">
            <span className="text-xs font-medium text-slate-400 group-hover:text-slate-900 transition-colors">0{idx + 1}</span>
            <div className="font-medium text-sm text-slate-900">{action}</div>
          </button>
        ))}
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
    },
    onError: (err: Error) => addToast(`Lỗi khởi tạo: ${err.message}`, 'error'),
  });

  const tags = ["Thương hiệu F&B", "Giọng điệu hài hước", "Chuẩn định dạng Facebook", "Tập trung chuyển đổi"];
  const toggleTag = (tag: string) => setSelectedTags(p => p.includes(tag) ? p.filter(t => t !== tag) : [...p, tag]);

  return (
    <div className="max-w-3xl mx-auto w-full animate-in fade-in duration-300">
      
      <button onClick={onBack} className="flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-slate-900 transition mb-8">
        <ArrowLeft className="w-4 h-4" /> Quay lại tổng quan
      </button>

      <div className="space-y-10">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold text-slate-900">Yêu cầu chiến dịch</h1>
          <p className="text-sm text-slate-500">Mô tả định hướng nội dung của bạn. Hệ thống sẽ tự động thiết lập không gian biên tập.</p>
        </div>

        {/* Khung Input Phẳng (Flat Design) */}
        <div className="space-y-6">
          <textarea
            className="w-full bg-transparent border-b-2 border-slate-100 hover:border-slate-200 focus:border-slate-900 outline-none resize-none text-base sm:text-lg placeholder:text-slate-300 min-h-[120px] leading-relaxed text-slate-900 transition-colors pb-4"
            placeholder="Ví dụ: Viết bài đăng Facebook quảng cáo món bánh mì mới, yêu cầu văn phong năng động, có lời kêu gọi hành động ở cuối bài..."
            value={request}
            onChange={e => setRequest(e.target.value)}
            autoFocus
          />

          {/* Thiết lập nhanh */}
          <div className="space-y-3">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Từ khóa định hướng</span>
            <div className="flex flex-wrap gap-2">
              {tags.map(tag => (
                <button key={tag}
                  onClick={() => toggleTag(tag)}
                  className={`px-4 py-2 rounded-md text-xs font-medium transition-colors ${selectedTags.includes(tag) ? 'bg-slate-900 text-white' : 'bg-slate-50 text-slate-600 hover:bg-slate-100'}`}>
                  {tag}
                </button>
              ))}
            </div>
          </div>

          {/* Tùy chỉnh Nâng cao */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-6 border-t border-slate-100">
            <div className="space-y-3">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Đối tượng mục tiêu</span>
              <div className="flex flex-wrap gap-2">
                {["Học sinh, sinh viên", "Dân văn phòng"].map(opt => (
                  <button key={opt} onClick={() => setSelectedAudience(opt)}
                    className={`px-4 py-2 rounded-md text-xs font-medium transition-colors ${selectedAudience === opt ? 'bg-slate-200 text-slate-900' : 'bg-white border border-slate-200 text-slate-500 hover:bg-slate-50'}`}>
                    {opt}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-3">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Ưu đãi nổi bật</span>
              <div className="flex flex-wrap gap-2">
                {["Giảm giá 20%", "Tặng kèm nước ngọt"].map(opt => (
                  <button key={opt} onClick={() => setSelectedPromo(opt)}
                    className={`px-4 py-2 rounded-md text-xs font-medium transition-colors ${selectedPromo === opt ? 'bg-slate-200 text-slate-900' : 'bg-white border border-slate-200 text-slate-500 hover:bg-slate-50'}`}>
                    {opt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Thanh Action Đáy */}
        <div className="flex items-center justify-between pt-8 border-t border-slate-100">
          <button
            onClick={() => setAutoMode(v => !v)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-medium transition-colors ${
              autoMode ? 'bg-slate-900 text-white' : 'text-slate-500 hover:bg-slate-50'
            }`}
          >
            <Zap className="w-4 h-4" /> Auto Mode: {autoMode ? 'Bật' : 'Tắt'}
          </button>
          
          <button
            onClick={() => startMutation.mutate()}
            disabled={!request.trim() || startMutation.isPending}
            className={`flex items-center gap-2 px-6 py-3 rounded-md text-sm font-medium transition-colors ${PRIMARY_COLOR} disabled:opacity-40 disabled:cursor-not-allowed`}>
            {startMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Bắt đầu soạn thảo'} <ArrowRight className="w-4 h-4" />
          </button>
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
      setChatMessages(p => [...p, { role: 'assistant', content: `Đã cập nhật bản thảo theo yêu cầu.` }]);
    },
    onError: (err: Error) => addToast(`Lỗi phản hồi: ${err.message}`, 'error'),
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
    onError: (err: Error) => addToast(`Lỗi chỉnh sửa: ${err.message}`, 'error'),
  });

  const approveMutation = useMutation({
    mutationFn: () => api.resumeWorkflow(sessionId, { action: 'approve', content: draftContent }),
    onSuccess: () => {
      setIsApproved(true);
      addToast('Đã chốt nội dung. Bạn có thể xuất bản.', 'success');
    },
    onError: (err: Error) => addToast(`Lỗi phê duyệt: ${err.message}`, 'error'),
  });

  const publishMutation = useMutation({
    mutationFn: () => api.publishWorkflow(sessionId),
    onSuccess: (data) => {
      addToast(`Đã xuất bản thành công! Trạng thái: ${data.publish_status}`, 'success');
      setIsApproved(false);
    },
    onError: (err: Error) => addToast(`Lỗi xuất bản: ${err.message}`, 'error'),
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
  };

  const rejectInlineSuggestion = () => {
    setInlineSuggestion(null);
    setSelection(null);
  };

  const wordCount = draftContent.trim().split(/\s+/).filter(Boolean).length;

  return (
    <div className="flex flex-col lg:flex-row h-full w-full bg-white border-t border-slate-100 overflow-hidden animate-in fade-in duration-300">
      
      {/* CỘT TRÁI: AI COPILOT (Layout phẳng, không đóng hộp) */}
      <div className="w-full lg:w-[320px] xl:w-[380px] bg-slate-50/50 flex flex-col border-r border-slate-100 shrink-0">
        <div className="flex border-b border-slate-100 p-2 shrink-0 gap-1">
          <button onClick={() => setActiveTab('copilot')}
            className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${activeTab === 'copilot' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'}`}>
            Trợ lý AI
          </button>
          <button onClick={() => setActiveTab('history')}
            className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${activeTab === 'history' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'}`}>
            Nhật ký
          </button>
        </div>

        {/* Khung Chat */}
        <div className="flex-1 overflow-y-auto p-5 text-sm space-y-6 scrollbar-thin">
          {activeTab === 'copilot' ? (
            <>
              {chatMessages.length === 0 && (
                <div className="text-slate-400 text-xs leading-relaxed space-y-4 pt-4">
                  <p>Hãy yêu cầu AI chỉnh sửa tổng thể bản thảo. Ví dụ:</p>
                  <ul className="space-y-2">
                    {["Làm giọng điệu chuyên nghiệp hơn", "Rút gọn thành 100 từ", "Thêm CTA mạnh mẽ"].map(p => (
                      <li key={p}>
                        <button onClick={() => { setChatInput(p); handleSendChat(); }} className="text-left hover:text-slate-900 transition-colors">
                          → {p}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} gap-1`}>
                  <span className="text-[10px] font-medium text-slate-400 uppercase">{msg.role === 'user' ? 'Bạn' : 'AI Engine'}</span>
                  <div className={`px-4 py-2.5 rounded-lg max-w-[90%] text-sm leading-relaxed ${
                    msg.role === 'user' ? 'bg-slate-100 text-slate-900' : 'text-slate-700 bg-transparent'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}

              {chatMutation.isPending && (
                <div className="flex items-center text-slate-400 text-xs gap-2 py-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Đang xử lý yêu cầu...
                </div>
              )}
              <div ref={chatBottomRef} />
            </>
          ) : (
            <div className="space-y-4">
              {chatMessages.filter(m => m.role === 'user').map((msg, i) => (
                <div key={i} className="text-xs space-y-1 pb-4 border-b border-slate-100">
                  <span className="text-slate-400 font-medium">Bản sửa đổi #{i + 1}</span>
                  <p className="text-slate-900">{msg.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Input Text Trợ Lý */}
        <div className="p-4 border-t border-slate-100 bg-white shrink-0">
          <div className="relative flex items-center">
            <input
              className="w-full bg-slate-50 border-0 rounded-md py-2.5 pl-3 pr-10 text-xs outline-none focus:ring-1 focus:ring-slate-200 text-slate-900 placeholder-slate-400 transition-all"
              placeholder="Nhập yêu cầu cho AI..."
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSendChat()}
            />
            <button onClick={handleSendChat} disabled={chatMutation.isPending || !chatInput.trim()}
              className="absolute right-1 p-1.5 text-slate-400 hover:text-slate-900 disabled:opacity-50 transition-colors">
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* CỘT PHẢI: KHÔNG GIAN SOẠN THẢO VĂN BẢN (Text Editor tinh gọn) */}
      <div className="flex-1 flex flex-col bg-white overflow-hidden relative">
        {/* Toolbar ngang mỏng nhẹ */}
        <div className="px-6 py-3 border-b border-slate-100 flex flex-wrap items-center justify-between gap-4 shrink-0 bg-white">
          <div className="flex items-center gap-4 text-xs font-medium text-slate-400">
            <span>{wordCount} từ</span>
            <span className="w-1 h-1 rounded-full bg-slate-200" />
            <span>V{workflow?.draft?.version ?? 1}</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onGoToReview} className="px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 transition-colors">
              Xem khác biệt
            </button>
            <button onClick={onGoToAuto} className="px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 transition-colors">
              Chế độ Tự động
            </button>
            <div className="w-px h-4 bg-slate-200 mx-2" />
            {!isApproved ? (
              <button onClick={() => approveMutation.mutate()} disabled={approveMutation.isPending}
                className="px-4 py-1.5 bg-slate-100 text-slate-900 rounded-md text-xs font-medium hover:bg-slate-200 transition-colors">
                {approveMutation.isPending ? 'Đang xử lý...' : 'Chốt nội dung'}
              </button>
            ) : (
              <button onClick={() => publishMutation.mutate()} disabled={publishMutation.isPending}
                className={`px-4 py-1.5 rounded-md text-xs font-medium ${PRIMARY_COLOR}`}>
                {publishMutation.isPending ? 'Đang xử lý...' : 'Xuất bản'}
              </button>
            )}
          </div>
        </div>

        {/* Khung soạn thảo (Tập trung vào typography) */}
        <div className="flex-1 overflow-y-auto p-8 lg:p-16 relative scrollbar-thin">
          
          {/* Popup Inline Suggestion (Khi có kết quả AI trả về) */}
          {inlineSuggestion && (
            <div className="absolute top-8 right-8 z-10 w-80 bg-white border border-slate-100 rounded-xl shadow-xl p-5 text-sm space-y-4 animate-in fade-in zoom-in-95">
              <div className="font-medium text-slate-900">Gợi ý từ AI</div>
              <div className="space-y-3 text-sm">
                <div className="line-through text-slate-400">{inlineSuggestion.original}</div>
                <div className="text-slate-900 font-medium">{inlineSuggestion.suggestion}</div>
              </div>
              <div className="flex gap-2 pt-2 border-t border-slate-50">
                <button onClick={acceptInlineSuggestion} className="flex-1 py-1.5 bg-slate-900 text-white rounded-md text-xs font-medium hover:bg-slate-800 transition-colors">Chấp nhận</button>
                <button onClick={rejectInlineSuggestion} className="flex-1 py-1.5 bg-slate-50 text-slate-600 rounded-md text-xs font-medium hover:bg-slate-100 transition-colors">Bỏ qua</button>
              </div>
            </div>
          )}

          {/* Popup Yêu cầu Inline (Khi bôi đen văn bản) */}
          {showInlineInput && !inlineSuggestion && (
            <div className="absolute top-8 right-8 z-10 w-80 bg-white border border-slate-100 rounded-xl shadow-xl p-4 text-sm space-y-3 animate-in slide-in-from-top-4">
              <div className="text-xs font-medium text-slate-400">Chỉnh sửa đoạn đã chọn</div>
              <input
                className="w-full bg-slate-50 border-0 rounded-md px-3 py-2 text-sm outline-none focus:bg-slate-100 transition-colors"
                placeholder="Ví dụ: Viết ngắn gọn lại..."
                value={inlineInstruction}
                onChange={e => setInlineInstruction(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleInlineSubmit()}
                autoFocus
              />
              <div className="flex justify-end gap-2">
                <button onClick={() => { setShowInlineInput(false); setSelection(null); }} className="px-3 py-1.5 text-xs text-slate-500 hover:text-slate-900">Hủy</button>
                <button onClick={handleInlineSubmit} disabled={inlineMutation.isPending} className="px-3 py-1.5 bg-slate-900 text-white rounded-md text-xs font-medium hover:bg-slate-800 transition-colors">
                  {inlineMutation.isPending ? 'Đang xử lý...' : 'Chỉnh sửa'}
                </button>
              </div>
            </div>
          )}

          <textarea
            ref={editorRef}
            className="w-full max-w-3xl mx-auto block bg-transparent outline-none resize-none border-0 min-h-full font-serif text-lg text-slate-800 leading-loose"
            value={draftContent}
            onChange={e => { setDraftContent(e.target.value); onDraftUpdate(e.target.value); }}
            onMouseUp={handleTextSelect}
            onKeyUp={handleTextSelect}
            placeholder="Nội dung sẽ hiển thị tại đây. Bôi đen một đoạn văn để yêu cầu AI chỉnh sửa riêng phần đó..."
          />
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
  const { data: versionsData, isLoading } = useQuery({
    queryKey: ['versions', sessionId],
    queryFn: () => api.getVersions(sessionId),
    enabled: !!sessionId,
  });

  const approveMutation = useMutation({
    mutationFn: () => api.resumeWorkflow(sessionId, { action: 'approve' }),
    onSuccess: () => addToast('Đã phê duyệt nội dung.', 'success'),
  });

  const versions = versionsData?.versions ?? [];
  const currentVersion = versionsData?.current_version ?? 0;
  const prevVersion = versions.find(v => v.version === currentVersion - 1);
  const currVersion = versions.find(v => v.version === currentVersion);

  return (
    <div className="max-w-6xl mx-auto w-full flex flex-col h-full animate-in fade-in duration-300">
      <div className="flex items-center justify-between pb-6 border-b border-slate-100 shrink-0">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-slate-400 hover:text-slate-900 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">So sánh phiên bản</h2>
            <p className="text-xs text-slate-500">Xem lại các thay đổi trước khi chốt bản thảo.</p>
          </div>
        </div>
        <button
          onClick={() => approveMutation.mutate()}
          disabled={approveMutation.isPending}
          className={`px-5 py-2.5 rounded-md text-sm font-medium transition-colors ${PRIMARY_COLOR} disabled:opacity-50`}>
          {approveMutation.isPending ? 'Đang xử lý...' : `Phê duyệt V${currentVersion}`}
        </button>
      </div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center text-slate-400 text-sm gap-2">
          <Loader2 className="w-4 h-4 animate-spin" /> Đang tải lịch sử thay đổi...
        </div>
      ) : (
        <div className="flex-1 flex flex-col md:flex-row gap-8 pt-8 overflow-hidden">
          {/* Cột bản cũ */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-4 shrink-0">Phiên bản V{currentVersion - 1} (Bản cũ)</div>
            <div className="flex-1 overflow-y-auto pr-4 font-serif text-base text-slate-500 leading-loose scrollbar-thin whitespace-pre-wrap opacity-80">
              {prevVersion?.content || "Không có dữ liệu bản cũ."}
            </div>
          </div>
          <div className="w-px bg-slate-100 hidden md:block shrink-0" />
          {/* Cột bản mới */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="text-xs font-medium text-slate-900 uppercase tracking-wider mb-4 shrink-0">Phiên bản V{currentVersion} (Mới nhất)</div>
            <div className="flex-1 overflow-y-auto pl-0 md:pl-4 font-serif text-base text-slate-900 leading-loose scrollbar-thin whitespace-pre-wrap">
              {currVersion?.content || "Không có dữ liệu bản mới."}
            </div>
          </div>
        </div>
      )}
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
    refetchInterval: (query) => query.state.data?.status === 'running' ? 3000 : false,
  });

  const status = workflow?.status ?? 'running';

  const steps = [
    { label: "Nghiên cứu", status: 'complete' as const },
    { label: "Biên soạn", status: status === 'running' || status === 'completed' ? 'complete' as const : 'active' as const },
    { label: "Hình ảnh", status: status === 'completed' ? 'complete' as const : status === 'running' ? 'active' as const : 'pending' as const },
    { label: "Xuất bản", status: status === 'completed' ? 'complete' as const : 'pending' as const },
  ];

  if (!started) {
    return (
      <div className="max-w-2xl mx-auto w-full pt-12 animate-in fade-in duration-300">
        <button onClick={onBack} className="flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-slate-900 transition mb-8">
          <ArrowLeft className="w-4 h-4" /> Quay lại
        </button>
        <div className="space-y-8">
          <h2 className="text-2xl font-semibold text-slate-900">Chiến dịch Tự động hóa</h2>
          <textarea
            className="w-full bg-transparent border-b-2 border-slate-100 hover:border-slate-200 focus:border-slate-900 outline-none resize-none text-base placeholder:text-slate-300 min-h-[100px] leading-relaxed text-slate-900 transition-colors"
            placeholder="Nhập thông điệp chính, AI sẽ tự động nghiên cứu, viết bài và đăng tải..."
            value={request}
            onChange={e => setRequest(e.target.value)}
          />
          <div className="flex justify-end">
            <button
              onClick={() => startMutation.mutate(request)}
              disabled={!request.trim() || startMutation.isPending}
              className={`px-6 py-2.5 rounded-md text-sm font-medium transition-colors ${PRIMARY_COLOR} disabled:opacity-50`}>
              {startMutation.isPending ? 'Đang khởi chạy...' : 'Chạy chiến dịch Auto'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto w-full pt-12 animate-in fade-in duration-300 space-y-12">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Luồng tự động đang chạy</h2>
          <p className="text-sm text-slate-500">Trạng thái: {status === 'running' ? 'Đang xử lý' : status === 'completed' ? 'Hoàn tất' : status}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setIsPaused(!isPaused)} className="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 rounded-md transition-colors">
            {isPaused ? "Tiếp tục" : "Tạm dừng"}
          </button>
          <button onClick={onBack} className="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 rounded-md transition-colors">Thoát</button>
        </div>
      </div>

      {/* Progress Line */}
      <div className="flex justify-between relative px-2">
        <div className="absolute top-3 left-4 right-4 h-px bg-slate-100 z-0" />
        {steps.map((step, idx) => (
          <div key={idx} className="relative z-10 flex flex-col items-center gap-2 bg-white px-2">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs transition-colors ${
              step.status === 'complete' ? 'bg-slate-900 text-white' :
              step.status === 'active' ? 'bg-slate-200 text-slate-900 animate-pulse' :
              'bg-slate-50 text-slate-400'
            }`}>
              {step.status === 'complete' ? <Check className="w-3 h-3" /> : idx + 1}
            </div>
            <span className={`text-xs font-medium ${step.status === 'active' ? 'text-slate-900' : 'text-slate-500'}`}>{step.label}</span>
          </div>
        ))}
      </div>

      {/* Nhật ký Logs (Clean text) */}
      <div className="bg-slate-50 p-6 rounded-xl text-sm font-mono text-slate-600 space-y-3">
        <div className="flex items-center gap-3"><span className="text-slate-400">[Hệ thống]</span> Khởi tạo phân tích dữ liệu...</div>
        <div className="flex items-center gap-3"><span className="text-slate-400">[AI Core]</span> Xây dựng khung nội dung.</div>
        {status === 'running' && <div className="flex items-center gap-3 text-slate-900"><Loader2 className="w-3 h-3 animate-spin" /> Đang tạo sinh văn bản chi tiết...</div>}
        {status === 'completed' && <div className="flex items-center gap-3 text-slate-900">Chiến dịch hoàn tất. Đã đẩy lên hệ thống phân phối.</div>}
      </div>
    </div>
  );
}