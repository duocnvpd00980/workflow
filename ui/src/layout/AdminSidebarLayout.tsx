import React from 'react';
import { FileText, UserSquare2, Layers, BarChart3, Settings, CreditCard } from 'lucide-react';
import { Link } from '@tanstack/react-router';

interface LayoutProps {
  activeTab: string;
  children: React.ReactNode;
}

export default function AdminSidebarLayout({ activeTab, children }: LayoutProps) {
  const menus = [
    { id: 'templates', label: "Templates mẫu", icon: FileText, path: "/templates" },
    { id: 'brand-profile', label: "Brand Profile", icon: UserSquare2, path: "/brand-profiles" },
    { id: 'integrations', label: "Tích hợp kênh", icon: Layers, path: "/integrations" },
    { id: 'analytics', label: "Báo cáo hiệu quả", icon: BarChart3, path: "/analytics" },
    { id: 'settings', label: "Cài đặt hệ thống", icon: Settings, path: "/settings" },
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased p-4 md:p-6">
      <div className="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Navigation Sidebar */}
        <div className="lg:col-span-3 xl:col-span-2 bg-white p-4 rounded-xl border border-slate-200 space-y-6 shadow-sm">
          <div className="space-y-1 flex flex-col">
            {menus.map((m) => {
              const Icon = m.icon;
              return (
                <Link
                  key={m.id}
                  to={m.path}
                  className={`w-full flex items-center gap-3 px-3 py-2 text-xs font-semibold rounded-md transition-colors ${
                    activeTab === m.id ? 'bg-slate-100 text-slate-900' : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  {m.label}
                </Link>
              );
            })}
          </div>

          {/* Credits Widget */}
          <div className="bg-slate-50 p-4 rounded-lg border text-xs space-y-3">
            <div className="flex justify-between items-center text-slate-500">
              <span className="flex items-center gap-1 font-medium"><CreditCard className="w-3.5 h-3.5" /> Credits</span>
              <span className="font-bold text-slate-900">182 / 500</span>
            </div>
            <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
              <div className="bg-indigo-600 h-full w-[36%]" />
            </div>
          </div>
        </div>

        {/* Content Workspace Panel */}
        <div className="lg:col-span-9 xl:col-span-10 space-y-6">
          {children}
        </div>
      </div>
    </div>
  );
}