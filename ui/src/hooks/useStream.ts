import { API_BASE } from "@/config";
import { useState, useCallback, useRef, useEffect } from "react";



export interface StreamOptions {
  endpoint: string;
  body: Record<string, unknown>;
  onChunk?: (fullText: string) => void;
  onDone?: (fullText: string) => void;
  onError?: (error: string) => void;
}

interface StreamResult {
  text: string;
  isStreaming: boolean;
  error: string | null;
  start: (options: StreamOptions) => void;
  stop: () => void;
  reset: () => void;
}

export function useStream(): StreamResult {
  const [text, setText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const fullTextRef = useRef("");

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
  }, []);

  const reset = useCallback(() => {
    stop();
    setText("");
    setError(null);
    fullTextRef.current = "";
  }, [stop]);

  const start = useCallback(
    async (options: StreamOptions) => {
      reset();

      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await fetch(
          `${API_BASE}${options.endpoint}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(options.body),
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          const err = await response.text();
          throw new Error(err || `HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();

        if (!reader) {
          throw new Error("No response body");
        }

        const decoder = new TextDecoder();

        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          buffer += decoder.decode(value, {
            stream: true,
          });

          const events = buffer.split("\n\n");
          buffer = events.pop() ?? "";

          for (const event of events) {
            const line = event.trim();

            if (!line.startsWith("data: ")) continue;

            const payload = JSON.parse(
              line.replace("data: ", "")
            );

            if (payload.text) {
              fullTextRef.current += payload.text;

              setText(fullTextRef.current);

              options.onChunk?.(
                fullTextRef.current
              );
            }

            if (payload.done) {
              options.onDone?.(
                fullTextRef.current
              );
              return;
            }
          }
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setError(err.message);
          options.onError?.(err.message);
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [reset]
  );

  useEffect(() => {
    return () => stop();
  }, [stop]);

  return {
    text,
    isStreaming,
    error,
    start,
    stop,
    reset,
  };
}