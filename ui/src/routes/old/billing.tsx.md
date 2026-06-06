import React, { useState } from 'react';
import { 
  LayoutDashboard, FolderKanban, FileText, UserSquare2, 
  Layers, BarChart3, Settings, CreditCard, Plus, Sparkles, 
  ArrowRight, ArrowLeft, Send, Check, History, Undo, 
  ChevronRight, AlignLeft, Eye, EyeOff, Play, Pause, 
  Smartphone, Monitor, ThumbsUp, Trash2, Sliders, Globe, 
  HelpCircle, Shield, Key, Database, Bell, DollarSign, 
  RefreshCw, TrendingUp, Users, ExternalLink, Mail, Zap
} from 'lucide-react';
import { createFileRoute } from '@tanstack/react-router';

// ============================================================================
// CONFIGS & DESIGN SYSTEM
// ============================================================================
const PRIMARY_COLOR = "bg-slate-900 text-white hover:bg-slate-800";
const ACCENT_TEXT = "text-indigo-600";
const ACCENT_BG = "bg-indigo-600 hover:bg-indigo-700 text-white";

export const Route = createFileRoute('/billing')({
  component: ContentEngineV2FullWorkspace,
})



export default function ContentEngineV2FullWorkspace() {
  // Quản lý giữa Nhóm Màn hình Core (1-6) và Nhóm Màn hình Hệ thống Mới (7-12)
  const [currentScreen, setCurrentScreen] = useState<number>(1);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased">
      
      {/* GLOBAL DEMO CONTROLLER HEADER */}
      <div className="bg-white border-b border-slate-200 px-4 py-2.5 flex flex-wrap items-center justify-between sticky top-0 z-50 gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-indigo-600" />
          <span className="font-bold text-sm tracking-tight">Content Engine V2.0 Redesign</span>
          <span className="text-[10px] bg-slate-100 font-mono px-1.5 py-0.5 rounded text-slate-600">Production Draft</span>
        </div>
        
        {/* Switcher cho toàn bộ 12 màn hình để test flow nhanh */}
        <div className="flex flex-wrap bg-slate-100 p-1 rounded-lg text-[11px] font-medium max-w-full overflow-x-auto gap-0.5">
          <div className="flex items-center px-1.5 text-slate-400 text-[10px] uppercase font-bold">Bộ 1 (Core):</div>
          {[1, 2, 3, 4, 5, 6].map((num) => (
            <button
              key={num}
              onClick={() => setCurrentScreen(num)}
              className={`px-2.5 py-1 rounded-md transition-all ${
                currentScreen === num ? 'bg-white text-slate-900 shadow-sm font-bold' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              M{num}
            </button>
          ))}
          <div className="w-[1px] bg-slate-200 mx-1 self-stretch" />
          <div className="flex items-center px-1.5 text-indigo-500 text-[10px] uppercase font-bold">Bộ 2 (Admin):</div>
          {[7, 8, 9, 10, 11, 12].map((num) => (
            <button
              key={num}
              onClick={() => setCurrentScreen(num)}
              className={`px-2.5 py-1 rounded-md transition-all ${
                currentScreen === num ? 'bg-indigo-600 text-white shadow-sm font-bold' : 'text-slate-500 hover:text-indigo-600'
              }`}
            >
              M{num}
            </button>
          ))}
        </div>

        <div className="text-xs font-medium text-slate-500 hidden md:block">
          Workspace Owner: <span className="text-slate-900 font-bold">Nguyen Minh</span>
        </div>
      </div>

      {/* WORKSPACE AREA CONTAINER */}
      <div className="p-4 md:p-6 max-w-[1600px] mx-auto min-h-[calc(100vh-60px)]">
        
        {/* BỘ 1: MÀN HÌNH WORKSPACE CHÍNH (1 ĐẾN 6) */}
        {currentScreen === 1 && <ScreenDashboard onNav={(s) => setCurrentScreen(s)} />}
        {currentScreen === 2 && <ScreenCreateContent onBack={() => setCurrentScreen(1)} onSubmit={() => setCurrentScreen(3)} />}
        {currentScreen === 3 && <ScreenWorkspace onBack={() => setCurrentScreen(2)} onGoToReview={() => setCurrentScreen(4)} onGoToAuto={() => setCurrentScreen(5)} />}
        {currentScreen === 4 && <ScreenReviewMode onBack={() => setCurrentScreen(3)} />}
        {currentScreen === 5 && <ScreenAutoMode onBack={() => setCurrentScreen(3)} />}
        {currentScreen === 6 && <ScreenMobileView />}

        {/* BỘ 2: MÀN HÌNH QUẢN TRỊ & THIẾT LẬP CHI TIẾT (7 ĐẾN 12) */}
        {currentScreen === 7 && <ScreenDashboardV2 onNav={(s) => setCurrentScreen(s)} />}
        {currentScreen === 8 && <ScreenTemplatesMau onNav={(s) => setCurrentScreen(s)} />}
        {currentScreen === 9 && <ScreenBrandProfile onNav={(s) => setCurrentScreen(s)} />}
        {currentScreen === 10 && <ScreenTichHopKenh onNav={(s) => setCurrentScreen(s)} />}
        {currentScreen === 11 && <ScreenBaoCaoHieuQua onNav={(s) => setCurrentScreen(s)} />}
        {currentScreen === 12 && <ScreenCaiDatHeThong onNav={(s) => setCurrentScreen(s)} />}

      </div>
    </div>
  );
}

// ============================================================================
// HỆ THỐNG SIDEBAR CHUNG CHO CÁC MÀN HÌNH CÓ LAYOUT CHUẨN (7-12)
// ============================================================================
function AdminSidebarLayout({ activeTab, onNav, children }: { activeTab: number, onNav: (s: number) => void, children: React.ReactNode }) {
  const menus = [
    { id: 7, label: "Dashboard", icon: LayoutDashboard },
    { id: 8, label: "Templates mẫu", icon: FileText },
    { id: 9, label: "Brand Profile", icon: UserSquare2 },
    { id: 10, label: "Tích hợp kênh", icon: Layers },
    { id: 11, label: "Báo cáo hiệu quả", icon: BarChart3 },
    { id: 12, label: "Cài đặt hệ thống", icon: Settings },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* Left Sidebar Fixed Width Style */}
      <div className="lg:col-span-3 xl:col-span-2 bg-white p-4 rounded-xl border border-slate-200 space-y-6">
        <div className="space-y-1">
          {menus.map((m) => {
            const Icon = m.icon;
            return (
              <button
                key={m.id}
                onClick={() => onNav(m.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 text-xs font-semibold rounded-md transition-colors ${
                  activeTab === m.id 
                    ? 'bg-slate-100 text-slate-900' 
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {m.label}
              </button>
            );
          })}
        </div>

        <hr className="border-slate-100" />

        {/* Credit Display Widget */}
        <div className="bg-slate-50 p-4 rounded-lg border border-slate-200/60 text-xs space-y-3">
          <div className="flex justify-between items-center text-slate-500">
            <span className="flex items-center gap-1 font-medium"><CreditCard className="w-3.5 h-3.5" /> Credits</span>
            <span className="font-bold text-slate-900">182 / 500</span>
          </div>
          <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
            <div className="bg-indigo-600 h-full w-[36%]" />
          </div>
          <button className="w-full py-1.5 bg-white border border-slate-200 rounded text-center font-bold text-slate-700 hover:bg-slate-50 transition">
            Nâng cấp
          </button>
        </div>

        {/* User Card */}
        <div className="flex items-center gap-2.5 pt-2 border-t border-slate-100">
          <div className="w-7 h-7 rounded-full bg-slate-300 overflow-hidden shrink-0">
            <div className="w-full h-full bg-gradient-to-tr from-amber-400 to-indigo-600 flex items-center justify-center text-[10px] font-bold text-white">NM</div>
          </div>
          <div className="text-[11px] overflow-hidden">
            <div className="font-bold text-slate-900 truncate">Nguyên Minh</div>
            <div className="text-slate-400 truncate">Pro Plan</div>
          </div>
        </div>
      </div>

      {/* Main Content Pane bên phải */}
      <div className="lg:col-span-9 xl:col-span-10 space-y-6">
        {children}
      </div>
    </div>
  );
}


// ============================================================================
// MÀN HÌNH 1 — DASHBOARD (BẢN CŨ GỐC)
// ============================================================================
function ScreenDashboard({ onNav }: { onNav: (s: number) => void }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-start">
      <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-6">
        <div className="space-y-1 text-xs">
          <button className="w-full flex items-center gap-3 px-3 py-2 font-medium bg-slate-100 rounded-md"><LayoutDashboard className="w-4 h-4" /> Tổng quan</button>
          <button onClick={() => onNav(8)} className="w-full flex items-center gap-3 px-3 py-2 font-medium text-slate-600 hover:bg-slate-50 rounded-md"><FileText className="w-4 h-4" /> Templates mẫu</button>
          <button onClick={() => onNav(9)} className="w-full flex items-center gap-3 px-3 py-2 font-medium text-slate-600 hover:bg-slate-50 rounded-md"><UserSquare2 className="w-4 h-4" /> Brand Profile</button>
          <button onClick={() => onNav(10)} className="w-full flex items-center gap-3 px-3 py-2 font-medium text-slate-600 hover:bg-slate-50 rounded-md"><Layers className="w-4 h-4" /> Tích hợp kênh</button>
          <button onClick={() => onNav(11)} className="w-full flex items-center gap-3 px-3 py-2 font-medium text-slate-600 hover:bg-slate-50 rounded-md"><BarChart3 className="w-4 h-4" /> Báo cáo hiệu quả</button>
          <button onClick={() => onNav(12)} className="w-full flex items-center gap-3 px-3 py-2 font-medium text-slate-600 hover:bg-slate-50 rounded-md"><Settings className="w-4 h-4" /> Cài đặt hệ thống</button>
        </div>
      </div>
      <div className="md:col-span-3 space-y-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight">Chào buổi sáng, Minh! 👋</h2>
            <p className="text-xs text-slate-500 mt-1">Hôm nay bạn muốn tối ưu hóa chiến dịch và tạo nội dung gì?</p>
          </div>
          <button onClick={() => onNav(2)} className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg shadow-sm transition ${PRIMARY_COLOR}`}>
            <Plus className="w-4 h-4" /> Tạo content mới
          </button>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {["Bài đăng Facebook", "Blog bài viết SEO", "Quảng cáo Ads", "Ý tưởng nội dung"].map((action, idx) => (
            <button key={idx} onClick={() => onNav(2)} className="bg-white p-4 rounded-xl border border-slate-200 text-left hover:border-indigo-500 transition hover:shadow-sm space-y-2">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-sm">0{idx+1}</div>
              <div className="font-semibold text-xs text-slate-900">{action}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MÀN HÌNH 2 — CREATE CONTENT
// ============================================================================
function ScreenCreateContent({ onBack, onSubmit }: { onBack: () => void; onSubmit: () => void }) {
  return (
    <div className="max-w-3xl mx-auto bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      <div className="border-b border-slate-100 p-4 flex items-center justify-between text-xs font-medium text-slate-500">
        <button onClick={onBack} className="flex items-center gap-1 hover:text-slate-900"><ArrowLeft className="w-3.5 h-3.5" /> Quay lại</button>
        <div className="flex gap-4 items-center">
          <span className="text-indigo-600 font-semibold border-b-2 border-indigo-600 pb-4 pt-1">1. Yêu cầu</span>
          <span className="opacity-50">2. Thông tin bổ sung</span>
          <span className="opacity-50">3. Tạo nội dung</span>
        </div>
      </div>
      <div className="p-8 space-y-6">
        <div className="text-center max-w-md mx-auto space-y-1">
          <h2 className="text-lg font-bold tracking-tight">Bạn muốn tạo nội dung gì?</h2>
          <p className="text-xs text-slate-500">Nhập yêu cầu chi tiết của bạn để AI lập không gian làm việc lý tưởng.</p>
        </div>
        <div className="border border-slate-200 rounded-xl p-4 bg-slate-50 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 transition relative">
          <textarea className="w-full bg-transparent border-0 outline-none resize-none text-sm min-h-[100px]" placeholder="Ví dụ: Viết bài đăng Facebook quảng cáo dòng sản phẩm bánh mì mới..." />
          <div className="flex justify-between items-center pt-2 text-xs text-slate-400">
            <span>Độ dài đề xuất: 50-200 từ</span>
            <button onClick={onSubmit} className="bg-indigo-600 text-white p-2 rounded-lg hover:bg-indigo-700 shadow-sm"><ArrowRight className="w-4 h-4" /></button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MÀN HÌNH 3 — CONTENT WORKSPACE
// ============================================================================
function ScreenWorkspace({ onBack, onGoToReview, onGoToAuto }: { onBack: () => void; onGoToReview: () => void; onGoToAuto: () => void }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div className="lg:col-span-4 bg-white border border-slate-200 rounded-xl overflow-hidden flex flex-col h-[600px]">
        <div className="flex border-b border-slate-100 p-2 bg-slate-50 text-xs font-semibold">
          <button className="flex-1 py-1 text-center bg-white rounded shadow-sm text-slate-900">Trợ lý Copilot</button>
          <button className="flex-1 py-1 text-center text-slate-400">Lịch sử (v3)</button>
        </div>
        <div className="flex-1 p-4 overflow-y-auto text-xs space-y-4">
          <div className="bg-slate-100 p-3 rounded-lg text-slate-600">Hệ thống áp dụng Brand Profile: <strong>Bánh mì ABC</strong></div>
        </div>
      </div>
      <div className="lg:col-span-8 bg-white border border-slate-200 rounded-xl overflow-hidden flex flex-col h-[600px]">
        <div className="border-b border-slate-200 p-4 flex flex-wrap items-center justify-between bg-slate-50/50 gap-2">
          <span className="text-xs font-bold text-slate-900">Bản thảo: Bánh mì ngon - Ngày mới vui hơn! (v3)</span>
          <div className="flex gap-2">
            <button onClick={onGoToReview} className="px-3 py-1 bg-white border rounded text-xs font-semibold hover:bg-slate-50">So sánh (Diff)</button>
            <button onClick={onGoToAuto} className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded text-xs font-semibold hover:bg-indigo-100">Auto Mode</button>
          </div>
        </div>
        <div className="p-6 text-sm flex-1 overflow-y-auto">
          <h1 className="text-xl font-bold">🥖 BÁNH MÌ NGON - NGÀY MỚI VUI HƠN! 🥖</h1>
          <p className="mt-4 text-slate-700">Mỗi ổ bánh mì là một câu chuyện ẩm thực đậm đà riêng biệt được nướng từ củi tự nhiên...</p>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MÀN HÌNH 4 — REVIEW MODE
// ============================================================================
function ScreenReviewMode({ onBack }: { onBack: () => void }) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-200">
        <span className="text-sm font-bold">Chế độ so sánh và phê duyệt (Diff Review)</span>
        <button onClick={onBack} className={`px-4 py-1.5 rounded text-xs font-semibold ${PRIMARY_COLOR}`}>Xong</button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        <div className="bg-white border p-4 rounded-xl opacity-75">
          <h4 className="font-bold text-red-600 line-through">Bản cũ (v2)</h4>
          <p className="mt-2">Ghé qua ăn thử bánh mì của quán chúng mình nhé mọi người.</p>
        </div>
        <div className="bg-white border-indigo-200 border p-4 rounded-xl shadow-sm">
          <h4 className="font-bold text-emerald-600">Đề xuất mới (v3)</h4>
          <p className="mt-2 font-medium">📍 Ghé ngay cơ sở gần nhất để áp dụng chương trình Mua 1 Tặng 1!</p>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MÀN HÌNH 5 — AUTO MODE
// ============================================================================
function ScreenAutoMode({ onBack }: { onBack: () => void }) {
  return (
    <div className="max-w-xl mx-auto bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden p-6 space-y-6">
      <div className="flex justify-between items-center border-b pb-3">
        <h3 className="text-sm font-bold text-indigo-600 flex items-center gap-2"><Play className="w-4 h-4" /> Hệ thống Auto Mode đang chạy</h3>
        <button onClick={onBack} className="text-xs text-slate-500 underline">Thoát</button>
      </div>
      <div className="space-y-2 text-xs">
        <div className="p-3 bg-slate-50 rounded border border-emerald-200 text-emerald-800 font-medium">✓ Hoàn tất tìm kiếm insights từ khóa hot trend tuần này.</div>
        <div className="p-3 bg-slate-50 rounded border border-indigo-200 text-indigo-800 font-medium animate-pulse">→ Đang tiến hành kết nối API tạo ảnh tự động...</div>
      </div>
    </div>
  );
}

// ============================================================================
// MÀN HÌNH 6 — MOBILE VIEW
// ============================================================================
function ScreenMobileView() {
  return (
    <div className="max-w-xs mx-auto bg-slate-900 p-3 rounded-[36px] border-4 border-slate-700 shadow-xl">
      <div className="bg-white rounded-[28px] min-h-[500px] p-4 flex flex-col text-xs">
        <div className="border-b pb-2 font-bold text-center">📱 Mobile Workspace Preview</div>
        <div className="flex-1 py-4 space-y-2">
          <div className="font-bold text-sm">🥖 Bánh Mì Ngon</div>
          <p className="text-slate-600">Nội dung hiển thị tối ưu hóa định dạng responsive trên giao diện Smartphone.</p>
        </div>
      </div>
    </div>
  );
}


// ============================================================================
// MÀN HÌNH 7 — DỰ ÁN GẦN ĐÂY / DASHBOARD V2 (CHẤT LƯỢNG CAO)
// ============================================================================
function ScreenDashboardV2({ onNav }: { onNav: (s: number) => void }) {
  const categories = [
    { title: "Social Post", desc: "Facebook, Instagram, TikTok", icon: Layers, count: "v1.2", badge: "~ 30s" },
    { title: "Blog Post", desc: "Bài viết chuẩn SEO", icon: FileText, count: "v2.0", badge: "~ 1-2 phút" },
    { title: "Ads Copy", desc: "Quảng cáo đa kênh", icon: MegaphoneIcon, count: "v1.0", badge: "~ 30s" },
    { title: "Campaign", desc: "Chiến dịch tổng thể", icon: Sparkles, count: "v2.1", badge: "~ 5 phút" },
    { title: "Image", desc: "Tạo hình ảnh AI", icon: Monitor, count: "v1.5", badge: "~ 1 phút" },
  ];

  return (
    <AdminSidebarLayout activeTab={7} onNav={onNav}>
      {/* Khối Greeting & Tạo mới nhanh */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">Xin chào, Minh! 👋</h2>
          <p className="text-xs text-slate-500 mt-0.5">Hôm nay bạn muốn tạo nội dung gì?</p>
        </div>
        <button onClick={() => onNav(2)} className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg shadow-sm transition ${ACCENT_BG}`}>
          <Plus className="w-3.5 h-3.5" /> Tạo nội dung mới
        </button>
      </div>

      {/* Grid Menu Tạo Nhanh Giữa Màn Hình */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {categories.map((c, i) => {
          const Icon = c.icon;
          return (
            <div key={i} className="bg-white p-4 rounded-xl border border-slate-200 hover:border-indigo-500 transition-all cursor-pointer group space-y-3">
              <div className="flex justify-between items-start">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <Icon className="w-4 h-4" />
                </div>
                <span className="text-[10px] bg-slate-100 px-1.5 py-0.5 rounded text-slate-500 font-mono">{c.badge}</span>
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">{c.title}</h4>
                <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">{c.desc}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Hai Cột: Dự Án Gần Đây & Gợi ý cho bạn */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Bảng danh sách dự án (Chiếm 2 cột) */}
        <div className="xl:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex justify-between items-center">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Dự án gần đây</h3>
            <button className="text-[11px] text-indigo-600 font-semibold hover:underline">Xem tất cả</button>
          </div>
          <div className="divide-y divide-slate-100 text-xs">
            {[
              { name: "Ra mắt bánh mì hè", channel: "Facebook Post", time: "3 phút trước", status: "Draft", color: "bg-slate-100 text-slate-700" },
              { name: "Blog SEO tháng 6", channel: "Blog Post", time: "Hôm qua", status: "Published", color: "bg-emerald-50 text-emerald-700" },
              { name: "Campaign khai trương", channel: "Campaign", time: "2 ngày trước", status: "In Review", color: "bg-amber-50 text-amber-700" },
              { name: "Ưu đãi cuối tuần", channel: "Instagram Post", time: "3 ngày trước", status: "Published", color: "bg-emerald-50 text-emerald-700" }
            ].map((proj, idx) => (
              <div key={idx} className="p-4 flex items-center justify-between hover:bg-slate-50/50 transition-colors">
                <div className="space-y-0.5">
                  <h4 className="font-bold text-slate-800">{proj.name}</h4>
                  <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
                    <span>{proj.channel}</span>
                    <span>•</span>
                    <span>{proj.time}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase ${proj.color}`}>{proj.status}</span>
                  <button className="p-1 text-slate-400 hover:text-slate-600"><ChevronRight className="w-4 h-4" /></button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Cột Phụ: Gợi ý cho bạn & Hoạt động */}
        <div className="space-y-6">
          {/* Hộp gợi ý thông minh từ AI */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Gợi ý cho bạn</h3>
            <div className="space-y-2">
              {[
                { title: "Tạo biến thể Instagram", desc: "Từ bài 'Ra mắt bánh mì hè'", icon: Zap },
                { title: "Làm mới bài viết cũ", desc: "Blog SEO tháng 5 đã qua 30 ngày", icon: RefreshCw },
                { title: "Tạo chiến dịch mới", desc: "Dựa trên hiệu suất tuần gần nhất", icon: TrendingUp }
              ].map((rec, i) => (
                <div key={i} className="p-2.5 rounded-lg border border-slate-100 hover:border-indigo-100 hover:bg-indigo-50/30 transition-all cursor-pointer flex gap-2.5 items-start">
                  <div className="p-1.5 bg-indigo-50 rounded-md text-indigo-600 shrink-0 mt-0.5">
                    <rec.icon className="w-3.5 h-3.5" />
                  </div>
                  <div className="text-[11px]">
                    <div className="font-bold text-slate-800">{rec.title}</div>
                    <div className="text-slate-400 text-[10px] mt-0.5">{rec.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Nhật ký hoạt động */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Hoạt động gần đây</h3>
            <div className="space-y-3 text-[11px] text-slate-600">
              <div className="flex gap-2"><div className="w-1.5 h-1.5 bg-indigo-500 rounded-full mt-1.5 shrink-0" /> <p>Bạn đã xuất bản bài viết <strong>"Ưu đãi tuần"</strong> lên Facebook</p></div>
              <div className="flex gap-2"><div className="w-1.5 h-1.5 bg-amber-500 rounded-full mt-1.5 shrink-0" /> <p>AI đã tạo bản nháp mới cho chiến dịch khai trương</p></div>
            </div>
          </div>
        </div>

      </div>
    </AdminSidebarLayout>
  );
}

// ============================================================================
// MÀN HÌNH 8 — TEMPLATES MẪU (PREDEFINED WORKFLOW SYSTEM)
// ============================================================================
function ScreenTemplatesMau({ onNav }: { onNav: (s: number) => void }) {
  const [filter, setFilter] = useState("Tất cả");
  const categories = ["Tất cả", "Social", "Blog", "Ads", "Research", "Campaign", "Image"];
  
  const templates = [
    { title: "Facebook Caption", desc: "Tạo caption hấp dẫn cho bài đăng Facebook kèm hashtag", type: "Social", time: "~ 30s" },
    { title: "Instagram Post", desc: "Bài đăng Instagram kèm cấu trúc định hướng thiết kế hình ảnh", type: "Social", time: "~ 30s" },
    { title: "SEO Blog Post", desc: "Bài viết chuẩn cấu trúc SEO (gồm Research + Outline + Blog)", type: "Blog", time: "~ 2-3 phút" },
    { title: "Google Ads Copy", desc: "Tạo tiêu đề và nội dung mô tả tối ưu hóa chuyển đổi quảng cáo", type: "Ads", time: "~ 30s" },
    { title: "Product Launch Campaign", desc: "Chiến dịch ra mắt sản phẩm đồng bộ trên tất cả các kênh", type: "Campaign", time: "~ 5 phút" },
    { title: "AI Image Generation", desc: "Tạo và xử lý hình ảnh AI theo mô tả chất lượng cao", type: "Image", time: "~ 1 phút" },
  ];

  return (
    <AdminSidebarLayout activeTab={8} onNav={onNav}>
      <div className="space-y-4">
        {/* Tiêu đề & Ô Tìm Kiếm */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">Templates hệ thống</h2>
            <p className="text-xs text-slate-500 mt-0.5">Chọn template phù hợp để AI tạo lập quy trình làm việc chuẩn xác nhất.</p>
          </div>
          <input 
            type="text" 
            placeholder="Tìm kiếm template mẫu..." 
            className="text-xs bg-white border border-slate-200 px-3 py-1.5 rounded-lg outline-none focus:border-indigo-500 w-full sm:w-64 shadow-sm"
          />
        </div>

        {/* Hệ thống lọc Tabs */}
        <div className="flex flex-wrap gap-1 bg-slate-200/60 p-1 rounded-lg w-fit text-[11px] font-semibold">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`px-3 py-1 rounded-md transition-all ${
                filter === cat ? "bg-white text-slate-900 shadow-xs" : "text-slate-500 hover:text-slate-800"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Grid hiển thị danh sách Templates */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates
            .filter((t) => filter === "Tất cả" || t.type === filter)
            .map((t, i) => (
              <div key={i} className="bg-white p-5 rounded-xl border border-slate-200 flex flex-col justify-between shadow-sm hover:shadow-md transition-all group">
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-bold uppercase tracking-wider">{t.type}</span>
                    <span className="text-[11px] text-slate-400 font-mono">{t.time}</span>
                  </div>
                  <h3 className="text-xs font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">{t.title}</h3>
                  <p className="text-[11px] text-slate-500 leading-relaxed line-clamp-2">{t.desc}</p>
                </div>
                <div className="pt-4 mt-4 border-t border-slate-100 flex justify-end">
                  <button onClick={() => onNav(2)} className="text-[11px] bg-slate-50 hover:bg-indigo-600 hover:text-white text-slate-700 px-3 py-1.5 rounded-md font-bold transition-colors w-full text-center">
                    Dùng template
                  </button>
                </div>
              </div>
            ))}
        </div>
      </div>
    </AdminSidebarLayout>
  );
}

// ============================================================================
// MÀN HÌNH 9 — BRAND PROFILE (KÝ ỨC DÀI HẠN / PERSISTENT MEMORY)
// ============================================================================
function ScreenBrandProfile({ onNav }: { onNav: (s: number) => void }) {
  const [subTab, setSubTab] = useState("Tổng quan");
  const subMenus = ["Tổng quan", "Giọng văn & Tone", "CTA & Thông điệp", "Phong cách hình ảnh", "Sản phẩm / Dịch vụ", "Tài liệu tham khảo"];

  return (
    <AdminSidebarLayout activeTab={9} onNav={onNav}>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        
        {/* Danh mục cài đặt con bên trong Brand Profile */}
        <div className="bg-white p-2 rounded-xl border border-slate-200 space-y-0.5">
          {subMenus.map((m) => (
            <button
              key={m}
              onClick={() => setSubTab(m)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 text-[11px] font-bold rounded-md text-left transition-colors ${
                subTab === m ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              <div className={`w-1.5 h-1.5 rounded-full ${subTab === m ? "bg-indigo-600" : "bg-transparent"}`} />
              {m}
            </button>
          ))}
        </div>

        {/* Form thiết lập cấu trúc thực tế */}
        <div className="lg:col-span-3 bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5 text-xs">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-sm font-bold text-slate-900">Thông tin thương hiệu</h2>
            <p className="text-[11px] text-slate-400 mt-0.5">Thông tin cốt lõi giúp AI hiểu sâu sắc về doanh nghiệp và sản phẩm của bạn.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="font-bold text-slate-700">Tên thương hiệu</label>
              <input type="text" defaultValue="ABC Bakery" className="w-full bg-white border border-slate-200 px-3 py-1.5 rounded-md outline-none focus:border-indigo-500 font-medium" />
            </div>
            <div className="space-y-1.5">
              <label className="font-bold text-slate-700">Ngành nghề kinh doanh</label>
              <select className="w-full bg-white border border-slate-200 px-3 py-1.5 rounded-md outline-none focus:border-indigo-500 font-medium">
                <option>F&B / Thực phẩm & Đồ uống</option>
                <option>Thời trang / Mỹ phẩm</option>
                <option>Công nghệ / SaaS</option>
              </select>
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label className="font-bold text-slate-700">Mô tả thương hiệu ngắn gọn</label>
              <span className="text-[10px] text-slate-400 font-mono">82/200</span>
            </div>
            <textarea 
              rows={3} 
              defaultValue="Tiệm bánh mì thủ công truyền thống, sử dụng 100% nguyên liệu tươi ngon hữu cơ tự nhiên, hương vị đậm đà bản sắc Việt." 
              className="w-full bg-white border border-slate-200 p-3 rounded-md outline-none focus:border-indigo-500 font-medium leading-relaxed" 
            />
          </div>

          {/* Tone of Voice Selection Option */}
          <div className="space-y-2">
            <label className="font-bold text-slate-700">Giọng văn chủ đạo (Tone of Voice)</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
              {["Chuyên nghiệp", "Thân thiện", "Trẻ trung", "Sang trọng"].map((tone) => (
                <label key={tone} className="flex items-center gap-2 border border-slate-200 p-2.5 rounded-lg cursor-pointer hover:bg-slate-50 transition-colors">
                  <input type="radio" name="tone" defaultChecked={tone === "Thân thiện"} className="text-indigo-600 focus:ring-indigo-500" />
                  <span className="font-medium text-slate-800">{tone}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Kênh phát hành cốt lõi */}
          <div className="space-y-2">
            <label className="font-bold text-slate-700">Kênh truyền thông phân phối chính</label>
            <div className="flex flex-wrap gap-4 text-[11px]">
              {["Facebook", "Instagram", "Blog / Website", "TikTok", "Email"].map((ch) => (
                <label key={ch} className="flex items-center gap-2 cursor-pointer font-medium text-slate-700">
                  <input type="checkbox" defaultChecked={["Facebook", "Instagram", "Blog / Website"].includes(ch)} className="rounded text-indigo-600 focus:ring-indigo-500" />
                  <span>{ch}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Phong cách hình ảnh trực quan */}
          <div className="space-y-2">
            <label className="font-bold text-slate-700">Phong cách định hướng hình ảnh thiết kế</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { name: "Tối giản", img: "https://images.unsplash.com/photo-1544816155-12df9643f363?w=150&auto=format&fit=crop&q=60" },
                { name: "Tự nhiên", img: "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=150&auto=format&fit=crop&q=60" },
                { name: "Sang trọng", img: "https://images.unsplash.com/photo-1541532713592-79a0317b6b77?w=150&auto=format&fit=crop&q=60" },
                { name: "Vui tươi", img: "https://images.unsplash.com/photo-1513151233558-d860c5398176?w=150&auto=format&fit=crop&q=60" }
              ].map((style, i) => (
                <div key={i} className={`border rounded-xl overflow-hidden cursor-pointer hover:border-indigo-500 transition-all text-center pb-2 ${i === 1 ? 'border-indigo-600 ring-2 ring-indigo-500/10' : 'border-slate-200'}`}>
                  <img src={style.img} alt={style.name} className="w-full h-16 object-cover bg-slate-100" />
                  <span className="text-[10px] font-bold block mt-1.5 text-slate-800">{style.name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Button Lưu hành động */}
          <div className="pt-4 border-t border-slate-100 flex justify-end">
            <button className={`px-5 py-2 text-xs font-bold rounded-lg shadow-sm ${ACCENT_BG}`}>
              Lưu thay đổi cấu trúc
            </button>
          </div>
        </div>

      </div>
    </AdminSidebarLayout>
  );
}

// ============================================================================
// MÀN HÌNH 10 — TÍCH HỢP KÊNH (GRAPH API / WEBHOOK LAYER)
// ============================================================================
function ScreenTichHopKenh({ onNav }: { onNav: (s: number) => void }) {
  const channels = [
    { name: "Facebook Page", account: "ABC Bakery", icon: Layers, isConnected: true, detail: "Kết nối trực tiếp Graph API công cụ đăng" },
    { name: "Instagram", account: "abc.bakery", icon: Smartphone, isConnected: true, detail: "Instagram Basic Display API" },
    { name: "WordPress", account: "abc-bakery.com", icon: Globe, isConnected: true, detail: "WordPress REST API để đẩy blog tự động" },
    { name: "TikTok", account: "Chưa kết nối", icon: Play, isConnected: false, detail: "TikTok Content Posting API" },
    { name: "YouTube", account: "Chưa kết nối", icon: Monitor, isConnected: false, detail: "YouTube Data API v3" },
    { name: "LinkedIn Page", account: "Chưa kết nối", icon: Users, isConnected: false, detail: "LinkedIn Share API" },
    { name: "X (Twitter)", account: "Chưa kết nối", icon: Zap, isConnected: false, detail: "X API v2 Content Suite" },
    { name: "Email (SMTP)", account: "Chưa kết nối", icon: Mail, isConnected: false, detail: "Hệ thống gửi Newsletter thông báo" },
  ];

  return (
    <AdminSidebarLayout activeTab={10} onNav={onNav}>
      <div className="space-y-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">Kết nối kênh phân phối nội dung</h2>
          <p className="text-xs text-slate-500 mt-0.5">Kết nối các tài khoản MXH hoặc Website của bạn để AI tự động xuất bản nội dung lên các kênh chỉ bằng một cú click.</p>
        </div>

        {/* Grid các kênh kết nối */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {channels.map((chan, idx) => {
            const Icon = chan.icon;
            return (
              <div key={idx} className="bg-white p-4 rounded-xl border border-slate-200 flex items-start justify-between shadow-xs gap-3">
                <div className="flex gap-3 items-start">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${chan.isConnected ? 'bg-indigo-50 text-indigo-600' : 'bg-slate-100 text-slate-400'}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-900">{chan.name}</h4>
                    <p className="text-[11px] text-slate-400 mt-0.5">{chan.detail}</p>
                    {chan.isConnected && (
                      <div className="text-[10px] text-emerald-600 font-medium bg-emerald-50 w-fit px-1.5 py-0.5 rounded mt-1.5 flex items-center gap-1">
                        <Check className="w-3 h-3" /> Tài khoản: {chan.account}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {chan.isConnected ? (
                    <>
                      <button className="px-2.5 py-1.5 bg-slate-50 text-slate-700 border border-slate-200 rounded text-[11px] font-bold hover:bg-slate-100">
                        Cấu hình
                      </button>
                      <button className="p-1.5 text-slate-300 hover:text-red-500"><Trash2 className="w-3.5 h-3.5" /></button>
                    </>
                  ) : (
                    <button className={`px-3 py-1.5 bg-white border border-slate-200 rounded text-[11px] font-bold text-slate-800 hover:bg-slate-50 shadow-xs`}>
                      Kết nối
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Khung cấu hình xuất bản mặc định đi kèm */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4 text-xs max-w-2xl">
          <h3 className="font-bold text-slate-900 border-b border-slate-100 pb-2">Cài đặt xuất bản bài viết mặc định</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="font-bold text-slate-700">Kênh đăng mặc định</label>
              <select className="w-full bg-white border border-slate-200 px-3 py-1.5 rounded-md outline-none">
                <option>Facebook Page - ABC Bakery</option>
                <option>Instagram - abc.bakery</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="font-bold text-slate-700">Thời gian đăng bài mặc định</label>
              <select className="w-full bg-white border border-slate-200 px-3 py-1.5 rounded-md outline-none">
                <option>Ngay lập tức sau khi duyệt</option>
                <option>Lưu trữ vào hàng đợi (Queue)</option>
              </select>
            </div>
          </div>
          <label className="flex items-center gap-2 cursor-pointer font-medium text-slate-700 pt-2">
            <input type="checkbox" defaultChecked className="rounded text-indigo-600 focus:ring-indigo-500" />
            <span>Xác nhận kiểm tra lại bài viết trước khi bấm đăng trực tiếp</span>
          </label>
        </div>
      </div>
    </AdminSidebarLayout>
  );
}

// ============================================================================
// MÀN HÌNH 11 — BÁO CÁO HIỆU QUẢ (ANALYTICS & CONVERSION TRACKING)
// ============================================================================
function ScreenBaoCaoHieuQua({ onNav }: { onNav: (s: number) => void }) {
  return (
    <AdminSidebarLayout activeTab={11} onNav={onNav}>
      <div className="space-y-6">
        {/* Tiêu đề trang & Bộ chọn thời gian */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">Báo cáo hiệu quả nội dung</h2>
            <p className="text-xs text-slate-500 mt-0.5">Theo dõi chi tiết số liệu, tỷ lệ duyệt và lượng Credits phân bổ.</p>
          </div>
          <select className="text-xs bg-white border border-slate-200 px-3 py-1.5 rounded-lg outline-none font-medium shadow-sm">
            <option>Tháng này (01/06/2026 - 30/06/2026)</option>
            <option>Tháng trước</option>
          </select>
        </div>

        {/* Khối Grid thống kê số liệu tổng quan */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "Nội dung đã xuất bản", value: "84", change: "+18% so với kỳ trước", isPositive: true },
            { label: "Tỷ lệ duyệt bài viết", value: "76%", change: "+4% so với kỳ trước", isPositive: true },
            { label: "Số lần chỉnh sửa trung bình", value: "1.8", change: "-12% so với kỳ trước", isPositive: true },
            { label: "Tổng Credits đã dùng", value: "124 / 300", change: "+15% so với kỳ trước", isPositive: false }
          ].map((stat, idx) => (
            <div key={idx} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wide block">{stat.label}</span>
              <div className="text-xl font-black text-slate-900 tracking-tight">{stat.value}</div>
              <span className={`text-[10px] font-medium block ${stat.isPositive ? 'text-emerald-600' : 'text-amber-600'}`}>
                {stat.change}
              </span>
            </div>
          ))}
        </div>

        {/* Đồ thị và biểu đồ phân bổ */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Mô phỏng đồ thị xu hướng (Chiếm 2 cột) */}
          <div className="lg:col-span-2 bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Nội dung theo thời gian</h3>
            {/* Giả lập đồ thị SVG tinh giản */}
            <div className="h-44 w-full flex items-end justify-between pt-4 relative">
              <div className="absolute inset-0 flex flex-col justify-between pointer-events-none text-[9px] text-slate-300">
                <div className="border-b w-full pt-1">115</div>
                <div className="border-b w-full pt-1">76</div>
                <div className="border-b w-full pt-1">45</div>
                <div className="border-b w-full pt-1">0</div>
              </div>
              {/* Vẽ đường line graph giả lập bằng div chấm hoặc cột */}
              <div className="w-full h-full flex items-end justify-around z-10 px-4">
                {[40, 65, 55, 85, 70, 95, 110, 80].map((h, i) => (
                  <div key={i} className="flex flex-col items-center gap-1 w-6 group">
                    <div style={{ height: `${h}px` }} className="w-2 bg-indigo-600 rounded-t-sm group-hover:bg-indigo-700 transition-all relative">
                      <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[9px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">{h} bài</div>
                    </div>
                    <span className="text-[9px] text-slate-400">0{i+1}/06</span>
                  </div>
                ))}
              </div>
            </div>
            {/* Chú thích màu */}
            <div className="flex gap-4 text-[10px] font-bold text-slate-500 justify-center pt-2">
              <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-indigo-600" /> Đã xuất bản</div>
              <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-amber-400" /> Đang xem xét</div>
              <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-slate-300" /> Bản nháp</div>
            </div>
          </div>

          {/* Phân bổ thể loại hình tròn bên phải */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Phân bổ theo loại nội dung</h3>
            <div className="flex items-center justify-center py-2">
              {/* Giả lập vòng tròn Donut Chart bằng css style */}
              <div className="w-28 h-28 rounded-full border-[12px] border-indigo-600 flex items-center justify-center relative font-bold text-xs text-slate-800">
                <div className="absolute inset-0 rounded-full border-[12px] border-emerald-500 rotate-45 pointer-events-none" />
                <div className="absolute inset-0 rounded-full border-[12px] border-amber-400 rotate-180 pointer-events-none" />
                <span>84 Bài</span>
              </div>
            </div>
            <div className="text-[11px] font-medium space-y-1.5 text-slate-600">
              <div className="flex justify-between"><span>• Blog Post</span> <span className="font-bold text-slate-950">42 (40%)</span></div>
              <div className="flex justify-between"><span>• Social Post</span> <span className="font-bold text-slate-950">31 (29%)</span></div>
              <div className="flex justify-between"><span>• Campaign</span> <span className="font-bold text-slate-950">11 (10%)</span></div>
            </div>
          </div>

        </div>

        {/* Bảng Top Template Hiệu Quả */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden text-xs">
          <div className="p-4 border-b border-slate-100 flex justify-between items-center">
            <h3 className="font-bold text-slate-900">Top template hiệu quả tối ưu</h3>
            <button className="text-[11px] text-indigo-600 font-bold hover:underline">Xem tất cả</button>
          </div>
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 text-slate-400 font-bold text-[10px] uppercase tracking-wider border-b border-slate-100">
                <th className="p-3 pl-4">Template</th>
                <th className="p-3">Số lượng</th>
                <th className="p-3">Tỷ lệ duyệt</th>
                <th className="p-3">Thời gian TB</th>
                <th className="p-3 pr-4 text-right">Credits sử dụng</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {[
                { name: "SEO Blog Post", count: 42, rate: "81%", time: "2.3 phút", credit: 42 },
                { name: "Facebook Caption", count: 28, rate: "77%", time: "0.8 phút", credit: 14 },
                { name: "Instagram Post", count: 14, rate: "72%", time: "0.9 phút", credit: 9 },
              ].map((row, i) => (
                <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                  <td className="p-3 pl-4 font-bold text-slate-900">{row.name}</td>
                  <td className="p-3">{row.count}</td>
                  <td className="p-3 text-emerald-600 font-bold">{row.rate}</td>
                  <td className="p-3">{row.time}</td>
                  <td className="p-3 pr-4 text-right font-bold text-slate-900">{row.credit} c</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AdminSidebarLayout>
  );
}

// ============================================================================
// MÀN HÌNH 12 — CÀI ĐẶT HỆ THỐNG (SYSTEM CONFIGURATION & SECURITY)
// ============================================================================
function ScreenCaiDatHeThong({ onNav }: { onNav: (s: number) => void }) {
  const [activeSubMenu, setActiveSubMenu] = useState("Chung");
  
  const subSettings = [
    { name: "Chung", icon: Sliders },
    { name: "AI & Workflow", icon: Sparkles },
    { name: "Giới hạn & Quota", icon: CreditCard },
    { name: "Bảo mật", icon: Shield },
    { name: "Thành viên & Phân quyền", icon: Users },
    { name: "Thanh toán & Gói dịch vụ", icon: DollarSign },
    { name: "Thông báo", icon: Bell },
    { name: "API & Webhooks", icon: Key },
    { name: "Sao lưu & Xuất dữ liệu", icon: Database },
  ];

  return (
    <AdminSidebarLayout activeTab={12} onNav={onNav}>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        
        {/* Thanh điều hướng Menu cài đặt phụ bên trong */}
        <div className="bg-white p-2 rounded-xl border border-slate-200 space-y-0.5">
          {subSettings.map((sub, i) => {
            const Icon = sub.icon;
            return (
              <button
                key={i}
                onClick={() => setActiveSubMenu(sub.name)}
                className={`w-full flex items-center gap-3 px-3 py-2 text-[11px] font-bold rounded-md text-left transition-colors ${
                  activeSubMenu === sub.name ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                <Icon className="w-3.5 h-3.5 shrink-0" />
                {sub.name}
              </button>
            );
          })}
        </div>

        {/* Content Khu vực chi tiết form cấu hình */}
        <div className="lg:col-span-3 bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6 text-xs">
          
          {/* Section 1: Cài đặt chung */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">Cài đặt chung</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="font-bold text-slate-700">Ngôn ngữ vùng hệ thống</label>
                <select className="w-full bg-white border border-slate-200 px-3 py-1.5 rounded-md outline-none">
                  <option>Tiếng Việt (Vietnamese)</option>
                  <option>English (US)</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="font-bold text-slate-700">Múi giờ làm việc</label>
                <select className="w-full bg-white border border-slate-200 px-3 py-1.5 rounded-md outline-none">
                  <option>(GMT+07:00) Ho Chi Minh City</option>
                  <option>(GMT+00:00) UTC Standard Time</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section 2: Giao diện */}
          <div className="space-y-3">
            <h4 className="font-bold text-slate-700">Giao diện người dùng</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {/* Radio Chế độ màu */}
              <div className="space-y-1.5">
                <span className="font-semibold text-slate-500 block text-[11px]">Chế độ nền màu</span>
                <div className="flex gap-4 font-medium">
                  {["Sáng", "Tối", "Hệ thống"].map((mode) => (
                    <label key={mode} className="flex items-center gap-1.5 cursor-pointer">
                      <input type="radio" name="colorMode" defaultChecked={mode === "Sáng"} className="text-indigo-600 focus:ring-indigo-500" />
                      <span>{mode}</span>
                    </label>
                  ))}
                </div>
              </div>
              {/* Mật độ hiển thị */}
              <div className="space-y-1.5">
                <span className="font-semibold text-slate-500 block text-[11px]">Mật độ hiển thị thông tin</span>
                <div className="flex gap-4 font-medium">
                  {["Thoải mái", "Vừa", "Gọn"].map((density) => (
                    <label key={density} className="flex items-center gap-1.5 cursor-pointer">
                      <input type="radio" name="density" defaultChecked={density === "Thoải mái"} className="text-indigo-600 focus:ring-indigo-500" />
                      <span>{density}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Section 3: Hành vi hệ thống (Toggle Switches) */}
          <div className="space-y-4 pt-2">
            <h4 className="font-bold text-slate-900 border-b border-slate-100 pb-2">Hành vi hệ thống và AI</h4>
            <div className="space-y-3 font-medium text-slate-700">
              
              {/* Toggle 1 */}
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-0.5">
                  <label className="font-bold text-slate-900 block">Tự động lưu bản nháp (Auto-save)</label>
                  <p className="text-[11px] text-slate-400">Tự động sao lưu văn bản lên hệ thống Cloud khi bạn đang thực hiện chỉnh sửa nội dung.</p>
                </div>
                <input type="checkbox" defaultChecked className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4 cursor-pointer mt-1" />
              </div>

              {/* Toggle 2 */}
              <div className="flex items-start justify-between gap-4 pt-1">
                <div className="space-y-0.5">
                  <label className="font-bold text-slate-900 block">Tự động hỏi thêm thông tin (Clarify Loop)</label>
                  <p className="text-[11px] text-slate-400">AI sẽ tự động kích hoạt bộ câu hỏi gợi ý khi phát hiện yêu cầu đầu vào bị mơ hồ hoặc thiếu dữ liệu ngành.</p>
                </div>
                <input type="checkbox" defaultChecked className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4 cursor-pointer mt-1" />
              </div>

              {/* Toggle 3 */}
              <div className="flex items-start justify-between gap-4 pt-1">
                <div className="space-y-0.5">
                  <label className="font-bold text-slate-900 block">Xác nhận trước khi trực tiếp xuất bản bài đăng</label>
                  <p className="text-[11px] text-slate-400">Hiển thị hộp thoại pop-up cảnh báo yêu cầu phê duyệt thủ công lần cuối trước khi gọi sang API tích hợp mạng xã hội.</p>
                </div>
                <input type="checkbox" defaultChecked className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4 cursor-pointer mt-1" />
              </div>

            </div>
          </div>

          {/* Nút hành động */}
          <div className="pt-4 border-t border-slate-100 flex justify-end">
            <button className={`px-5 py-2 text-xs font-bold rounded-lg shadow-sm ${ACCENT_BG}`}>
              Lưu cấu hình cài đặt
            </button>
          </div>

        </div>
      </div>
    </AdminSidebarLayout>
  );
}

// Icon Component phụ trợ cho phần grid
function MegaphoneIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="m3 11 18-5v12L3 13v-2Z" />
      <path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" />
    </svg>
  );
}