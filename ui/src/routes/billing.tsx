"use client";

import { MenuIcon, PiggyBank, ShieldAlert, Sliders, 
ArrowDownRight,  Building2, HelpCircle,
  FileDown, Plus, CheckCircle2,
} from "lucide-react";
import { useState } from "react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { createFileRoute } from "@tanstack/react-router";
import SidebarNav from "@/layout/navbar";

// ─── Mock Data cho Hệ thống Kế toán & Hạn mức ──────────────────────────────
const MOCK_BILLING_SUMMARY = {
  currentUsage: 48.60,
  monthlyBudget: 150.00,
  creditRemaining: 241.40,
  estimatedTotal: 62.50,
};

const MOCK_DEPARTMENT_BUDGETS = [
  { id: "dept-1", name: "Đội ngũ Marketing", used: 28.20, limit: 50.00, agentCount: 3, status: "safe" },
  { id: "dept-2", name: "Phòng Tech & Dev Sandbox", used: 16.50, limit: 20.00, agentCount: 2, status: "warning" },
  { id: "dept-3", name: "Phòng Chăm sóc Khách hàng", used: 3.90, limit: 80.00, agentCount: 1, status: "safe" },
];

const MOCK_INVOICES = [
  { id: "INV-2026-005", date: "2026-06-01", amount: "$42.10", status: "paid" },
  { id: "INV-2026-004", date: "2026-05-01", amount: "$89.50", status: "paid" },
  { id: "INV-2026-003", date: "2026-04-01", amount: "$112.00", status: "paid" },
];

export const Route = createFileRoute('/billing')({
  component: BillingBudgetingPage,
})


export default function BillingBudgetingPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [globalHardLimit, setGlobalHardLimit] = useState(150);

  const handleDeposit = () => {
    toast.success("Đang chuyển hướng đến cổng thanh toán Stripe / VNPay...");
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#fafbfc] text-slate-900 select-none antialiased font-sans">
      
      {/* ─── 1. SIDEBAR TRÁI (Đồng bộ cấu trúc 100% điều hướng) ─── */}
      <aside className={`fixed inset-y-0 left-0 z-30 flex w-[260px] flex-col border-r bg-white transition-transform duration-200 md:relative md:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        
        <SidebarNav />

        <div className="flex-1 overflow-y-auto px-3 py-4 flex flex-col min-h-0">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1 mb-2">Số dư hiện tại</p>
          <div className="p-3 border border-emerald-100 rounded-xl bg-emerald-50/20 shadow-xs">
            <span className="text-[20px] font-extrabold font-mono text-emerald-700">${MOCK_BILLING_SUMMARY.creditRemaining.toFixed(2)}</span>
            <p className="text-[10px] text-emerald-600 font-medium mt-1">Sẵn sàng phân bổ token</p>
          </div>
        </div>

        <div className="border-t p-3 shrink-0 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-[11px] font-bold shrink-0">TH</div>
            <span className="text-[13px] font-medium text-slate-700 truncate">Thành</span>
          </div>
        </div>
      </aside>

      {/* ─── 2. MAIN CENTER (Quản lý Hạn ngạch & Theo dõi Ngân sách Phòng ban) ─── */}
      <main className="flex-1 flex flex-col min-w-0 bg-slate-50/60 overflow-hidden relative">
        <header className="h-14 bg-white border-b flex items-center justify-between px-6 shrink-0 z-10 shadow-xs">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => setSidebarOpen(true)} className="p-1.5 -ml-1.5 hover:bg-slate-100 rounded-md text-slate-500 md:hidden shrink-0"><MenuIcon size={18} /></button>
            <h2 className="font-bold text-[15px] text-slate-800">Chi phí & Hạn mức Token</h2>
            <div className="h-4 w-px bg-slate-200" />
            <span className="text-[11px] text-slate-500 font-medium hidden sm:inline">Chu kỳ tính toán: Tháng 06/2026</span>
          </div>

          <button onClick={handleDeposit} className="h-8 px-3 text-[11px] bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold flex items-center gap-1.5 shadow-md transition-all">
            <Plus size={13} /> Nạp thêm tiền quỹ
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="max-w-[800px] mx-auto space-y-6">
            
            {/* Thẻ Đo lường Tiêu thụ Tổng quan */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-white border border-slate-100 p-4 rounded-2xl shadow-xs space-y-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Đã tiêu thụ (Tháng này)</span>
                <div className="text-[22px] font-extrabold text-slate-800 font-mono">${MOCK_BILLING_SUMMARY.currentUsage.toFixed(2)}</div>
                <Progress value={(MOCK_BILLING_SUMMARY.currentUsage / MOCK_BILLING_SUMMARY.monthlyBudget) * 100} className="h-1 bg-slate-100 [&>div]:bg-indigo-600" />
              </div>

              <div className="bg-white border border-slate-100 p-4 rounded-2xl shadow-xs space-y-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Ngưỡng giới hạn cứng</span>
                <div className="text-[22px] font-extrabold text-slate-800 font-mono">${MOCK_BILLING_SUMMARY.monthlyBudget.toFixed(2)}</div>
                <span className="text-[10px] text-slate-400 font-medium">Đạt {((MOCK_BILLING_SUMMARY.currentUsage / MOCK_BILLING_SUMMARY.monthlyBudget) * 100).toFixed(1)}% giới hạn</span>
              </div>

              <div className="bg-white border border-slate-100 p-4 rounded-2xl shadow-xs space-y-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Dự báo cuối tháng</span>
                <div className="text-[22px] font-extrabold text-slate-600 font-mono">${MOCK_BILLING_SUMMARY.estimatedTotal.toFixed(2)}</div>
                <span className="text-[10px] text-emerald-600 font-bold flex items-center"><ArrowDownRight size={12} className="mr-0.5"/> Nằm trong tầm kiểm soát</span>
              </div>
            </div>

            {/* Quản lý Hạn ngạch Phân rã theo Phòng ban (Granular Department Budgeting) */}
            <div className="bg-white border border-slate-100 rounded-2xl p-5 shadow-xs space-y-4">
              <div className="flex justify-between items-center border-b pb-3">
                <div className="flex items-center gap-2">
                  <Building2 size={16} className="text-indigo-600" />
                  <h3 className="text-[13.5px] font-bold text-slate-800">Cấu hình ngân sách theo Phòng ban / Dự án</h3>
                </div>
                <button className="text-[11px] font-bold text-indigo-600 hover:underline flex items-center gap-0.5"><Plus size={12}/> Tạo phòng ban mới</button>
              </div>

              <div className="space-y-3">
                {MOCK_DEPARTMENT_BUDGETS.map((dept) => {
                  const percentage = (dept.used / dept.limit) * 100;
                  return (
                    <div key={dept.id} className="p-4 border border-slate-100 bg-slate-50/30 rounded-xl space-y-2.5">
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="font-bold text-[13px] text-slate-800">{dept.name}</h4>
                          <p className="text-[10px] text-slate-400 font-medium">Mã phân cấp: {dept.id} • Kích hoạt {dept.agentCount} Agent</p>
                        </div>
                        <div className="text-right">
                          <span className="font-mono font-bold text-[13px] text-slate-800">${dept.used.toFixed(2)}</span>
                          <span className="text-slate-400 text-[11px] font-mono"> / ${dept.limit.toFixed(2)}</span>
                        </div>
                      </div>

                      <div className="space-y-1">
                        <Progress 
                          value={percentage} 
                          className={`h-1.5 bg-slate-100 ${dept.status === "warning" ? "[&>div]:bg-amber-500" : "[&>div]:bg-emerald-500"}`} 
                        />
                        <div className="flex justify-between items-center text-[10px] font-medium">
                          <span className="text-slate-400">Đã tiêu thụ {percentage.toFixed(0)}%</span>
                          {dept.status === "warning" && <span className="text-amber-600 font-bold bg-amber-50 px-1.5 py-0.2 rounded">Sắp chạm ngưỡng tối đa</span>}
                          {dept.status === "safe" && <span className="text-emerald-600 font-bold">An toàn</span>}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Bảng Lịch sử Hóa đơn điện tử (Invoices Archive) */}
            <div className="bg-white border border-slate-100 rounded-2xl p-5 shadow-xs space-y-3">
              <div className="flex justify-between items-center border-b pb-3">
                <h3 className="text-[13.5px] font-bold text-slate-800">Lịch sử thanh toán & Sao kê</h3>
                <span className="text-[10px] text-slate-400 font-mono">Báo cáo tài chính</span>
              </div>

              <div className="divide-y text-[12.5px]">
                {MOCK_INVOICES.map((inv) => (
                  <div key={inv.id} className="py-3 flex items-center justify-between first:pt-0 last:pb-0">
                    <div className="space-y-0.5">
                      <p className="font-bold text-slate-800 font-mono">{inv.id}</p>
                      <p className="text-[11px] text-slate-400 font-medium">Ngày thanh toán: {new Date(inv.date).toLocaleDateString("vi-VN")}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="font-mono font-bold text-slate-700">{inv.amount}</span>
                      <Badge className="bg-emerald-50 text-emerald-700 border-none hover:bg-emerald-50 font-bold text-[10.5px] px-2 py-0.5 flex items-center gap-0.5">
                        <CheckCircle2 size={11}/> Thành công
                      </Badge>
                      <button title="Tải xuống hóa đơn PDF" className="p-1 hover:bg-slate-100 rounded-md text-slate-400 hover:text-slate-600 transition-colors">
                        <FileDown size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      </main>

      {/* ─── 3. INSPECTOR SIDEBAR PHẢI (Cài đặt Ngưỡng báo động & Chặn khẩn cấp) ─── */}
      <aside className="w-[300px] border-l bg-white hidden xl:flex flex-col shrink-0 overflow-hidden">
        <div className="h-14 border-b flex items-center justify-between px-4 shrink-0">
          <span className="text-[13px] font-bold text-slate-800">Thiết lập Ngưỡng cảnh báo</span>
          <Sliders size={14} className="text-slate-400" />
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-6 flex flex-col min-h-0">
          
          {/* Cài đặt Ngưỡng Giới Hạn Cứng (Global Hard Limit) */}
          <div className="space-y-3 shrink-0">
            <div className="flex justify-between items-center text-[11px]">
              <span className="font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                Giới hạn cứng / Tháng
                <HelpCircle size={12} className="text-slate-300 cursor-help" />
              </span>
              <span className="font-mono font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.2 rounded text-[12px]">${globalHardLimit}</span>
            </div>
            <input
              type="range"
              min="50"
              max="500"
              step="50"
              value={globalHardLimit}
              onChange={(e) => setGlobalHardLimit(parseInt(e.target.value))}
              className="w-full accent-indigo-600 h-1 bg-slate-100 rounded-lg cursor-pointer"
            />
            <p className="text-[10px] text-slate-400 font-medium">Bảo hiểm tài chính: Ngăn chặn tuyệt đối tình trạng Agent gọi API vô tận khi gặp lỗi logic code.</p>
          </div>

          {/* Hộp Thông tin Giám sát Chi phí từ AI (AI Cost Analysis Notification) */}
          <div className="bg-amber-50/50 border border-amber-200/60 rounded-xl p-4 space-y-3 shadow-xs shrink-0">
            <div className="flex items-center gap-1.5 text-amber-800 font-bold text-[12px]">
              <ShieldAlert size={14} className="text-amber-600 shrink-0" />
              <span>Chính sách Chặn Khẩn cấp</span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
              Hệ thống sẽ gửi email báo động khi ngân sách tháng của toàn công ty chạm ngưỡng <strong className="font-bold text-slate-800">80%</strong>. 
            </p>
            <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
              Nếu chạm mốc <strong className="font-bold text-rose-600">100%</strong>, token của các Sub-Agent sẽ bị thu hồi và đưa về trạng thái đóng băng cho tới chu kỳ tiếp theo.
            </p>
          </div>

          {/* Gợi ý Tiết kiệm Quỹ (Cost Savings Insight) */}
          <div className="mt-auto bg-slate-900 text-white rounded-xl p-4 space-y-2 shrink-0 shadow-sm">
            <div className="flex items-center gap-1.5 text-[12px] font-bold text-emerald-400">
              <PiggyBank size={15} />
              <span>Phân tích từ Hệ thống</span>
            </div>
            <p className="text-[10.5px] text-slate-300 leading-relaxed font-medium">
              Tháng trước bạn đã lãng phí <strong className="text-white font-semibold">$14.20</strong> do phân bổ nhầm tác vụ dịch thuật cho mô hình đắt tiền. Hãy sử dụng tính năng định tuyến tự động (Router Model) để tối ưu hóa.
            </p>
          </div>

        </div>
      </aside>

    </div>
  );
}