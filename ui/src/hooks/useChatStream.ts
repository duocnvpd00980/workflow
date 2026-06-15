import { useState, useRef, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  type: "user" | "final_result" | "error";
  text: string;
}

export type StreamStatus = "idle" | "streaming" | "done" | "error";

interface UseChatStreamOpts {
  api: string;
  conversationId: string;
  brandId?: string;
  businessId?: string;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useChatStream({ api, conversationId, brandId, businessId }: UseChatStreamOpts) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [status, setStatus]     = useState<StreamStatus>("idle");
  const [error, setError]       = useState<string | null>(null);

  const abortRef       = useRef<AbortController | null>(null);
  // Buffer token trực tiếp vào ref để tránh setState flood — flush theo RAF
  const tokenBufRef    = useRef("");
  const assistantIdRef = useRef("");
  const rafRef         = useRef<number | null>(null);

  // Flush accumulated tokens vào message cuối cùng (assistant đang stream)
  const flushTokens = useCallback(() => {
    rafRef.current = null;
    const chunk = tokenBufRef.current;
    if (!chunk) return;
    tokenBufRef.current = "";

    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last?.id === assistantIdRef.current && last.role === "assistant") {
        return [
          ...prev.slice(0, -1),
          { ...last, text: last.text + chunk },
        ];
      }
      // Tạo mới nếu chưa có placeholder
      return [
        ...prev,
        {
          id: assistantIdRef.current,
          role: "assistant",
          type: "final_result",
          text: chunk,
        },
      ];
    });
  }, []);

  const scheduleFlush = useCallback(() => {
    if (rafRef.current !== null) return;
    rafRef.current = requestAnimationFrame(flushTokens);
  }, [flushTokens]);

  // ── Send message ──────────────────────────────────────────────────────────
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || status === "streaming") return;

      if (!conversationId) {
        setError("Chưa có conversationId.");
        setStatus("error");
        return;
      }

      const userMsgId      = crypto.randomUUID();
      const assistantMsgId = crypto.randomUUID();
      assistantIdRef.current = assistantMsgId;
      tokenBufRef.current    = "";

      // Thêm message user + placeholder assistant ngay lập tức
      setMessages((prev) => [
        ...prev,
        { id: userMsgId,      role: "user",      type: "user",         text },
        { id: assistantMsgId, role: "assistant",  type: "final_result", text: "" },
      ]);
      setError(null);
      setStatus("streaming");

      abortRef.current = new AbortController();

      try {
        const res = await fetch(`${api}/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            conversation_id: conversationId,
            message:         text,
            msg_id:          assistantMsgId,
            brand_id:        brandId  ?? null,
            business_id:     businessId ?? null,
          }),
          signal: abortRef.current.signal,
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
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

            let dataLine = "";
            for (const line of part.split("\n")) {
              if (line.startsWith("data:")) dataLine = line.slice(5).trim();
            }
            if (!dataLine) continue;

            let payload: { type: string; text?: string; message?: string };
            try { payload = JSON.parse(dataLine); }
            catch { continue; }

            if (payload.type === "token" && payload.text) {
              // Gom token, flush qua RAF để tránh quá nhiều re-render
              tokenBufRef.current += payload.text;
              scheduleFlush();
            } else if (payload.type === "done") {
              // Flush phần còn lại ngay lập tức
              if (rafRef.current !== null) {
                cancelAnimationFrame(rafRef.current);
                rafRef.current = null;
              }
              flushTokens();
              setStatus("done");
            } else if (payload.type === "error") {
              const msg = payload.message ?? "Lỗi không xác định";
              if (rafRef.current !== null) {
                cancelAnimationFrame(rafRef.current);
                rafRef.current = null;
              }
              // Xóa placeholder rỗng nếu chưa có nội dung, thêm error bubble
              setMessages((prev) => {
                const withoutEmpty = prev.filter(
                  (m) => !(m.id === assistantMsgId && m.text === "")
                );
                return [
                  ...withoutEmpty,
                  { id: `error-${Date.now()}`, role: "assistant", type: "error", text: `⚠ ${msg}` },
                ];
              });
              setError(msg);
              setStatus("error");
            }
          }
        }

        // Reader closed mà chưa nhận "done" (e.g. connection drop)
        if (rafRef.current !== null) {
          cancelAnimationFrame(rafRef.current);
          rafRef.current = null;
        }
        flushTokens();
        setStatus((s) => (s === "streaming" ? "done" : s));

      } catch (e: unknown) {
        if (rafRef.current !== null) {
          cancelAnimationFrame(rafRef.current);
          rafRef.current = null;
        }
        if (e instanceof Error && e.name === "AbortError") {
          setStatus("idle");
          return;
        }
        const msg = e instanceof Error ? e.message : "Stream failed";
        setError(msg);
        setStatus("error");
        setMessages((prev) => {
          const withoutEmpty = prev.filter(
            (m) => !(m.id === assistantMsgId && m.text === "")
          );
          return [
            ...withoutEmpty,
            { id: `error-${Date.now()}`, role: "assistant", type: "error", text: `⚠ ${msg}` },
          ];
        });
      }
    },
    [api, conversationId, brandId, businessId, status, scheduleFlush, flushTokens]
  );

  // ── Stop ─────────────────────────────────────────────────────────────────
  const stop = useCallback(async () => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    abortRef.current?.abort();
    setStatus("idle");

    if (conversationId) {
      try {
        await fetch(`${api}/chat/stop?conversation_id=${conversationId}`, { method: "POST" });
      } catch { /* best-effort */ }
    }
  }, [api, conversationId]);

  // ── Reset ─────────────────────────────────────────────────────────────────
  const reset = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    abortRef.current?.abort();
    tokenBufRef.current = "";
    setMessages([]);
    setStatus("idle");
    setError(null);
  }, []);

  // ── Hydrate từ DB history ─────────────────────────────────────────────────
  const hydrate = useCallback((raw: { id: string; role: string; content: string }[]) => {
    const normalized: ChatMsg[] = raw.map((m) => ({
      id:   m.id ?? crypto.randomUUID(),
      role: m.role === "user" ? "user" : "assistant",
      type: m.role === "user" ? "user" : "final_result",
      text: m.content ?? "",
    }));
    setMessages(normalized);
    setStatus("idle");
    setError(null);
  }, []);

  return { messages, status, error, sendMessage, stop, reset, hydrate };
}