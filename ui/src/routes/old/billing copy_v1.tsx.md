"use client";

import { createFileRoute } from "@tanstack/react-router";




import React, { useState } from 'react';
import { 
  LayoutDashboard, FolderKanban, FileText, UserSquare2, 
  Layers, BarChart3, Settings, CreditCard, Plus, Sparkles, 
  ArrowRight, ArrowLeft, Send, Check, History, Undo, 
  ChevronRight, AlignLeft, Eye, EyeOff, Play, Pause, 
  Smartphone, Monitor, ThumbsUp, Trash2
} from 'lucide-react';

// ==========================================
// MOCK DATA & CONFIGS (Design System Rules)
// ==========================================
const PRIMARY_COLOR = "bg-slate-900 text-white hover:bg-slate-800";
const ACCENT_COLOR = "bg-indigo-600 text-white hover:bg-indigo-700 text-indigo-600";

export const Route = createFileRoute('/billing copy')({
  component: ContentEngineWorkspace,
})


export default function ContentEngineWorkspace() {
  const [currentScreen, setCurrentScreen] = useState<1 | 2 | 3 | 4 | 5 | 6>(1);
  const [viewMode, setViewMode] = useState<'desktop' | 'mobile'>('desktop');

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased">
      {/* Top Navigation Bar Bar để Demo giữa các màn hình nhanh */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-indigo-600" />
          <span className="font-bold tracking-tight text-slate-900">Content Engine V2.0</span>
          <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full font-medium">Balanced Option</span>
        </div>
        
        {/* Quick Screen Switcher (Shadcn Tabs Style) */}
        <div className="flex bg-slate-100 p-1 rounded-lg text-xs font-medium">
          {[1, 2, 3, 4, 5, 6].map((num) => (
            <button
              key={num}
              onClick={() => setCurrentScreen(num as any)}
              className={`px-3 py-1.5 rounded-md transition-all ${
                currentScreen === num ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              Màn {num}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span>User: <strong>Alex</strong></span>
        </div>
      </div>

      {/* Render Screen Content */}
      <main className="p-6 max-w-[1600px] mx-auto">
        {currentScreen === 1 && <ScreenDashboard onCreateContent={() => setCurrentScreen(2)} />}
        {currentScreen === 2 && <ScreenCreateContent onBack={() => setCurrentScreen(1)} onSubmit={() => setCurrentScreen(3)} />}
        {currentScreen === 3 && <ScreenWorkspace onBack={() => setCurrentScreen(2)} onGoToReview={() => setCurrentScreen(4)} onGoToAuto={() => setCurrentScreen(5)} />}
        {currentScreen === 4 && <ScreenReviewMode onBack={() => setCurrentScreen(3)} />}
        {currentScreen === 5 && <ScreenAutoMode onBack={() => setCurrentScreen(3)} />}
        {currentScreen === 6 && <ScreenMobileView />}
      </main>
    </div>
  );
}

// ==========================================
// SCREEN 1 — DASHBOARD (Notion + Linear Style)
// ==========================================
function ScreenDashboard({ onCreateContent }: { onCreateContent: () => void }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-start">
      {/* Sidebar - Tối đa 2 level sidebar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-6">
        <div className="space-y-1">
          <button className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium bg-slate-100 text-slate-900 rounded-md"><LayoutDashboard className="w-4 h-4" /> Tổng quan</button>
          <button className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-md"><FolderKanban className="w-4 h-4" /> Dự án gần đây</button>
          <button className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-md"><FileText className="w-4 h-4" /> Templates mẫu</button>
          <button className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-md"><UserSquare2 className="w-4 h-4" /> Brand Profile</button>
          <button className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-md"><Layers className="w-4 h-4" /> Tích hợp kênh</button>
          <button className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-md"><BarChart3 className="w-4 h-4" /> Báo cáo hiệu quả</button>
          <button className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-md"><Settings className="w-4 h-4" /> Cài đặt hệ thống</button>
        </div>
        
        <hr className="border-slate-100" />
        
        {/* Credit System Component */}
        <div className="bg-slate-50 p-4 rounded-lg border border-slate-100 text-xs space-y-3">
          <div className="flex justify-between items-center text-slate-600">
            <span className="flex items-center gap-1 font-medium"><CreditCard className="w-3.5 h-3.5" /> Credit còn lại</span>
            <span className="font-bold text-slate-900">182 / 500</span>
          </div>
          <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
            <div className="bg-indigo-600 h-full w-[36%]" />
          </div>
          <button className="w-full py-2 bg-white border border-slate-200 rounded text-center font-semibold text-slate-700 hover:bg-slate-50 transition">Nâng cấp gói</button>
        </div>
      </div>

      {/* Main Panel */}
      <div className="md:grid-cols-1 md:col-span-3 space-y-6">
        {/* Greeting & Quick Action Callout */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900">Chào buổi sáng, Minh! 👋</h2>
            <p className="text-xs text-slate-500 mt-1">Hôm nay bạn muốn tối ưu hóa chiến dịch và tạo nội dung gì?</p>
          </div>
          <button onClick={onCreateContent} className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg shadow-sm transition ${PRIMARY_COLOR}`}>
            <Plus className="w-4 h-4" /> Tạo content mới
          </button>
        </div>

        {/* Quick Action Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {["Bài đăng Facebook", "Blog bài viết SEO", "Quảng cáo Ads", "Ý tưởng nội dung"].map((action, idx) => (
            <button key={idx} onClick={onCreateContent} className="bg-white p-4 rounded-xl border border-slate-200 text-left hover:border-indigo-500 transition hover:shadow-sm space-y-2">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-sm">0{idx+1}</div>
              <div className="font-semibold text-xs text-slate-900">{action}</div>
            </button>
          ))}
        </div>

        {/* Split Section: Recent and Activities */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent projects */}
          <div className="lg:col-span-2 bg-white p-5 rounded-xl border border-slate-200 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Dự án gần đây</h3>
            <div className="divide-y divide-slate-100 text-xs">
              {[
                { name: "Bánh mì ABC - Tháng 6", type: "Facebook Post", time: "2 giờ trước", status: "Đã đăng", color: "bg-emerald-50 text-emerald-700" },
                { name: "Khuyến mãi cuối tuần", type: "Blog Post", time: "1 ngày trước", status: "Bản nháp", color: "bg-amber-50 text-amber-700" },
                { name: "Campaign mùa hè 2024", type: "Multi-channel", time: "2 ngày trước", status: "Đang xử lý", color: "bg-indigo-50 text-indigo-700" }
              ].map((proj, i) => (
                <div key={i} className="py-3 flex justify-between items-center first:pt-0 last:pb-0">
                  <div>
                    <h4 className="font-semibold text-slate-900">{proj.name}</h4>
                    <span className="text-[11px] text-slate-400">{proj.type} • {proj.time}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded font-medium ${proj.color}`}>{proj.status}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Activity Log */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Hoạt động gần đây</h3>
            <div className="space-y-3 text-xs text-slate-600">
              <div className="flex gap-2"><div className="w-1.5 h-1.5 bg-indigo-500 rounded-full mt-1.5 shrink-0" /> <p>Bạn đã xuất bản <strong>Bánh mì ngon</strong> lên Fanpage</p></div>
              <div className="flex gap-2"><div className="w-1.5 h-1.5 bg-amber-500 rounded-full mt-1.5 shrink-0" /> <p>AI đã tạo bản nhập mới cho chiến dịch tuần mới</p></div>
              <div className="flex gap-2"><div className="w-1.5 h-1.5 bg-slate-300 rounded-full mt-1.5 shrink-0" /> <p>Cập nhật lại cấu trúc <strong>Brand Profile</strong></p></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// SCREEN 2 — CREATE CONTENT (Copilot Input Focus)
// ==========================================
function ScreenCreateContent({ onBack, onSubmit }: { onBack: () => void; onSubmit: () => void }) {
  return (
    <div className="max-w-3xl mx-auto bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
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
          <h2 className="text-lg font-bold tracking-tight">Bạn muốn tạo nội dung gì hôm nay?</h2>
          <p className="text-xs text-slate-500">Nhập yêu cầu chi tiết của bạn, AI Engine sẽ thiết lập không gian xử lý tối ưu.</p>
        </div>

        {/* Ô nhập yêu cầu cực lớn */}
        <div className="border border-slate-200 rounded-xl p-4 bg-slate-50 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 transition relative">
          <textarea 
            className="w-full bg-transparent border-0 outline-none resize-none text-sm placeholder:text-slate-400 min-h-[120px]" 
            placeholder="Ví dụ: Viết bài đăng Facebook quảng cáo dòng sản phẩm bánh mì thịt nướng mới của quán ABC, yêu cầu văn phong vui vẻ, có kêu gọi hành động cuối bài..."
          />
          <div className="flex justify-between items-center pt-2 border-t border-slate-200 text-xs text-slate-400">
            <span>Độ dài đề xuất: 50-200 từ</span>
            <button onClick={onSubmit} className="bg-indigo-600 text-white p-2 rounded-lg hover:bg-indigo-700 transition shadow-sm"><ArrowRight className="w-4 h-4" /></button>
          </div>
        </div>

        {/* Suggested Actions / Placeholders Tags */}
        <div className="space-y-2 text-xs">
          <span className="font-semibold text-slate-500">Gợi ý nhanh cấu trúc:</span>
          <div className="flex flex-wrap gap-1.5">
            {["Bánh mì ABC", "Tone vui vẻ", "Mạng xã hội Facebook", "Quảng cáo sản phẩm", "Thêm CTA ưu đãi"].map((tag) => (
              <span key={tag} className="bg-slate-100 px-2.5 py-1 rounded-md text-slate-600 font-medium cursor-pointer hover:bg-slate-200 transition">{tag}</span>
            ))}
          </div>
        </div>

        {/* AI Clarification Loop - Max 2 loops inline */}
        <div className="bg-indigo-50/60 border border-indigo-100 rounded-xl p-4 space-y-4">
          <div className="flex items-start gap-2.5 text-xs">
            <div className="w-5 h-5 bg-indigo-600 text-white rounded-full flex items-center justify-center shrink-0 font-bold text-[10px]">AI</div>
            <div className="space-y-1">
              <h4 className="font-bold text-indigo-900">AI Clarification (Gợi ý tối ưu hóa)</h4>
              <p className="text-indigo-700">Để bản thảo đầu tiên sát nhất với mong muốn, bạn có thể chọn thêm các chi tiết sau:</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pl-7">
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">1. Đối tượng khách hàng mục tiêu?</label>
              <div className="flex gap-1.5">
                <span className="bg-white border border-indigo-200 px-2 py-1 rounded text-indigo-700 font-medium cursor-pointer">Học sinh, sinh viên</span>
                <span className="bg-white border border-slate-200 px-2 py-1 rounded text-slate-600 cursor-pointer hover:bg-slate-50">Dân văn phòng</span>
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">2. Chương trình ưu đãi đi kèm?</label>
              <div className="flex gap-1.5">
                <span className="bg-white border border-slate-200 px-2 py-1 rounded text-slate-600 cursor-pointer hover:bg-slate-50">Giảm giá 20%</span>
                <span className="bg-white border border-indigo-200 px-2 py-1 rounded text-indigo-700 font-medium cursor-pointer">Tặng kèm nước ngọt</span>
              </div>
            </div>
          </div>

          <div className="pt-2 text-right border-t border-indigo-100">
            <button onClick={onSubmit} className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold">Bỏ qua & Tiến hành tạo nội dung ngay →</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// SCREEN 3 — CONTENT WORKSPACE (Core Interface)
// ==========================================
function ScreenWorkspace({ onBack, onGoToReview, onGoToAuto }: { onBack: () => void; onGoToReview: () => void; onGoToAuto: () => void }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* Cột trái: Chat Copilot + History (Chiếm 4 cột) */}
      <div className="lg:col-span-4 bg-white border border-slate-200 rounded-xl overflow-hidden flex flex-col h-[680px]">
        {/* Sub-tabs trong chat sidebar */}
        <div className="flex border-b border-slate-100 p-2 bg-slate-50 text-xs font-semibold">
          <button className="flex-1 py-1.5 text-center bg-white rounded shadow-sm text-slate-900">Trợ lý Copilot</button>
          <button className="flex-1 py-1.5 text-center text-slate-400 hover:text-slate-600">Lịch sử phiên (v3)</button>
        </div>

        {/* Khung chat / Workspace log */}
        <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-slate-500 text-center">
            Hệ thống áp dụng Brand Profile: <strong>Bánh mì ABC</strong>
          </div>

          {/* User message */}
          <div className="flex gap-2 items-start justify-end">
            <div className="bg-indigo-600 text-white p-3 rounded-xl rounded-tr-none max-w-[85%]">
              Thay đổi cho tao phần mở đầu hướng tới đối tượng người trẻ và thêm bộ hashtag nhận diện ở cuối.
            </div>
          </div>

          {/* AI Copilot Response */}
          <div className="flex gap-2 items-start">
            <div className="w-6 h-6 bg-indigo-100 text-indigo-600 font-bold rounded-full flex items-center justify-center shrink-0">AI</div>
            <div className="bg-slate-100 p-3 rounded-xl rounded-tl-none max-w-[85%] space-y-2">
              <p>Đã cập nhật xong! Tôi đã chuyển đổi văn phong tươi trẻ hơn và chèn thêm CTA kèm bộ hashtag thương hiệu của bạn vào trình soạn thảo.</p>
              <div className="bg-white border border-slate-200 p-2 rounded text-[11px] font-medium text-slate-700 flex justify-between items-center">
                <span>Bản ghi mới nhất: Version 3</span>
                <span className="text-indigo-600 font-bold">Đã lưu nháp</span>
              </div>
            </div>
          </div>
        </div>

        {/* Input box hỗ trợ của chat */}
        <div className="p-3 border-t border-slate-100 flex gap-2 bg-slate-50">
          <input className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-indigo-500" placeholder="Yêu cầu AI sửa đổi nội dung văn bản..." />
          <button className="bg-indigo-600 text-white p-1.5 rounded-lg hover:bg-indigo-700"><Send className="w-3.5 h-3.5" /></button>
        </div>
      </div>

      {/* Cột phải: Editor WYSIWYG chiếm ưu thế tuyệt đối (Chiếm 8 cột) */}
      <div className="lg:col-span-8 bg-white border border-slate-200 rounded-xl overflow-hidden flex flex-col h-[680px]">
        {/* Editor Toolbar Header */}
        <div className="border-b border-slate-200 p-4 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50">
          <div className="flex items-center gap-2 text-xs">
            <span className="font-bold text-slate-900">Bản thảo: Bánh mì ngon - Ngày mới vui hơn!</span>
            <span className="bg-slate-200 px-2 py-0.5 rounded text-[11px] font-medium text-slate-700 flex items-center gap-1"><History className="w-3 h-3" /> v3</span>
          </div>
          
          {/* Action buttons hàng đầu */}
          <div className="flex items-center gap-2">
            <button onClick={onGoToReview} className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5"><Eye className="w-3.5 h-3.5" /> So sánh phiên bản (Diff)</button>
            <button onClick={onGoToAuto} className="px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-lg text-xs font-semibold hover:bg-indigo-100 flex items-center gap-1.5"><Play className="w-3.5 h-3.5" /> Kích hoạt Auto Mode</button>
            <button className={`px-4 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition ${PRIMARY_COLOR}`}>Duyệt & Đăng bài</button>
          </div>
        </div>

        {/* Editor Thực Tế (Workspace Canvas) */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-4 divide-x divide-slate-100 overflow-hidden">
          {/* Textarea Area */}
          <div className="md:col-span-3 p-6 overflow-y-auto space-y-4">
            {/* Thanh menu định dạng text giả lập */}
            <div className="flex gap-2 border-b border-slate-100 pb-2 text-xs text-slate-400 font-mono">
              <span className="font-bold text-slate-800 cursor-pointer">H1</span>
              <span className="font-bold text-slate-800 cursor-pointer">H2</span>
              <span className="underline cursor-pointer">U</span>
              <span className="italic cursor-pointer">I</span>
              <span className="cursor-pointer">Link</span>
              <span className="cursor-pointer">Quote</span>
            </div>

            {/* Khối văn bản nội dung chính */}
            <div className="space-y-4 text-sm text-slate-800 outline-none leading-relaxed">
              <h1 className="text-xl font-bold text-slate-900">🥖 BÁNH MÌ NGON - NGÀY MỚI VUI HƠN! 🥖</h1>
              <p>Bạn đã sẵn sàng để bùng nổ năng lượng cho ngày mới chưa? Ghé ngay hệ thống <strong>Bánh mì ABC</strong> để nhận trọn combo bữa sáng giòn rụm, đầy ắp năng lượng và ngập tràn hương vị quê hương!</p>
              
              {/* Highlight inline AI Action popup giống Cursor */}
              <div className="bg-indigo-50 border-l-4 border-indigo-600 p-3 rounded text-xs my-2 space-y-2">
                <p className="font-medium text-indigo-900">✨ Mỗi ổ bánh mì là một câu chuyện ẩm thực đậm đà riêng biệt được nướng từ củi tự nhiên.</p>
                <div className="flex gap-1.5 pt-1 text-[10px] font-bold">
                  <span className="bg-white px-2 py-0.5 rounded border border-indigo-200 text-indigo-700 cursor-pointer hover:bg-indigo-100">Ngắn gọn hơn</span>
                  <span className="bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-600 cursor-pointer hover:bg-slate-50">Tăng độ hài hước</span>
                  <span className="bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-600 cursor-pointer hover:bg-slate-50">Thêm CTA ưu đãi</span>
                </div>
              </div>

              <p>📍 Ghé ngay cơ sở gần nhất tại 123 Nguyễn Văn Linh để được áp dụng chương trình mua 1 tặng 1 trong khung giờ vàng từ nay đến cuối tuần!</p>
              <p className="text-slate-500 font-medium text-xs">#BanhMiABC #BanhMiNgon #AnLaMe #BữaSángNăngLượng</p>
            </div>
          </div>

          {/* Quick AI Action Sidebar (Phía bên phải editor) */}
          <div className="p-4 bg-slate-50/50 space-y-3 text-xs">
            <h4 className="font-bold uppercase tracking-wider text-slate-400 text-[10px]">AI Actions nhanh</h4>
            <button className="w-full text-left bg-white border border-slate-200 p-2.5 rounded-lg hover:border-indigo-500 font-medium flex items-center justify-between"><span>Tối ưu hóa chuẩn SEO</span> <ChevronRight className="w-3.5 h-3.5" /></button>
            <button className="w-full text-left bg-white border border-slate-200 p-2.5 rounded-lg hover:border-indigo-500 font-medium flex items-center justify-between"><span>Rút gọn văn bản gốc</span> <ChevronRight className="w-3.5 h-3.5" /></button>
            <button className="w-full text-left bg-white border border-slate-200 p-2.5 rounded-lg hover:border-indigo-500 font-medium flex items-center justify-between"><span>Đổi văn phong (Tone)</span> <ChevronRight className="w-3.5 h-3.5" /></button>
            <button className="w-full text-left bg-white border border-slate-200 p-2.5 rounded-lg hover:border-indigo-500 font-medium flex items-center justify-between"><span>Tự động tạo ảnh AI</span> <ChevronRight className="w-3.5 h-3.5" /></button>
            
            <hr className="border-slate-200 my-2" />
            <div className="text-[11px] text-slate-400 space-y-1">
              <div>Độ dài: <strong>123 từ</strong></div>
              <div>Ước tính token: <strong>450 tokens</strong></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// SCREEN 4 — REVIEW MODE (Compare Versions Diff)
// ==========================================
function ScreenReviewMode({ onBack }: { onBack: () => void }) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-200">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50"><ArrowLeft className="w-4 h-4" /></button>
          <div>
            <h2 className="text-sm font-bold">Chế độ so sánh và phê duyệt (Diff Review)</h2>
            <p className="text-xs text-slate-500">Xem các chỉnh sửa chi tiết mà AI Copilot đã đề xuất thực hiện.</p>
          </div>
        </div>
        <div className="flex gap-2 text-xs">
          <button className="px-4 py-2 bg-slate-100 rounded-lg font-semibold text-slate-600 hover:bg-slate-200">Khôi phục về v2</button>
          <button onClick={onBack} className={`px-4 py-2 rounded-lg font-semibold shadow-sm transition ${PRIMARY_COLOR}`}>Phê duyệt bản v3</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Version cũ (v2) */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 relative opacity-75">
          <span className="absolute top-3 right-3 text-[10px] uppercase tracking-wider bg-slate-100 px-2 py-0.5 rounded font-bold text-slate-500">Bản cũ (v2)</span>
          <h3 className="text-sm font-bold text-slate-900">🥖 BÁNH MÌ NGON - MÓN QUÀ BUỔI SÁNG</h3>
          <p className="text-xs text-slate-700 leading-relaxed">Hệ thống cửa hàng Bánh mì ABC chuyên cung cấp các bữa ăn sáng tiện lợi cho mọi người.</p>
          <div className="bg-red-50 text-red-700 text-xs p-2.5 rounded border border-red-100 line-through">
            Hãy ghé qua mua ăn thử nếu bạn rảnh vào tuần này nhé mọi người ơi.
          </div>
        </div>

        {/* Version mới do AI đề xuất (v3) */}
        <div className="bg-white border border-indigo-200 rounded-xl p-5 space-y-3 relative ring-1 ring-indigo-500/20">
          <span className="absolute top-3 right-3 text-[10px] uppercase tracking-wider bg-indigo-50 px-2 py-0.5 rounded font-bold text-indigo-600">Đề xuất mới (v3)</span>
          <h3 className="text-sm font-bold text-slate-900">🥖 BÁNH MÌ NGON - NGÀY MỚI VUI HƠN! </h3>
          <p className="text-xs text-slate-700 leading-relaxed">Hệ thống cửa hàng Bánh mì ABC chuyên cung cấp các bữa ăn sáng tiện lợi cho mọi người.</p>
          <div className="bg-emerald-50 text-emerald-800 text-xs p-2.5 rounded border border-emerald-100 font-medium">
            ✨ <strong className="text-emerald-900">📍 Ghé ngay cơ sở gần nhất tại 123 Nguyễn Văn Linh để được áp dụng chương trình mua 1 tặng 1 trong khung giờ vàng!</strong> [AI: Đổi văn phong sang dạng CTA thu hút hành động cụ thể]
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// SCREEN 5 — AUTO MODE (Campaign Workflow Pipeline)
// ==========================================
function ScreenAutoMode({ onBack }: { onBack: () => void }) {
  const [isPaused, setIsPaused] = useState(false);

  return (
    <div className="max-w-4xl mx-auto bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      {/* Top Banner Control */}
      <div className="bg-slate-900 text-white p-4 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-semibold tracking-wide uppercase">Hệ thống đang vận hành tự động (Auto Campaign Engine)</span>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={() => setIsPaused(!isPaused)} 
            className="px-3 py-1 bg-white/10 hover:bg-white/20 text-white text-xs font-medium rounded flex items-center gap-1 transition"
          >
            {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            {isPaused ? "Tiếp tục" : "Tạm dừng kiểm soát"}
          </button>
          <button onClick={onBack} className="px-3 py-1 bg-white text-slate-900 text-xs font-semibold rounded hover:bg-slate-100 transition">Thoát ra</button>
        </div>
      </div>

      {/* Workflow Progress Steps Line */}
      <div className="p-8 space-y-8">
        <div className="flex items-center justify-between relative max-w-2xl mx-auto">
          {/* Progress Connecting Line */}
          <div className="absolute left-0 right-0 top-1/2 h-0.5 bg-slate-200 -translate-y-1/2 z-0" />
          <div className="absolute left-0 w-[66%] top-1/2 h-0.5 bg-indigo-600 -translate-y-1/2 z-0" />

          {/* Steps Indicator Nodes */}
          {[
            { label: "Research", status: "complete" },
            { label: "Generate", status: "complete" },
            { label: "Image Gen", status: "active" },
            { label: "Publish", status: "pending" }
          ].map((step, idx) => (
            <div key={idx} className="relative z-10 flex flex-col items-center space-y-1 text-center">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                step.status === 'complete' ? 'bg-indigo-600 text-white' : 
                step.status === 'active' ? 'bg-indigo-50 border-2 border-indigo-600 text-indigo-600 animate-pulse' : 
                'bg-white border-2 border-slate-200 text-slate-400'
              }`}>
                {step.status === 'complete' ? <Check className="w-4 h-4" /> : idx + 1}
              </div>
              <span className={`text-xs font-semibold ${step.status === 'active' ? 'text-indigo-600' : 'text-slate-500'}`}>{step.label}</span>
            </div>
          ))}
        </div>

        {/* Detailed Status Logs Card */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-3 max-w-2xl mx-auto text-xs">
          <div className="flex justify-between items-center border-b border-slate-200 pb-2">
            <span className="font-bold text-slate-700">Nhật ký tiến trình thực tế</span>
            <span className="text-slate-400">Tiến độ tổng thể: 75%</span>
          </div>
          <div className="space-y-2 text-slate-600">
            <div className="flex gap-2 text-emerald-600"><Check className="w-3.5 h-3.5 shrink-0" /> <span>[Xong] Hoàn tất quét dữ liệu từ khóa xu hướng ngành F&B Việt Nam.</span></div>
            <div className="flex gap-2 text-emerald-600"><Check className="w-3.5 h-3.5 shrink-0" /> <span>[Xong] Khởi tạo thành công cấu trúc bản thảo bài đăng Facebook v3.</span></div>
            <div className="flex gap-2 text-indigo-600 font-medium"><div className="w-1.5 h-1.5 rounded-full bg-indigo-600 mt-1.5 animate-ping shrink-0" /> <span>[Đang chạy] Đang tổng hợp prompt để kết nối API DALL-E 3 tạo hình ảnh bánh mì...</span></div>
            <div className="flex gap-2 text-slate-400"><div className="w-1.5 h-1.5 rounded-full bg-slate-300 mt-1.5 shrink-0" /> <span>[Chờ] Xuất bản bài viết tự động thông qua Graph API kết nối Fanpage.</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// SCREEN 6 — MOBILE VIEW (Content First Framework)
// ==========================================
function ScreenMobileView() {
  return (
    <div className="max-w-md mx-auto bg-slate-900 p-3 rounded-[40px] shadow-2xl border-4 border-slate-800">
      {/* Mobile Screen Area Simulation */}
      <div className="bg-white rounded-[32px] overflow-hidden min-h-[640px] flex flex-col text-slate-900">
        
        {/* Mobile Header Bar */}
        <div className="px-4 pt-6 pb-3 border-b border-slate-100 flex justify-between items-center text-xs font-bold">
          <span className="text-slate-900">⚡ Copilot Workspace</span>
          <span className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full">v3 Draft</span>
        </div>

        {/* Content Area chiếm vị trí trung tâm ưu tiên cao nhất */}
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <div className="space-y-2">
            <h1 className="text-base font-bold text-slate-900">🥖 BÁNH MÌ NGON - NGÀY MỚI VUI HƠN!</h1>
            <p className="text-xs text-slate-600 leading-relaxed">
              Bạn đã sẵn sàng để bùng nổ năng lượng cho ngày mới chưa? Ghé ngay hệ thống <strong>Bánh mì ABC</strong> để nhận trọn combo bữa sáng giòn rụm!
            </p>
          </div>

          {/* Khối hiển thị ảnh đính kèm được ưu tiên trên màn mobile */}
          <div className="bg-slate-100 rounded-xl h-36 flex items-center justify-center border border-slate-200 text-xs text-slate-400 font-medium">
            [ Khung hiển thị Banner AI đã tạo kèm theo ]
          </div>
        </div>

        {/* Bottom Panel Component: Khu vực hỗ trợ và phím action nhanh */}
        <div className="p-3 bg-slate-50 border-t border-slate-100 space-y-3">
          <div className="flex gap-1.5 text-[10px] font-bold overflow-x-auto pb-1">
            <span className="bg-white border border-slate-200 px-2.5 py-1 rounded text-slate-700 shrink-0">✨ Rút ngắn gọn</span>
            <span className="bg-white border border-slate-200 px-2.5 py-1 rounded text-slate-700 shrink-0">✨ Thêm CTA gấp</span>
            <span className="bg-white border border-slate-200 px-2.5 py-1 rounded text-slate-700 shrink-0">🔄 Đổi văn phong</span>
          </div>

          <div className="flex gap-2">
            <input 
              className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs outline-none" 
              placeholder="Nhập yêu cầu nhanh cho trợ lý..." 
            />
            <button className={`px-4 py-2 rounded-lg text-xs font-bold shrink-0 shadow-sm ${PRIMARY_COLOR}`}>
              Đăng bài
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}