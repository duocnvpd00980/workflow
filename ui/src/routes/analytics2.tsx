import React from 'react';
import { TrendingUp, Users, Zap, BarChart3 } from 'lucide-react';
import { createFileRoute } from '@tanstack/react-router';
import AdminSidebarLayout from '@/layout/AdminSidebarLayout';

export const Route = createFileRoute('/analytics2')({
  component: PageAnalytics,
});

function PageAnalytics() {
  const stats = [
    { label: "Tổng bài đã sinh", value: "1,240 bài", change: "+12.3% tuần này", icon: BarChart3, color: "text-indigo-600 bg-indigo-50" },
    { label: "Lượt tiếp cận (Reach)", value: "45,200", change: "+8.1% so với tháng trước", icon: Users, color: "text-emerald-600 bg-emerald-50" },
    { label: "Tỉ lệ chuyển đổi", value: "3.42%", change: "+0.5% tối ưu từ AI", icon: TrendingUp, color: "text-amber-600 bg-amber-50" }
  ];

  return (
    <AdminSidebarLayout activeTab="analytics">
      <div className="space-y-6 animate-fadeIn">
        <div>
          <h2 className="text-base font-bold text-slate-900">Báo cáo hiệu quả nội dung</h2>
          <p className="text-xs text-slate-500 mt-0.5">Theo dõi chi tiết mức độ tương tác của độc giả đối với các bài đăng do AI sinh cấu trúc.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {stats.map((st, i) => {
            const Icon = st.icon;
            return (
              <div key={i} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <span className="text-[11px] text-slate-400 font-medium block">{st.label}</span>
                  <span className="text-lg font-bold text-slate-900 block">{st.value}</span>
                  <span className="text-[10px] text-slate-500 font-medium block">{st.change}</span>
                </div>
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${st.color}`}>
                  <Icon className="w-5 h-5" />
                </div>
              </div>
            );
          })}
        </div>

        {/* Mock Chart Area */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Xu hướng tương tác theo thời gian</h3>
          <div className="h-48 bg-slate-50 rounded-lg border border-dashed flex items-center justify-center text-xs text-slate-400 font-medium">
            [Biểu đồ hiển thị biến thiên lượng Reach và Engagement đa kênh]
          </div>
        </div>
      </div>
    </AdminSidebarLayout>
  );
}