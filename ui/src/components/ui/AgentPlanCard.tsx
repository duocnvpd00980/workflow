"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { ChevronDown, ChevronUp, Terminal } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PlanStep {
  id: string;
  label: string;
  order: number;
  status: "pending" | "running" | "done" | "error";
  input?: Record<string, unknown>;
  output?: {
    text: string;
    state: Record<string, unknown>;
    metrics: Record<string, unknown>;
  };
  logs: string[];
  startedAt?: number;
  completedAt?: number;
  durationMs?: number;
}

export interface AgentPlanData {
  content: string;
  steps: PlanStep[];
  routeTo?: string;
  timestamp: number;
}

// ─── Status Config ──────────────────────────────────────────────────────────

const statusConfig = {
  pending: {
    bg: "bg-slate-50",
    border: "border-slate-200",
    text: "text-slate-500",
    badge: "bg-slate-100 text-slate-500 border-slate-200",
    label: "○ Chờ",
    dot: "bg-slate-300",
    icon: "○",
  },
  running: {
    bg: "bg-blue-50/80",
    border: "border-blue-200",
    text: "text-blue-700",
    badge: "bg-blue-100 text-blue-700 border-blue-200",
    label: "▶ Đang chạy...",
    dot: "bg-blue-500",
    icon: "▶",
  },
  done: {
    bg: "bg-emerald-50/80",
    border: "border-emerald-200",
    text: "text-emerald-700",
    badge: "bg-emerald-100 text-emerald-700 border-emerald-200",
    label: "✓ Xong",
    dot: "bg-emerald-500",
    icon: "✓",
  },
  error: {
    bg: "bg-red-50/80",
    border: "border-red-200",
    text: "text-red-700",
    badge: "bg-red-100 text-red-700 border-red-200",
    label: "✗ Lỗi",
    dot: "bg-red-500",
    icon: "✗",
  },
};

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatTime(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

// ─── Component ──────────────────────────────────────────────────────────────

export function AgentPlanCard({ content, steps, routeTo, timestamp }: AgentPlanData) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const toggleStep = (stepId: string) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(stepId)) next.delete(stepId);
      else next.add(stepId);
      return next;
    });
  };

  const runningCount = steps.filter((s) => s.status === "running").length;
  const doneCount = steps.filter((s) => s.status === "done").length;
  const totalCount = steps.length;

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-md">
          <Terminal size={14} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-medium text-slate-800 leading-relaxed">
            {content}
          </p>
          {routeTo && (
            <p className="text-[10px] text-slate-400 mt-1">
              Định tuyến: <span className="font-mono text-indigo-600">{routeTo}</span>
            </p>
          )}
        </div>
      </div>

      {/* Progress summary */}
      <div className="flex items-center gap-2 text-[11px] text-slate-500">
        <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all duration-500"
            style={{ width: `${totalCount > 0 ? (doneCount / totalCount) * 100 : 0}%` }}
          />
        </div>
        <span className="shrink-0 font-medium">
          {doneCount}/{totalCount} bước
        </span>
        {runningCount > 0 && (
          <span className="shrink-0 text-blue-600 animate-pulse">
            ({runningCount} đang chạy)
          </span>
        )}
      </div>

      {/* Steps list */}
      <div className="space-y-1.5">
        {steps.map((step) => {
          const cfg = statusConfig[step.status];
          const isStepExpanded = expandedSteps.has(step.id);

          return (
            <div key={step.id} className="space-y-1">
              {/* Step row */}
              <div
                className={cn(
                  "flex items-center justify-between p-2.5 rounded-xl border transition-all cursor-pointer hover:shadow-sm",
                  cfg.bg,
                  cfg.border
                )}
                onClick={() => toggleStep(step.id)}
              >
                <div className="flex items-center gap-3 min-w-0">
                  {/* Order badge */}
                  <div
                    className={cn(
                      "w-6 h-6 rounded-full text-white text-[11px] font-bold flex items-center justify-center shrink-0 transition-colors",
                      step.status === "pending" ? "bg-slate-300" : cfg.dot,
                      step.status === "running" && "animate-pulse"
                    )}
                  >
                    {step.status === "done" ? "✓" : step.order}
                  </div>

                  {/* Label */}
                  <span className={cn("text-[12px] font-medium truncate", cfg.text)}>
                    {step.label}
                  </span>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {/* Duration */}
                  {step.durationMs && step.durationMs > 0 && (
                    <span className="text-[9px] font-mono text-slate-400">
                      {formatDuration(step.durationMs)}
                    </span>
                  )}

                  {/* Status badge */}
                  <Badge
                    className={cn(
                      "border font-bold text-[10px] px-2 py-0 h-5",
                      cfg.badge
                    )}
                  >
                    {cfg.label}
                  </Badge>

                  {/* Expand chevron */}
                  {step.output && (
                    <div className="text-slate-400">
                      {isStepExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </div>
                  )}
                </div>
              </div>

              {/* Step detail (collapsible) */}
              {isStepExpanded && step.output && (
                <div className="ml-9 mr-2 p-3 bg-slate-50/80 border border-slate-100 rounded-xl space-y-2.5">
                  {/* Output text */}
                  {step.output.text && step.output.text !== "string" && (
                    <div>
                      <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                        Output
                      </p>
                      <p className="text-[11px] text-slate-700 bg-white border border-slate-100 rounded-lg p-2 max-h-32 overflow-y-auto leading-relaxed">
                        {step.output.text}
                      </p>
                    </div>
                  )}

                  {/* State */}
                  {Object.keys(step.output.state || {}).length > 0 && (
                    <div>
                      <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                        State
                      </p>
                      <pre className="text-[10px] text-slate-600 bg-white border border-slate-100 rounded-lg p-2 overflow-x-auto max-h-32 overflow-y-auto">
                        {JSON.stringify(step.output.state, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Metrics */}
                  {Object.keys(step.output.metrics || {}).length > 0 && (
                    <div>
                      <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                        Metrics
                      </p>
                      <pre className="text-[10px] text-slate-600 bg-white border border-slate-100 rounded-lg p-2 overflow-x-auto">
                        {JSON.stringify(step.output.metrics, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Logs */}
                  {step.logs.length > 0 && (
                    <div>
                      <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                        Logs ({step.logs.length})
                      </p>
                      <div className="space-y-0.5">
                        {step.logs.map((log, i) => (
                          <p key={i} className="text-[10px] text-slate-500 font-mono">
                            [{i + 1}] {log}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Timing */}
                  <div className="flex items-center gap-3 text-[9px] text-slate-400 pt-1 border-t border-slate-100">
                    {step.startedAt && (
                      <span>Bắt đầu: {formatTime(step.startedAt)}</span>
                    )}
                    {step.completedAt && (
                      <span>Hoàn thành: {formatTime(step.completedAt)}</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-slate-100">
        <p className="text-[10px] text-slate-400">
          {formatTime(timestamp)} • Hệ thống đã lập kế hoạch
        </p>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-[10px] text-indigo-600 hover:text-indigo-700 font-medium transition-colors"
        >
          {isExpanded ? "Thu gọn" : "Mở rộng"}
        </button>
      </div>
    </div>
  );
}

export default AgentPlanCard;