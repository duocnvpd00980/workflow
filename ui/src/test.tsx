"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useState } from "react";

export default function TestUseChat() {
  const [logs, setLogs] = useState<string[]>([]);
  const [input, setInput] = useState("");

  const { messages, status, sendMessage, data, stop } = useChat({
    transport: new DefaultChatTransport({
      api: "http://localhost:8000/api/v1/chat/stream/ai-sdk",
      body: {
        session_id: "test-ui",
        conversation_id: "c1803f49-8230-4906-9341-4a41f1b28509",
        msg_id: "",
      },
    }),
    onData: (dataPart) => {
      const log = `[onData] ${JSON.stringify(dataPart).slice(0, 200)}`;
      console.log(log);
      setLogs((prev) => [...prev.slice(-50), log]);
    },
    onError: (e) => {
      const log = `[onError] ${e.message}`;
      console.error(log);
      setLogs((prev) => [...prev.slice(-50), log]);
    },
    onFinish: (options) => {
      const log = `[onFinish] isError=${options.isError} finishReason=${options.finishReason}`;
      console.log(log);
      setLogs((prev) => [...prev.slice(-50), log]);
    },
  });

  const isLoading = status === "submitted" || status === "streaming";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    console.log("[sendMessage] input:", input);
    sendMessage({ text: input });
    setInput("");
  };

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-4">
      <h1 className="text-xl font-bold">Test useChat v5.x</h1>

      <div className="border rounded p-4 space-y-2">
        <h2 className="font-semibold">Messages ({messages.length}):</h2>
        {messages.map((msg) => (
          <div key={msg.id} className="text-sm border-l-2 pl-2" style={{ borderColor: msg.role === "user" ? "#3b82f6" : "#10b981" }}>
            <strong>{msg.role}:</strong>{" "}
            {msg.parts?.filter((p) => p.type === "text").map((p) => p.text).join("") || "(no text)"}
          </div>
        ))}
        {messages.length === 0 && <div className="text-gray-400 text-sm">No messages yet</div>}
      </div>

      <div className="border rounded p-4 space-y-2">
        <h2 className="font-semibold">Data ({data?.length || 0}):</h2>
        {data?.map((d, i) => (
          <div key={i} className="text-xs bg-gray-100 p-2 rounded">{JSON.stringify(d).slice(0, 300)}</div>
        ))}
        {(!data || data.length === 0) && <div className="text-gray-400 text-sm">No data</div>}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type and press Enter..."
          className="flex-1 border rounded px-3 py-2"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {isLoading ? "Loading..." : "Send"}
        </button>
        {isLoading && (
          <button type="button" onClick={stop} className="bg-red-500 text-white px-4 py-2 rounded">
            Stop
          </button>
        )}
      </form>

      <div className="border rounded p-4 space-y-2">
        <h2 className="font-semibold">Logs:</h2>
        <div className="h-48 overflow-y-auto text-xs space-y-1">
          {logs.map((log, i) => (
            <div key={i} className="font-mono">{log}</div>
          ))}
        </div>
      </div>
    </div>
  );
}