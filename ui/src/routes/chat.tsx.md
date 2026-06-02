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
  ModelSelectorList, ModelSelectorLogo, ModelSelectorLogoGroup,
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
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckIcon, GlobeIcon, MessageSquarePlus, MenuIcon, XIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import type { Conv } from "./lib/api";
import { API_BASE_URL, createConversation, fetchConversations, queryKeys } from "./lib/api";
import { useChatStream, PIPELINE_STEPS } from "./hooks/useChatStream";

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

// ─── Sub-components ───────────────────────────────────────────────────────────

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

// ─── Pipeline Progress Bar ────────────────────────────────────────────────────

function PipelineProgress({ nodes, isStreaming }: {
  nodes: { label: string; step: number }[];
  isStreaming: boolean;
}) {
  const entries = Object.entries(PIPELINE_STEPS);
  const lastStep = nodes.length > 0 ? nodes[nodes.length - 1].step : 0;

  return (
    // max-w phải bằng max-w của msg-wrap bên trên (max-w-[720px])
    <div className="w-full max-w-[720px] mx-auto px-4 pb-2">
      <div className="flex items-start">
        {entries.map(([stepKey, defaultLabel], idx) => {
          const step    = Number(stepKey);
          const node    = nodes.find((n) => n.step === step);
          const label   = node?.label ?? defaultLabel;
          const isDone  = !!node && (!isStreaming || lastStep > step);
          const isActive = isStreaming && lastStep === step;
          const isLast  = idx === entries.length - 1;

          return (
            <div key={step} className="flex items-start flex-1 min-w-0">
              {/* Circle + label */}
              <div className="flex flex-col items-center gap-1 shrink-0">
                <div className={[
                  "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-medium border transition-all duration-300",
                  isDone  ? "bg-foreground text-background border-foreground"
                  : isActive ? "bg-muted border-foreground text-foreground animate-pulse"
                  : "bg-background border-border text-muted-foreground",
                ].join(" ")}>
                  {isDone ? "✓" : step}
                </div>
                <span className={[
                  "text-[10px] text-center leading-tight px-0.5 whitespace-nowrap",
                  isDone || isActive ? "text-foreground font-medium" : "text-muted-foreground",
                ].join(" ")}>
                  {label}
                </span>
              </div>

              {/* Connector */}
              {!isLast && (
                <div className={[
                  "h-px flex-1 mx-1 mt-[9px] transition-all duration-500",
                  isDone ? "bg-foreground" : "bg-border",
                ].join(" ")} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function EmptyState({ onSuggest }: { onSuggest: (s: string) => void }) {
  const defaults = [
    "Xu hướng AI mới nhất là gì?",
    "Machine learning hoạt động như thế nào?",
    "Giải thích quantum computing",
    "Best practices cho React",
  ];
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4 py-8 text-center">
      <MessageSquarePlus size={32} className="text-muted-foreground" />
      <div>
        <p className="text-base font-medium">Bắt đầu cuộc trò chuyện</p>
        <p className="mt-1 text-sm text-muted-foreground">Hỏi bất cứ điều gì bạn muốn biết</p>
      </div>
      <div className="flex flex-wrap justify-center gap-2 mt-1">
        {defaults.map((s) => (
          <button
            key={s}
            onClick={() => onSuggest(s)}
            className="px-3 py-1.5 text-xs border border-border rounded-md bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({
  conversations, convId, onNew, onSelect, open, onClose,
}: {
  conversations: Conv[];
  convId: string | null;
  onNew: () => void;
  onSelect: (id: string) => void;
  open: boolean;
  onClose: () => void;
}) {
  const groups = useMemo(() => groupConvsByDate(conversations), [conversations]);

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-20 bg-black/40 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <aside className={[
        // base
        "fixed inset-y-0 left-0 z-30 flex flex-col border-r bg-muted/40",
        "transition-transform duration-200",
        // mobile: slide in/out
        open ? "translate-x-0" : "-translate-x-full",
        // md+: always visible, static
        "md:relative md:z-auto md:translate-x-0",
        // width: 260px desktop, 220px tablet, 260px mobile drawer
        "w-[260px] md:w-[220px] lg:w-[260px]",
      ].join(" ")}>

        {/* Header */}
        <div className="flex h-[52px] items-center gap-2 border-b px-3 shrink-0">
          <span className="flex-1 text-[15px] font-medium">Chat</span>
          <button
            onClick={onNew}
            title="Chat mới"
            className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-background text-muted-foreground hover:bg-accent transition-colors shrink-0"
          >
            <MessageSquarePlus size={15} />
          </button>
          {/* Close button — mobile only */}
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent transition-colors md:hidden shrink-0"
          >
            <XIcon size={15} />
          </button>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
          {groups.map((g) => (
            <div key={g.label}>
              <p className="px-2 pb-1 pt-2 text-[11px] uppercase tracking-wider text-muted-foreground/60 font-medium">
                {g.label}
              </p>
              {g.items.map((c) => (
                <button
                  key={c.id}
                  onClick={() => { onSelect(c.id); onClose(); }}
                  className={[
                    "w-full text-left rounded-md px-2.5 py-2 mb-px transition-colors",
                    convId === c.id
                      ? "bg-background border border-border/60 shadow-none"
                      : "hover:bg-background/60",
                  ].join(" ")}
                >
                  <div className="truncate text-[13px] font-medium">{c.title}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">
                    {relativeTime(c.last_message_at)}
                  </div>
                </button>
              ))}
            </div>
          ))}
        </div>

        {/* Footer — user row */}
        <div className="border-t px-2 py-2.5 shrink-0">
          <div className="flex items-center gap-2 rounded-md px-2 py-1.5 cursor-pointer hover:bg-background/60 transition-colors">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-[11px] font-medium shrink-0">
              TH
            </div>
            <span className="flex-1 text-[13px] font-medium truncate">Thành</span>
          </div>
        </div>
      </aside>
    </>
  );
}

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

  // Khởi tạo conversation lần đầu
  useEffect(() => { createConvMutation.mutate(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
  const activeTitle  = conversations.find((c) => c.id === convId)?.title ?? "Chat";
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

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar
        conversations={conversations}
        convId={convId}
        onNew={newChat}
        onSelect={selectConv}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* ── Main ── */}
      <div className="relative flex flex-1 flex-col overflow-hidden min-w-0">

        {/* Mobile topbar — hidden md+ */}
        <div className="flex h-[52px] items-center gap-2.5 border-b px-3 md:hidden shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-muted transition-colors"
          >
            <MenuIcon size={18} />
          </button>
          <span className="flex-1 text-sm font-medium truncate">{activeTitle}</span>
          <button
            onClick={newChat}
            className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-muted transition-colors"
          >
            <MessageSquarePlus size={16} />
          </button>
        </div>

        {/* ── Conversation area ── */}
        <div className="flex-1 overflow-hidden relative">
          {isEmpty ? (
            <EmptyState onSuggest={(s) => { setInput(s); }} />
          ) : (
            <Conversation>
              <ConversationContent>
                {messages.map((msg) => (
                  <MessageBranch key={msg.id} defaultBranch={0}>
                    <MessageBranchContent>
                      <Message from={msg.role}>
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
          )}
        </div>

        {/* ── Bottom area: pipeline + suggestions + input ── */}
        <div className="shrink-0 border-t">

          {/* Pipeline progress bar — visible while streaming or just finished */}
          {(isLoading || nodes.length > 0) && (
            <div className="pt-3">
              <PipelineProgress nodes={nodes} isStreaming={isLoading} />
            </div>
          )}

          {/* Suggestions — dynamic from backend, hidden while streaming */}
          {!isLoading && suggestions.length > 0 && (
            <div className="px-4 pt-2">
              <Suggestions>
                {suggestions.map((s) => (
                  <Suggestion key={s} suggestion={s} onClick={() => submit(s)} />
                ))}
              </Suggestions>
            </div>
          )}

          {/* Input box */}
          <div className="px-3 pb-3 pt-2 md:px-4 md:pb-4">
            <div className="max-w-[720px] mx-auto">
              <PromptInput
                globalDrop
                multiple
                onSubmit={(m) => {
                  if (m.files?.length) toast.success(`${m.files.length} tệp đính kèm`);
                  submit(m.text || "Đã gửi tệp đính kèm");
                }}
              >
                <PromptInputHeader><PromptInputAttachmentsDisplay /></PromptInputHeader>
                <PromptInputBody>
                  <PromptInputTextarea
                    value={input}
                    placeholder="Nhắn tin..."
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                  />
                </PromptInputBody>
                <PromptInputFooter>
                  <PromptInputTools>
                    {/* Attachment */}
                    <PromptInputActionMenu>
                      <PromptInputActionMenuTrigger />
                      <PromptInputActionMenuContent>
                        <PromptInputActionAddAttachments />
                      </PromptInputActionMenuContent>
                    </PromptInputActionMenu>

                    {/* Speech */}
                    <SpeechInput
                      size="icon-sm"
                      variant="ghost"
                      onTranscriptionChange={(t) => setInput((p) => p ? `${p} ${t}` : t)}
                    />

                    {/* Web search toggle */}
                    <PromptInputButton
                      variant={webSearch ? "default" : "ghost"}
                      onClick={() => setWebSearch((p) => !p)}
                    >
                      <GlobeIcon size={15} />
                      <span className="hidden sm:inline text-xs">Tìm kiếm</span>
                    </PromptInputButton>

                    {/* Model selector */}
                    <ModelSelector open={modelOpen} onOpenChange={setModelOpen}>
                      <ModelSelectorTrigger asChild>
                        <PromptInputButton>
                          <ModelSelectorLogo provider={selected.chef.toLowerCase()} />
                          <ModelSelectorName className="hidden sm:inline text-xs">
                            {selected.name}
                          </ModelSelectorName>
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
                                  <ModelSelectorLogoGroup>
                                    {m.providers.map((p) => <ModelSelectorLogo key={p} provider={p} />)}
                                  </ModelSelectorLogoGroup>
                                  {model === m.id
                                    ? <CheckIcon className="ml-auto size-4" />
                                    : <div className="ml-auto size-4" />}
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
                  />
                </PromptInputFooter>
              </PromptInput>

              {/* Hint */}
              <p className="mt-2 text-center text-[11px] text-muted-foreground">
                AI có thể mắc lỗi. Hãy kiểm tra thông tin quan trọng.
              </p>
            </div>
          </div>
        </div>

      </div>{/* /main */}
    </div>
  );
}