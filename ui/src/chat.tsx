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
import { CheckIcon, GlobeIcon, MessageSquarePlus } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

const API = "http://localhost:8000/api/v1";

const SUGGESTIONS = [
  "What are the latest trends in AI?",
  "How does machine learning work?",
  "Explain quantum computing",
  "Best practices for React development",
];

const MODELS = [
  { id: "gpt-4o", name: "GPT-4o", chef: "OpenAI", providers: ["openai"] },
  { id: "claude-sonnet-4", name: "Claude 4 Sonnet", chef: "Anthropic", providers: ["anthropic"] },
  { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", chef: "Google", providers: ["google"] },
];

interface Conv {
  id: string;
  title: string;
  last_message_at: string;
}

interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  content: string;
}

const AttachmentItem = ({ a, onRemove }: { a: { id: string; name: string; type: string; url: string }; onRemove: (id: string) => void }) => (
  <Attachment data={a} onRemove={() => onRemove(a.id)}><AttachmentPreview /><AttachmentRemove /></Attachment>
);

const PromptInputAttachmentsDisplay = () => {
  const { files, remove } = usePromptInputAttachments();
  if (!files.length) return null;
  return <Attachments variant="inline">{files.map((f) => <AttachmentItem key={f.id} a={f} onRemove={remove} />)}</Attachments>;
};

export default function ChatPage() {
  const [model, setModel] = useState(MODELS[0].id);
  const [open, setOpen] = useState(false);
  const [webSearch, setWebSearch] = useState(false);
  const [input, setInput] = useState("");
  const [conversations, setConversations] = useState<Conv[]>([]);
  const [convId, setConvId] = useState<string | undefined>();
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [status, setStatus] = useState<"ready" | "submitted" | "streaming">("ready");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetch(`${API}/chat/conversations`)
      .then((r) => r.json())
      .then(setConversations)
      .catch(() => toast.error("Failed to load conversations"));
  }, []);

  const isLoading = status === "submitted" || status === "streaming";
  const selected = useMemo(() => MODELS.find((m) => m.id === model)!, [model]);

  const parseChunk = (line: string): { type: "text" | "done" | "progress" | null; data?: string } => {
    const t = line.trim();
    if (!t) return { type: null };
    if (t.startsWith('0:"')) {
      return { type: "text", data: t.slice(2).replace(/^"|"$/g, "") };
    }
    if (t.startsWith("d:")) {
      return { type: "done" };
    }
    if (t.startsWith("2:")) {
      try {
        const events = JSON.parse(t.slice(2));
        if (Array.isArray(events) && events[0]?.type === "node_progress") {
          return { type: "progress", data: events[0].label };
        }
      } catch { /* ignore */ }
    }
    return { type: null };
  };

  const submit = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    // Add user message
    const userMsg: ChatMsg = { id: `u-${Date.now()}`, role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStatus("submitted");

    // Add empty assistant message
    const assistantId = `a-${Date.now()}`;
    setMessages((prev) => [...prev, { id: assistantId, role: "assistant", content: "" }]);

    try {
      abortRef.current = new AbortController();

      // === ĐÚNG PAYLOAD SCHEMA ===
      const payload = {
        message: text,
        session_id: "web-ui",
        conversation_id: "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        msg_id: "", 
      };

      console.log("[Submit] payload:", payload);

      const res = await fetch(`${API}/chat/stream/ai-sdk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: abortRef.current.signal,
      });

      console.log("[Fetch] status:", res.status);

      if (!res.ok) {
        const errText = await res.text();
        console.error("[Fetch] error body:", errText);
        throw new Error(`HTTP ${res.status}: ${errText}`);
      }
      if (!res.body) throw new Error("No body");

      setStatus("streaming");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const chunk = parseChunk(line);
          if (chunk.type === "text" && chunk.data) {
            fullText += chunk.data;
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: fullText } : m))
            );
          }
          if (chunk.type === "done") {
            setStatus("ready");
            return;
          }
        }
      }

      if (buffer.trim()) {
        const chunk = parseChunk(buffer);
        if (chunk.type === "text" && chunk.data) {
          fullText += chunk.data;
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: fullText } : m))
          );
        }
      }
      setStatus("ready");
    } catch (err) {
      console.error("[Submit] error:", err);
      setStatus("ready");
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: m.content + "\n\n*[Error: " + (err as Error).message + "]*" }
            : m
        )
      );
      toast.error((err as Error).message);
    }
  }, [isLoading, convId]);

  const onSuggestion = useCallback((s: string) => { setInput(s); submit(s); }, [submit]);
  const onSpeech = useCallback((t: string) => setInput((p) => (p ? `${p} ${t}` : t)), []);
  const newChat = useCallback(() => { setConvId(undefined); setMessages([]); setInput(""); }, []);
  const selectConv = useCallback((id: string) => { setConvId(id); setMessages([]); }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(input);
    }
  }, [input, submit]);

  return (
    <div className="flex h-screen">
      <aside className="w-64 border-r bg-muted/40 flex flex-col">
        <div className="p-3">
          <button onClick={newChat} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted transition-colors">
            <MessageSquarePlus size={16} /> New chat
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1">
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => selectConv(c.id)}
              className={`w-full text-left rounded-lg px-3 py-2 text-sm transition-colors ${convId === c.id ? "bg-muted font-medium" : "hover:bg-muted"}`}
            >
              <div className="truncate">{c.title}</div>
              <div className="text-xs text-muted-foreground">{new Date(c.last_message_at).toLocaleDateString()}</div>
            </button>
          ))}
        </div>
      </aside>

      <div className="relative flex flex-1 flex-col divide-y overflow-hidden">
        <Conversation>
          <ConversationContent>
            {messages.map((msg) => (
              <MessageBranch key={msg.id} defaultBranch={0}>
                <MessageBranchContent>
                  <Message from={msg.role}>
                    <MessageContent>
                      <MessageResponse>{msg.content}</MessageResponse>
                    </MessageContent>
                  </Message>
                </MessageBranchContent>
              </MessageBranch>
            ))}
          </ConversationContent>
          <ConversationScrollButton />
        </Conversation>

        <div className="grid shrink-0 gap-4 pt-4">
          <Suggestions className="px-4">
            {SUGGESTIONS.map((s) => <Suggestion key={s} suggestion={s} onClick={() => onSuggestion(s)} />)}
          </Suggestions>

          <div className="w-full px-4 pb-4">
            <PromptInput globalDrop multiple onSubmit={(m) => { if (m.files?.length) toast.success(`${m.files.length} file(s) attached`); submit(m.text || "Sent with attachments"); }}>
              <PromptInputHeader><PromptInputAttachmentsDisplay /></PromptInputHeader>
              <PromptInputBody>
                <PromptInputTextarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} />
              </PromptInputBody>
              <PromptInputFooter>
                <PromptInputTools>
                  <PromptInputActionMenu>
                    <PromptInputActionMenuTrigger />
                    <PromptInputActionMenuContent><PromptInputActionAddAttachments /></PromptInputActionMenuContent>
                  </PromptInputActionMenu>
                  <SpeechInput size="icon-sm" variant="ghost" onTranscriptionChange={onSpeech} />
                  <PromptInputButton variant={webSearch ? "default" : "ghost"} onClick={() => setWebSearch((p) => !p)}>
                    <GlobeIcon size={16} /><span>Search</span>
                  </PromptInputButton>
                  <ModelSelector open={open} onOpenChange={setOpen}>
                    <ModelSelectorTrigger asChild>
                      <PromptInputButton>
                        <ModelSelectorLogo provider={selected.chef.toLowerCase()} />
                        <ModelSelectorName>{selected.name}</ModelSelectorName>
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
                                <ModelSelectorLogoGroup>{m.providers.map((p) => <ModelSelectorLogo key={p} provider={p} />)}</ModelSelectorLogoGroup>
                                {model === m.id ? <CheckIcon className="ml-auto size-4" /> : <div className="ml-auto size-4" />}
                              </ModelSelectorItem>
                            ))}
                          </ModelSelectorGroup>
                        ))}
                      </ModelSelectorList>
                    </ModelSelectorContent>
                  </ModelSelector>
                </PromptInputTools>
                <PromptInputSubmit disabled={!input.trim() || isLoading} status={status} onClick={() => submit(input)} />
              </PromptInputFooter>
            </PromptInput>
          </div>
        </div>
      </div>
    </div>
  );
}