
import { Globe, Shield, RefreshCw, ExternalLink } from 'lucide-react';
import { createFileRoute } from '@tanstack/react-router';
import AdminSidebarLayout from '@/layout/AdminSidebarLayout';
import SidebarNav from '@/layout/navbar';

export const Route = createFileRoute('/integrations')({
  component: PageIntegrations,
});

function PageIntegrations() {
  const channels = [
    { name: "Facebook Fanpage", desc: "Tự động đăng bài viết và hình ảnh lên dòng thời gian.", status: "Đã kết nối", account: "Tiệm Bánh ABC (Page ID: 8932)", icon: Globe, active: true },
    { name: "WordPress CMS Web", desc: "Đẩy bài viết chuẩn SEO trực tiếp vào mục lưu nháp (Draft).", status: "Chưa cấu hình", account: "Chưa liên kết tài khoản", icon: Shield, active: false }
  ];

  return (
    <div class="flex">
    <SidebarNav />
      <div className="space-y-6 animate-fadeIn">
        <div>
          <h2 className="text-base font-bold text-slate-900">Tích hợp kênh phân phối</h2>
          <p className="text-xs text-slate-500 mt-0.5">Kết nối Content Factory với các nền tảng mạng xã hội hoặc CMS để tự động hóa khâu xuất bản bài đăng.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {channels.map((ch, i) => {
            const Icon = ch.icon;
            return (
              <div key={i} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
                <div className="flex justify-between items-start">
                  <div className="flex gap-3 items-center">
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${ch.active ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-50 text-slate-400'}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-slate-900">{ch.name}</h3>
                      <p className="text-[11px] text-slate-400 mt-0.5">{ch.desc}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${ch.active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-400'}`}>
                    {ch.status}
                  </span>
                </div>
                <div className="bg-slate-50 p-2.5 rounded border border-slate-100 text-[11px] flex justify-between items-center text-slate-600">
                  <span className="font-medium truncate max-w-[200px]">{ch.account}</span>
                  <button className="text-indigo-600 font-semibold hover:underline flex items-center gap-1 shrink-0">
                    {ch.active ? <RefreshCw className="w-3 h-3" /> : <ExternalLink className="w-3 h-3" />}
                    {ch.active ? 'Đổi cấu hình' : 'Liên kết ngay'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}