import { createFileRoute } from '@tanstack/react-router'
"use client";

import { useQuery } from "@tanstack/react-query";
import { 
  Zap, History, Settings, BarChart3, MenuIcon, LogOut, MessageSquarePlus,
  Search, SlidersHorizontal, CheckCircle2, AlertCircle, PlayCircle, StopCircle,
  Calendar, Clock, HardDrive, ArrowUpRight, ChevronRight, FileText, Download, Trash2
} from "lucide-react";
import { useMemo, useState } from "react";
import { fetchConversations, queryKeys, type Conv } from "../lib/api";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import SidebarNav from '@/components/layout/navbar';

// ─── Mock Data cho Lịch sử công việc chi tiết ───────────────────────────────
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
})


export default function JobHistoryPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedJobId, setSelectedJobId] = useState<string>("JOB-9921-A");

  // Lấy danh sách conversation gốc để đồng bộ sidebar trái
  const { data: conversations = [] } = useQuery<Conv[]>({
    queryKey: queryKeys.conversations,
    staleTime: 30_000,
  });

  // Tìm job đang được chọn để hiển thị ở Inspector bên phải
  const selectedJob = useMemo(() => {
    return MOCK_JOB_HISTORY.find(j => j.id === selectedJobId) || MOCK_JOB_HISTORY[0];
  }, [selectedJobId]);

  // Lọc danh sách job theo ô tìm kiếm và bộ lọc trạng thái
  const filteredJobs = useMemo(() => {
    return MOCK_JOB_HISTORY.filter(job => {
      const matchSearch = job.title.toLowerCase().includes(searchTerm.toLowerCase()) || job.id.toLowerCase().includes(searchTerm.toLowerCase());
      const matchStatus = statusFilter === "all" || job.status === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [searchTerm, statusFilter]);

  // Render Badge trạng thái chuẩn chỉnh
  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "running":
        return <Badge className="bg-indigo-100 text-indigo-700 hover:bg-indigo-100 border-none font-bold text-[10px] px-2 py-0.5 flex gap-1 items-center"><PlayCircle size={12}/> Đang chạy</Badge>;
      case "success":
        return <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-none font-bold text-[10px] px-2 py-0.5 flex gap-1 items-center"><CheckCircle2 size={12}/> Thành công</Badge>;
      case "failed":
        return <Badge className="bg-rose-100 text-rose-700 hover:bg-rose-100 border-none font-bold text-[10px] px-2 py-0.5 flex gap-1 items-center"><AlertCircle size={12}/> Thất bại</Badge>;
      case "stopped":
        return <Badge className="bg-slate-100 text-slate-600 hover:bg-slate-100 border-none font-bold text-[10px] px-2 py-0.5 flex gap-1 items-center"><StopCircle size={12}/> Đã dừng</Badge>;
      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#fafbfc] text-slate-900 select-none antialiased font-sans">
      
      {/* ─── 1. SIDEBAR TRÁI (Giữ nguyên cấu trúc đồng bộ từ Chat Page) ─── */}
      <aside className={`fixed inset-y-0 left-0 z-30 flex w-[260px] flex-col border-r bg-white transition-transform duration-200 md:relative md:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        

        <SidebarNav />

        {/* Danh sách mini các công việc đang chạy nạp từ API */}
        <div className="flex-1 overflow-y-auto px-3 py-4 flex flex-col min-h-0">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1 mb-2.5">Đang chạy</p>
          <div className="p-3 border border-indigo-100 rounded-xl bg-indigo-50/20 shadow-xs relative mb-4">
            <div className="flex justify-between items-start mb-1.5">
              <span className="text-[12px] font-bold text-slate-800 truncate">Chiến dịch tháng 6</span>
              <span className="text-[10px] text-indigo-600 font-bold">60%</span>
            </div>
            <Progress value={60} className="h-1 bg-slate-100 [&>div]:bg-indigo-600" />
          </div>

          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1 mb-2">Gần đây</p>
          <div className="space-y-1">
            {conversations.slice(0, 4).map((c) => (
              <div key={c.id} className="w-full flex items-center justify-between p-1.5 rounded-lg text-[12px] text-slate-600">
                <span className="truncate pr-2">✓ {c.title}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="border-t p-3 shrink-0 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-[11px] font-bold shrink-0">TH</div>
            <span className="text-[13px] font-medium text-slate-700 truncate">Thành</span>
          </div>
          <button title="Tạo Session mới" className="p-1.5 hover:bg-slate-200/60 text-slate-400 hover:text-slate-600 rounded-md transition-colors">
            <MessageSquarePlus size={16} />
          </button>
        </div>
      </aside>

      {/* ─── 2. MAIN CENTER (Bảng quản lý Lịch sử công việc) ─── */}
      <main className="flex-1 flex flex-col min-w-0 bg-slate-50/60 overflow-hidden relative">
        {/* Header chính */}
        <header className="h-14 bg-white border-b flex items-center justify-between px-6 shrink-0 z-10 shadow-xs">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => setSidebarOpen(true)} className="p-1.5 -ml-1.5 hover:bg-slate-100 rounded-md text-slate-500 md:hidden shrink-0">
              <MenuIcon size={18} />
            </button>
            <h2 className="font-bold text-[15px] text-slate-800">Lịch sử công việc</h2>
            <div className="h-4 w-px bg-slate-200" />
            <span className="text-[11px] text-slate-500 font-medium hidden sm:inline">Tổng số: {MOCK_JOB_HISTORY.length} tiến trình</span>
          </div>

          <div className="flex items-center gap-2">
            <button className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-500 text-[12px] font-medium flex items-center gap-1 border border-slate-200 bg-white">
              <Download size={14} /> Xuất CSV
            </button>
          </div>
        </header>

        {/* Khu vực công cụ bộ lọc (Filter Toolbar) */}
        <div className="bg-white border-b p-4 flex flex-col sm:flex-row gap-3 items-center justify-between shrink-0">
          {/* Ô tìm kiếm */}
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Tìm kiếm mã Job hoặc tên..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 text-[13px] bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>

          {/* Các nút lọc Trạng thái nhanh */}
          <div className="flex items-center gap-1 w-full sm:w-auto overflow-x-auto self-start sm:self-auto">
            <SlidersHorizontal size={14} className="text-slate-400 mr-2 shrink-0 hidden md:inline" />
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
                className={`px-3 py-1.5 text-[12px] font-medium rounded-lg whitespace-nowrap transition-colors ${statusFilter === tab.id ? "bg-indigo-600 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"}`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Nội dung danh sách các Job cũ */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-[900px] mx-auto space-y-3">
            {filteredJobs.length > 0 ? (
              filteredJobs.map((job) => (
                <div
                  key={job.id}
                  onClick={() => setSelectedJobId(job.id)}
                  className={`p-4 border bg-white rounded-2xl shadow-xs transition-all cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-slate-300 ${selectedJobId === job.id ? "ring-2 ring-indigo-500/80 border-transparent shadow-sm" : "border-slate-100"}`}
                >
                  {/* Left content inside card */}
                  <div className="flex items-start gap-3.5 min-w-0">
                    <div className={`p-2.5 rounded-xl mt-0.5 shrink-0 ${job.status === "running" ? "bg-indigo-50 text-indigo-600" : job.status === "success" ? "bg-emerald-50 text-emerald-600" : job.status === "failed" ? "bg-rose-50 text-rose-600" : "bg-slate-50 text-slate-500"}`}>
                      <History size={18} />
                    </div>
                    <div className="space-y-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[10px] font-mono font-bold text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">{job.id}</span>
                        {renderStatusBadge(job.status)}
                      </div>
                      <h3 className="font-bold text-[14px] text-slate-800 truncate pr-2 tracking-tight">{job.title}</h3>
                      
                      {/* Meta info row */}
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400 font-medium">
                        <span className="flex items-center gap-1"><Calendar size={12}/>{new Date(job.startTime).toLocaleDateString("vi-VN")}</span>
                        <span className="flex items-center gap-1"><Clock size={12}/>{job.duration}</span>
                        <span>Model: <strong className="text-slate-600 font-semibold">{job.model}</strong></span>
                      </div>
                    </div>
                  </div>

                  {/* Right progress/action inside card */}
                  <div className="flex items-center justify-between md:justify-end gap-6 border-t md:border-none pt-3 md:pt-0 shrink-0">
                    <div className="text-left md:text-right space-y-1">
                      <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Tiến độ</p>
                      <div className="flex items-center gap-2">
                        <span className="text-[12px] font-bold text-slate-700">{job.stepsCount.done}/{job.stepsCount.total} Bước</span>
                        <div className="w-16 hidden sm:block">
                          <Progress value={(job.stepsCount.done / job.stepsCount.total) * 100} className="h-1" />
                        </div>
                      </div>
                    </div>
                    <ChevronRight size={16} className={`text-slate-400 transition-transform ${selectedJobId === job.id ? "translate-x-1 text-indigo-500" : ""}`} />
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-12 border-2 border-dashed border-slate-200 rounded-2xl bg-white">
                <History className="mx-auto text-slate-300 mb-2" size={32} />
                <p className="text-[13px] font-medium text-slate-500">Không tìm thấy lịch sử thực thi công việc nào phù hợp.</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ─── 3. INSPECTOR SIDEBAR PHẢI (Chi tiết Log & Tài nguyên của Job được chọn) ─── */}
      <aside className="w-[340px] border-l bg-white hidden xl:flex flex-col shrink-0 overflow-hidden">
        {/* Header */}
        <div className="h-14 border-b flex items-center justify-between px-4 shrink-0">
          <span className="text-[13px] font-bold text-slate-800">Chi tiết công việc</span>
          <span className="text-[10px] font-mono font-bold text-slate-400 bg-slate-50 border px-1.5 py-0.5 rounded">{selectedJob.id}</span>
        </div>

        {/* Nội dung thanh bên phải */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5 flex flex-col min-h-0">
          
          {/* Tên & Trạng thái lớn */}
          <div className="space-y-1.5 border-b pb-4 shrink-0">
            <h4 className="font-bold text-[14px] text-slate-800 leading-snug tracking-tight">{selectedJob.title}</h4>
            <div className="flex items-center justify-between">
              {renderStatusBadge(selectedJob.status)}
              <span className="text-[11px] text-slate-400 font-medium">Bởi: {selectedJob.triggeredBy}</span>
            </div>
          </div>

          {/* Chi tiết tài nguyên tiêu thụ */}
          <div className="grid grid-cols-2 gap-2.5 shrink-0">
            <div className="bg-slate-50/70 border border-slate-100 p-3 rounded-xl">
              <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Chi phí ước tính</span>
              <span className="text-[15px] font-extrabold text-indigo-600 font-mono">{selectedJob.cost}</span>
            </div>
            <div className="bg-slate-50/70 border border-slate-100 p-3 rounded-xl">
              <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Mô hình xử lý</span>
              <span className="text-[12px] font-bold text-slate-700 truncate block">{selectedJob.model}</span>
            </div>
          </div>

          {/* Thời gian biểu */}
          <div className="space-y-2 shrink-0 text-[11px] font-medium text-slate-600 bg-slate-50/40 p-3 border rounded-xl">
            <div className="flex justify-between">
              <span className="text-slate-400">Thời gian bắt đầu:</span>
              <span>{new Date(selectedJob.startTime).toLocaleTimeString("vi-VN")}</span>
            </div>
            {selectedJob.endTime && (
              <div className="flex justify-between">
                <span className="text-slate-400">Thời gian kết thúc:</span>
                <span>{new Date(selectedJob.endTime).toLocaleTimeString("vi-VN")}</span>
              </div>
            )}
            <div className="flex justify-between pt-1.5 border-t border-slate-200/50">
              <span className="text-slate-400">Tổng thời gian:</span>
              <span className="font-bold text-slate-800">{selectedJob.duration}</span>
            </div>
          </div>

          {/* Console Log độc lập của riêng Job được chọn */}
          <div className="flex-1 bg-slate-900 rounded-xl p-3.5 flex flex-col font-mono text-[11px] leading-relaxed overflow-hidden text-slate-300 shadow-inner min-h-[220px]">
            <div className="flex items-center gap-1.5 mb-2.5 text-white font-sans text-[10px] font-bold tracking-wider shrink-0">
              <FileText size={12} className="text-indigo-400" />
              <span>LOG TIẾN TRÌNH CHI TIẾT</span>
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 font-mono text-[10.5px]">
              {selectedJob.logs.map((log, idx) => {
                let colorClass = "text-slate-400";
                if (log.includes("✓")) colorClass = "text-emerald-400";
                if (log.includes("▶")) colorClass = "text-indigo-400 animate-pulse";
                if (log.includes("❌")) colorClass = "text-rose-400";
                
                return <p key={idx} className={colorClass}>{log}</p>;
              })}
            </div>
          </div>

          {/* Khối Actions cuối góc phải */}
          <div className="pt-2 border-t mt-auto space-y-2 shrink-0">
            <button className="w-full h-9 text-[12px] bg-slate-100 text-slate-700 font-bold rounded-xl flex items-center justify-center gap-1.5 hover:bg-slate-200 transition-colors">
              <ArrowUpRight size={14}/> Mở Workspace Nhiệm Vụ
            </button>
            <button className="w-full h-9 text-[12px] bg-rose-50 hover:bg-rose-100 text-rose-600 font-bold rounded-xl flex items-center justify-center gap-1.5 transition-colors">
              <Trash2 size={14}/> Xóa Log Lịch Sử
            </button>
          </div>

        </div>
      </aside>

    </div>
  );
}