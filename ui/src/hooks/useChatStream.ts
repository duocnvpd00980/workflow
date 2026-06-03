import { useState, useRef, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface NodeEvent {
  label: string;
  step: number;
}

export interface NodeDetail {
  node_id: string;
  node_label: string;
  step: number;
  status: string;
  text: string;
  state: Record<string, unknown>;
  metrics: Record<string, unknown>;
  timestamp: number | null;
}

export interface ResultEvent {
  status: "success" | "fallback" | "review" | "error";
  text: string;
  answer_source: string;
  confidence: number;
  sources: unknown[];
  suggestions: string[];
  metrics: {
    latency_ms: number;
    model: string;
    input_tokens: number;
    output_tokens: number;
    node_path: string[];
  };
  error: {
    code: string;
    message: string;
    retryable: boolean;
  } | null;
  node_history?: NodeDetail[];
}

export interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  text: string;
  result?: ResultEvent;
}

export type StreamStatus = "idle" | "streaming" | "done" | "error";

// ─── Hook ─────────────────────────────────────────────────────────────────────

interface UseChatStreamOpts {
  api: string;
  sessionId: string;
  conversationId: string;
}

export function useChatStream({ api, sessionId, conversationId }: UseChatStreamOpts) {
  const [messages, setMessages]       = useState<ChatMsg[]>([]);
  const [nodes, setNodes]             = useState<NodeEvent[]>([]);
  const [nodeDetails, setNodeDetails] = useState<NodeDetail[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [status, setStatus]           = useState<StreamStatus>("idle");
  const [error, setError]             = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  // ── Upsert node detail by node_id ─────────────────────────────────────────
  const upsertNodeDetail = useCallback((detail: NodeDetail) => {
    setNodeDetails((prev) => {
      const idx = prev.findIndex((x) => x.node_id === detail.node_id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = detail;
        return next;
      }
      return [...prev, detail];
    });
  }, []);

  // ── Send message ──────────────────────────────────────────────────────────
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || status === "streaming") return;

      const userMsgId      = crypto.randomUUID();
      const assistantMsgId = crypto.randomUUID();

      // Optimistically append user + empty assistant bubble
      setMessages((prev) => [
        ...prev,
        { id: userMsgId,      role: "user",      text },
        { id: assistantMsgId, role: "assistant",  text: "" },
      ]);
      setNodes([]);
      setNodeDetails([]);
      setSuggestions([]);
      setError(null);
      setStatus("streaming");

      abortRef.current = new AbortController();

      try {
        const res = await fetch(api, {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message:         text,
            session_id:      sessionId,
            conversation_id: conversationId,
            msg_id:          "",
          }),
          signal: abortRef.current.signal,
        });

        if (!res.ok)   throw new Error(`HTTP ${res.status}`);
        if (!res.body) throw new Error("No response body");

        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer    = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            if (!part.trim()) continue;

            let eventType = "message";
            let dataLine  = "";

            for (const line of part.split("\n")) {
              if (line.startsWith("event:"))      eventType = line.slice(6).trim();
              else if (line.startsWith("data:"))  dataLine  = line.slice(5).trim();
            }

            if (!dataLine) continue;

            try {
              const payload = JSON.parse(dataLine);

              switch (eventType) {
                case "node":
                  setNodes((prev) => [...prev, payload as NodeEvent]);
                  break;

                case "node_detail":
                  upsertNodeDetail(payload as NodeDetail);
                  break;

                case "result": {
                  const result = payload as ResultEvent;

                  // Update assistant bubble with final text
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsgId ? { ...m, text: result.text, result } : m
                    )
                  );

                  if (result.node_history?.length) {
                    setNodeDetails(result.node_history);
                  }
                  if (result.suggestions?.length) {
                    setSuggestions(result.suggestions);
                  }
                  if (result.status === "error") {
                    setError(result.error?.message ?? "Unknown error");
                    setStatus("error");
                  }
                  break;
                }

                case "done":
                  setStatus("done");
                  break;
              }
            } catch {
              // malformed SSE frame — skip
            }
          }
        }

        setStatus((s) => s === "streaming" ? "done" : s);
      } catch (e: unknown) {
        if (e instanceof Error && e.name === "AbortError") {
          setStatus("idle");
          return;
        }
        const msg = e instanceof Error ? e.message : "Stream failed";
        setError(msg);
        setStatus("error");
        setMessages((prev) =>
          prev.map((m) => m.id === assistantMsgId ? { ...m, text: `⚠ ${msg}` } : m)
        );
      }
    },
    // conversationId intentionally excluded — we want the ref value at call time,
    // not a stale closure. The parent always passes the current value.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [api, sessionId, conversationId, status, upsertNodeDetail]
  );

  // ── Stop stream ───────────────────────────────────────────────────────────
  const stop = useCallback(() => {
    abortRef.current?.abort();
    setStatus("idle");
  }, []);

  // ── Reset all state ───────────────────────────────────────────────────────
  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setNodes([]);
    setNodeDetails([]);
    setSuggestions([]);
    setStatus("idle");
    setError(null);
  }, []);

  // ── Hydrate from DB history (called when switching conversations) ─────────
  // Accepts raw DB messages: { id, role, content, ... }
  // Normalizes to ChatMsg shape.
  const hydrate = useCallback((raw: any[]) => {
    const normalized: ChatMsg[] = raw.map((m) => ({
      id:   m.id   ?? crypto.randomUUID(),
      role: m.role === "user" ? "user" : "assistant",
      text: m.text ?? m.content ?? "",
    }));
    setMessages(normalized);
    setNodes([]);
    setNodeDetails([]);
    setSuggestions([]);
    setStatus("idle");
    setError(null);
  }, []);

  return {
    messages,
    nodes,
    nodeDetails,
    suggestions,
    status,
    error,
    sendMessage,
    stop,
    reset,
    hydrate,
  };
}