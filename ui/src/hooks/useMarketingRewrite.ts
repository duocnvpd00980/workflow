import { useState, useRef, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/v1";

export type RewriteStatus = "idle" | "streaming" | "done" | "error";

interface UseMarketingRewriteProps {
  sessionId: string;
  draft: string;
}

export function useMarketingRewrite({ sessionId, draft }: UseMarketingRewriteProps) {
  const [content, setContent] = useState("");
  const [status, setStatus] = useState<RewriteStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const rewrite = useCallback(async (instruction: string) => {
    if (!instruction.trim()) return;

    // Guard: session_id bắt buộc
    if (!sessionId) {
      console.error("[useMarketingRewrite] sessionId is undefined!")
      setError("Thiếu session_id")
      setStatus("error")
      return
    }

    setContent("");
    setError(null);
    setStatus("streaming");

    const controller = new AbortController();
    abortRef.current = controller;

    const requestBody = {
      session_id: sessionId,   // ← key phải khớp với ChatEditRequest backend
      draft,
      instruction,
    }

    // Debug log — xóa sau khi confirm OK
    console.log("[useMarketingRewrite] POST body:", requestBody)

    try {
      const response = await fetch(`${API_BASE}/marketing/chat/edit-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
        signal: controller.signal,
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const line = frame.trim();
          if (!line.startsWith("data:")) continue;

          try {
            const payload = JSON.parse(line.replace("data:", "").trim());
            if (payload.text) {
              fullText += payload.text;
              setContent(fullText);
            }
            if (payload.done) setStatus("done");
          } catch {
            // ignore malformed frame
          }
        }
      }

      setStatus("done");
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        setStatus("idle");
        return;
      }
      const message = err instanceof Error ? err.message : "Rewrite failed";
      setError(message);
      setStatus("error");
    }
  }, [sessionId, draft]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setStatus("idle");
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setContent("");
    setError(null);
    setStatus("idle");
  }, []);

  return {
    content,
    status,
    error,
    rewrite,
    stop,
    reset,
    isStreaming: status === "streaming",
  };
}