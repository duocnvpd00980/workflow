"use client";

import { createFileRoute } from '@tanstack/react-router';
import { 
  MenuIcon, 
  TrendingUp, 
  Clock, 
  DollarSign, 
  CheckCircle2, 
  AlertTriangle, 
  ArrowUpRight,
  TrendingDown, 
  RefreshCw, 
  FileSpreadsheet, 
  Layers, 
  HelpCircle 
} from "lucide-react";
import { useState } from "react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

// ─── MOCK DATA CHO ANALYTICS ────────────────────────────────────────────────
const MOCK_OVERVIEW_METRICS = {
  totalJobs: { value: "142", change: "+12%", isPositive: true },
  avgDuration: { value: "18m 45s", change: "-4.2%", isPositive: true }, 
  totalCost: { value: "$48.60", change: "+8.3%", isPositive: false },
  successRate: { value: "94.2%", change: "+1.5%", isPositive: true }
};

const MOCK_MODEL_USAGE = [
  { name: "Claude 4 Sonnet", requests: 840, percentage: 55, cost: "$28.20", color: "bg-indigo-600" },
  { name: "GPT-4o", requests: 420, percentage: 30, cost: "$16.50", color: "bg-emerald-500" },
  { name: "Gemini 2.0 Flash", requests: 210, percentage: 15, cost: "$3.90", color: "bg-amber-500" }
];

const MOCK_TOP_AGENTS = [
  { name: "Writer Agent", taskType: "Content Generation", successRate: "98%", executions: 48 },
  { name: "Research Agent", taskType: "Web Crawling & Analysis", successRate: "91%", executions: 62 },
  { name: "Designer Agent", taskType: "Image & Banner Creation", successRate: "95%", executions: 22 },
  { name: "Ads Manager Agent", taskType: "Campaign Deploy", successRate: "89%", executions: 10 }
];

export const Route = createFileRoute('/analytics')({
  component: AnalyticsPage,
});

export default function AnalyticsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [timeRange, setTimeRange] = useState("7d");

  return (
    <div className="flex w-full min-h-screen bg-[#fafbfc] text-slate-900 select-none antialiased font-sans">
      
      {/* ─── MAIN CENTER (Khu vực Đồ thị & Chỉ số phân tích tổng quan) ─── */}
      <main className="flex-1 flex flex-col min-w-0 bg-slate-50/60 overflow-hidden relative">
        
        {/* HEADER CHÍNH */}
        <header className="h-14 bg-white border-b flex items-center justify-between px-6 shrink-0 z-10 shadow-xs">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => setSidebarOpen(true)} className="p-1.5 -ml-1.5 hover:bg-slate-100 rounded-md text-slate-500 md:hidden shrink-0">
              <MenuIcon size={18} />
            </button>
            <h2 className="font-bold text-[15px] text-slate-800">Analytics & Báo cáo</h2>
            <div className="h-4 w-px bg-slate-200" />
            <span className="text-[11px] text-slate-500 font-medium hidden sm:inline">Dữ liệu tính toán thời gian thực</span>
          </div>

          {/* Cụm chức năng bộ lọc và gọi Drawer hạn mức */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Bộ lọc thời gian */}
            <div className="bg-white border rounded-xl p-0.5 flex gap-0.5 shadow-xs">
              {[
                { id: "24h", label: "24h" },
                { id: "7d", label: "7 ngày" },
                { id: "30d", label: "30 ngày" },
              ].map((range) => (
                <button
                  key={range.id}
                  onClick={() => setTimeRange(range.id)}
                  className={cn(
                    "px-2.5 py-1 text-[11px] font-bold rounded-lg transition-colors outline-none",
                    timeRange === range.id ? "bg-slate-900 text-white shadow-sm" : "text-slate-600 hover:bg-slate-50"
                  )}
                >
                  {range.label}
                </button>
              ))}
            </div>

            {/* TRIGGER SHEET: Mở xem nhanh Giới hạn định mức thay thế Cột 3 */}
            <Sheet>
              <SheetTrigger asChild>
                <button className="h-8 px-3 hover:bg-amber-50 text-amber-700 bg-amber-50/40 border border-amber-200/60 rounded-xl text-[11px] font-bold flex items-center gap-1.5 transition-colors shadow-xs">
                  <AlertTriangle size={13} className="text-amber-600" />
                  <span>Xem định mức</span>
                </button>
              </SheetTrigger>
              
              <SheetContent className="w-full sm:max-w-[400px] rounded-l-[20px] md:rounded-l-xl p-6 flex flex-col h-full gap-5">
                <SheetHeader className="border-b pb-3 shrink-0">
                  <div className="flex items-center justify-between w-full pr-6">
                    <SheetTitle className="text-sm font-bold text-slate-800">Giới hạn định mức</SheetTitle>
                    <RefreshCw size={13} className="text-slate-400 cursor-pointer hover:rotate-45 transition-transform" />
                  </div>
                </SheetHeader>

                {/* Vùng nội dung Hạn ngạch & Khuyến nghị */}
                <div className="flex-1 overflow-y-auto space-y-5 min-h-0 flex flex-col">
                  {/* Quota Trackers */}
                  <div className="space-y-4 border-b pb-5">
                    <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Hạn mức tài khoản tháng này</p>
                    
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-[11px] font-medium text-slate-600">
                        <span>Ngân sách API LLM</span>
                        <span className="font-bold text-slate-800 font-mono">$48.60 / $100.00</span>
                      </div>
                      <Progress value={48.6} className="h-1.5 bg-slate-100 [&>div]:bg-indigo-600" />
                    </div>

                    <div className="space-y-1.5">
                      <div className="flex justify-between text-[11px] font-medium text-slate-600">
                        <span>Số lượng Task thực thi</span>
                        <span className="font-bold text-slate-800 font-mono">142 / 500 tasks</span>
                      </div>
                      <Progress value={28.4} className="h-1.5 bg-slate-100 [&>div]:bg-emerald-500" />
                    </div>
                  </div>

                  {/* Thẻ khuyến nghị thông minh */}
                  <div className="bg-amber-50/60 border border-amber-200/50 rounded-xl p-4 space-y-2.5 shadow-xs shrink-0">
                    <div className="flex items-center gap-1.5 text-amber-800 font-bold text-[12px]">
                      <AlertTriangle size={14} className="text-amber-600 shrink-0" />
                      <span>Khuyến nghị tối ưu chi phí</span>
                    </div>
                    <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
                      Hệ thống nhận thấy mô hình <strong className="text-indigo-600 font-semibold">Claude 4 Sonnet</strong> đang chiếm <strong className="font-semibold">55%</strong> tổng tài nguyên nhưng chủ yếu xử lý các tác vụ dịch thuật đơn giản. 
                    </p>
                    <p className="text-[11px] text-amber-700 font-bold underline cursor-pointer hover:text-amber-800 flex items-center gap-0.5">
                      Chuyển sang Gemini để tiết kiệm ~30% chi phí <ArrowUpRight size={12}/>
                    </p>
                  </div>
                </div>

                {/* Tài liệu thống kê dưới đáy */}
                <div className="border-2 border-dashed border-slate-100 rounded-xl p-4 flex flex-col justify-center items-center text-center text-slate-400 mt-auto shrink-0 bg-slate-50/30">
                  <HelpCircle size={20} className="text-slate-300 mb-1.5" />
                  <h4 className="text-[12px] font-bold text-slate-700 mb-0.5">Cần xuất báo cáo tùy chỉnh?</h4>
                  <p className="text-[10px] font-medium px-2 max-w-[220px]">Liên hệ Quản trị viên để cấu hình Webhook đẩy dữ liệu trực tiếp.</p>
                </div>
              </SheetContent>
            </Sheet>

            <button className="h-8 px-2.5 hover:bg-slate-100 rounded-xl border bg-white text-slate-600 text-[11px] font-bold flex items-center gap-1 shadow-xs">
              <FileSpreadsheet size={13} /> <span className="hidden sm:inline">Xuất Báo cáo</span>
            </button>
          </div>
        </header>

        {/* NỘI DUNG BÁO CÁO CHÍNH */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="max-w-[1000px] mx-auto space-y-6">
            
            {/* Hàng 4 Thẻ chỉ số tổng quan */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              
              {/* Thẻ 1: Tổng công việc */}
              <div className="bg-white border border-slate-100 p-4 rounded-2xl shadow-xs space-y-2">
                <div className="flex justify-between items-center text-slate-400">
                  <span className="text-[10px] font-bold uppercase tracking-wider">Tổng công việc</span>
                  <div className="p-1.5 bg-indigo-50 text-indigo-600 rounded-lg"><Layers size={14}/></div>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-[20px] font-extrabold text-slate-800 font-mono">{MOCK_OVERVIEW_METRICS.totalJobs.value}</span>
                  <span className="text-[10px] font-bold text-emerald-600 flex items-center"><TrendingUp size={10} className="mr-0.5"/>{MOCK_OVERVIEW_METRICS.totalJobs.change}</span>
                </div>
                <p className="text-[10px] text-slate-400 font-medium">Nhiệm vụ giao cho Agent</p>
              </div>

              {/* Thẻ 2: Thời gian xử lý trung bình */}
              <div className="bg-white border border-slate-100 p-4 rounded-2xl shadow-xs space-y-2">
                <div className="flex justify-between items-center text-slate-400">
                  <span className="text-[10px] font-bold uppercase tracking-wider">Thời gian trung bình</span>
                  <div className="p-1.5 bg-amber-50 text-amber-600 rounded-lg"><Clock size={14}/></div>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-[20px] font-extrabold text-slate-800 font-mono">{MOCK_OVERVIEW_METRICS.avgDuration.value}</span>
                  <span className="text-[10px] font-bold text-emerald-600 flex items-center"><TrendingDown size={10} className="mr-0.5"/>{MOCK_OVERVIEW_METRICS.avgDuration.change}</span>
                </div>
                <p className="text-[10px] text-slate-400 font-medium">Tối ưu hóa tốc độ phần cứng</p>
              </div>

              {/* Thẻ 3: Tổng chi phí Token */}
              <div className="bg-white border border-slate-100 p-4 rounded-2xl shadow-xs space-y-2">
                <div className="flex justify-between items-center text-slate-400">
                  <span className="text-[10px] font-bold uppercase tracking-wider">Chi phí Token</span>
                  <div className="p-1.5 bg-rose-50 text-rose-600 rounded-lg"><DollarSign size={14}/></div>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-[20px] font-extrabold text-slate-800 font-mono">{MOCK_OVERVIEW_METRICS.totalCost.value}</span>
                  <span className="text-[10px] font-bold text-rose-600 flex items-center"><TrendingUp size={10} className="mr-0.5"/>{MOCK_OVERVIEW_METRICS.totalCost.change}</span>
                </div>
                <p className="text-[10px] text-slate-400 font-medium">Phát sinh từ cổng API LLM</p>
              </div>

              {/* Thẻ 4: Tỷ lệ thành công */}
              <div className="bg-white border border-slate-100 p-4 rounded-2xl shadow-xs space-y-2">
                <div className="flex justify-between items-center text-slate-400">
                  <span className="text-[10px] font-bold uppercase tracking-wider">Tỷ lệ thành công</span>
                  <div className="p-1.5 bg-emerald-50 text-emerald-600 rounded-lg"><CheckCircle2 size={14}/></div>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-[20px] font-extrabold text-slate-800 font-mono">{MOCK_OVERVIEW_METRICS.successRate.value}</span>
                  <span className="text-[10px] font-bold text-emerald-600 flex items-center"><TrendingUp size={10} className="mr-0.5"/>{MOCK_OVERVIEW_METRICS.successRate.change}</span>
                </div>
                <p className="text-[10px] text-slate-400 font-medium">Hạn chế tối đa lỗi ngắt quãng</p>
              </div>

            </div>

            {/* Khối Đồ thị Phân phối Mô hình LLM */}
            <div className="bg-white border border-slate-100 rounded-2xl p-5 shadow-xs space-y-4">
              <div className="flex justify-between items-center">
                <div className="space-y-0.5">
                  <h3 className="text-[14px] font-bold text-slate-800">Tỷ lệ sử dụng mô hình ngôn ngữ lớn (LLM)</h3>
                  <p className="text-[11px] text-slate-400 font-medium">Dựa trên khối lượng Token xử lý và số Request gửi đi</p>
                </div>
                <span className="text-[11px] font-mono font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">API Phân phối</span>
              </div>

              {/* Thanh Tiến Trình Phân Cấp Đồ Thị */}
              <div className="h-3.5 w-full bg-slate-100 rounded-full flex overflow-hidden shadow-inner">
                {MOCK_MODEL_USAGE.map((m, idx) => (
                  <div 
                    key={idx} 
                    style={{ width: `${m.percentage}%` }} 
                    className={`${m.color} h-full first:rounded-l-full last:rounded-r-full transition-all`} 
                    title={`${m.name}: ${m.percentage}%`}
                  />
                ))}
              </div>

              {/* Bảng chú giải chi tiết */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                {MOCK_MODEL_USAGE.map((m, idx) => (
                  <div key={idx} className="p-3 border border-slate-50 bg-slate-50/40 rounded-xl flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className={`w-2.5 h-2.5 rounded-full ${m.color} shrink-0`}></div>
                      <div className="min-w-0">
                        <p className="text-[12px] font-bold text-slate-700 truncate">{m.name}</p>
                        <p className="text-[10px] text-slate-400 font-medium">{m.requests} requests</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-[12px] font-extrabold text-slate-800 font-mono">{m.percentage}%</p>
                      <p className="text-[10px] text-slate-400 font-mono">{m.cost}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Bảng Hiệu suất Từng Agent Độc Lập */}
            <div className="bg-white border border-slate-100 rounded-2xl p-5 shadow-xs space-y-3">
              <div className="flex justify-between items-center border-b pb-3">
                <h3 className="text-[14px] font-bold text-slate-800">Xếp hạng hiệu suất các Sub-Agent</h3>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Độ ổn định hệ thống</span>
              </div>

              <div className="divide-y text-[13px]">
                {MOCK_TOP_AGENTS.map((agent, index) => (
                  <div key={index} className="py-3 flex items-center justify-between gap-4 first:pt-0 last:pb-0">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center font-mono font-bold text-[11px] text-slate-500 shrink-0">
                        #{index + 1}
                      </div>
                      <div className="min-w-0">
                        <p className="font-bold text-slate-800 truncate">{agent.name}</p>
                        <p className="text-[11px] text-slate-400 truncate">{agent.taskType}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-6 shrink-0 text-right">
                      <div className="space-y-0.5">
                        <p className="text-[10px] text-slate-400 font-medium">Số lượt chạy</p>
                        <p className="font-bold font-mono text-slate-700 text-[12px]">{agent.executions} lần</p>
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-[10px] text-slate-400 font-medium">Thành công</p>
                        <Badge className="bg-emerald-50 text-emerald-700 border-none hover:bg-emerald-50 font-bold font-mono text-[11px] px-1.5 py-0">{agent.successRate}</Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      </main>
    </div>
  );
}