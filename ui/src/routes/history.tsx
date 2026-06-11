"use client";

import { createFileRoute } from '@tanstack/react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  History,
  Search,
  SlidersHorizontal,
  CheckCircle2,
  AlertCircle,
  PlayCircle,
  StopCircle,
  Calendar,
  Clock,
  ArrowUpRight,
  ChevronRight,
  FileText,
  Trash2,
  Loader2
} from "lucide-react";
import { useMemo, useState } from "react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────
// API CONFIG
// ─────────────────────────────────────────────
const API_BASE = "http://localhost:8000/api/v1";

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────
interface Task {
  id: number;
  source: string;
  source_id: string;
  title: string;
  status: string;
  triggered_by: string | null;
  steps_done: number;
  steps_total: number;
  model: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
}

interface TaskListResponse {
  items: Task[];
  total: number;
  limit: number;
  offset: number;
}

export const Route = createFileRoute('/history')({
  component: JobHistoryPage,
});

export default function JobHistoryPage() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [offset, setOffset] = useState(0);
  const [limit] = useState(20);
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);

  // ─── QUERY 1: Lấy danh sách tasks ───
  const { data: taskListData, isLoading: isLoadingList, error: listError } = useQuery<TaskListResponse>({
    queryKey: ["tasks", "list", statusFilter, searchTerm, offset, limit],
    queryFn: async () => {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });

      if (statusFilter !== "all") {
        params.append("status", statusFilter);
      }

      if (searchTerm.trim()) {
        params.append("search", searchTerm);
      }

      const res = await fetch(`${API_BASE}/tasks?${params.toString()}`);
      if (!res.ok) throw new Error("Không thể tải danh sách tasks");
      return await res.json();
    },
    retry: 2,
    refetchInterval: 5000,
  });

  // ─── QUERY 2: Lấy chi tiết task ───
  const { data: selectedTask, isLoading: isLoadingDetail } = useQuery<Task>({
    queryKey: ["tasks", "detail", selectedTaskId],
    queryFn: async () => {
      if (!selectedTaskId) throw new Error("No task selected");
      const res = await fetch(`${API_BASE}/tasks/${selectedTaskId}`);
      if (!res.ok) throw new Error("Không thể tải chi tiết task");
      return await res.json();
    },
    enabled: !!selectedTaskId,
    retry: 1,
  });

  // ─── MUTATION: Xóa task ───
  const deleteTaskMutation = useMutation({
    mutationFn: async (taskId: number) => {
      const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Không thể xóa task");
      return await res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks", "list"] });
      setSelectedTaskId(null);
    },
  });

  // ─── UTILS ───
  const formatDuration = (durationSeconds: number | null) => {
    if (!durationSeconds) return "Đang chạy...";
    const minutes = Math.floor(durationSeconds / 60);
    const seconds = durationSeconds % 60;
    return `${minutes} phút ${seconds} giây`;
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString("vi-VN");
  };

  const getStatusColorClass = (status: string) => {
    switch (status) {
      case "running":
        return "bg-primary/10 text-primary";
      case "completed":
        return "bg-emerald-500/10 text-emerald-600";
      case "failed":
        return "bg-destructive/10 text-destructive";
      case "stopped":
        return "bg-muted text-muted-foreground";
      default:
        return "bg-muted text-muted-foreground";
    }
  };

  // Render Badge trạng thái
  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "running":
        return <Badge className="bg-primary/10 text-primary hover:bg-primary/10 border-none font-bold text-[10px] px-2 py-0.5 flex gap-1 items-center"><PlayCircle size={12}/> Đang chạy</Badge>;
      case "completed":
        return <Badge className="bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/10 border-none font-bold text-[10px] px-2 py-0.5 flex gap-1 items-center"><CheckCircle2 size={12}/> Thành công</Badge>;
      case "failed":
        return <Badge className="bg-destructive/10 text-destructive hover:bg-destructive/10 border-none font-bold text-[10px] px-2 py-0.5 flex gap-1 items-center"><AlertCircle size={12}/> Thất bại</Badge>;
      case "stopped":
        return <Badge className="bg-muted text-muted-foreground hover:bg-muted border-none font-bold text-[10px] px-2 py-0.5 flex gap-1 items-center"><StopCircle size={12}/> Đã dừng</Badge>;
      default:
        return null;
    }
  };

  const filteredJobs = taskListData?.items || [];

  return (
    <div className="space-y-4 max-w-[1000px] mx-auto w-full">
      
      {/* ─── THANH CÔNG CỤ: TÌM KIẾM & PHÂN LOẠI ─── */}
      <div className="bg-background border rounded-xl p-4 flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-64">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Tìm mã Job hoặc tên..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setOffset(0);
            }}
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-ring transition-all"
          />
        </div>

        <div className="flex items-center gap-1 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
          <SlidersHorizontal size={13} className="text-muted-foreground mr-1.5 shrink-0 hidden lg:inline" />
          {[
            { id: "all", label: "Tất cả" },
            { id: "running", label: "Đang chạy" },
            { id: "completed", label: "Thành công" },
            { id: "failed", label: "Thất bại" },
            { id: "stopped", label: "Đã dừng" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setStatusFilter(tab.id);
                setOffset(0);
              }}
              className={cn(
                "px-3 py-1.5 text-[11px] font-semibold rounded-lg whitespace-nowrap transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring",
                statusFilter === tab.id
                  ? "bg-foreground text-background shadow-sm"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* ─── DANH SÁCH THẺ TIẾN TRÌNH LỊCH SỬ ─── */}
      <div className="space-y-3">
        {isLoadingList ? (
          <div className="text-center py-12 border border-dashed rounded-xl bg-background">
            <Loader2 className="mx-auto text-muted-foreground/40 mb-2 animate-spin" size={28} />
            <p className="text-xs font-medium text-muted-foreground">Đang tải lịch sử...</p>
          </div>
        ) : filteredJobs.length > 0 ? (
          filteredJobs.map((job) => (
            <Sheet key={job.id}>
              <SheetTrigger asChild>
                <div 
                  onClick={() => setSelectedTaskId(job.id)}
                  className="p-4 border bg-background rounded-xl transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-muted-foreground/30 group"
                >
                  
                  {/* Khối thông tin bên trái */}
                  <div className="flex items-start gap-3.5 min-w-0">
                    <div className={cn(
                      "p-2.5 rounded-lg mt-0.5 shrink-0 transition-colors",
                      getStatusColorClass(job.status)
                    )}>
                      <History size={16} />
                    </div>
                    
                    <div className="space-y-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[10px] font-mono font-bold text-muted-foreground bg-muted px-1.5 py-0.5 rounded">ID-{job.id}</span>
                        {renderStatusBadge(job.status)}
                      </div>
                      <h3 className="font-semibold text-sm text-foreground group-hover:text-primary transition-colors truncate pr-2 tracking-tight">{job.title}</h3>
                      
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground font-medium">
                        <span className="flex items-center gap-1"><Calendar size={11}/>{new Date(job.created_at).toLocaleDateString("vi-VN")}</span>
                        <span className="flex items-center gap-1"><Clock size={11}/>{formatDuration(job.duration_seconds)}</span>
                        {job.model && (
                          <span>Model: <strong className="text-foreground/80 font-semibold">{job.model}</strong></span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Khối hiển thị tiến độ bên phải */}
                  <div className="flex items-center justify-between sm:justify-end gap-6 border-t sm:border-none pt-3 sm:pt-0 shrink-0">
                    <div className="text-left sm:text-right space-y-1">
                      <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">Tiến độ</p>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-foreground">{job.steps_done}/{job.steps_total} Bước</span>
                        <div className="w-16 hidden md:block">
                          <Progress value={(job.steps_total > 0 ? (job.steps_done / job.steps_total) * 100 : 0)} className="h-1 bg-muted" />
                        </div>
                      </div>
                    </div>
                    <ChevronRight size={15} className="text-muted-foreground/60 group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                  </div>

                </div>
              </SheetTrigger>

              {/* ─── SHEET DETAIL ─── */}
              <SheetContent className="w-full sm:max-w-[420px] rounded-l-[20px] md:rounded-l-xl p-6 flex flex-col h-full gap-4">
                <SheetHeader className="border-b pb-3 shrink-0">
                  <div className="flex items-center justify-between w-full pr-6">
                    <span className="text-[10px] font-mono font-bold text-muted-foreground bg-muted border px-1.5 py-0.5 rounded">ID-{job.id}</span>
                    <span className="text-[11px] text-muted-foreground font-medium">Khởi chạy bởi: {job.triggered_by || "Hệ thống"}</span>
                  </div>
                  <SheetTitle className="text-sm font-bold text-foreground tracking-tight text-left pt-1 leading-snug">
                    {job.title}
                  </SheetTitle>
                </SheetHeader>

                {/* Thân Sheet */}
                {isLoadingDetail ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 size={24} className="animate-spin text-muted-foreground" />
                  </div>
                ) : selectedTask ? (
                  <div className="flex-1 overflow-y-auto space-y-4 min-h-0 flex flex-col">
                    {/* Trạng thái */}
                    <div className="flex items-center justify-between bg-muted/20 border p-3 rounded-xl shrink-0">
                      <span className="text-xs font-semibold text-muted-foreground">Trạng thái xử lý:</span>
                      {renderStatusBadge(selectedTask.status)}
                    </div>

                    {/* Source & Model */}
                    <div className="grid grid-cols-2 gap-2.5 shrink-0">
                      <div className="bg-muted/40 border p-3 rounded-xl">
                        <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">Nguồn</span>
                        <span className="text-sm font-bold text-primary font-mono">{selectedTask.source}</span>
                      </div>
                      <div className="bg-muted/40 border p-3 rounded-xl">
                        <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">Mô hình</span>
                        <span className="text-xs font-semibold text-foreground truncate block">{selectedTask.model || "N/A"}</span>
                      </div>
                    </div>

                    {/* Timeline */}
                    <div className="space-y-2 shrink-0 text-[11px] font-medium text-muted-foreground bg-muted/30 p-3 border rounded-xl">
                      <div className="flex justify-between">
                        <span>Bắt đầu:</span>
                        <span className="text-foreground font-mono">{formatTime(selectedTask.created_at)}</span>
                      </div>
                      {selectedTask.finished_at && (
                        <div className="flex justify-between">
                          <span>Kết thúc:</span>
                          <span className="text-foreground font-mono">{formatTime(selectedTask.finished_at)}</span>
                        </div>
                      )}
                      <div className="flex justify-between pt-1.5 border-t">
                        <span>Tổng thời gian:</span>
                        <span className="font-bold text-foreground">{formatDuration(selectedTask.duration_seconds)}</span>
                      </div>
                    </div>

                    {/* Error message */}
                    {selectedTask.error_message && (
                      <div className="bg-destructive/10 border border-destructive/20 p-3 rounded-xl">
                        <p className="text-[10px] font-bold text-destructive uppercase tracking-wider mb-1">Lỗi</p>
                        <p className="text-[11px] text-destructive/80 break-words">{selectedTask.error_message}</p>
                      </div>
                    )}

                    {/* Progress */}
                    <div className="bg-muted/20 border p-3 rounded-xl">
                      <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-2">Tiến độ chi tiết</p>
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground">Bước hoàn thành:</span>
                          <span className="font-bold text-foreground">{selectedTask.steps_done}/{selectedTask.steps_total}</span>
                        </div>
                        <Progress 
                          value={(selectedTask.steps_total > 0 ? (selectedTask.steps_done / selectedTask.steps_total) * 100 : 0)}
                          className="h-2"
                        />
                      </div>
                    </div>

                    {/* Terminal Console Log */}
                    <div className="flex-1 bg-neutral-950 rounded-xl p-3 flex flex-col font-mono text-[11px] leading-relaxed overflow-hidden text-neutral-300 shadow-inner min-h-[180px]">
                      <div className="flex items-center gap-1.5 mb-2 text-white font-sans text-[10px] font-bold tracking-wider shrink-0">
                        <FileText size={12} className="text-primary" />
                        <span>CHI TIẾT TÁC VỤ</span>
                      </div>
                      
                      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 text-neutral-400">
                        <p>Task ID: {selectedTask.id}</p>
                        <p>Source: {selectedTask.source} ({selectedTask.source_id})</p>
                        <p>Status: {selectedTask.status}</p>
                        <p>Progress: {selectedTask.steps_done}/{selectedTask.steps_total}</p>
                        {selectedTask.status === "running" && (
                          <p className="text-primary animate-pulse">⚙ Đang xử lý...</p>
                        )}
                        {selectedTask.status === "completed" && (
                          <p className="text-emerald-400">✓ Hoàn thành</p>
                        )}
                        {selectedTask.status === "failed" && (
                          <p className="text-destructive">❌ Lỗi</p>
                        )}
                        {selectedTask.status === "stopped" && (
                          <p className="text-muted-foreground">⏸ Đã dừng</p>
                        )}
                      </div>
                    </div>

                  </div>
                ) : null}

                {/* Nút tương tác */}
                <div className="pt-3 border-t mt-auto space-y-2 shrink-0">
                  <button className="w-full h-8 text-[11px] bg-muted hover:bg-muted/80 text-foreground font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    <ArrowUpRight size={13}/> Mở Không gian làm việc
                  </button>
                  <button 
                    onClick={() => {
                      if (job.id && window.confirm("Xác nhận xóa task?")) {
                        deleteTaskMutation.mutate(job.id);
                      }
                    }}
                    disabled={deleteTaskMutation.isPending}
                    className="w-full h-8 text-[11px] bg-destructive/10 hover:bg-destructive/20 disabled:opacity-50 text-destructive font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {deleteTaskMutation.isPending ? (
                      <>
                        <Loader2 size={13} className="animate-spin"/> Đang xóa...
                      </>
                    ) : (
                      <>
                        <Trash2 size={13}/> Xóa bản ghi lịch sử
                      </>
                    )}
                  </button>
                </div>

              </SheetContent>
            </Sheet>
          ))
        ) : (
          <div className="text-center py-12 border border-dashed rounded-xl bg-background">
            <History className="mx-auto text-muted-foreground/40 mb-2" size={28} />
            <p className="text-xs font-medium text-muted-foreground">
              {listError ? "Có lỗi tải dữ liệu" : "Không tìm thấy lịch sử tiến trình nào phù hợp."}
            </p>
          </div>
        )}
      </div>

      {/* ─── PAGINATION ─── */}
      {taskListData && taskListData.total > 0 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <button
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
            className="px-3 py-1 text-xs rounded border disabled:opacity-50 hover:bg-muted transition-colors"
          >
            Trước
          </button>
          <span className="text-xs text-muted-foreground">
            {offset + 1} - {Math.min(offset + limit, taskListData.total)} / {taskListData.total}
          </span>
          <button
            onClick={() => {
              if (offset + limit < taskListData.total) {
                setOffset(offset + limit);
              }
            }}
            disabled={offset + limit >= taskListData.total}
            className="px-3 py-1 text-xs rounded border disabled:opacity-50 hover:bg-muted transition-colors"
          >
            Tiếp
          </button>
        </div>
      )}

    </div>
  );
}