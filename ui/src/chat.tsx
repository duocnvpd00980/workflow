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
import { CheckIcon, GlobeIcon, MenuIcon, MessageSquarePlus, XIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

// ─── Config ───────────────────────────────────────────────────────────────────

const API        = "http://localhost:8000/api/v1";
const SESSION_ID = "web-ui";

const SUGGESTIONS = [
  "What are the latest trends in AI?",
  "How does machine learning work?",
  "Explain quantum computing",
  "Best practices for React development",
];

const MODELS = [
  { id: "gpt-4o",           name: "GPT-4o",           chef: "OpenAI",    providers: ["openai"]    },
  { id: "claude-sonnet-4",  name: "Claude 4 Sonnet",  chef: "Anthropic", providers: ["anthropic"] },
  { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", chef: "Google",    providers: ["google"]    },
];

// ─── Types ────────────────────────────────────────────────────────────────────

interface Conv { id: string; title: string; last_message_at: string }
interface NodeEvent { label: string; step: number }
interface ResultEvent {
  status: "success" | "fallback" | "review" | "error";
  text: string; answer_source: string; confidence: number; sources: unknown[];
  metrics: { latency_ms: number; model: string; input_tokens: number; output_tokens: number; node_path: string[] };
  error: { code: string; message: string; retryable: boolean } | null;
}
interface ChatMsg { id: string; role: "user" | "assistant"; text: string; result?: ResultEvent }
type StreamStatus = "idle" | "streaming" | "done" | "error";

// ─── useChatStream ────────────────────────────────────────────────────────────

function useChatStream(opts: { api: string; sessionId: string; conversationId: string }) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [nodes,    setNodes]    = useState<NodeEvent[]>([]);
  const [status,   setStatus]   = useState<StreamStatus>("idle");
  const [error,    setError]    = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || status === "streaming") return;

    const assistantId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", text },
      { id: assistantId, role: "assistant", text: "" },
    ]);
    setNodes([]);
    setError(null);
    setStatus("streaming");
    abortRef.current = new AbortController();

    try {
      const res = await fetch(opts.api, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text, session_id: opts.sessionId,
          conversation_id: opts.conversationId, msg_id: "",
        }),
        signal: abortRef.current.signal,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          if (!part.trim()) continue;
          let eventType = "message", dataLine = "";
          for (const line of part.split("\n")) {
            if (line.startsWith("event:"))     eventType = line.slice(6).trim();
            else if (line.startsWith("data:")) dataLine  = line.slice(5).trim();
          }
          if (!dataLine) continue;
          try {
            const payload = JSON.parse(dataLine);
            if (eventType === "node") {
              setNodes((prev) => [...prev, payload as NodeEvent]);
            } else if (eventType === "result") {
              const result = payload as ResultEvent;
              setMessages((prev) =>
                prev.map((m) => m.id === assistantId ? { ...m, text: result.text, result } : m)
              );
              if (result.status === "error") {
                setError(result.error?.message ?? "Unknown error");
                setStatus("error");
              }
            } else if (eventType === "done") {
              setStatus("done");
            }
          } catch { /* skip malformed */ }
        }
      }
      setStatus("done");
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") { setStatus("idle"); return; }
      const msg = e instanceof Error ? e.message : "Stream failed";
      setError(msg);
      setStatus("error");
      setMessages((prev) =>
        prev.map((m) => m.id === assistantId ? { ...m, text: "⚠ " + msg } : m)
      );
    }
  }, [opts.api, opts.sessionId, opts.conversationId, status]);

  const stop  = useCallback(() => abortRef.current?.abort(), []);
  const reset = useCallback(() => { setMessages([]); setNodes([]); setStatus("idle"); setError(null); }, []);
  return { messages, nodes, status, error, sendMessage, stop, reset };
}

// ─── API helpers ──────────────────────────────────────────────────────────────

async function createConversation(): Promise<string> {
  const res = await fetch(`${API}/chat/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: "New chat" }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.id ?? data.conversation_id;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

const AttachmentItem = ({ a, onRemove }: { a: { id: string; name: string; type: string; url: string }; onRemove: (id: string) => void }) => (
  <Attachment data={a} onRemove={() => onRemove(a.id)}><AttachmentPreview /><AttachmentRemove /></Attachment>
);

const PromptInputAttachmentsDisplay = () => {
  const { files, remove } = usePromptInputAttachments();
  if (!files.length) return null;
  return <Attachments variant="inline">{files.map((f) => <AttachmentItem key={f.id} a={f} onRemove={remove} />)}</Attachments>;
};

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
  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-20 bg-black/40 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Drawer — slides in on mobile, always visible on md+ */}
      <aside className={`
        fixed inset-y-0 left-0 z-30 flex w-72 flex-col border-r bg-background
        transition-transform duration-200
        ${open ? "translate-x-0" : "-translate-x-full"}
        md:relative md:z-auto md:w-64 md:translate-x-0
      `}>
        {/* Header */}
        <div className="flex items-center justify-between p-3">
          <button
            onClick={onNew}
            className="flex flex-1 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted transition-colors"
          >
            <MessageSquarePlus size={16} /> New chat
          </button>
          {/* Close button — mobile only */}
          <button
            onClick={onClose}
            className="ml-1 rounded-lg p-2 hover:bg-muted transition-colors md:hidden"
          >
            <XIcon size={16} />
          </button>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-0.5">
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => { onSelect(c.id); onClose(); }}
              className={`w-full text-left rounded-lg px-3 py-2 text-sm transition-colors ${
                convId === c.id ? "bg-muted font-medium" : "hover:bg-muted"
              }`}
            >
              <div className="truncate">{c.title}</div>
              <div className="text-xs text-muted-foreground">
                {new Date(c.last_message_at).toLocaleDateString()}
              </div>
            </button>
          ))}
        </div>
      </aside>
    </>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const [model,         setModel]         = useState(MODELS[0].id);
  const [open,          setOpen]          = useState(false);
  const [webSearch,     setWebSearch]     = useState(false);
  const [input,         setInput]         = useState("");
  const [sidebarOpen,   setSidebarOpen]   = useState(false);
  const [conversations, setConversations] = useState<Conv[]>([]);
  const [convId,        setConvId]        = useState<string | null>(null);

  const { messages, nodes, status, error, sendMessage, stop, reset } = useChatStream({
    api:            `${API}/chat/stream`,
    sessionId:      SESSION_ID,
    conversationId: convId ?? "",
  });

  const isLoading    = status === "streaming";
  const submitStatus = isLoading ? "streaming" : "ready";
  const selected     = useMemo(() => MODELS.find((m) => m.id === model)!, [model]);

  const refreshConversations = useCallback(() => {
    fetch(`${API}/chat/conversations`)
      .then((r) => r.json())
      .then(setConversations)
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshConversations();
    createConversation()
      .then(setConvId)
      .catch(() => toast.error("Failed to create conversation"));
  }, []);

  useEffect(() => { if (error) toast.error(error); }, [error]);

  const submit = useCallback((text: string) => {
    if (!text.trim() || isLoading || !convId) return;
    setInput("");
    sendMessage(text);
  }, [isLoading, sendMessage, convId]);

  const newChat = useCallback(async () => {
    try {
      const id = await createConversation();
      reset(); setConvId(id); setInput("");
      refreshConversations();
    } catch { toast.error("Failed to create conversation"); }
  }, [reset, refreshConversations]);

  const selectConv = useCallback((id: string) => {
    reset(); setConvId(id); setInput("");
  }, [reset]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(input); }
  }, [input, submit]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        conversations={conversations}
        convId={convId}
        onNew={newChat}
        onSelect={selectConv}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main */}
      <div className="relative flex flex-1 flex-col divide-y overflow-hidden min-w-0">

        {/* Mobile top bar */}
        <div className="flex items-center gap-2 px-3 py-2 border-b md:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-lg p-2 hover:bg-muted transition-colors"
          >
            <MenuIcon size={18} />
          </button>
          <span className="text-sm font-medium truncate flex-1">
            {conversations.find((c) => c.id === convId)?.title ?? "Chat"}
          </span>
        </div>

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

        <div className="grid shrink-0 gap-3 pt-3">
          {/* Pipeline node pills */}
          {nodes.length > 0 && (
            <div className="flex flex-wrap gap-1.5 px-4">
              {nodes.map((n, i) => (
                <span key={i} className="text-[11px] px-2 py-0.5 rounded-full border border-border text-muted-foreground bg-muted">
                  {n.step}. {n.label}
                </span>
              ))}
            </div>
          )}

          <Suggestions className="px-4">
            {SUGGESTIONS.map((s) => (
              <Suggestion key={s} suggestion={s} onClick={() => submit(s)} />
            ))}
          </Suggestions>

          <div className="w-full px-3 pb-3 md:px-4 md:pb-4">
            <PromptInput
              globalDrop
              multiple
              onSubmit={(m) => {
                if (m.files?.length) toast.success(`${m.files.length} file(s) attached`);
                submit(m.text || "Sent with attachments");
              }}
            >
              <PromptInputHeader><PromptInputAttachmentsDisplay /></PromptInputHeader>
              <PromptInputBody>
                <PromptInputTextarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                />
              </PromptInputBody>
              <PromptInputFooter>
                <PromptInputTools>
                  <PromptInputActionMenu>
                    <PromptInputActionMenuTrigger />
                    <PromptInputActionMenuContent><PromptInputActionAddAttachments /></PromptInputActionMenuContent>
                  </PromptInputActionMenu>

                  <SpeechInput
                    size="icon-sm"
                    variant="ghost"
                    onTranscriptionChange={(t) => setInput((p) => p ? `${p} ${t}` : t)}
                  />

                  <PromptInputButton
                    variant={webSearch ? "default" : "ghost"}
                    onClick={() => setWebSearch((p) => !p)}
                  >
                    <GlobeIcon size={16} /><span className="hidden sm:inline">Search</span>
                  </PromptInputButton>

                  <ModelSelector open={open} onOpenChange={setOpen}>
                    <ModelSelectorTrigger asChild>
                      <PromptInputButton>
                        <ModelSelectorLogo provider={selected.chef.toLowerCase()} />
                        <ModelSelectorName className="hidden sm:inline">{selected.name}</ModelSelectorName>
                      </PromptInputButton>
                    </ModelSelectorTrigger>
                    <ModelSelectorContent>
                      <ModelSelectorInput placeholder="Search models..." />
                      <ModelSelectorList>
                        <ModelSelectorEmpty>No models found.</ModelSelectorEmpty>
                        {Array.from(new Set(MODELS.map((m) => m.chef))).map((chef) => (
                          <ModelSelectorGroup heading={chef} key={chef}>
                            {MODELS.filter((m) => m.chef === chef).map((m) => (
                              <ModelSelectorItem key={m.id} value={m.id} onSelect={() => { setModel(m.id); setOpen(false); }}>
                                <ModelSelectorLogo provider={m.chef.toLowerCase()} />
                                <ModelSelectorName>{m.name}</ModelSelectorName>
                                <ModelSelectorLogoGroup>
                                  {m.providers.map((p) => <ModelSelectorLogo key={p} provider={p} />)}
                                </ModelSelectorLogoGroup>
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
                />
              </PromptInputFooter>
            </PromptInput>
          </div>
        </div>
      </div>
    </div>
  );
}