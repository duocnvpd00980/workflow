"use client";

import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FileText, Mail, Smartphone, Target, Video,
  CheckCircle2, AlertCircle, PlayCircle, StopCircle,
  Clock, RefreshCw, Trash2, Eye, Square,
  RotateCcw, ChevronLeft, ChevronRight,
  Inbox, Loader2, ExternalLink, AlertTriangle,
  SlidersHorizontal, Search, Database, Wrench,
} from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────
// API CONFIG
// ─────────────────────────────────────────────
const API_BASE = "http://localhost:8000/api/v1";

// ─────────────────────────────────────────────
// TYPES — khớp với API hiện tại + field mới optional
// ─────────────────────────────────────────────
interface TaskStep {
  id: number;
  task_id: number;
  step_index: number;
  message: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
}

interface Task {
  id: number;
  source: string;                    // "marketing" | "research" | "rag"
  source_id: string;
  content_type: string | null;       // optional — API mới có
  title: string;
  status: "running" | "completed" | "failed" | "stopped";
  triggered_by: string | null;
  steps_done: number;
  steps_total: number;
  model: string | null;
  error_message: string | null;
  meta: Record<string, unknown> | null;  // optional — API mới có
  created_at: string;
  updated_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  progress_percent?: number;         // optional — API mới có, tự tính nếu thiếu
  steps?: TaskStep[];                // optional — chỉ có trong GET /tasks/{id}
}

interface TaskListResponse {
  items: Task[];
  total: number;
  limit: number;
  offset: number;
}

// ─────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────

// Map source → icon/color khi chưa có content_type
const SOURCE_CONFIG: Record<string, { label: string; icon: React.ElementType; iconBg: string }> = {
  marketing: { label: "Marketing", icon: Target,    iconBg: "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400" },
  research:  { label: "Research",  icon: Search,    iconBg: "bg-cyan-50 text-cyan-600 dark:bg-cyan-950/50 dark:text-cyan-400" },
  rag:       { label: "RAG",       icon: Database,  iconBg: "bg-violet-50 text-violet-600 dark:bg-violet-950/50 dark:text-violet-400" },
};

const CONTENT_TYPE_CONFIG: Record<string, { label: string; icon: React.ElementType; iconBg: string }> = {
  blog:     { label: "Blog",    icon: FileText,   iconBg: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400" },
  email:    { label: "Email",   icon: Mail,       iconBg: "bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400" },
  social:   { label: "Social",  icon: Smartphone, iconBg: "bg-pink-50 text-pink-600 dark:bg-pink-950/50 dark:text-pink-400" },
  ads:      { label: "Ads",     icon: Target,     iconBg: "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400" },
  video:    { label: "Video",   icon: Video,      iconBg: "bg-purple-50 text-purple-600 dark:bg-purple-950/50 dark:text-purple-400" },
  research: { label: "Research",icon: Search,     iconBg: "bg-cyan-50 text-cyan-600 dark:bg-cyan-950/50 dark:text-cyan-400" },
};

const STATUS_CONFIG: Record<string, { label: string; badgeClass: string; icon: React.ElementType }> = {
  running:   { label: "Đang chạy",  icon: PlayCircle,    badgeClass: "bg-blue-50 text-blue-600 border-blue-200/60 dark:bg-blue-950/20 dark:text-blue-400" },
  completed: { label: "Hoàn thành", icon: CheckCircle2,  badgeClass: "bg-emerald-50 text-emerald-600 border-emerald-200/60 dark:bg-emerald-950/20 dark:text-emerald-400" },
  failed:    { label: "Lỗi",        icon: AlertCircle,   badgeClass: "bg-red-50 text-red-600 border-red-200/60 dark:bg-red-950/20 dark:text-red-400" },
  stopped:   { label: "Đã dừng",    icon: StopCircle,    badgeClass: "bg-muted text-muted-foreground border-border" },
};

const FILTERS = [
  { label: "Tất cả",    value: "all" },
  { label: "Đang chạy", value: "running" },
  { label: "Hoàn thành",value: "completed" },
  { label: "Lỗi",       value: "failed" },
  { label: "Đã dừng",   value: "stopped" },
] as const;

// ─────────────────────────────────────────────
// UTILS
// ─────────────────────────────────────────────
function calcProgress(task: Task): number {
  if (task.status === "completed" || task.status === "failed" || task.status === "stopped") return 100;
  return 0;
}

function getTypeConfig(task: Task) {
  if (task.content_type && CONTENT_TYPE_CONFIG[task.content_type]) {
    return CONTENT_TYPE_CONFIG[task.content_type];
  }
  return SOURCE_CONFIG[task.source] ?? { label: task.source, icon: Wrench, iconBg: "bg-muted text-muted-foreground" };
}

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins  = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days  = Math.floor(diff / 86400000);
  if (mins < 1)  return "Vừa xong";
  if (mins < 60) return `${mins} phút trước`;
  if (hours < 24)return `${hours} giờ trước`;
  return `${days} ngày trước`;
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function formatDuration(secs: number | null): string {
  if (!secs) return "—";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return m > 0 ? `${m}p ${s}s` : `${s}s`;
}

function estimateRemaining(task: Task): string {
  if (task.status !== "running" || task.steps_done === 0) return "";
  const elapsed = (Date.now() - new Date(task.created_at).getTime()) / 1000;
  const rate = task.steps_done / elapsed;
  const remaining = (task.steps_total - task.steps_done) / rate;
  const mins = Math.ceil(remaining / 60);
  return mins > 0 ? `~${mins} phút` : "Sắp xong";
}

// ─────────────────────────────────────────────
// SMALL COMPONENTS
// ─────────────────────────────────────────────
function ContentTypeIcon({ task, className }: { task: Task; className?: string }) {
  const cfg = getTypeConfig(task);
  const Icon = cfg.icon;
  return (
    <span className={cn("inline-flex items-center justify-center w-7 h-7 rounded-lg shrink-0", cfg.iconBg, className)}>
      <Icon className="h-3.5 w-3.5" />
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.stopped;
  const Icon = cfg.icon;
  return (
    <Badge variant="outline" className={cn("text-[11px] font-medium px-2 py-0.5 rounded-full gap-1 inline-flex items-center border select-none", cfg.badgeClass)}>
      <Icon className="h-3 w-3" />
      {cfg.label}
    </Badge>
  );
}

function StepStatusIcon({ status }: { status: TaskStep["status"] }) {
  if (status === "completed") return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />;
  if (status === "running")   return <PlayCircle   className="h-3.5 w-3.5 text-blue-500 shrink-0 animate-pulse" />;
  if (status === "failed")    return <AlertCircle  className="h-3.5 w-3.5 text-red-500 shrink-0" />;
  return <Clock className="h-3.5 w-3.5 text-muted-foreground/40 shrink-0" />;
}

// ─────────────────────────────────────────────
// TASK DETAIL DRAWER
// ─────────────────────────────────────────────
function TaskDetailDrawer({ taskId, onStop, onRetry, onDelete, isStopping, isRetrying, isDeleting }: {
  taskId: number;
  onStop: () => void;
  onRetry: () => void;
  onDelete: () => void;
  isStopping: boolean;
  isRetrying: boolean;
  isDeleting: boolean;
}) {
  // Fetch chi tiết task (có steps) khi drawer mở
  const { data: task, isLoading } = useQuery<Task>({
    queryKey: ["tasks", "detail", taskId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/tasks/${taskId}`);
      if (!res.ok) throw new Error("Không thể tải chi tiết task");
      return res.json();
    },
    refetchInterval: 3000,
    retry: 1,
  });

  if (isLoading || !task) {
    return (
      <SheetContent className="w-full sm:max-w-[460px] p-0 flex flex-col h-full rounded-l-2xl">
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground/50" />
        </div>
      </SheetContent>
    );
  }

  const progress = calcProgress(task);
  const meta     = task.meta ?? {};
  const steps    = task.steps ?? [];
  const remaining = estimateRemaining(task);
  const typeCfg  = getTypeConfig(task);
  const runningStep = steps.find(s => s.status === "running");

  return (
    <SheetContent className="w-full sm:max-w-[460px] p-0 flex flex-col h-full gap-0 rounded-l-2xl overflow-hidden">

      {/* ── Section 1: Header ── */}
      <SheetHeader className="px-5 pt-5 pb-4 border-b shrink-0">
        <div className="flex items-start gap-3 mb-2">
          <ContentTypeIcon task={task} className="w-9 h-9 rounded-xl mt-0.5" />
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <StatusBadge status={task.status} />
              <span className="text-[10px] text-muted-foreground font-medium bg-muted px-1.5 py-0.5 rounded">
                {typeCfg.label}
              </span>
              {task.model && (
                <span className="text-[10px] text-muted-foreground font-mono bg-muted px-1.5 py-0.5 rounded">
                  {task.model}
                </span>
              )}
            </div>
          </div>
        </div>
        <SheetTitle className="text-sm font-bold text-foreground leading-snug tracking-tight text-left">
          {task.title}
        </SheetTitle>
        <p className="text-[11px] text-muted-foreground mt-0.5">
          Khởi chạy bởi <span className="font-medium text-foreground/70">{task.triggered_by ?? "hệ thống"}</span>
          {" · "}ID-{task.id}
          {" · "}{formatRelativeTime(task.created_at)}
        </p>
      </SheetHeader>

      {/* ── Body scroll ── */}
      <div className="flex-1 overflow-y-auto divide-y divide-border/40 min-h-0">

        {/* ── Section 2: Progress ── */}
        <div className="px-5 py-4 space-y-2.5">
          <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Tiến độ</p>
          <Progress value={progress} className="h-2" />
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-muted-foreground">
              Bước <span className="font-bold text-foreground">{task.steps_done}/{task.steps_total}</span>
              {runningStep && (
                <span className="ml-1 text-muted-foreground/60">· {runningStep.message}</span>
              )}
            </span>
            {remaining ? (
              <span className="text-muted-foreground font-medium">Còn {remaining}</span>
            ) : task.duration_seconds ? (
              <span className="text-muted-foreground font-medium">{formatDuration(task.duration_seconds)}</span>
            ) : null}
          </div>
        </div>

        {/* ── Section 3: Step Log ── */}
        {steps.length > 0 && (
          <div className="px-5 py-4 space-y-2">
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Nhật ký bước</p>
            <div className="space-y-2">
              {steps.map((step) => (
                <div key={step.id} className="flex items-start gap-2">
                  <StepStatusIcon status={step.status} />
                  <span className={cn(
                    "flex-1 text-[12px] leading-snug",
                    step.status === "completed" ? "text-foreground/75" :
                    step.status === "running"   ? "text-blue-600 dark:text-blue-400 font-medium" :
                    step.status === "failed"    ? "text-red-600 dark:text-red-400" :
                    "text-muted-foreground/40"
                  )}>
                    {step.message}
                    {step.status === "running" && " (đang chạy)"}
                  </span>
                  <span className="text-[10px] text-muted-foreground/50 shrink-0 font-mono">
                    {formatTime(step.created_at)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Section 4: Input / Request ── */}
        {(meta.prompt || meta.brand || meta.template || meta.tone) && (
          <div className="px-5 py-4 space-y-2">
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Yêu cầu</p>
            <div className="space-y-1.5 text-[12px]">
              {[
                ["Template",  meta.template],
                ["Brand",     meta.brand],
                ["Tone",      meta.tone],
                ["Framework", meta.framework],
                ["Độ dài",    meta.length],
              ].filter(([, v]) => v).map(([label, value]) => (
                <div key={String(label)} className="flex gap-2">
                  <span className="text-muted-foreground w-20 shrink-0">{String(label)}</span>
                  <span className="text-foreground font-medium">{String(value)}</span>
                </div>
              ))}
              {Array.isArray(meta.rag_docs) && (meta.rag_docs as string[]).length > 0 && (
                <div className="flex gap-2">
                  <span className="text-muted-foreground w-20 shrink-0">RAG docs</span>
                  <span className="text-foreground font-medium">{(meta.rag_docs as string[]).join(", ")}</span>
                </div>
              )}
              {meta.prompt && (
                <div className="mt-2 bg-muted/40 border border-border/60 rounded-lg p-3">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5">Prompt</p>
                  <p className="text-[12px] text-foreground/80 leading-relaxed italic">"{String(meta.prompt)}"</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Section 5: Output — completed ── */}
        {task.status === "completed" && meta.output_preview && (
          <div className="px-5 py-4 space-y-2">
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Kết quả</p>
            <div className="bg-muted/30 border border-border/60 rounded-lg p-3">
              <p className="text-[12px] text-foreground/80 leading-relaxed line-clamp-4 italic">
                "{String(meta.output_preview)}"
              </p>
            </div>
            {meta.content_id && (
              <button className="flex items-center gap-1.5 text-[12px] text-primary font-medium hover:underline">
                <ExternalLink className="h-3 w-3" />
                Xem đầy đủ →
              </button>
            )}
          </div>
        )}

        {/* ── Section 6: Error ── */}
        {task.status === "failed" && task.error_message && (
          <div className="px-5 py-4 space-y-2">
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Lỗi</p>
            <div className="bg-red-50 dark:bg-red-950/20 border border-red-200/60 dark:border-red-900/40 rounded-lg p-3 space-y-1.5">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-3.5 w-3.5 text-red-500 shrink-0 mt-0.5" />
                <p className="text-[12px] text-red-700 dark:text-red-400 font-medium break-words">{task.error_message}</p>
              </div>
              <p className="text-[11px] text-red-500/70 pl-5">
                Gợi ý: Thử lại với prompt ngắn hơn hoặc chia nhỏ task.
              </p>
            </div>
          </div>
        )}

        {/* Fallback khi task cũ không có meta/steps */}
        {steps.length === 0 && !meta.prompt && (
          <div className="px-5 py-4 space-y-1.5 text-[12px]">
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-2">Thông tin</p>
            <div className="flex gap-2">
              <span className="text-muted-foreground w-20 shrink-0">Source</span>
              <span className="text-foreground font-medium font-mono">{task.source}</span>
            </div>
            <div className="flex gap-2">
              <span className="text-muted-foreground w-20 shrink-0">Source ID</span>
              <span className="text-foreground font-medium font-mono">{task.source_id}</span>
            </div>
            {task.finished_at && (
              <div className="flex gap-2">
                <span className="text-muted-foreground w-20 shrink-0">Kết thúc</span>
                <span className="text-foreground font-medium">{formatTime(task.finished_at)}</span>
              </div>
            )}
            <div className="flex gap-2">
              <span className="text-muted-foreground w-20 shrink-0">Thời gian</span>
              <span className="text-foreground font-medium">{formatDuration(task.duration_seconds)}</span>
            </div>
          </div>
        )}

      </div>

      {/* ── Section 7: Actions footer ── */}
      <div className="px-5 py-4 border-t bg-muted/10 shrink-0 space-y-2">
        {task.status === "running" && (
          <Button
            variant="outline"
            className="w-full h-8 text-xs gap-1.5 text-destructive border-destructive/30 hover:bg-destructive/10 hover:text-destructive"
            onClick={onStop}
            disabled={isStopping}
          >
            {isStopping ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Square className="h-3.5 w-3.5" />}
            Hủy tác vụ
          </Button>
        )}

        {task.status === "completed" && (
          <div className="flex gap-2">
            {meta.content_id && (
              <Button variant="outline" className="flex-1 h-8 text-xs gap-1.5">
                <Eye className="h-3.5 w-3.5" /> Xem content
              </Button>
            )}
            <Button variant="outline" className="flex-1 h-8 text-xs gap-1.5" onClick={onRetry} disabled={isRetrying}>
              {isRetrying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
              Tạo lại
            </Button>
            <Button
              variant="outline"
              className="h-8 w-8 p-0 text-destructive border-destructive/30 hover:bg-destructive/10"
              onClick={onDelete}
              disabled={isDeleting}
            >
              {isDeleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
            </Button>
          </div>
        )}

        {(task.status === "failed" || task.status === "stopped") && (
          <div className="flex gap-2">
            <Button className="flex-1 h-8 text-xs gap-1.5" onClick={onRetry} disabled={isRetrying}>
              {isRetrying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
              Thử lại
            </Button>
            <Button
              variant="outline"
              className="h-8 w-8 p-0 text-destructive border-destructive/30 hover:bg-destructive/10"
              onClick={onDelete}
              disabled={isDeleting}
            >
              {isDeleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
            </Button>
          </div>
        )}
      </div>

    </SheetContent>
  );
}

// ─────────────────────────────────────────────
// TASK ROW
// ─────────────────────────────────────────────
function TaskRow({ task, onStop, onRetry, onDelete, isStopping, isRetrying, isDeleting }: {
  task: Task;
  onStop: (id: number) => void;
  onRetry: (id: number) => void;
  onDelete: (id: number) => void;
  isStopping: boolean;
  isRetrying: boolean;
  isDeleting: boolean;
}) {
  const [open, setOpen] = useState(false);
  const progress  = calcProgress(task);
  const typeCfg   = getTypeConfig(task);
  const meta      = task.meta ?? {};

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <div className="group flex items-center gap-3.5 px-4 h-14 cursor-pointer hover:bg-muted/40 transition-colors select-none">

          {/* Icon */}
          <ContentTypeIcon task={task} />

          {/* Task name + brand */}
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-medium text-foreground truncate group-hover:text-primary transition-colors">
              {task.title}
            </p>
            {meta.brand && (
              <p className="text-[11px] text-muted-foreground/60 truncate">{String(meta.brand)}</p>
            )}
          </div>

          {/* Type */}
          <span className="hidden md:block text-[11px] text-muted-foreground font-medium w-20 shrink-0">
            {typeCfg.label}
          </span>

          {/* Status + progress mini */}
          <div className="hidden sm:block w-28 shrink-0">
            <StatusBadge status={task.status} progress={progress} />
            {task.status === "running" && (
              <Progress value={progress} className="h-0.5 mt-1.5 bg-muted" />
            )}
          </div>

          {/* Time */}
          <span className="text-[11px] text-muted-foreground/70 font-medium whitespace-nowrap shrink-0 w-20 text-right">
            {formatRelativeTime(task.created_at)}
          </span>

          {/* Quick actions — hiện khi hover */}
          <div
            className="hidden sm:flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={(e) => e.stopPropagation()}
          >
            {task.status === "running" && (
              <Button variant="ghost" size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                onClick={() => onStop(task.id)} disabled={isStopping} title="Hủy">
                {isStopping ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Square className="h-3.5 w-3.5" />}
              </Button>
            )}
            {(task.status === "failed" || task.status === "stopped") && (
              <Button variant="ghost" size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-primary hover:bg-primary/10"
                onClick={() => onRetry(task.id)} disabled={isRetrying} title="Thử lại">
                {isRetrying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
              </Button>
            )}
            {task.status === "completed" && (
              <Button variant="ghost" size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-foreground hover:bg-muted" title="Xem">
                <Eye className="h-3.5 w-3.5" />
              </Button>
            )}
            <Button variant="ghost" size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
              onClick={(e) => {
                e.stopPropagation();
                if (window.confirm("Xác nhận xóa task này?")) onDelete(task.id);
              }}
              disabled={isDeleting} title="Xóa">
              {isDeleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
            </Button>
          </div>
        </div>
      </SheetTrigger>

      {open && (
        <TaskDetailDrawer
          taskId={task.id}
          onStop={() => { onStop(task.id); setOpen(false); }}
          onRetry={() => onRetry(task.id)}
          onDelete={() => {
            if (window.confirm("Xác nhận xóa task này?")) {
              onDelete(task.id);
              setOpen(false);
            }
          }}
          isStopping={isStopping}
          isRetrying={isRetrying}
          isDeleting={isDeleting}
        />
      )}
    </Sheet>
  );
}

// ─────────────────────────────────────────────
// ROUTE
// ─────────────────────────────────────────────
export const Route = createFileRoute("/tasks")({
  component: TaskPage,
});

// ─────────────────────────────────────────────
// PAGE
// ─────────────────────────────────────────────
export default function TaskPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchTerm, setSearchTerm]     = useState("");
  const [offset, setOffset]             = useState(0);
  const [limit]                         = useState(20);

  // ── Query: danh sách tasks ──
  const { data: taskListData, isLoading, error } = useQuery<TaskListResponse>({
    queryKey: ["tasks", "list", statusFilter, searchTerm, offset],
    queryFn: async () => {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });
      if (statusFilter !== "all") params.append("status", statusFilter);
      if (searchTerm.trim())      params.append("search", searchTerm);

      const res = await fetch(`${API_BASE}/tasks?${params}`);
      if (!res.ok) throw new Error("Không thể tải danh sách tasks");
      return res.json();
    },
    refetchInterval: 5000,
    retry: 2,
  });

  // ── Mutations ──
  const stopMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`${API_BASE}/tasks/${id}/stop`, { method: "POST" });
      // Nếu endpoint chưa có thì fallback silent
      if (!res.ok && res.status !== 404) throw new Error();
      return res.ok ? res.json() : null;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const retryMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`${API_BASE}/tasks/${id}/retry`, { method: "POST" });
      if (!res.ok && res.status !== 404) throw new Error();
      return res.ok ? res.json() : null;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`${API_BASE}/tasks/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error();
      return res.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const tasks = taskListData?.items ?? [];

  return (
    <div className="h-[calc(100vh-4rem)] overflow-hidden bg-background flex flex-col">

      {/* ── Toolbar ── */}
      <div className="shrink-0 flex items-center justify-between px-4 h-12 border-b border-border/60 bg-background gap-2 select-none">
        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost" size="sm"
            className="h-8 text-xs gap-1.5 text-muted-foreground hover:bg-muted/80"
            onClick={() => queryClient.invalidateQueries({ queryKey: ["tasks"] })}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Làm mới</span>
          </Button>
          <Separator orientation="vertical" className="h-4" />
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            <input
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setOffset(0); }}
              placeholder="Tìm task..."
              className="h-8 pl-8 pr-3 text-xs bg-muted/50 border border-border/60 rounded-lg focus:outline-none focus:ring-1 focus:ring-ring w-44 transition-all"
            />
          </div>
        </div>

        <span className="text-xs text-muted-foreground font-medium hidden sm:block">
          {taskListData?.total ?? 0} tác vụ
        </span>
      </div>

      {/* ── Filter bar ── */}
      <div className="shrink-0 flex items-center gap-1.5 px-4 h-10 border-b border-border/40 bg-muted/20 overflow-x-auto scrollbar-none select-none">
        <SlidersHorizontal className="h-3.5 w-3.5 text-muted-foreground/50 shrink-0 mr-0.5" />
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => { setStatusFilter(f.value); setOffset(0); }}
            className={cn(
              "inline-flex items-center px-3 h-6 rounded-full text-xs font-medium whitespace-nowrap transition-all duration-150",
              statusFilter === f.value
                ? "bg-foreground text-background shadow-sm font-semibold"
                : "text-muted-foreground hover:text-foreground hover:bg-accent/80"
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* ── Column headers ── */}
      <div className="shrink-0 flex items-center gap-3.5 px-4 h-8 border-b border-border/30 bg-muted/10">
        <div className="w-7 shrink-0" />
        <span className="flex-1 text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Task</span>
        <span className="hidden md:block text-[10px] font-bold text-muted-foreground uppercase tracking-wider w-20 shrink-0">Type</span>
        <span className="hidden sm:block text-[10px] font-bold text-muted-foreground uppercase tracking-wider w-28 shrink-0">Status</span>
        <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider w-20 text-right shrink-0">Thời gian</span>
        <div className="hidden sm:block w-24 shrink-0" />
      </div>

      {/* ── Task list ── */}
      <div className="flex-1 overflow-y-auto divide-y divide-border/30">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin opacity-40" />
            <p className="text-xs font-medium">Đang tải...</p>
          </div>
        ) : tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground py-16">
            <Inbox className="h-9 w-9 opacity-25 stroke-[1.5]" />
            <p className="text-xs font-medium">
              {error ? "Không thể tải dữ liệu" : "Không có task nào"}
            </p>
          </div>
        ) : (
          tasks.map((task) => (
            <TaskRow
              key={task.id}
              task={task}
              onStop={(id) => stopMutation.mutate(id)}
              onRetry={(id) => retryMutation.mutate(id)}
              onDelete={(id) => deleteMutation.mutate(id)}
              isStopping={stopMutation.isPending && stopMutation.variables === task.id}
              isRetrying={retryMutation.isPending && retryMutation.variables === task.id}
              isDeleting={deleteMutation.isPending && deleteMutation.variables === task.id}
            />
          ))
        )}
      </div>

      {/* ── Pagination ── */}
      {taskListData && taskListData.total > limit && (
        <div className="shrink-0 flex items-center justify-center gap-2 px-4 h-11 border-t border-border/40">
          <Button variant="ghost" size="icon" className="h-7 w-7"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}>
            <ChevronLeft className="h-3.5 w-3.5" />
          </Button>
          <span className="text-xs text-muted-foreground font-medium">
            {offset + 1}–{Math.min(offset + limit, taskListData.total)} / {taskListData.total}
          </span>
          <Button variant="ghost" size="icon" className="h-7 w-7"
            disabled={offset + limit >= taskListData.total}
            onClick={() => setOffset(offset + limit)}>
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}

    </div>
  );
}
