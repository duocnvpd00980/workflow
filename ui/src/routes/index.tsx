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
  ModelSelectorList, ModelSelectorLogo, ModelSelectorName, ModelSelectorTrigger,
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
  Pause, Square, LogOut, Terminal, Database, Sparkles, AlertTriangle,
  Save,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import type { Conv } from "../lib/api";
import { API_BASE_URL, createConversation, fetchConversations, queryKeys } from "../lib/api";
import { useChatStream } from "../hooks/useChatStream";
import type { NodeDetail } from "../hooks/useChatStream";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { createFileRoute } from "@tanstack/react-router";
import SidebarNav from "@/components/layout/navbar";

// ─── Constants ────────────────────────────────────────────────────────────────

const SESSION_ID = "web-ui";

const MODELS = [
  { id: "gpt-4o",            name: "GPT-4o",           chef: "OpenAI"    },
  { id: "claude-sonnet-4",   name: "Claude 4 Sonnet",  chef: "Anthropic" },
  { id: "gemini-2.0-flash",  name: "Gemini 2.0 Flash", chef: "Google"    },
] as const;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1)  return "vừa xong";
  if (m < 60) return `${m} phút trước`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} giờ trước`;
  return new Date(iso).toLocaleDateString("vi-VN");
}

// ─── Sub-components ───────────────────────────────────────────────────────────

const AttachmentItem = ({
  a,
  onRemove,
}: {
  a: { id: string; name?: string; type?: string; url?: string };
  onRemove: (id: string) => void;
}) => (
  <Attachment data={{ ...a, mediaType: a.type ?? "unknown" } as any} onRemove={() => onRemove(a.id)}>
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

// ─── Node status helpers ──────────────────────────────────────────────────────

const nodeStatusClass = (status: string) => {
  if (status === "SUCCESS") return {
    row:   "border-emerald-100 bg-emerald-50/20",
    dot:   "bg-emerald-500",
    text:  "text-slate-700",
    badge: "bg-emerald-100 text-emerald-700",
  };
  if (status === "FAILED") return {
    row:   "border-red-100 bg-red-50/20",
    dot:   "bg-red-500",
    text:  "text-red-700",
    badge: "bg-red-100 text-red-700",
  };
  return {
    row:   "border-indigo-200 bg-indigo-50/40 shadow-xs",
    dot:   "bg-indigo-600",
    text:  "text-indigo-900 font-bold",
    badge: "bg-indigo-100 text-indigo-700",
  };
};

const nodeStatusLabel = (status: string) =>
  status === "SUCCESS" ? "✓ Xong" : status === "FAILED" ? "✗ Lỗi" : "▶ Đang chạy...";

const nodeStatusIcon = (status: string) =>
  status === "SUCCESS" ? "✓" : status === "FAILED" ? "✗" : "•";

// ─── NodeDetailPanel ──────────────────────────────────────────────────────────

function NodeDetailPanel({ nodes }: { nodes: NodeDetail[] }) {
  if (!nodes.length) return null;

  return (
    <div className="flex gap-4 items-start">
      <div className="w-9 h-9 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-md">
        <Terminal size={14} />
      </div>

      <div className="flex-1 bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm space-y-4">
        <p className="text-[13px] font-medium text-slate-800">
          Đã phân tích yêu cầu. Thực hiện{" "}
          <strong className="text-indigo-600 font-bold">{nodes.length} bước</strong>:
        </p>

        <div className="space-y-2">
          {nodes.map((node) => {
            const cls = nodeStatusClass(node.status);
            return (
              <div
                key={node.node_id}
                className={`flex items-center justify-between p-2.5 rounded-xl border transition-all ${cls.row}`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-6 h-6 rounded-full text-white text-[11px] font-bold flex items-center justify-center ${cls.dot}`}>
                    {nodeStatusIcon(node.status)}
                  </div>
                  <span className={`text-[12px] font-medium ${cls.text}`}>{node.node_label}</span>
                </div>
                <Badge className={`border-none font-bold text-[10px] px-2 py-0 ${cls.badge}`}>
                  {nodeStatusLabel(node.status)}
                </Badge>
              </div>
            );
          })}
        </div>

        <div className="border-t border-slate-100 pt-4 space-y-3">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Chi tiết kiểm tra chất lượng
          </p>

          {nodes.map((node) => (
            <div key={`detail-${node.node_id}`} className="border border-slate-100 rounded-lg p-3 bg-slate-50/50">
              <div className="flex justify-between items-center mb-2">
                <span className="text-[11px] font-bold text-slate-700">{node.node_label}</span>
                <span className="text-[10px] font-mono text-slate-400">
                  Step {node.step} • {node.node_id}
                </span>
              </div>

              {node.text && node.text !== "string" && (
                <div className="mb-2">
                  <p className="text-[9px] font-bold text-slate-400 uppercase mb-0.5">Output</p>
                  <p className="text-[11px] text-slate-700 bg-white border border-slate-100 rounded p-1.5 max-h-24 overflow-y-auto">
                    {node.text}
                  </p>
                </div>
              )}

              {Object.keys(node.state).length > 0 && (
                <div className="mb-2">
                  <p className="text-[9px] font-bold text-slate-400 uppercase mb-0.5">State</p>
                  <pre className="text-[10px] text-slate-600 bg-white border border-slate-100 rounded p-1.5 overflow-x-auto">
                    {JSON.stringify(node.state, null, 2)}
                  </pre>
                </div>
              )}

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
  );
}

// ─── Route ────────────────────────────────────────────────────────────────────

export const Route = createFileRoute("/")({ component: ChatPage });

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const queryClient = useQueryClient();

  const [model, setModel]           = useState(MODELS[0].id);
  const [modelOpen, setModelOpen]   = useState(false);
  const [webSearch, setWebSearch]   = useState(false);
  const [input, setInput]           = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [convId, setConvId]         = useState<string | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Guard: prevent double-creating a conversation on mount
  const initDone = useRef(false);

  // ── Data fetching ──────────────────────────────────────────────────────────

  const {
    data: conversations = [],
    isLoading: convsLoading,
    isError: convsError,
  } = useQuery<Conv[]>({
    queryKey: queryKeys.conversations,
    queryFn:  fetchConversations,
    staleTime: 0,
    refetchOnWindowFocus: true,
  });

  const { data: historyData } = useQuery({
    queryKey: ["conversation", convId],
    enabled:  !!convId,
    staleTime: 30_000,
    queryFn:  async () => {
      const r = await fetch(`${API_BASE_URL}/chat/conversations/${convId}`);
      if (!r.ok) throw new Error("Không tải được lịch sử hội thoại");
      return r.json();
    },
  });

  const createConvMutation = useMutation({
    mutationFn: createConversation,
    onSuccess: (id) => {
      setConvId(id);
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations });
    },
    onError: () => toast.error("Không thể tạo cuộc trò chuyện"),
  });

  // ── Stream ─────────────────────────────────────────────────────────────────

  const {
    messages, nodes, nodeDetails, suggestions,
    status, error: streamError,
    sendMessage, stop, reset, hydrate,
  } = useChatStream({
    api:            `${API_BASE_URL}/chat/stream`,
    sessionId:      SESSION_ID,
    conversationId: convId ?? "",
  });

  // ── Init: pick latest conv or create new ──────────────────────────────────
  //
  // Runs once when conversations list finishes loading.
  // - Has existing convs → select the most recent one (index 0, already sorted desc)
  // - Empty list         → create a brand-new conversation
  //
  // The `initDone` ref prevents this from firing again when the query
  // re-fetches after a new conv is created (invalidateQueries above).

  useEffect(() => {
    if (convsLoading || initDone.current) return;
    initDone.current = true;

    if (conversations.length > 0) {
      setConvId(conversations[0].id);
    } else {
      createConvMutation.mutate();
    }
  }, [convsLoading, conversations]);

  // ── Surface stream errors ──────────────────────────────────────────────────

  useEffect(() => {
    if (streamError) toast.error(streamError);
  }, [streamError]);

  // ── Hydrate messages when switching conversations ──────────────────────────

  useEffect(() => {
    if (!historyData?.messages) return;
    if (status === "streaming") return;
    const mapped = historyData.messages.map((m: any) => ({
      ...m,
      id:   m.id   ?? crypto.randomUUID(),
      text: m.text ?? m.content ?? "",
    }));
    hydrate(mapped);
    setIsLoadingHistory(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historyData]);

  // ── Derived ────────────────────────────────────────────────────────────────

  const isLoading  = status === "streaming";
  const selected   = useMemo(() => MODELS.find((m) => m.id === model) ?? MODELS[0], [model]);
  const activeTitle = conversations.find((c) => c.id === convId)?.title ?? "Cuộc trò chuyện mới";
  const isEmpty    = messages.length === 0 && !isLoading && !isLoadingHistory;

  // ── Handlers ───────────────────────────────────────────────────────────────

  const submit = useCallback((text: string) => {
    if (!text.trim() || isLoading || !convId) return;
    setInput("");
    sendMessage(text);
  }, [isLoading, sendMessage, convId]);

  const selectConv = useCallback((id: string) => {
    if (id === convId) return;          // already active — no-op
    reset();
    setConvId(id);
    setInput("");
    setIsLoadingHistory(true);
  }, [convId, reset]);

  const newChat = useCallback(() => {
    reset();
    setInput("");
    initDone.current = true;            // prevent init effect from firing again
    createConvMutation.mutate();
  }, [reset, createConvMutation]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(input);
    }
  }, [input, submit]);

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#fafbfc] text-slate-900 select-none antialiased font-sans">

      {/* ── Left Sidebar ── */}
      <aside className={`fixed inset-y-0 left-0 z-30 flex w-[260px] flex-col border-r bg-white transition-transform duration-200 md:relative md:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <SidebarNav />

        <div className="flex-1 overflow-y-auto px-3 py-4 flex flex-col min-h-0">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1 mb-2.5">
            Công việc đang chạy
          </p>

          <div className="space-y-2">
            {convsLoading && (
              <div className="p-3 text-[11px] text-slate-400">Đang tải...</div>
            )}
            {convsError && (
              <div className="p-3 text-[11px] text-red-500">Không tải được dữ liệu</div>
            )}
            {!convsLoading && !convsError && conversations.slice(0, 20).map((c, i) => {
              const progress = [60, 34, 12][i] ?? 12;
              const active   = convId === c.id;
              const title    = c.title?.trim() || `Chat ${c.id.slice(0, 8)}`;

              return (
                <div
                  key={c.id}
                  onClick={() => selectConv(c.id)}
                  className={`p-3 rounded-xl bg-white cursor-pointer transition-all ${active ? "border-2 border-indigo-500 shadow-sm" : "border border-slate-100 hover:border-slate-200"}`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className={`text-[12px] font-bold truncate pr-2 ${active ? "text-slate-800" : "text-slate-700"}`}>
                      {title}
                    </span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md shrink-0 ${active ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-600"}`}>
                      {progress}%
                    </span>
                  </div>
                  <Progress value={progress} className={`${active ? "h-1.5 [&>div]:bg-indigo-600" : "h-1 [&>div]:bg-slate-400"}`} />
                  <div className="flex justify-between items-center text-[10px] text-slate-400 mt-2 font-medium">
                    <span>{active ? "Đang hoạt động" : "Cuộc trò chuyện"}</span>
                    <span>{relativeTime(c.last_message_at)}</span>
                  </div>
                </div>
              );
            })}

            {!convsLoading && !convsError && conversations.length === 0 && (
              <div className="p-3 text-[11px] text-slate-400 text-center">
                Chưa có cuộc trò chuyện nào
              </div>
            )}
          </div>
        </div>

        {/* User row */}
        <div className="border-t p-3 shrink-0 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-[11px] font-bold shrink-0">TH</div>
            <span className="text-[13px] font-medium text-slate-700 truncate">Thành</span>
          </div>
          <button
            onClick={newChat}
            disabled={createConvMutation.isPending}
            title="Tạo Session mới"
            className="p-1.5 hover:bg-slate-200/60 text-slate-400 hover:text-slate-600 rounded-md transition-colors disabled:opacity-40"
          >
            <MessageSquarePlus size={16} />
          </button>
        </div>
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-slate-900/20 backdrop-blur-xs md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── Main Content ── */}
      <main className="flex-1 flex flex-col min-w-0 bg-slate-50/60 overflow-hidden relative">

        {/* Header */}
        <header className="h-14 bg-white border-b flex items-center justify-between px-6 shrink-0 z-10 shadow-xs">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-1.5 -ml-1.5 hover:bg-slate-100 rounded-md text-slate-500 md:hidden shrink-0"
            >
              <MenuIcon size={18} />
            </button>
            <h2 className="font-bold text-[15px] text-slate-800 truncate">{activeTitle}</h2>
            <div className="h-4 w-px bg-slate-200 hidden sm:block shrink-0" />
            <div className="items-center gap-2 hidden sm:flex text-[11px] text-slate-500 min-w-0">
              <span className={`w-2 h-2 rounded-full shrink-0 ${isLoading ? "bg-indigo-500 animate-pulse" : "bg-emerald-400"}`} />
              <span className="truncate">
                {isLoading ? "Agent đang xử lý..." : "Sẵn sàng • Bạn có thể can thiệp"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Button variant="outline" size="sm" className="h-8 text-[11px] border-slate-200 text-slate-600 bg-white shadow-xs hover:bg-slate-50">
              <LogOut size={12} className="mr-1 rotate-180" /> Xuất
            </Button>
            <Button
              variant="outline" size="sm"
              className="h-8 text-[11px] border-amber-200 text-amber-700 bg-amber-50/40 shadow-xs hover:bg-amber-50"
              onClick={stop}
              disabled={!isLoading}
            >
              <Pause size={12} className="mr-1 fill-current" /> Tạm dừng
            </Button>
            <Button
              variant="outline" size="sm"
              className="h-8 text-[11px] border-red-200 text-red-600 bg-red-50/40 shadow-xs hover:bg-red-50"
              onClick={stop}
              disabled={!isLoading}
            >
              <Square size={12} className="mr-1 fill-current" /> Dừng hẳn
            </Button>
            <Button
              onClick={newChat}
              disabled={createConvMutation.isPending}
              className="h-8 px-3 text-[11px] bg-indigo-600 hover:bg-indigo-700 shadow-xs disabled:opacity-60"
            >
              <Save size={13} /> Chat mới
            </Button>
          </div>
        </header>

        {/* Workspace */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="max-w-[800px] mx-auto space-y-6">

            {/* Node pipeline panel */}
            <NodeDetailPanel nodes={nodeDetails} />

            {/* Loading history state */}
            {isLoadingHistory && (
              <div className="flex items-center justify-center py-12 text-[13px] text-slate-400">
                <span className="animate-pulse">Đang tải lịch sử hội thoại...</span>
              </div>
            )}

            {/* Empty state */}
            {isEmpty && !isLoadingHistory && (
              <div className="flex flex-col items-center justify-center py-20 text-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center">
                  <Sparkles size={20} className="text-indigo-400" />
                </div>
                <p className="text-[15px] font-semibold text-slate-700">Bắt đầu cuộc trò chuyện</p>
                <p className="text-[13px] text-slate-400 max-w-xs">
                  Nhập câu hỏi hoặc lệnh bên dưới để agent bắt đầu làm việc
                </p>
              </div>
            )}

            {/* Conversation */}
            {!isEmpty && !isLoadingHistory && (
              <div className="border-t pt-4 space-y-4">
                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Hội thoại</p>
                <Conversation key={convId}>
                  <ConversationContent>
                    {messages.map((msg) => (
                      <MessageBranch key={msg.id} defaultBranch={0}>
                        <MessageBranchContent>
                          <Message from={msg.role === "user" ? "user" : "assistant"}>
                            <MessageContent>
                              <MessageResponse>{msg.text}</MessageResponse>
                            </MessageContent>
                          </Message>
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

        {/* Bottom Input Panel */}
        <div className="shrink-0 border-t bg-white p-4 shadow-xl">
          <div className="max-w-[800px] mx-auto flex flex-col gap-3">

            {/* Quick chips */}
            <div className="flex flex-wrap gap-1.5">
              {[
                { icon: <Sparkles size={12} className="text-amber-500" />, label: "Làm nhanh hơn" },
                { icon: <Sparkles size={12} className="text-red-500"   />, label: "Focus vào AI Agentic" },
                { icon: <span>✋</span>,                                    label: "Dừng bước 3" },
                { icon: <span>📎</span>,                                    label: "Thêm yêu cầu" },
              ].map(({ icon, label }) => (
                <button
                  key={label}
                  onClick={() => setInput(label)}
                  className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors"
                >
                  {icon} {label}
                </button>
              ))}
            </div>

            {/* Prompt input */}
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
                  placeholder={convId ? "Ra lệnh cho hệ thống..." : "Đang khởi tạo..."}
                  disabled={!convId || createConvMutation.isPending}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="min-h-[44px] max-h-[120px] bg-transparent text-[13px] border-none focus-visible:ring-0 shadow-none px-3 py-2 text-slate-800 font-medium disabled:opacity-50"
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

                  <SpeechInput
                    size="icon-sm"
                    variant="ghost"
                    onTranscriptionChange={(t) => setInput((p) => p ? `${p} ${t}` : t)}
                  />

                  <PromptInputButton
                    variant={webSearch ? "default" : "ghost"}
                    onClick={() => setWebSearch((p) => !p)}
                    className="h-8 text-[11px] text-slate-500"
                  >
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
                              <ModelSelectorItem
                                key={m.id}
                                value={m.id}
                                onSelect={() => { setModel(m.id); setModelOpen(false); }}
                              >
                                <ModelSelectorLogo provider={m.chef.toLowerCase()} />
                                <ModelSelectorName>{m.name}</ModelSelectorName>
                                {model === m.id
                                  ? <CheckIcon className="ml-auto size-4" />
                                  : <div className="ml-auto size-4" />
                                }
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
                  status={isLoading ? "streaming" : "ready"}
                  onClick={isLoading ? stop : () => submit(input)}
                  className="bg-indigo-600 text-white rounded-xl h-9 w-9 flex items-center justify-center p-0 hover:bg-indigo-700 shadow-md transition-all shrink-0 disabled:opacity-40"
                />
              </PromptInputFooter>
            </PromptInput>

            <p className="text-center text-[10px] text-slate-400 font-medium">
              Hệ thống tự động thực thi nhiều bước. Bạn có thể can thiệp bất cứ lúc nào.
            </p>
          </div>
        </div>
      </main>

      {/* ── Right Inspector Sidebar ── */}
      <aside className="w-[300px] border-l bg-white hidden xl:flex flex-col shrink-0 overflow-hidden">
        <div className="h-14 border-b flex items-center justify-between px-4 shrink-0">
          <span className="text-[13px] font-bold text-slate-800">Trạng thái hệ thống</span>
          <Badge variant="secondary" className="bg-slate-100 text-slate-500 font-mono text-[9px] px-1.5 py-0 border-none">
            {isLoading ? "Đang chạy" : "Chờ"}
          </Badge>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-5 flex flex-col min-h-0">

          {/* Performance */}
          <Card className="p-3.5 border-slate-100 bg-slate-50/50 shadow-none rounded-xl space-y-3.5 shrink-0">
            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Hiệu năng</p>
            {[
              { label: "CPU",    value: "34%",        progress: 34, color: "[&>div]:bg-emerald-500" },
              { label: "Memory", value: "2.4GB / 8GB", progress: 30, color: "[&>div]:bg-indigo-600"  },
            ].map(({ label, value, progress, color }) => (
              <div key={label}>
                <div className="flex justify-between text-[11px] font-medium text-slate-600 mb-1">
                  <span>{label}</span><span className="font-bold text-slate-800">{value}</span>
                </div>
                <Progress value={progress} className={`h-1.5 bg-slate-200/70 ${color}`} />
              </div>
            ))}
            <div className="pt-2 border-t border-slate-200/60 flex justify-between items-center text-[11px] font-medium text-slate-600">
              <span>Độ trễ API</span>
              <span className="font-mono text-emerald-600 font-bold">1.2s</span>
            </div>
          </Card>

          {/* Running Agents */}
          <div className="shrink-0">
            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-2">Agent đang chạy</p>
            <div className="space-y-1.5 text-[11px]">
              {[
                { name: "Writer Agent",   status: "Active", color: "text-indigo-600" },
                { name: "Research Agent", status: "Done",   color: "text-emerald-600" },
                { name: "Designer Agent", status: "Idle",   color: "text-slate-400" },
                { name: "Ads Agent",      status: "Idle",   color: "text-slate-400" },
              ].map(({ name, status, color }) => (
                <div key={name} className="flex justify-between items-center">
                  <span className={status === "Idle" ? "text-slate-400" : "text-slate-600 font-medium"}>{name}</span>
                  <span className={`font-bold text-[10px] ${color}`}>{status}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Terminal log */}
          <div className="flex-1 bg-slate-900 rounded-xl p-3.5 flex flex-col font-mono text-[11px] leading-relaxed overflow-hidden text-slate-300 shadow-inner min-h-[220px]">
            <div className="flex items-center gap-1.5 mb-2.5 text-white font-sans text-[10px] font-bold tracking-wider shrink-0">
              <Terminal size={12} className="text-indigo-400" />
              <span>NHẬT KÝ THỰC THI</span>
            </div>
            <div className="flex-1 overflow-y-auto space-y-1 pr-1">
              {[
                { time: "14:32:01", msg: "Khởi tạo nhiệm vụ",     color: "text-slate-500" },
                { time: "14:32:02", msg: "Tải parser",             color: "text-slate-500" },
                { time: "14:32:03", msg: "✓ Phân tích intent",     color: "text-slate-400" },
                { time: "14:32:04", msg: "✓ Khóa nguồn dữ liệu",  color: "text-emerald-400" },
                { time: "14:32:05", msg: "Khởi động extractor",    color: "text-slate-400" },
                { time: "14:32:06", msg: "✓ Bloomberg API",        color: "text-slate-300" },
                { time: "14:32:07", msg: "✓ Yahoo Finance",        color: "text-emerald-400" },
              ].map(({ time, msg, color }) => (
                <p key={time} className={color}>{`[${time}] ${msg}`}</p>
              ))}
              <p className="text-amber-400 flex items-start gap-1">
                <AlertTriangle size={11} className="mt-0.5 shrink-0" />
                <span>[14:32:08] ⚠ SEC giới hạn tốc độ</span>
              </p>
              <p className="text-indigo-400">[14:32:12] ▶ Batch 14/21</p>
              <p className="text-indigo-400/90 animate-pulse">_ Đang xử lý HubSpot...</p>
            </div>
          </div>

          {/* Data Sources */}
          <div className="shrink-0">
            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-2">Nguồn dữ liệu</p>
            <div className="space-y-1.5">
              {["Bloomberg", "Yahoo Finance"].map((src) => (
                <div key={src} className="bg-emerald-50/60 border border-emerald-100 rounded-lg px-2.5 py-1.5 flex justify-between items-center text-[11px]">
                  <span className="flex items-center gap-1.5 font-bold text-emerald-800">
                    <Database size={12} /> {src}
                  </span>
                  <span className="text-[9px] font-bold text-emerald-600">Hoạt động</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}