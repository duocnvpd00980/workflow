"use client";

import {
  Attachment, AttachmentPreview, AttachmentRemove, Attachments,
} from "@/components/ai-elements/attachments";
import {
  Conversation, ConversationContent, ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  Message, MessageBranch, MessageBranchContent,
  MessageContent, MessageResponse,
} from "@/components/ai-elements/message";
import {
  ModelSelector, ModelSelectorContent, ModelSelectorEmpty,
  ModelSelectorGroup, ModelSelectorInput, ModelSelectorItem,
  ModelSelectorList, ModelSelectorLogo,
  ModelSelectorName, ModelSelectorTrigger,
} from "@/components/ai-elements/model-selector";
import {
  PromptInput, PromptInputActionAddAttachments, PromptInputActionMenu,
  PromptInputActionMenuContent, PromptInputActionMenuTrigger,
  PromptInputBody, PromptInputButton, PromptInputFooter,
  PromptInputHeader, PromptInputSubmit, PromptInputTextarea,
  PromptInputTools, usePromptInputAttachments,
} from "@/components/ai-elements/prompt-input";
import { SpeechInput } from "@/components/ai-elements/speech-input";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { 
  CheckIcon, GlobeIcon, MessageSquarePlus, MenuIcon,
  Zap, History, Settings, BarChart3, Pause, Square, LogOut, Terminal, 
  Database, Sparkles, AlertTriangle, FileText
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import type { Conv } from "../lib/api";
import { API_BASE_URL, createConversation, fetchConversations, queryKeys } from "../lib/api";
import { useChatStream, PIPELINE_STEPS } from "../hooks/useChatStream";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { createFileRoute } from '@tanstack/react-router'
import SidebarNav from "@/components/layout/navbar";

// ─── Config ───────────────────────────────────────────────────────────────────
const SESSION_ID = "web-ui";

const MODELS = [
  { id: "gpt-4o",           name: "GPT-4o",           chef: "OpenAI",    providers: ["openai"]    },
  { id: "claude-sonnet-4",  name: "Claude 4 Sonnet",  chef: "Anthropic", providers: ["anthropic"] },
  { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", chef: "Google",    providers: ["google"]    },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────
function groupConvsByDate(convs: Conv[]) {
  const today     = new Date(); today.setHours(0,0,0,0);
  const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
  const groups: { label: string; items: Conv[] }[] = [
    { label: "Hôm nay",   items: [] },
    { label: "Hôm qua",   items: [] },
    { label: "Trước đó",  items: [] },
  ];
  for (const c of convs) {
    const d = new Date(c.last_message_at); d.setHours(0,0,0,0);
    if (d >= today)          groups[0].items.push(c);
    else if (d >= yesterday) groups[1].items.push(c);
    else                     groups[2].items.push(c);
  }
  return groups.filter((g) => g.items.length > 0);
}

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)  return "vừa xong";
  if (m < 60) return `${m} phút trước`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} giờ trước`;
  return new Date(iso).toLocaleDateString("vi-VN");
}

const AttachmentItem = ({ a, onRemove }: {
  a: { id: string; name?: string; type?: string; url?: string };
  onRemove: (id: string) => void;
}) => (
  <Attachment data={{ ...a, mediaType: a.type || "unknown" } as any} onRemove={() => onRemove(a.id)}>
    <AttachmentPreview />
    <AttachmentRemove />
  </Attachment>
);

const PromptInputAttachmentsDisplay = () => {
  const { files, remove } = usePromptInputAttachments();
  if (!files.length) return null;
  return (
    <Attachments variant="inline">
      {files.map((f) => <AttachmentItem key={f.id} a={f as any} onRemove={remove} />)}
    </Attachments>
  );
};




export const Route = createFileRoute('/')({
  component: ChatPage,
})



// ─── Page ─────────────────────────────────────────────────────────────────────
export default function ChatPage() {
  const queryClient = useQueryClient();

  const [model,       setModel]       = useState(MODELS[0].id);
  const [modelOpen,   setModelOpen]   = useState(false);
  const [webSearch,   setWebSearch]   = useState(false);
  const [input,       setInput]       = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [convId,      setConvId]      = useState<string | null>(null);

  // ── Fetch conversations ──────────────────────────────────────────────────
  const { data: conversations = [] } = useQuery<Conv[]>({
    queryKey: queryKeys.conversations,
    queryFn:  fetchConversations,
    staleTime: 30_000,
  });

  // ── Create conversation ──────────────────────────────────────────────────
  const createConvMutation = useMutation({
    mutationFn: createConversation,
    onSuccess: (id) => {
      setConvId(id);
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations });
    },
    onError: () => toast.error("Không thể tạo cuộc trò chuyện"),
  });

  useEffect(() => { createConvMutation.mutate(); }, []);

  // ── Stream ───────────────────────────────────────────────────────────────
  const { messages, nodes, suggestions, status, error: streamError, sendMessage, stop, reset } = useChatStream({
    api:            `${API_BASE_URL}/chat/stream`,
    sessionId:      SESSION_ID,
    conversationId: convId ?? "",
  });

  useEffect(() => { if (streamError) toast.error(streamError); }, [streamError]);

  const isLoading    = status === "streaming";
  const submitStatus = isLoading ? "streaming" : "ready";
  const selected     = useMemo(() => MODELS.find((m) => m.id === model)!, [model]);
  const activeTitle  = conversations.find((c) => c.id === convId)?.title ?? "Chiến dịch tháng 6";
  const isEmpty      = messages.length === 0 && !isLoading;

  const submit = useCallback((text: string) => {
    if (!text.trim() || isLoading || !convId) return;
    setInput("");
    sendMessage(text);
  }, [isLoading, sendMessage, convId]);

  const newChat = useCallback(() => {
    reset();
    setInput("");
    createConvMutation.mutate();
  }, [reset, createConvMutation]);

  const selectConv = useCallback((id: string) => {
    reset();
    setConvId(id);
    setInput("");
  }, [reset]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(input); }
  }, [input, submit]);

  const groups = useMemo(() => groupConvsByDate(conversations), [conversations]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#fafbfc] text-slate-900 select-none antialiased font-sans">
      
      {/* ─── 1. SIDEBAR TRÁI (Hệ thống thực thi & Danh sách công việc) ─── */}
      <aside className={`fixed inset-y-0 left-0 z-30 flex w-[260px] flex-col border-r bg-white transition-transform duration-200 md:relative md:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        

        <SidebarNav />

        {/* Active Jobs Section */}
        <div className="flex-1 overflow-y-auto px-3 py-4 flex flex-col min-h-0">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1 mb-2.5">Công việc đang chạy</p>
          
          <div className="space-y-2">
            {/* Job 1 (Active) */}
            <div className="p-3 border-2 border-indigo-500 rounded-xl bg-white shadow-sm relative cursor-pointer">
              <div className="flex justify-between items-start mb-2">
                <span className="text-[12px] font-bold text-slate-800 truncate pr-2">Chiến dịch tháng 6</span>
                <span className="bg-indigo-100 text-indigo-700 text-[10px] font-bold px-1.5 py-0.5 rounded-md shrink-0">60%</span>
              </div>
              <Progress value={60} className="h-1.5 bg-slate-100 [&>div]:bg-indigo-600" />
              <div className="flex justify-between items-center text-[10px] text-slate-400 mt-2 font-medium">
                <span>Bước 3/5: Tạo ảnh</span>
                <span>4m left</span>
              </div>
            </div>

            {/* Job 2 */}
            <div className="p-3 border border-slate-100 rounded-xl bg-white hover:border-slate-200 transition-colors cursor-pointer">
              <div className="flex justify-between items-start mb-2">
                <span className="text-[12px] font-bold text-slate-700 truncate pr-2">SaaS Q3 Analysis</span>
                <span className="bg-amber-100 text-amber-700 text-[10px] font-bold px-1.5 py-0.5 rounded-md shrink-0">34%</span>
              </div>
              <Progress value={34} className="h-1 bg-slate-100 [&>div]:bg-amber-500" />
              <p className="text-[10px] text-slate-400 mt-1.5 font-medium truncate">Trích xuất dữ liệu...</p>
            </div>

            {/* Job 3 */}
            <div className="p-3 border border-slate-100 rounded-xl bg-white hover:border-slate-200 transition-colors cursor-pointer">
              <div className="flex justify-between items-start mb-2">
                <span className="text-[12px] font-bold text-slate-700 truncate pr-2">Research đối thủ</span>
                <span className="bg-slate-100 text-slate-600 text-[10px] font-bold px-1.5 py-0.5 rounded-md shrink-0">12%</span>
              </div>
              <Progress value={12} className="h-1 bg-slate-100 [&>div]:bg-slate-400" />
              <p className="text-[10px] text-slate-400 mt-1.5 font-medium truncate">Web crawling...</p>
            </div>
          </div>

          {/* Recent list */}
          <div className="mt-6">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1 mb-2">Gần đây</p>
            <div className="space-y-1">
              {groups.flatMap(g => g.items).slice(0, 3).map((c) => (
                <button key={c.id} onClick={() => selectConv(c.id)} className={`w-full flex items-center justify-between p-1.5 rounded-lg text-left text-[12px] transition-colors ${convId === c.id ? "bg-slate-100 font-medium" : "text-slate-600 hover:bg-slate-50"}`}>
                  <span className="truncate pr-2">✓ {c.title}</span>
                  <span className="text-[10px] text-slate-400 shrink-0">{relativeTime(c.last_message_at)}</span>
                </button>
              )) || (
                <>
                  <div className="flex items-center justify-between p-1.5 text-[11px] text-slate-600"><span className="truncate">✓ Báo cáo Q2 Financial</span><span className="text-slate-400">2h trước</span></div>
                  <div className="flex item-center justify-between p-1.5 text-[11px] text-slate-600"><span className="truncate">✓ Security Audit</span><span className="text-slate-400">1d trước</span></div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar User Row */}
        <div className="border-t p-3 shrink-0 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-[11px] font-bold shrink-0">TH</div>
            <span className="text-[13px] font-medium text-slate-700 truncate">Thành</span>
          </div>
          <button onClick={newChat} title="Tạo Session mới" className="p-1.5 hover:bg-slate-200/60 text-slate-400 hover:text-slate-600 rounded-md transition-colors">
            <MessageSquarePlus size={16} />
          </button>
        </div>
      </aside>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && <div className="fixed inset-0 z-20 bg-slate-900/20 backdrop-blur-xs md:hidden" onClick={() => setSidebarOpen(false)} />}

      {/* ─── 2. MAIN CENTER (Vùng hiển thị kịch bản & Tiến trình Agent) ─── */}
      <main className="flex-1 flex flex-col min-w-0 bg-slate-50/60 overflow-hidden relative">
        
        {/* Main Content Header */}
        <header className="h-14 bg-white border-b flex items-center justify-between px-6 shrink-0 z-10 shadow-xs">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => setSidebarOpen(true)} className="p-1.5 -ml-1.5 hover:bg-slate-100 rounded-md text-slate-500 md:hidden shrink-0">
              <MenuIcon size={18} />
            </button>
            <h2 className="font-bold text-[15px] text-slate-800 truncate">{activeTitle}</h2>
            <div className="h-4 w-px bg-slate-200 hidden sm:block shrink-0" />
            <div className="items-center gap-2 hidden sm:flex text-[11px] text-slate-500 min-w-0">
              <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse shrink-0" />
              <span className="truncate">Agent đang làm việc • Bạn có thể can thiệp</span>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px] font-mono text-slate-400 bg-slate-100 border px-1.5 py-0.5 rounded hidden lg:inline">ID: AGENT-8829-X</span>
            <Button variant="outline" size="sm" className="h-8 text-[11px] border-slate-200 text-slate-600 bg-white shadow-xs hover:bg-slate-50">
              <LogOut size={12} className="mr-1 rotate-180" /> Xuất
            </Button>
            <Button variant="outline" size="sm" className="h-8 text-[11px] border-amber-200 text-amber-700 bg-amber-50/40 shadow-xs hover:bg-amber-50" onClick={stop}>
              <Pause size={12} className="mr-1 fill-current" /> Tạm dừng
            </Button>
            <Button variant="outline" size="sm" className="h-8 text-[11px] border-red-200 text-red-600 bg-red-50/40 shadow-xs hover:bg-red-50">
              <Square size={12} className="mr-1 fill-current" /> Dừng hẳn
            </Button>
          </div>
        </header>

        {/* Workspace Display Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="max-w-[800px] mx-auto space-y-6">

            {/* Khối 0: User Prompt Rendered (Giống ảnh 2) */}
            <div className="flex gap-4 items-start">
              <div className="w-9 h-9 rounded-full bg-slate-200 text-slate-600 font-bold text-[11px] flex items-center justify-center shrink-0 shadow-xs">Bạn</div>
              <div className="flex-1 bg-white border border-slate-100 p-4 rounded-2xl shadow-sm relative">
                <p className="text-[13px] leading-relaxed text-slate-700 font-medium">
                  "Tạo chiến dịch marketing tháng 6 cho sản phẩm mới. Cần: 1 blog về AI trends, 3 ảnh banner, 2 bộ ads Facebook, và lên lịch đăng tuần tới. Target: startup tech."
                </p>
                <div className="text-[10px] text-slate-400 mt-2 flex items-center gap-2">
                  <span>14:32:05</span><span>•</span><span>Bạn vừa ra lệnh</span>
                </div>
              </div>
            </div>

            {/* Khối 1: Bảng kế hoạch 5 bước (Giống y hệt hình 2) */}
            <div className="flex gap-4 items-start">
              <div className="w-9 h-9 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-md">
                <Terminal size={14} />
              </div>
              <div className="flex-1 bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm space-y-4">
                <p className="text-[13px] font-medium text-slate-800">Đã phân tích yêu cầu. Tôi sẽ thực hiện <strong className="text-indigo-600 font-bold">5 bước</strong>:</p>
                
                <div className="space-y-2">
                  {/* Step 1 */}
                  <div className="flex items-center justify-between p-2.5 rounded-xl border border-emerald-100 bg-emerald-50/20 transition-all">
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 rounded-full bg-emerald-500 text-white text-[11px] font-bold flex items-center justify-center">1</div>
                      <span className="text-[12px] font-medium text-slate-700">Research AI trends 2025</span>
                    </div>
                    <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-none font-bold text-[10px] px-2 py-0">✓ Xong</Badge>
                  </div>

                  {/* Step 2 */}
                  <div className="flex items-center justify-between p-2.5 rounded-xl border border-indigo-200 bg-indigo-50/40 shadow-xs animate-pulse">
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 rounded-full bg-indigo-600 text-white text-[11px] font-bold flex items-center justify-center">2</div>
                      <span className="text-[12px] font-bold text-indigo-900">Viết blog 1,500 từ</span>
                    </div>
                    <Badge className="bg-indigo-100 text-indigo-700 border-none font-bold text-[10px] px-2 py-0">▶ Đang viết...</Badge>
                  </div>

                  {/* Steps 3,4,5 (Pending) */}
                  {["Tạo 3 ảnh banner", "Tạo 2 bộ ads Facebook", "Lên lịch đăng tuần tới"].map((lbl, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2.5 rounded-xl border border-slate-100 bg-slate-50/50 opacity-60">
                      <div className="flex items-center gap-3">
                        <div className="w-6 h-6 rounded-full bg-slate-200 text-slate-500 text-[11px] font-bold flex items-center justify-center">{idx + 3}</div>
                        <span className="text-[12px] text-slate-500 font-medium">{lbl}</span>
                      </div>
                      <span className="text-[10px] font-bold text-slate-400 pr-2">Chờ</span>
                    </div>
                  ))}
                </div>
                <div className="text-[10px] text-slate-400 pt-1 border-t flex items-center gap-1.5">
                  <span>14:32:08</span><span>•</span><span>Hệ thống đã lập kế hoạch</span>
                </div>
              </div>
            </div>

            {/* Khối 2: Kết quả Thực tế Bước 1 (Research) (Giống y hệt hình 1) */}
            <div className="flex gap-4 items-start">
              <div className="w-9 h-9 rounded-full bg-emerald-500 text-white font-bold text-[14px] flex items-center justify-center shrink-0 shadow-md">✓</div>
              <div className="flex-1 bg-emerald-50/20 border border-emerald-200 rounded-2xl p-5 shadow-xs">
                <div className="flex flex-col gap-1 mb-3">
                  <h4 className="font-bold text-[13px] text-emerald-800">✓ Bước 1 hoàn thành — Research</h4>
                  <p className="text-[12px] text-emerald-700/90 font-medium">Đã tìm được 5 xu hướng AI hot nhất 2025 từ 12 nguồn:</p>
                </div>

                {/* Sub Cards inside Step 1 */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    { title: "Agentic AI", metric: "2.4M mentions" },
                    { title: "Multimodal LLM", metric: "1.8M mentions" },
                    { title: "Edge AI", metric: "980K mentions" },
                  ].map((card, idx) => (
                    <div key={idx} className="bg-white border border-emerald-100 p-3 rounded-xl shadow-xs hover:shadow-sm transition-shadow">
                      <span className="text-[10px] text-slate-300 font-mono block mb-0.5">#{idx + 1}</span>
                      <p className="font-bold text-[12px] text-slate-800 tracking-tight leading-tight mb-1">{card.title}</p>
                      <p className="text-[10px] text-emerald-600 font-medium">{card.metric}</p>
                    </div>
                  ))}
                </div>
                <div className="text-[10px] text-emerald-600/70 mt-3 font-medium">14:32:45 • 40 giây</div>
              </div>
            </div>

            {/* Khối 3: Trạng thái thực thi Bước 2 (Viết blog) (Giống y hệt hình 1) */}
            <div className="flex gap-4 items-start">
              <div className="w-9 h-9 rounded-full bg-indigo-500/20 border border-indigo-400 text-indigo-600 font-bold flex items-center justify-center shrink-0 shadow-xs">
                <FileText size={16} />
              </div>
              <div className="flex-1 border-2 border-indigo-500 bg-white rounded-2xl shadow-sm overflow-hidden">
                <div className="bg-indigo-50/50 border-b border-indigo-100 px-4 py-2.5 flex justify-between items-center">
                  <span className="text-[12px] font-bold text-indigo-900 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-indigo-600 rounded-full animate-ping" />
                    ▶ Bước 2 đang chạy — Viết blog
                  </span>
                  <span className="text-[10px] font-mono font-bold bg-indigo-100/80 px-2 py-0.5 rounded text-indigo-700">1,247/1,500 từ</span>
                </div>
                
                <div className="p-5 space-y-3">
                  <h3 className="font-bold text-[14px] text-slate-800 tracking-tight">5 Xu hướng AI định hình 2025</h3>
                  <p className="text-[12px] text-slate-600 leading-relaxed">
                    Năm 2025 đánh dấu bước ngoặt khi AI không còn chỉ là công cụ hỗ trợ mà trở thành <strong className="text-indigo-600 font-semibold underline decoration-wavy decoration-indigo-300">đồng nghiệp ảo</strong> thực thụ. Dưới đây là 5 xu hướng đang thay đổi ngành công nghiệp...
                  </p>
                  <div className="space-y-1.5 pt-1">
                    <div className="h-1.5 bg-slate-100 rounded-full w-full animate-pulse" />
                    <div className="h-1.5 bg-slate-100 rounded-full w-[85%] animate-pulse" />
                  </div>
                </div>
              </div>
            </div>

            {!isEmpty && (
            <div className="border-t pt-4 space-y-4">
                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Hội thoại bổ sung</p>
                <Conversation>
                <ConversationContent>
                    {messages.map((msg) => (
                    <MessageBranch key={msg.id} defaultBranch={0}>
                        <MessageBranchContent>
                        <Message from={msg.role}>
                            <MessageContent>
                            <MessageResponse>{msg.text}</MessageResponse>
                            </MessageContent>
                        </Message> {/* <--- Đóng sai thứ tự ở đây */}
                        </MessageBranchContent>
                    </MessageBranch>
                    ))}
                </ConversationContent>
                <ConversationScrollButton />
                </Conversation>
            </div>
            )}

          </div>
        </div>

        {/* Bottom Panel (Quick actions & Prompt Input) */}
        <div className="shrink-0 border-t bg-white p-4 shadow-xl">
          <div className="max-w-[800px] mx-auto flex flex-col gap-3">
            
            {/* Quick Chips Action Row (Giống hệt hình 1) */}
            <div className="flex flex-wrap gap-1.5">
              <button onClick={() => setInput("Làm nhanh hơn")} className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors">
                <Sparkles size={12} className="text-amber-500" /> Làm nhanh hơn
              </button>
              <button onClick={() => setInput("Focus vào xu hướng Agentic AI")} className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors">
                <Sparkles size={12} className="text-red-500" /> Focus vào AI Agentic
              </button>
              <button onClick={() => setInput("Dừng bước 3")} className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors">
                ✋ Dừng bước 3
              </button>
              <button onClick={() => setInput("Thêm yêu cầu ")} className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors">
                📎 Thêm yêu cầu
              </button>
            </div>

            {/* Prompt Input Component */}
            <PromptInput
              globalDrop
              multiple
              onSubmit={(m) => {
                if (m.files?.length) toast.success(`${m.files.length} tệp đính kèm`);
                submit(m.text || "Đã gửi tệp đính kèm");
              }}
            >
              <PromptInputHeader><PromptInputAttachmentsDisplay /></PromptInputHeader>
              <PromptInputBody className="border rounded-xl bg-slate-50/50 shadow-inner p-1 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-500">
                <PromptInputTextarea
                  value={input}
                  placeholder="Ra lệnh cho hệ thống... (ví dụ: 'Tập trung vào xu hướng Agentic AI', 'Thêm phần so sánh giá', 'Dừng lại')"
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="min-h-[44px] max-h-[120px] bg-transparent text-[13px] border-none focus-visible:ring-0 shadow-none px-3 py-2 text-slate-800 font-medium"
                />
              </PromptInputBody>
              <PromptInputFooter className="px-1 pt-1 flex justify-between items-center">
                <PromptInputTools className="flex gap-1 items-center">
                  <PromptInputActionMenu>
                    <PromptInputActionMenuTrigger />
                    <PromptInputActionMenuContent>
                      <PromptInputActionAddAttachments />
                    </PromptInputActionMenuContent>
                  </PromptInputActionMenu>

                  <SpeechInput size="icon-sm" variant="ghost" onTranscriptionChange={(t) => setInput((p) => p ? `${p} ${t}` : t)} />

                  <PromptInputButton variant={webSearch ? "default" : "ghost"} onClick={() => setWebSearch((p) => !p)} className="h-8 text-[11px] text-slate-500">
                    <GlobeIcon size={14} className={webSearch ? "text-white" : "text-slate-400"} />
                    <span className="hidden sm:inline ml-1">Tìm kiếm</span>
                  </PromptInputButton>

                  <ModelSelector open={modelOpen} onOpenChange={setModelOpen}>
                    <ModelSelectorTrigger asChild>
                      <PromptInputButton className="h-8 text-[11px] text-slate-500">
                        <ModelSelectorLogo provider={selected.chef.toLowerCase()} className="w-3.5 h-3.5" />
                        <ModelSelectorName className="hidden sm:inline ml-1">{selected.name}</ModelSelectorName>
                      </PromptInputButton>
                    </ModelSelectorTrigger>
                    <ModelSelectorContent>
                      <ModelSelectorInput placeholder="Tìm model..." />
                      <ModelSelectorList>
                        <ModelSelectorEmpty>Không tìm thấy model.</ModelSelectorEmpty>
                        {Array.from(new Set(MODELS.map((m) => m.chef))).map((chef) => (
                          <ModelSelectorGroup heading={chef} key={chef}>
                            {MODELS.filter((m) => m.chef === chef).map((m) => (
                              <ModelSelectorItem key={m.id} value={m.id} onSelect={() => { setModel(m.id); setModelOpen(false); }}>
                                <ModelSelectorLogo provider={m.chef.toLowerCase()} />
                                <ModelSelectorName>{m.name}</ModelSelectorName>
                                {model === m.id ? <CheckIcon className="ml-auto size-4" /> : <div className="ml-auto size-4" />}
                              </ModelSelectorItem>
                            ))}
                          </ModelSelectorGroup>
                        ))}
                      </ModelSelectorList>
                    </ModelSelectorContent>
                  </ModelSelector>
                </PromptInputTools>

                <PromptInputSubmit
                  disabled={!input.trim() || isLoading || !convId}
                  status={submitStatus}
                  onClick={isLoading ? stop : () => submit(input)}
                  className="bg-indigo-600 text-white rounded-xl h-9 w-9 flex items-center justify-center p-0 hover:bg-indigo-700 shadow-md transition-all shrink-0"
                />
              </PromptInputFooter>
            </PromptInput>

            <p className="text-center text-[10px] text-slate-400 font-medium">
              Hệ thống tự động thực thi nhiều bước. Bạn có thể can thiệp bất cứ lúc nào.
            </p>
          </div>
        </div>
      </main>

      {/* ─── 3. INSPECTOR SIDEBAR PHẢI (Trạng thái hệ thống, Logs & Data Source) ─── */}
      <aside className="w-[300px] border-l bg-white hidden xl:flex flex-col shrink-0 overflow-hidden">
        
        {/* Header */}
        <div className="h-14 border-b flex items-center justify-between px-4 shrink-0">
          <span className="text-[13px] font-bold text-slate-800">Trạng thái hệ thống</span>
          <Badge variant="secondary" className="bg-slate-100 text-slate-500 font-mono text-[9px] px-1.5 py-0 border-none">Bước 2</Badge>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-5 flex flex-col min-h-0">
          
          {/* Performance Widget */}
          <Card className="p-3.5 border-slate-100 bg-slate-50/50 shadow-none rounded-xl space-y-3.5 shrink-0">
            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Hiệu năng</p>
            
            <div>
              <div className="flex justify-between text-[11px] font-medium text-slate-600 mb-1">
                <span>CPU</span><span className="font-bold text-slate-800">34%</span>
              </div>
              <Progress value={34} className="h-1.5 bg-slate-200/70 [&>div]:bg-emerald-500" />
            </div>

            <div>
              <div className="flex justify-between text-[11px] font-medium text-slate-600 mb-1">
                <span>Memory</span><span className="font-bold text-slate-800">2.4GB / 8GB</span>
              </div>
              <Progress value={30} className="h-1.5 bg-slate-200/70 [&>div]:bg-indigo-600" />
            </div>

            <div className="pt-2 border-t border-slate-200/60 flex justify-between items-center text-[11px] font-medium text-slate-600">
              <span>Độ trễ API</span>
              <span className="font-mono text-emerald-600 font-bold">1.2s</span>
            </div>
          </Card>

          {/* Running Agents list */}
          <div className="shrink-0">
            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-2">Agent đang chạy</p>
            <div className="space-y-1.5 text-[11px]">
              <div className="flex justify-between items-center"><span className="text-slate-600 font-medium">Writer Agent</span><span className="text-indigo-600 font-bold text-[10px]">Active</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-600 font-medium">Research Agent</span><span className="text-emerald-600 font-bold text-[10px]">Done</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-400">Designer Agent</span><span className="text-slate-400 text-[10px]">Idle</span></div>
              <div className="flex justify-between items-center"><span className="text-slate-400">Ads Agent</span><span className="text-slate-400 text-[10px]">Idle</span></div>
            </div>
          </div>

          {/* Terminal Console Block (NHẬT KÝ THỰC THI) */}
          <div className="flex-1 bg-slate-900 rounded-xl p-3.5 flex flex-col font-mono text-[11px] leading-relaxed overflow-hidden text-slate-300 shadow-inner min-h-[220px]">
            <div className="flex items-center gap-1.5 mb-2.5 text-white font-sans text-[10px] font-bold tracking-wider shrink-0">
              <Terminal size={12} className="text-indigo-400" />
              <span>NHẬT KÝ THỰC THI</span>
            </div>
            
            {/* Scrollable logs contents */}
            <div className="flex-1 overflow-y-auto space-y-1 pr-1 font-mono text-[11px]">
              <p className="text-slate-500">{"[14:32:01] Khởi tạo nhiệm vụ"}</p>
              <p className="text-slate-500">{"[14:32:02] Tải parser"}</p>
              <p className="text-slate-400">{"[14:32:03] ✓ Phân tích intent"}</p>
              <p className="text-emerald-400">{"[14:32:04] ✓ Khóa nguồn dữ liệu"}</p>
              <p className="text-slate-400">{"[14:32:05] Khởi động extractor"}</p>
              <p className="text-slate-300">{"[14:32:06] ✓ Bloomberg API"}</p>
              <p className="text-emerald-400">{"[14:32:07] ✓ Yahoo Finance"}</p>
              <p className="text-amber-400 flex items-start gap-1">
                <AlertTriangle size={11} className="mt-0.5 shrink-0" />
                <span>{"[14:32:08] ⚠ SEC giới hạn tốc độ"}</span>
              </p>
              <p className="text-indigo-400">{"[14:32:12] ▶ Batch 14/21"}</p>
              <p className="text-indigo-400/90 animate-pulse">{"_ Đang xử lý HubSpot..."}</p>
            </div>
          </div>

          {/* Data Sources Section */}
          <div className="shrink-0">
            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-2">Nguồn dữ liệu</p>
            <div className="space-y-1.5">
              <div className="bg-emerald-50/60 border border-emerald-100 rounded-lg px-2.5 py-1.5 flex justify-between items-center text-[11px]">
                <span className="flex items-center gap-1.5 font-bold text-emerald-800"><Database size={12}/> Bloomberg</span>
                <span className="text-[9px] font-bold text-emerald-600">Hoạt động</span>
              </div>
              <div className="bg-emerald-50/60 border border-emerald-100 rounded-lg px-2.5 py-1.5 flex justify-between items-center text-[11px]">
                <span className="flex items-center gap-1.5 font-bold text-emerald-800"><Database size={12}/> Yahoo Finance</span>
                <span className="text-[9px] font-bold text-emerald-600">Hoạt động</span>
              </div>
            </div>
          </div>

        </div>
      </aside>

    </div>
  );
}