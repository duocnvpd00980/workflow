"use client";

import { CheckCircle2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface NodeResultMessageProps {
  nodeLabel: string;
  status: "done" | "error";
  text: string;
}

export function NodeResultMessage({ nodeLabel, status, text }: NodeResultMessageProps) {
  const isDone = status === "done";

  return (
    <div
      className={cn(
        "flex items-start gap-3 p-4 rounded-xl border transition-all",
        isDone
          ? "bg-emerald-50/60 border-emerald-100"
          : "bg-red-50/60 border-red-100"
      )}
    >
      <div
        className={cn(
          "w-7 h-7 rounded-full flex items-center justify-center text-white shrink-0",
          isDone ? "bg-emerald-500" : "bg-red-500"
        )}
      >
        {isDone ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
      </div>
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-sm font-semibold",
            isDone ? "text-emerald-700" : "text-red-700"
          )}
        >
          {isDone ? "✓" : "✗"} {nodeLabel} — {isDone ? "Hoàn thành" : "Lỗi"}
        </p>
        {text && text !== "string" && (
          <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">
            {text}
          </p>
        )}
      </div>
    </div>
  );
}

export default NodeResultMessage;