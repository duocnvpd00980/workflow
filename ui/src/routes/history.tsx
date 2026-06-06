"use client";

import { createFileRoute } from '@tanstack/react-router';
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
  Trash2
} from "lucide-react";
import { useMemo, useState } from "react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────
// MOCK DATA LỊCH SỬ CÔNG VIỆC
// ─────────────────────────────────────────────
const MOCK_JOB_HISTORY = [
  {
    id: "JOB-9921-A",
    title: "Chiến dịch marketing tháng 6",
    status: "running",
    triggeredBy: "Thành",
    startTime: "2026-06-02T14:32:00Z",
    endTime: null,
    duration: "45 phút (Đang chạy)",
    stepsCount: { done: 2, total: 5 },
    model: "Claude 4 Sonnet",
    cost: "$0.45",
    logs: [
      "[14:32:01] Khởi tạo nhiệm vụ: Tạo chiến dịch marketing tháng 6",
      "[14:32:05] ✓ Bước 1: Hoàn thành Research AI trends 2025",
      "[14:32:12] ▶ Bước 2: Đang viết blog 1,500 từ (Xử lý được 1,247 từ)..."
    ]
  },
  {
    id: "JOB-9812-B",
    title: "Phân tích báo cáo tài chính Q2 SaaS",
    status: "success",
    triggeredBy: "Thành",
    startTime: "2026-06-02T09:15:00Z",
    endTime: "2026-06-02T10:02:00Z",
    duration: "47 phút",
    stepsCount: { done: 4, total: 4 },
    model: "GPT-4o",
    cost: "$1.20",
    logs: [
      "[09:15:22] Nhận file PDF Báo cáo tài chính Q2.pdf",
      "[09:17:10] ✓ Trích xuất bảng cân đối kế toán thành công",
      "[09:30:45] ✓ Đang chạy thuật toán dự phóng doanh thu Q3",
      "[10:02:00] ✓ Xuất báo cáo dạng Markdown & biểu đồ hoàn tất."
    ]
  },
  {
    id: "JOB-9701-F",
    title: "Nghiên cứu đối thủ cạnh tranh (E-commerce)",
    status: "failed",
    triggeredBy: "Hệ thống (Lịch trình)",
    startTime: "2026-06-01T23:00:00Z",
    endTime: "2026-06-01T23:15:00Z",
    duration: "15 phút",
    stepsCount: { done: 1, total: 3 },
    model: "Gemini 2.0 Flash",
    cost: "$0.08",
    logs: [
      "[23:00:00] Kích hoạt tự động theo lịch trình",
      "[23:02:11] ✓ Thu thập dữ liệu từ 3/10 website đối thủ",
      "[23:15:00] ❌ Lỗi: Cloudflare chặn IP (403 Forbidden) tại mục tiêu chính.",
      "[23:15:02] Tiến trình bị hủy bỏ do cấu hình nghiêm ngặt."
    ]
  },
  {
    id: "JOB-9644-X",
    title: "Kiểm tra lỗ hổng bảo mật hệ thống (Security Audit)",
    status: "stopped",
    triggeredBy: "Admin",
    startTime: "2026-05-31T08:00:00Z",
    endTime: "2026-05-31T08:20:00Z",
    duration: "20 phút",
    stepsCount: { done: 3, total: 10 },
    model: "Llama 3 70B",
    cost: "$0.15",
    logs: [
      "[08:00:00] Khởi chạy công cụ quét lỗ hổng",
      "[08:10:22] ✓ Quét xong các cổng mạng (Port Scanning)",
      "[08:20:00] ✋ Người dùng bấm dừng khẩn cấp (User Interrupted)."
    ]
  }
];

export const Route = createFileRoute('/history')({
  component: JobHistoryPage,
});

export default function JobHistoryPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filteredJobs = useMemo(() => {
    return MOCK_JOB_HISTORY.filter(job => {
      const matchSearch = job.title.toLowerCase().includes(searchTerm.toLowerCase()) || job.id.toLowerCase().includes(searchTerm.toLowerCase());
      const matchStatus = statusFilter === "all" || job.status === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [searchTerm, statusFilter]);

  // Render Badge trạng thái đồng bộ hệ màu sắc Shadcn
  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "running":
        return <Badge className="bg-primary/10 text-primary hover:bg-primary/10 border-none font-bold text-[10px] px-2 py-0.5 flex gap-1 items-center"><PlayCircle size={12}/> Đang chạy</Badge>;
      case "success":
        return <Badge className="bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/10 border-none font-bold text-[10px] px-2 py-0.5 flex gap-1 items-center"><CheckCircle2 size={12}/> Thành công</Badge>;
      case "failed":
        return <Badge className="bg-destructive/10 text-destructive hover:bg-destructive/10 border-none font-bold text-[10px] px-2 py-0.5 flex gap-1 items-center"><AlertCircle size={12}/> Thất bại</Badge>;
      case "stopped":
        return <Badge className="bg-muted text-muted-foreground hover:bg-muted border-none font-bold text-[10px] px-2 py-0.5 flex gap-1 items-center"><StopCircle size={12}/> Đã dừng</Badge>;
      default:
        return null;
    }
  };

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
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-ring transition-all"
          />
        </div>

        <div className="flex items-center gap-1 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
          <SlidersHorizontal size={13} className="text-muted-foreground mr-1.5 shrink-0 hidden lg:inline" />
          {[
            { id: "all", label: "Tất cả" },
            { id: "running", label: "Đang chạy" },
            { id: "success", label: "Thành công" },
            { id: "failed", label: "Thất bại" },
            { id: "stopped", label: "Đã dừng" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
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

      {/* ─── DANH SÁCH THẺ TIẾN TRÌNH LỊCH SỬ LỒNG SHEET TRIGGER ─── */}
      <div className="space-y-3">
        {filteredJobs.length > 0 ? (
          filteredJobs.map((job) => (
            <Sheet key={job.id}>
              {/* Mỗi thẻ Task/Job đóng vai trò là một Trigger mở cửa sổ chi tiết */}
              <SheetTrigger asChild>
                <div className="p-4 border bg-background rounded-xl transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-muted-foreground/30 group">
                  
                  {/* Khối thông tin bên trái */}
                  <div className="flex items-start gap-3.5 min-w-0">
                    <div className={cn(
                      "p-2.5 rounded-lg mt-0.5 shrink-0 transition-colors",
                      job.status === "running" ? "bg-primary/10 text-primary" : 
                      job.status === "success" ? "bg-emerald-500/10 text-emerald-600" : 
                      job.status === "failed" ? "bg-destructive/10 text-destructive" : "bg-muted text-muted-foreground"
                    )}>
                      <History size={16} />
                    </div>
                    
                    <div className="space-y-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[10px] font-mono font-bold text-muted-foreground bg-muted px-1.5 py-0.5 rounded">{job.id}</span>
                        {renderStatusBadge(job.status)}
                      </div>
                      <h3 className="font-semibold text-sm text-foreground group-hover:text-primary transition-colors truncate pr-2 tracking-tight">{job.title}</h3>
                      
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground font-medium">
                        <span className="flex items-center gap-1"><Calendar size={11}/>{new Date(job.startTime).toLocaleDateString("vi-VN")}</span>
                        <span className="flex items-center gap-1"><Clock size={11}/>{job.duration}</span>
                        <span>Model: <strong className="text-foreground/80 font-semibold">{job.model}</strong></span>
                      </div>
                    </div>
                  </div>

                  {/* Khối hiển thị tiến độ bên phải */}
                  <div className="flex items-center justify-between sm:justify-end gap-6 border-t sm:border-none pt-3 sm:pt-0 shrink-0">
                    <div className="text-left sm:text-right space-y-1">
                      <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">Tiến độ</p>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-foreground">{job.stepsCount.done}/{job.stepsCount.total} Bước</span>
                        <div className="w-16 hidden md:block">
                          <Progress value={(job.stepsCount.done / job.stepsCount.total) * 100} className="h-1 bg-muted" />
                        </div>
                      </div>
                    </div>
                    <ChevronRight size={15} className="text-muted-foreground/60 group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                  </div>

                </div>
              </SheetTrigger>

              {/* ─── DRAWER PANEL XEM CHI TIẾT LOG & TRA CỨU TIÊU THỤ ─── */}
              <SheetContent className="w-full sm:max-w-[420px] rounded-l-[20px] md:rounded-l-xl p-6 flex flex-col h-full gap-4">
                <SheetHeader className="border-b pb-3 shrink-0">
                  <div className="flex items-center justify-between w-full pr-6">
                    <span className="text-[10px] font-mono font-bold text-muted-foreground bg-muted border px-1.5 py-0.5 rounded">{job.id}</span>
                    <span className="text-[11px] text-muted-foreground font-medium">Khởi chạy bởi: {job.triggeredBy}</span>
                  </div>
                  <SheetTitle className="text-sm font-bold text-foreground tracking-tight text-left pt-1 leading-snug">
                    {job.title}
                  </SheetTitle>
                </SheetHeader>

                {/* Thân Drawer chứa dữ liệu chi tiết */}
                <div className="flex-1 overflow-y-auto space-y-4 min-h-0 flex flex-col">
                  {/* Trạng thái hiện tại của tác vụ */}
                  <div className="flex items-center justify-between bg-muted/20 border p-3 rounded-xl shrink-0">
                    <span className="text-xs font-semibold text-muted-foreground">Trạng thái xử lý:</span>
                    {renderStatusBadge(job.status)}
                  </div>

                  {/* Chi phí & Mô hình sử dụng */}
                  <div className="grid grid-cols-2 gap-2.5 shrink-0">
                    <div className="bg-muted/40 border p-3 rounded-xl">
                      <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">Chi phí ước tính</span>
                      <span className="text-sm font-bold text-primary font-mono">{job.cost}</span>
                    </div>
                    <div className="bg-muted/40 border p-3 rounded-xl">
                      <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">Mô hình toán học</span>
                      <span className="text-xs font-semibold text-foreground truncate block">{job.model}</span>
                    </div>
                  </div>

                  {/* Dòng mốc dòng thời gian chạy */}
                  <div className="space-y-2 shrink-0 text-[11px] font-medium text-muted-foreground bg-muted/30 p-3 border rounded-xl">
                    <div className="flex justify-between">
                      <span>Thời điểm bắt đầu:</span>
                      <span className="text-foreground font-mono">{new Date(job.startTime).toLocaleTimeString("vi-VN")}</span>
                    </div>
                    {job.endTime && (
                      <div className="flex justify-between">
                        <span>Thời điểm kết thúc:</span>
                        <span className="text-foreground font-mono">{new Date(job.endTime).toLocaleTimeString("vi-VN")}</span>
                      </div>
                    )}
                    <div className="flex justify-between pt-1.5 border-t">
                      <span>Tổng thời gian thực thi:</span>
                      <span className="font-bold text-foreground">{job.duration}</span>
                    </div>
                  </div>

                  {/* Terminal Console Log màu đen hệ thống */}
                  <div className="flex-1 bg-neutral-950 rounded-xl p-3 flex flex-col font-mono text-[11px] leading-relaxed overflow-hidden text-neutral-300 shadow-inner min-h-[220px]">
                    <div className="flex items-center gap-1.5 mb-2 text-white font-sans text-[10px] font-bold tracking-wider shrink-0">
                      <FileText size={12} className="text-primary" />
                      <span>LOG TIẾN TRÌNH CHI TIẾT</span>
                    </div>
                    
                    <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 font-mono text-[10px] text-neutral-400">
                      {job.logs.map((log, idx) => {
                        let colorClass = "text-neutral-400";
                        if (log.includes("✓")) colorClass = "text-emerald-400";
                        if (log.includes("▶")) colorClass = "text-primary animate-pulse";
                        if (log.includes("❌")) colorClass = "text-destructive";
                        
                        return <p key={idx} className={colorClass}>{log}</p>;
                      })}
                    </div>
                  </div>
                </div>

                {/* Hệ thống cụm nút tương tác đáy ngăn kéo */}
                <div className="pt-3 border-t mt-auto space-y-2 shrink-0">
                  <button className="w-full h-8 text-[11px] bg-muted hover:bg-muted/80 text-foreground font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    <ArrowUpRight size={13}/> Mở Không gian làm việc
                  </button>
                  <button className="w-full h-8 text-[11px] bg-destructive/10 hover:bg-destructive/20 text-destructive font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    <Trash2 size={13}/> Xóa bản ghi lịch sử
                  </button>
                </div>

              </SheetContent>
            </Sheet>
          ))
        ) : (
          <div className="text-center py-12 border border-dashed rounded-xl bg-background">
            <History className="mx-auto text-muted-foreground/40 mb-2" size={28} />
            <p className="text-xs font-medium text-muted-foreground">Không tìm thấy lịch sử tiến trình nào phù hợp.</p>
          </div>
        )}
      </div>

    </div>
  );
}