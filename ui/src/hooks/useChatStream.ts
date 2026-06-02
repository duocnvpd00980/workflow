import { useState, useRef, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface NodeEvent {
  label: string;
  step: number;
}

export interface ResultEvent {
  status: "success" | "fallback" | "review" | "error";
  text: string;
  answer_source: string;
  confidence: number;
  sources: unknown[];
  /** Gợi ý câu hỏi tiếp theo — backend trả về sau mỗi lượt chat */
  suggestions: string[];
  metrics: {
    latency_ms: number;
    model: string;
    input_tokens: number;
    output_tokens: number;
    node_path: string[];
  };
  error: { code: string; message: string; retryable: boolean } | null;
}

export interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  text: string;
  result?: ResultEvent;
}

export type StreamStatus = "idle" | "streaming" | "done" | "error";

// ─── 4 bước pipeline cố định ──────────────────────────────────────────────────
// Backend stream `node` events với step 1–4.
// Label mặc định dùng khi backend chưa gửi node tương ứng.
export const PIPELINE_STEPS: Record<number, string> = {
  1: "Kiểm duyệt đầu vào",
  2: "Định tuyến",
  3: "Đọc cache",
  4: "Hoàn tất",
};

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useChatStream(opts: {
  api: string;
  sessionId: string;
  conversationId: string;
}) {
  const [messages,    setMessages]    = useState<ChatMsg[]>([]);
  const [nodes,       setNodes]       = useState<NodeEvent[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [status,      setStatus]      = useState<StreamStatus>("idle");
  const [error,       setError]       = useState<string | null>(null);
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
    setSuggestions([]);
    setError(null);
    setStatus("streaming");
    abortRef.current = new AbortController();

    try {
      const res = await fetch(opts.api, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          session_id: opts.sessionId,
          conversation_id: opts.conversationId,
          msg_id: "",
        }),
        signal: abortRef.current.signal,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      if (!res.body) throw new Error("No response body");

      const reader  = res.body.getReader();
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

          let eventType = "message";
          let dataLine  = "";

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
                prev.map((m) =>
                  m.id === assistantId ? { ...m, text: result.text, result } : m
                )
              );

              // Cập nhật suggestions từ kết quả
              if (result.suggestions?.length) {
                setSuggestions(result.suggestions);
              }

              if (result.status === "error") {
                setError(result.error?.message ?? "Unknown error");
                setStatus("error");
              }

            } else if (eventType === "done") {
              setStatus("done");
            }
          } catch {
            // skip malformed SSE frame
          }
        }
      }

      setStatus("done");

    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") {
        setStatus("idle");
        return;
      }
      const msg = e instanceof Error ? e.message : "Stream failed";
      setError(msg);
      setStatus("error");
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, text: "⚠ " + msg } : m
        )
      );
    }
  }, [opts.api, opts.sessionId, opts.conversationId, status]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    setMessages([]);
    setNodes([]);
    setSuggestions([]);
    setStatus("idle");
    setError(null);
  }, []);

  return { messages, nodes, suggestions, status, error, sendMessage, stop, reset };
}