import { API_BASE } from "@/config";
import { useState, useRef, useCallback, useEffect } from "react";



export type RewriteStatus = "idle" | "streaming" | "done" | "error";

interface UseMarketingRewriteProps {
  sessionId: string;
  draft: string;
  onToken?: (token: string, accumulated: string) => void;
  onDone?: (finalContent: string) => void;
}

export function useMarketingRewrite({
  sessionId,
  draft,
  onToken,
  onDone,
}: UseMarketingRewriteProps) {
  const [status, setStatus] = useState<RewriteStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Always-fresh refs — never stale, never in useCallback deps
  const onTokenRef = useRef(onToken);
  const onDoneRef = useRef(onDone);
  const draftRef = useRef(draft);
  const sessionIdRef = useRef(sessionId);

  useEffect(() => { onTokenRef.current = onToken; }, [onToken]);
  useEffect(() => { onDoneRef.current = onDone; }, [onDone]);
  useEffect(() => { draftRef.current = draft; }, [draft]);
  useEffect(() => { sessionIdRef.current = sessionId; }, [sessionId]);

  const rewrite = useCallback(async (instruction: string) => {
     let tokenCount = 0; 
    if (!instruction.trim()) return;

    const currentSessionId = sessionIdRef.current;
    const currentDraft = draftRef.current;

    if (!currentSessionId) {
      setError("Thiếu session_id");
      setStatus("error");
      return;
    }

    setError(null);
    setStatus("streaming");

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch(`${API_BASE}/marketing/chat/edit-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: currentSessionId,
          draft: currentDraft,
          instruction,
        }),
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
              // Call ref directly — always fresh, no closure staleness
               console.log(`[SSE] token #${tokenCount++} at ${Date.now()} | "${payload.text}" | total chars: ${fullText.length}`);  // 👈 thêm dòng này
              onTokenRef.current?.(payload.text, fullText);
            }
            if (payload.done) {
              setStatus("done");
              onDoneRef.current?.(fullText);
            }
          } catch {
            // ignore malformed frame
          }
        }
      }

      setStatus("done");
      onDoneRef.current?.(fullText);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        setStatus("idle");
        return;
      }
      const message = err instanceof Error ? err.message : "Rewrite failed";
      setError(message);
      setStatus("error");
    }
  }, []); // stable — no deps needed, all values via refs

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setStatus("idle");
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setError(null);
    setStatus("idle");
  }, []);

  return {
    status,
    error,
    rewrite,
    stop,
    reset,
    isStreaming: status === "streaming",
  };
}