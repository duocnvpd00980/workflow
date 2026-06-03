// src/components/SidebarNav.tsx
import { Link } from '@tanstack/react-router'
import { Zap, History, BrainCircuit, Settings, BarChart3, CreditCard } from 'lucide-react'

export default function SidebarNav() {
  // Bộ CSS class gom nhóm để giao diện thống nhất và scannable
  const baseLinkClass = "w-full flex items-center gap-2.5 px-3 py-2 rounded-lg font-medium text-[13px] transition-colors"
  const inactiveClass = "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
  const activeClass = "bg-indigo-50/70 text-indigo-700 font-bold"

  return (
    <>
      
      {/* BRAND HEADER */}
      <div className="flex h-14 items-center gap-2.5 border-b px-4 shrink-0">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
          <Zap size={18} className="fill-current" />
        </div>
        <div className="flex flex-col min-w-0">
          <span className="text-[14px] font-bold tracking-tight text-slate-800 leading-none mb-1">Agent Command</span>
          <span className="text-[10px] text-slate-400 font-medium">Hệ thống thực thi</span>
        </div>
      </div>

      {/* NAVIGATION LINKS CONTAINER */}
      <div className="px-2 py-3 border-b space-y-0.5 shrink-0">
        
        {/* 1. ĐANG THỰC THI (Trang chủ - Map vào file src/routes/index.tsx) */}
        <Link 
          to="/" 
          className={`${baseLinkClass} ${inactiveClass}`}
          activeProps={{ className: `${baseLinkClass} ${activeClass}` }}
          activeOptions={{ exact: true }} // Chỉ sáng đèn khi url chuẩn xác là "/"
        >
          {({ isActive }) => (
            <>
              <div className="flex items-center gap-2.5">
                <Zap size={16} className={isActive ? "text-indigo-600" : "text-slate-400"} />
                <span>Đang thực thi</span>
              </div>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${isActive ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-100 text-slate-500'}`}>
                1
              </span>
            </>
          )}
        </Link>

        {/* 2. LỊCH SỬ CÔNG VIỆC (Map vào file src/routes/history.tsx) */}
        <Link 
          to="/history" 
          className={`${baseLinkClass} ${inactiveClass}`}
          activeProps={{ className: `${baseLinkClass} ${activeClass}` }}
        >
          {({ isActive }) => (
            <>
              <History size={16} className={isActive ? "text-indigo-600" : "text-slate-400"} />
              <span>Lịch sử công việc</span>
            </>
          )}
        </Link>

        {/* 3. CƠ SỞ TRI THỨC RAG (Map vào file src/routes/knowledge.tsx) */}
        <Link 
          to="/knowledge" 
          className={`${baseLinkClass} ${inactiveClass}`}
          activeProps={{ className: `${baseLinkClass} ${activeClass}` }}
        >
          {({ isActive }) => (
            <>
              <BrainCircuit size={16} className={isActive ? "text-indigo-600" : "text-slate-400"} />
              <span>Cơ sở tri thức RAG</span>
            </>
          )}
        </Link>

        {/* 4. CẤU HÌNH AGENT (Map vào file src/routes/settings.tsx) */}
        <Link 
          to="/settings" 
          className={`${baseLinkClass} ${inactiveClass}`}
          activeProps={{ className: `${baseLinkClass} ${activeClass}` }}
        >
          {({ isActive }) => (
            <>
              <Settings size={16} className={isActive ? "text-indigo-600" : "text-slate-400"} />
              <span>Cấu hình Agent</span>
            </>
          )}
        </Link>

        {/* 5. ANALYTICS & BÁO CÁO (Map vào file src/routes/analytics.tsx) */}
        <Link 
          to="/analytics" 
          className={`${baseLinkClass} ${inactiveClass}`}
          activeProps={{ className: `${baseLinkClass} ${activeClass}` }}
        >
          {({ isActive }) => (
            <>
              <BarChart3 size={16} className={isActive ? "text-indigo-600" : "text-slate-400"} />
              <span>Analytics & Báo cáo</span>
            </>
          )}
        </Link>

         <Link 
          to="/artifacts" 
          className={`${baseLinkClass} ${inactiveClass}`}
          activeProps={{ className: `${baseLinkClass} ${activeClass}` }}
        >
          {({ isActive }) => (
            <>
              <CreditCard size={16} className={isActive ? "text-indigo-600" : "text-slate-400"} />
              <span>Kho sản phẩm của Agent</span>
            </>
          )}
        </Link>

        {/* 6. CHI PHÍ & HÓA ĐƠN (Map vào file src/routes/budget.tsx hoặc billing.tsx tùy bạn đặt tên file con) */}
        <Link 
          to="/billing" 
          className={`${baseLinkClass} ${inactiveClass}`}
          activeProps={{ className: `${baseLinkClass} ${activeClass}` }}
        >
          {({ isActive }) => (
            <>
              <CreditCard size={16} className={isActive ? "text-indigo-600" : "text-slate-400"} />
              <span>Chi phí & Hóa đơn</span>
            </>
          )}
        </Link>


        

      </div>
    </>
  )
}