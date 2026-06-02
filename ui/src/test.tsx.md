"use client";

import { useState, useRef, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface NodeEvent {
  label: string;
  step: number;
}

interface ResultEvent {
  status: "success" | "fallback" | "review" | "error";
  text: string;
  answer_source: string;
  confidence: number;
  sources: unknown[];
  metrics: {
    latency_ms: number;
    model: string;
    input_tokens: number;
    output_tokens: number;
    node_path: string[];
  };
  error: { code: string; message: string; retryable: boolean } | null;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  result?: ResultEvent;
}

type StreamStatus = "idle" | "streaming" | "done" | "error";

// ─── Hook ─────────────────────────────────────────────────────────────────────

function useChatStream(opts: {
  api: string;
  sessionId: string;
  conversationId: string;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [nodes, setNodes] = useState<NodeEvent[]>([]);
  const [status, setStatus] = useState<StreamStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || status === "streaming") return;

      // Optimistically add user message
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        text,
      };
      const assistantId = crypto.randomUUID();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        text: "",
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setNodes([]);
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

            // Parse SSE block: may have multiple lines
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
                setNodes((prev) => [...prev, payload as NodeEvent]);
              } else if (eventType === "result") {
                const result = payload as ResultEvent;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, text: result.text, result }
                      : m
                  )
                );
                if (result.status === "error") {
                  setError(result.error?.message ?? "Unknown error");
                  setStatus("error");
                }
              } else if (eventType === "done") {
                setStatus("done");
              }
            } catch {
              // ignore malformed JSON
            }
          }
        }

        setStatus("done");
      } catch (e: unknown) {
        if (e instanceof Error && e.name === "AbortError") {
          setStatus("idle");
        } else {
          const msg = e instanceof Error ? e.message : "Stream failed";
          setError(msg);
          setStatus("error");
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, text: "⚠ " + msg }
                : m
            )
          );
        }
      }
    },
    [opts.api, opts.sessionId, opts.conversationId, status]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    setMessages([]);
    setNodes([]);
    setStatus("idle");
    setError(null);
  }, []);

  return { messages, nodes, status, error, sendMessage, stop, reset };
}

// ─── UI ───────────────────────────────────────────────────────────────────────

export default function TestChat() {
  const [input, setInput] = useState("");

  const { messages, nodes, status, error, sendMessage, stop, reset } =
    useChatStream({
      api: "http://localhost:8000/api/v1/chat/stream",
      sessionId: "test-ui",
      conversationId: "c1803f49-8230-4906-9341-4a41f1b28509",
    });

  const isLoading = status === "streaming";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput("");
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 p-6">
      <div className="max-w-2xl mx-auto space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <h1 className="text-sm font-semibold tracking-widest uppercase text-slate-400">
            Chat Stream
          </h1>
          <button
            onClick={reset}
            className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
          >
            reset
          </button>
        </div>

        {/* Pipeline nodes */}
        {nodes.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {nodes.map((n, i) => (
              <span
                key={i}
                className="text-[11px] px-2 py-0.5 rounded border border-blue-200 text-blue-600 bg-blue-50"
              >
                {n.step}. {n.label}
              </span>
            ))}
          </div>
        )}

        {/* Messages */}
        <div className="space-y-3 min-h-[200px]">
          {messages.length === 0 && (
            <p className="text-slate-300 text-sm text-center pt-12">
              — no messages —
            </p>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className="space-y-1">
              <div className="text-[11px] text-slate-400 uppercase tracking-wider">
                {msg.role === "user" ? "you" : "assistant"}
              </div>
              <div
                className={`text-sm leading-relaxed px-3 py-2 rounded-lg border ${
                  msg.role === "user"
                    ? "border-blue-200 bg-blue-50 text-blue-800"
                    : "border-emerald-200 bg-emerald-50 text-emerald-800"
                }`}
              >
                {msg.text || (
                  <span className="text-slate-300 italic">
                    {isLoading ? "thinking…" : "(empty)"}
                  </span>
                )}
              </div>

              {/* Metrics badge */}
              {msg.result?.metrics?.latency_ms > 0 && (
                <div className="text-[10px] text-slate-400 pl-1">
                  {msg.result.metrics.latency_ms.toFixed(0)}ms ·{" "}
                  {msg.result.answer_source} ·{" "}
                  {(msg.result.confidence * 100).toFixed(0)}% conf
                  {msg.result.metrics.model
                    ? ` · ${msg.result.metrics.model}`
                    : ""}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="text-xs text-red-600 border border-red-200 bg-red-50 px-3 py-2 rounded-lg">
            ✗ {error}
          </div>
        )}

        {/* Input */}
        <form onSubmit={handleSubmit} className="flex gap-2 pt-1">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="type a message…"
            disabled={isLoading}
            className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 placeholder-slate-300 focus:outline-none focus:border-slate-400 disabled:opacity-40"
          />
          {isLoading ? (
            <button
              type="button"
              onClick={stop}
              className="px-4 py-2 text-sm bg-red-50 border border-red-200 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
            >
              stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-30 transition-colors"
            >
              send
            </button>
          )}
        </form>

        {/* Status */}
        <div className="text-[10px] text-slate-300 text-right">
          status: {status}
        </div>
      </div>
    </div>
  );
}