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
// ─── Component render từng node như message bubble ─────────────────────────────

function NodeMessageCard({
  nodeId,
  nodeLabel,
  step,
  status,
  text,
  state,
  metrics,
}: {
  nodeId: string;
  nodeLabel: string;
  step: number;
  status: string;
  text: string;
  state: Record<string, unknown>;
  metrics: Record<string, unknown>;
}) {
  const isDone = status === "success" || status === "SUCCESS";
  const isRunning = !isDone && status !== "error";
  
  // Màu theo trạng thái
  const colors = isDone
    ? { bg: "bg-emerald-50/30", border: "border-emerald-200", text: "text-emerald-800", badge: "bg-emerald-100 text-emerald-700" }
    : isRunning
    ? { bg: "bg-indigo-50/30", border: "border-indigo-300", text: "text-indigo-900", badge: "bg-indigo-100 text-indigo-700" }
    : { bg: "bg-red-50/30", border: "border-red-200", text: "text-red-800", badge: "bg-red-100 text-red-700" };

  return (
    <div className={`flex gap-4 items-start w-full ${isRunning ? "animate-pulse" : ""}`}>
      {/* Avatar */}
      <div className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 shadow-md ${
        isDone ? "bg-emerald-500 text-white" :
        isRunning ? "bg-indigo-600 text-white" :
        "bg-red-500 text-white"
      }`}>
        {isDone ? "✓" : isRunning ? <Terminal size={14} /> : "✗"}
      </div>
      
      {/* Bubble */}
      <div className={`flex-1 ${colors.bg} border ${colors.border} rounded-2xl p-5 shadow-sm space-y-3`}>
        {/* Header */}
        <div className="flex justify-between items-center">
          <h4 className={`font-bold text-[13px] ${colors.text}`}>
            {isDone ? "✓" : isRunning ? "▶" : "✗"} Bước {step} {isDone ? "hoàn thành" : isRunning ? "đang chạy" : "lỗi"} — {nodeLabel}
          </h4>
          <Badge className={`${colors.badge} border-none font-bold text-[10px]`}>
            {isDone ? "✓ Xong" : isRunning ? "▶ Đang chạy..." : "✗ Lỗi"}
          </Badge>
        </div>
        
        {/* Content text */}
        {text && text !== "string" && (
          <p className="text-[13px] text-slate-700 leading-relaxed">
            {text}
          </p>
        )}
        
        {/* Special render cho research results (card grid) */}
        {nodeId === "knowledge_base" && isDone && state?.retrieved_chunks && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
            {/* Parse retrieved chunks thành cards */}
            {Array.from({ length: (state.retrieved_chunks as number) || 3 }).map((_, i) => (
              <div key={i} className="bg-white border border-slate-100 p-3 rounded-xl shadow-xs">
                <span className="text-[10px] text-slate-300 font-mono block mb-0.5">#{i + 1}</span>
                <p className="font-bold text-[12px] text-slate-800">Kết quả {i + 1}</p>
                <p className="text-[10px] text-slate-500">Đã truy xuất</p>
              </div>
            ))}
          </div>
        )}
        
        {/* Metrics bar */}
        {Object.keys(metrics).length > 0 && (
          <div className="flex gap-4 pt-2 border-t border-slate-200/60">
            {Object.entries(metrics).map(([k, v]) => (
              <div key={k} className="text-center">
                <p className="text-[9px] text-slate-400 uppercase">{k}</p>
                <p className="text-[13px] font-bold text-slate-800">
                  {typeof v === "number" ? v.toFixed(2) : String(v)}
                </p>
              </div>
            ))}
          </div>
        )}
        
        {/* State toggle (manager kiểm tra) */}
        {Object.keys(state).length > 0 && (
          <details className="mt-2">
            <summary className="text-[10px] text-slate-400 cursor-pointer hover:text-slate-600">
              Chi tiết kiểm tra ({Object.keys(state).length} fields)
            </summary>
            <pre className="text-[10px] text-slate-600 bg-white border border-slate-100 rounded p-2 mt-1 overflow-x-auto">
              {JSON.stringify(state, null, 2)}
            </pre>
          </details>
        )}
        
        {/* Timestamp */}
        <div className="text-[10px] text-slate-400 mt-1">
          {new Date().toLocaleTimeString("vi-VN")} • {nodeId}
        </div>
      </div>
    </div>
  );
}



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
    const { messages, nodes, nodeDetails, suggestions, status, error: streamError, sendMessage, stop, reset } = useChatStream({
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


            {/* ─── Agent Steps — Render từ nodeDetails thật ─── */}
            {nodeDetails.length > 0 && (
              <div className="flex gap-4 items-start">
                <div className="w-9 h-9 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-md">
                  <Terminal size={14} />
                </div>
                <div className="flex-1 bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm space-y-4">
                  <p className="text-[13px] font-medium text-slate-800">
                    Đã phân tích yêu cầu. Tôi sẽ thực hiện <strong className="text-indigo-600 font-bold">{nodeDetails.length} bước</strong>:
                  </p>
                  
                  {/* Danh sách steps */}
                  <div className="space-y-2">
                    {nodeDetails.map((node) => (
                      <div 
                        key={node.node_id} 
                        className={`flex items-center justify-between p-2.5 rounded-xl border transition-all ${
                          node.status === "SUCCESS" ? "border-emerald-100 bg-emerald-50/20" :
                          node.status === "FAILED" ? "border-red-100 bg-red-50/20" :
                          "border-indigo-200 bg-indigo-50/40 shadow-xs"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-6 h-6 rounded-full text-white text-[11px] font-bold flex items-center justify-center ${
                            node.status === "SUCCESS" ? "bg-emerald-500" :
                            node.status === "FAILED" ? "bg-red-500" :
                            "bg-indigo-600"
                          }`}>
                            {node.status === "SUCCESS" ? "✓" : node.step}
                          </div>
                          <span className={`text-[12px] font-medium ${
                            node.status === "SUCCESS" ? "text-slate-700" :
                            node.status === "FAILED" ? "text-red-700" :
                            "text-indigo-900 font-bold"
                          }`}>
                            {node.node_label}
                          </span>
                        </div>
                        <Badge className={`border-none font-bold text-[10px] px-2 py-0 ${
                          node.status === "SUCCESS" ? "bg-emerald-100 text-emerald-700" :
                          node.status === "FAILED" ? "bg-red-100 text-red-700" :
                          "bg-indigo-100 text-indigo-700"
                        }`}>
                          {node.status === "SUCCESS" ? "✓ Xong" :
                           node.status === "FAILED" ? "✗ Lỗi" :
                           "▶ Đang chạy..."}
                        </Badge>
                      </div>
                    ))}
                  </div>

                  {/* ─── Chi tiết từng node cho manager kiểm tra ─── */}
                  <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                      Chi tiết kiểm tra chất lượng
                    </p>
                    
                    {nodeDetails.map((node) => (
                      <div key={`detail-${node.node_id}`} className="border border-slate-100 rounded-lg p-3 bg-slate-50/50">
                        {/* Header */}
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-[11px] font-bold text-slate-700">{node.node_label}</span>
                          <span className="text-[10px] font-mono text-slate-400">Step {node.step} • {node.node_id}</span>
                        </div>
                        
                        {/* Output text */}
                        {node.text && node.text !== "string" && (
                          <div className="mb-2">
                            <p className="text-[9px] font-bold text-slate-400 uppercase mb-0.5">Output</p>
                            <p className="text-[11px] text-slate-700 bg-white border border-slate-100 rounded p-1.5 max-h-24 overflow-y-auto">
                              {node.text}
                            </p>
                          </div>
                        )}
                        
                        {/* State */}
                        {Object.keys(node.state).length > 0 && (
                          <div className="mb-2">
                            <p className="text-[9px] font-bold text-slate-400 uppercase mb-0.5">State</p>
                            <pre className="text-[10px] text-slate-600 bg-white border border-slate-100 rounded p-1.5 overflow-x-auto">
                              {JSON.stringify(node.state, null, 2)}
                            </pre>
                          </div>
                        )}
                        
                        {/* Metrics */}
                        {Object.keys(node.metrics).length > 0 && (
                          <div>
                            <p className="text-[9px] font-bold text-slate-400 uppercase mb-0.5">Metrics</p>
                            <pre className="text-[10px] text-slate-600 bg-white border border-slate-100 rounded p-1.5 overflow-x-auto">
                              {JSON.stringify(node.metrics, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}


            {!isEmpty && (
            <div className="border-t pt-4 space-y-4">
                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Hội thoại bổ sung</p>
                                <Conversation>
                  <ConversationContent>
                    {messages.map((msg) => (
                      <MessageBranch key={msg.id} defaultBranch={0}>
                        <MessageBranchContent>
                          {msg.role === "user" ? (
                            // User message giữ nguyên
                            <Message from="user">
                              <MessageContent>
                                <MessageResponse>{msg.text}</MessageResponse>
                              </MessageContent>
                            </Message>
                          ) : msg.result?.node_id ? (
                            // Node detail message — render theo loại node
                            <NodeMessageCard 
                              nodeId={msg.result.node_id as string}
                              nodeLabel={msg.result.node_label as string}
                              step={msg.result.step as number}
                              status={(msg.result as any).status || "streaming"}
                              text={msg.text}
                              state={(msg.result as any).state || {}}
                              metrics={(msg.result as any).metrics || {}}
                            />
                          ) : (
                            // Final result message
                            <Message from="assistant">
                              <MessageContent>
                                <MessageResponse>{msg.text}</MessageResponse>
                              </MessageContent>
                            </Message>
                          )}
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