import { useState, useRef, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface NodeEvent {
  label: string;
  step: number;
}

// ─── Chi tiết node để manager kiểm tra ────────────────────────────────────────
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

  // restore node history
  node_history?: NodeDetail[];

  node_id?: string;
  node_label?: string;
  step?: number;
}

export interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  text: string;
  result?: ResultEvent;
}

export type StreamStatus = "idle" | "streaming" | "done" | "error";

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
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [nodes, setNodes] = useState<NodeEvent[]>([]);
  const [nodeDetails, setNodeDetails] = useState<NodeDetail[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [status, setStatus] = useState<StreamStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || status === "streaming") return;

      const assistantId = crypto.randomUUID();

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "user",
          text,
        },
        {
          id: assistantId,
          role: "assistant",
          text: "",
        },
      ]);

      setNodes([]);
      setNodeDetails([]);
      setSuggestions([]);
      setError(null);
      setStatus("streaming");

      abortRef.current = new AbortController();

      try {
        const res = await fetch(opts.api, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: text,
            session_id: opts.sessionId,
            conversation_id: opts.conversationId,
            msg_id: "",
          }),
          signal: abortRef.current.signal,
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        if (!res.body) {
          throw new Error("No response body");
        }

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

            let eventType = "message";
            let dataLine = "";

            for (const line of part.split("\n")) {
              if (line.startsWith("event:")) {
                eventType = line.slice(6).trim();
              } else if (line.startsWith("data:")) {
                dataLine = line.slice(5).trim();
              }
            }

            if (!dataLine) continue;

            try {
              const payload = JSON.parse(dataLine);

              if (eventType === "node") {
                setNodes((prev) => [
                  ...prev,
                  payload as NodeEvent,
                ]);
                           } else if (eventType === "node_detail") {
                const detail = payload as NodeDetail;
                
                // Thêm vào nodeDetails để tracking
                setNodeDetails((prev) => [...prev, detail]);
                
                // THÊM: Tạo message riêng cho mỗi node để hiển thị như chat bubble
                setMessages((prev) => {
                  // Kiểm tra đã có message cho node này chưa
                  const existingIdx = prev.findIndex(
                    m => m.role === "assistant" && m.result?.node_id === detail.node_id
                  );
                  
                  if (existingIdx >= 0) {
                    // Update message hiện có
                    const updated = [...prev];
                    updated[existingIdx] = {
                      ...updated[existingIdx],
                      text: detail.text || updated[existingIdx].text,
                      result: {
                        ...updated[existingIdx].result,
                        status: detail.status === "SUCCESS" ? "success" : "streaming",
                        text: detail.text,
                        node_id: detail.node_id,
                        node_label: detail.node_label,
                        step: detail.step,
                        state: detail.state,
                        metrics: detail.metrics,
                      } as any,
                    };
                    return updated;
                  }
                  
                  // Tạo message mới cho node này
                  return [
                    ...prev,
                    {
                      id: `node-${detail.node_id}-${detail.step}`,
                      role: "assistant",
                      text: detail.text || `[${detail.node_label}] Đang xử lý...`,
                      result: {
                        status: detail.status === "SUCCESS" ? "success" : "streaming",
                        text: detail.text,
                        node_id: detail.node_id,
                        node_label: detail.node_label,
                        step: detail.step,
                        state: detail.state,
                        metrics: detail.metrics,
                      } as any,
                    },
                  ];
                });
              } else if (eventType === "result") {
                const result = payload as ResultEvent;

                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? {
                          ...m,
                          text: result.text,
                          result,
                        }
                      : m
                  )
                );

                if (result.node_history?.length) {
                  setNodeDetails(result.node_history);
                }

                if (result.suggestions?.length) {
                  setSuggestions(result.suggestions);
                }

                if (result.status === "error") {
                  setError(
                    result.error?.message ?? "Unknown error"
                  );
                  setStatus("error");
                }
              } else if (eventType === "done") {
                setStatus("done");
              }
            } catch {
              // malformed SSE frame
            }
          }
        }

        setStatus("done");
      } catch (e: unknown) {
        if (
          e instanceof Error &&
          e.name === "AbortError"
        ) {
          setStatus("idle");
          return;
        }

        const msg =
          e instanceof Error
            ? e.message
            : "Stream failed";

        setError(msg);
        setStatus("error");

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  text: `⚠ ${msg}`,
                }
              : m
          )
        );
      }
    },
    [
      opts.api,
      opts.sessionId,
      opts.conversationId,
      status,
    ]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    setMessages([]);
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
  };
}