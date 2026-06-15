"use client";

import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Zap, CheckCircle2, Loader2, Clock, AlertCircle, XCircle } from "lucide-react";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/config";



interface Task {
  id: number;
  title: string;
  status: "running" | "completed" | "stopped" | "failed" | "paused";
  progress_percent: number;
  steps_done: number;
  steps_total: number;
  duration_seconds: number | null;
  created_at: string;
  updated_at: string;
  finished_at: string | null;
  error_message: string | null;
}

interface TaskListResponse {
  items: Task[];
  total: number;
  limit: number;
  offset: number;
}

function Badge({ count }: { count: number }) {
  if (count === 0) return null;
  return (
    <span className="absolute -top-1 -right-1 h-4 min-w-4 px-0.5 flex items-center justify-center rounded-full bg-zinc-900 text-white text-[9px] font-bold leading-none">
      {count}
    </span>
  );
}

// ✅ Status badge thay vì progress bar
function StatusBadge({ status }: { status: Task["status"] }) {
  const styles = {
    running: "bg-amber-50 text-amber-700 border-amber-200",
    paused: "bg-blue-50 text-blue-700 border-blue-200",
    completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
    stopped: "bg-zinc-100 text-zinc-600 border-zinc-200",
    failed: "bg-red-50 text-red-700 border-red-200",
  };

  const labels = {
    running: "Đang chạy",
    paused: "Chờ duyệt",
    completed: "Hoàn thành",
    stopped: "Đã dừng",
    failed: "Thất bại",
  };

  const icons = {
    running: Loader2,
    paused: Clock,
    completed: CheckCircle2,
    stopped: XCircle,
    failed: AlertCircle,
  };

  const Icon = icons[status];

  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border",
      styles[status]
    )}>
      <Icon className={cn("h-3 w-3", status === "running" && "animate-spin")} />
      {labels[status]}
    </span>
  );
}

function formatAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  
  if (diffMin < 1) return "Vừa xong";
  if (diffMin < 60) return `${diffMin} phút trước`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour} giờ trước`;
  return `${Math.floor(diffHour / 24)} ngày trước`;
}

export function TaskBell() {
  const { data, isLoading, error } = useQuery<TaskListResponse>({
    queryKey: ["tasks", "bell"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/tasks?limit=20&offset=0`);
      if (!res.ok) throw new Error("Không thể tải danh sách tasks");
      return res.json();
    },
    refetchInterval: 5000,
    retry: 2,
  });

  const runningTasks = data?.items?.filter(t => t.status === "running") || [];
  const activeTasks = data?.items?.filter(t => t.status === "running" || t.status === "paused") || [];
  const doneTasks = data?.items?.filter(t => t.status === "completed" || t.status === "stopped" || t.status === "failed") || [];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="relative h-8 w-8 flex items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-100 transition-colors">
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Zap className="h-4 w-4" />
          )}
          <Badge count={activeTasks.length} />
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-80 rounded-xl shadow-lg border-zinc-200/80 p-0 overflow-hidden">
        
        {error && (
          <div className="p-4 text-center">
            <p className="text-[12px] text-red-500">{error.message}</p>
          </div>
        )}

        {/* Active Tasks (running + paused) */}
        {activeTasks.length > 0 && (
          <div className="p-3 border-b border-zinc-100">
            <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider mb-2.5">
              Đang hoạt động ({activeTasks.length})
            </p>
            <div className="space-y-3">
              {activeTasks.map((task) => (
                <div key={task.id} className="flex items-center justify-between">
                  <div className="flex-1 min-w-0 pr-3">
                    <p className="text-[12.5px] font-medium text-zinc-700 truncate">
                      {task.title}
                    </p>
                    <p className="text-[11px] text-zinc-400 mt-0.5">
                      {formatAgo(task.created_at)}
                    </p>
                  </div>
                  <StatusBadge status={task.status} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Done Tasks */}
        {doneTasks.length > 0 && (
          <div className="p-3 border-b border-zinc-100">
            <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              Hoàn thành ({doneTasks.length})
            </p>
            <div className="space-y-0.5">
              {doneTasks.slice(0, 5).map((task) => (
                <div key={task.id} className="flex items-center gap-2 h-8 px-1 rounded-md hover:bg-zinc-50 cursor-pointer transition-colors">
                  <StatusBadge status={task.status} />
                  <span className="text-[12.5px] text-zinc-600 truncate flex-1">{task.title}</span>
                  <span className="text-[11px] text-zinc-400 shrink-0">
                    {task.finished_at ? formatAgo(task.finished_at) : formatAgo(task.updated_at)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && activeTasks.length === 0 && doneTasks.length === 0 && (
          <div className="p-4 text-center">
            <p className="text-[12px] text-zinc-400">Không có task nào</p>
          </div>
        )}

        {/* Footer */}
        <div className="p-2">
          <Link
            to="/tasks"
            className="block w-full text-center text-[12px] text-zinc-500 hover:text-zinc-800 font-medium py-1.5 transition-colors"
          >
            Xem tất cả lịch sử →
          </Link>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}