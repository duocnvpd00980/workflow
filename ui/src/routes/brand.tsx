import React, { useState } from 'react';
import { 
  LayoutDashboard, FolderKanban, FileText, UserSquare2, 
  Layers, BarChart3, Settings, CreditCard, Plus, Sparkles, 
  ArrowRight, ArrowLeft, Send, Check, History, Undo, 
  ChevronRight, AlignLeft, Eye, EyeOff, Play, Pause, 
  Smartphone, Monitor, ThumbsUp, Trash2, Sliders, Globe, 
  HelpCircle, Shield, Key, Database, Bell, DollarSign, 
  RefreshCw, TrendingUp, Users, ExternalLink, Mail, Zap,
  Volume2, Smile, Briefcase, Flame, MessageSquare, Image as ImageIcon,
  FileDown, Upload, Paperclip, Edit3, Bookmark
} from 'lucide-react';
import { createFileRoute } from '@tanstack/react-router';

// ============================================================================
// CONFIGS & DESIGN SYSTEM
// ============================================================================
const PRIMARY_COLOR = "bg-slate-900 text-white hover:bg-slate-800";
const ACCENT_TEXT = "text-indigo-600";
const ACCENT_BG = "bg-indigo-600 hover:bg-indigo-700 text-white";

export const Route = createFileRoute('/brand')({
  component: ContentEngineV2FullWorkspace,
})


export default function ContentEngineV2FullWorkspace() {
  // Quản lý giữa các Nhóm Màn hình Core, Hệ thống và trang Brand Voice mới (M13)
  const [currentScreen, setCurrentScreen] = useState<number>(13); // Mặc định mở ngay màn hình Brand Voice mới để review

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased">
      
      {/* GLOBAL DEMO CONTROLLER HEADER */}
      <div className="bg-white border-b border-slate-200 px-4 py-2.5 flex flex-wrap items-center justify-between sticky top-0 z-50 gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-indigo-600" />
          <span className="font-bold text-sm tracking-tight">Content Engine V2.0 Redesign</span>
          <span className="text-[10px] bg-indigo-50 text-indigo-600 font-mono px-1.5 py-0.5 rounded font-bold">Brand Voice Added</span>
        </div>
        
        {/* Switcher cho toàn bộ 13 màn hình để test flow nhanh */}
        <div className="flex flex-wrap bg-slate-100 p-1 rounded-lg text-[11px] font-medium max-w-full overflow-x-auto gap-0.5">
          <div className="flex items-center px-1.5 text-slate-400 text-[10px] uppercase font-bold">Bộ 1:</div>
          {[1, 2, 3, 4, 5, 6].map((num) => (
            <button key={num} onClick={() => setCurrentScreen(num)} className={`px-2.5 py-1 rounded-md transition-all ${currentScreen === num ? 'bg-white text-slate-900 shadow-sm font-bold' : 'text-slate-500 hover:text-slate-900'}`}>M{num}</button>
          ))}
          <div className="w-[1px] bg-slate-200 mx-1 self-stretch" />
          <div className="flex items-center px-1.5 text-slate-400 text-[10px] uppercase font-bold">Bộ 2 (Admin):</div>
          {[7, 8, 9, 10, 11, 12].map((num) => (
            <button key={num} onClick={() => setCurrentScreen(num)} className={`px-2.5 py-1 rounded-md transition-all ${currentScreen === num ? 'bg-indigo-600 text-white shadow-sm font-bold' : 'text-slate-500 hover:text-indigo-600'}`}>M{num}</button>
          ))}
          <div className="w-[1px] bg-slate-200 mx-1 self-stretch" />
          <button onClick={() => setCurrentScreen(13)} className={`px-3 py-1 rounded-md transition-all ${currentScreen === 13 ? 'bg-emerald-600 text-white shadow-sm font-bold' : 'text-emerald-600 font-bold hover:bg-emerald-50'}`}>
            ★ Brand Voice (M13)
          </button>
        </div>

        <div className="text-xs font-medium text-slate-500 hidden md:block">
          Workspace Owner: <span className="text-slate-900 font-bold">Nguyen Minh</span>
        </div>
      </div>

      {/* WORKSPACE AREA CONTAINER */}
      <div className="p-4 md:p-6 max-w-[1600px] mx-auto min-h-[calc(100vh-60px)]">
        
        {/* BỘ 1 & 2 KHÔNG ĐỔI */}
        {currentScreen === 1 && <ScreenDashboard onNav={(s) => setCurrentScreen(s)} />}
        {currentScreen === 2 && <ScreenCreateContent onBack={() => setCurrentScreen(1)} onSubmit={() => setCurrentScreen(3)} />}
        {currentScreen === 3 && <ScreenWorkspace onBack={() => setCurrentScreen(2)} onGoToReview={() => setCurrentScreen(4)} onGoToAuto={() => setCurrentScreen(5)} />}
        {currentScreen === 4 && <ScreenReviewMode onBack={() => setCurrentScreen(3)} />}
        {currentScreen === 5 && <ScreenAutoMode onBack={() => setCurrentScreen(3)} />}
        {currentScreen === 6 && <ScreenMobileView />}
        {currentScreen === 7 && <ScreenDashboardV2 onNav={(s) => setCurrentScreen(s)} />}
        {currentScreen === 8 && <ScreenTemplatesMau onNav={(s) => setCurrentScreen(s)} />}
        {currentScreen === 9 && <ScreenBrandProfile onNav={(s) => setCurrentScreen(s)} />}
        {currentScreen === 10 && <ScreenTichHopKenh onNav={(s) => setCurrentScreen(s)} />}
        {currentScreen === 11 && <ScreenBaoCaoHieuQua onNav={(s) => setCurrentScreen(s)} />}
        {currentScreen === 12 && <ScreenCaiDatHeThong onNav={(s) => setCurrentScreen(s)} />}

        {/* MÀN HÌNH MỚI BỔ SUNG: 13 — BRAND VOICE THEO DESIGN CHUẨN */}
        {currentScreen === 13 && <ScreenBrandVoice ONNav={(s) => setCurrentScreen(s)} />}

      </div>
    </div>
  );
}

// ============================================================================
// SIDEBAR CẬP NHẬT THÊM ITEM "BRAND VOICE" THEO PHONG CÁCH DESIGN MỚI
// ============================================================================
function AdminSidebarLayout({ activeTab, onNav, children }: { activeTab: number, onNav: (s: number) => void, children: React.ReactNode }) {
  const menus = [
    { id: 7, label: "Dashboard", icon: LayoutDashboard },
    { id: 2, label: "Create Content", icon: Plus },
    { id: 3, label: "Projects", icon: FolderKanban },
    { id: 8, label: "Templates", icon: FileText },
    { id: 13, label: "Brand Voice", icon: Volume2 }, // Điểm cập nhật mới kết nối đến M13
    { id: 10, label: "Integrations", icon: Layers },
    { id: 11, label: "Reports", icon: BarChart3 },
    { id: 12, label: "Settings", icon: Settings },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* Left Sidebar Layout */}
      <div className="lg:col-span-3 xl:col-span-2 bg-white p-4 rounded-xl border border-slate-200 space-y-6 shadow-xs">
        <div className="space-y-1">
          {menus.map((m) => {
            const Icon = m.icon;
            return (
              <button
                key={m.id}
                onClick={() => onNav(m.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 text-xs font-semibold rounded-md transition-colors ${
                  activeTab === m.id 
                    ? 'bg-indigo-50 text-indigo-700 font-bold' 
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

        {/* Credit Widget */}
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

        {/* User profile */}
        <div className="flex items-center gap-2.5 pt-2 border-t border-slate-100">
          <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-amber-400 to-indigo-600 flex items-center justify-center text-[10px] font-bold text-white shrink-0">NM</div>
          <div className="text-[11px] overflow-hidden">
            <div className="font-bold text-slate-900 truncate">Nguyễn Minh</div>
            <div className="text-slate-400 truncate">Pro Plan</div>
          </div>
        </div>
      </div>

      {/* Right Workspace Pane */}
      <div className="lg:col-span-9 xl:col-span-10 space-y-6">
        {children}
      </div>
    </div>
  );
}

// ============================================================================
// MÀN HÌNH 13 — CHI TIẾT PHÂN HỆ QUẢN TRỊ "BRAND VOICE" MỚI
// ============================================================================
function ScreenBrandVoice({ ONNav }: { ONNav: (s: number) => void }) {
  const [selectedVoice, setSelectedVoice] = useState("Thân thiện");
  const [ctaStyle, setCtaStyle] = useState("Mềm mại");
  const [selectedStyle, setSelectedStyle] = useState("Tối giản");
  const [selectedImgType, setSelectedImgType] = useState("Ảnh thực tế");

  return (
    <AdminSidebarLayout activeTab={13} onNav={ONNav}>
      
      {/* Header chính của Page Brand Voice */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-lg font-black tracking-tight text-slate-900 flex items-center gap-2">
            <Volume2 className="w-5 h-5 text-indigo-600" /> Brand Voice
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">Thiết lập giọng văn, phong cách và thông điệp thương hiệu của bạn.</p>
        </div>
        <div className="flex items-center gap-2 self-end sm:self-auto">
          <button className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-slate-50 shadow-xs flex items-center gap-1.5">
            <Eye className="w-3.5 h-3.5" /> Xem trước
          </button>
          <button className={`px-4 py-1.5 text-xs font-bold rounded-lg shadow-sm ${ACCENT_BG}`}>
            Lưu thay đổi
          </button>
        </div>
      </div>

      {/* Grid trên: Gồm 3 cột cấu hình chính độc lập */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 text-xs">
        
        {/* Khối 1: Giọng văn & Tone */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center font-mono text-[11px]">1</span>
            <h3>Giọng văn & Tone</h3>
          </div>
          <p className="text-[11px] text-slate-400">Chọn giọng văn phù hợp với thương hiệu của bạn.</p>
          
          {/* Tone of voice selector */}
          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Tone of Voice</span>
            <div className="space-y-2">
              {[
                { name: "Thân thiện", desc: "Gần gũi, tự nhiên, dễ hiểu", emoji: "😊" },
                { name: "Chuyên nghiệp", desc: "Trang trọng, đáng tin cậy", emoji: "💼" },
                { name: "Truyền cảm hứng", desc: "Tích cực, động viên, thúc đẩy", emoji: "✨" },
                { name: "Hài hước", desc: "Vui vẻ, dí dỏm, sáng tạo", emoji: "😆" },
                { name: "Tối giản", desc: "Ngắn gọn, rõ ràng, súc tích", emoji: "📝" },
              ].map((tone) => (
                <div 
                  key={tone.name}
                  onClick={() => setSelectedVoice(tone.name)}
                  className={`p-3 rounded-lg border transition-all cursor-pointer flex items-start gap-3 ${
                    selectedVoice === tone.name 
                      ? 'border-indigo-600 bg-indigo-50/20 ring-1 ring-indigo-600' 
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <input 
                    type="radio" 
                    checked={selectedVoice === tone.name} 
                    onChange={() => {}} 
                    className="text-indigo-600 focus:ring-indigo-500 mt-0.5" 
                  />
                  <div>
                    <div className="font-bold text-slate-900 flex items-center gap-1">
                      <span>{tone.emoji}</span> {tone.name}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{tone.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quy tắc giọng văn */}
          <div className="space-y-2 pt-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Quy tắc giọng văn</span>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2 text-slate-600 font-medium">
              <div className="flex items-start gap-2"><Check className="w-3.5 h-3.5 text-indigo-600 mt-0.5 shrink-0" /> <span>Sử dụng ngôn ngữ đơn giản, dễ hiểu</span></div>
              <div className="flex items-start gap-2"><Check className="w-3.5 h-3.5 text-indigo-600 mt-0.5 shrink-0" /> <span>Tránh thuật ngữ chuyên môn phức tạp</span></div>
              <div className="flex items-start gap-2"><Check className="w-3.5 h-3.5 text-indigo-600 mt-0.5 shrink-0" /> <span>Ưu tiên câu ngắn, chủ động</span></div>
              <div className="flex items-start gap-2"><Check className="w-3.5 h-3.5 text-indigo-600 mt-0.5 shrink-0" /> <span>Luôn tích cực và khích lệ</span></div>
              <div className="text-right text-[10px] text-slate-400 font-mono pt-1">4/10 quy tắc</div>
            </div>
          </div>
        </div>

        {/* Khối 2: CTA & Thông điệp */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center font-mono text-[11px]">2</span>
            <h3>CTA & Thông điệp</h3>
          </div>
          <p className="text-[11px] text-slate-400">Thiết lập các CTA và thông điệp cốt lõi.</p>

          {/* CTA Style */}
          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">CTA Style</span>
            <div className="grid grid-cols-3 gap-2 text-center font-bold">
              {[
                { name: "Mềm mại", icon: Smile },
                { name: "Trung tính", icon: MessageSquare },
                { name: "Mạnh mẽ", icon: Flame }
              ].map((style) => (
                <button
                  key={style.name}
                  onClick={() => setCtaStyle(style.name)}
                  className={`py-2 rounded-lg border text-[11px] flex items-center justify-center gap-1 transition-all ${
                    ctaStyle === style.name 
                      ? 'bg-indigo-50 text-indigo-700 border-indigo-300 shadow-xs' 
                      : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <style.icon className="w-3 h-3" />
                  {style.name}
                </button>
              ))}
            </div>
          </div>

          {/* CTA Mẫu */}
          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">CTA Mẫu</span>
            <div className="space-y-1.5">
              {["Khám phá ngay", "Tìm hiểu thêm", "Bắt đầu hành trình của bạn", "Nhận ưu đãi đặc biệt", "Đăng ký miễn phí"].map((cta, idx) => (
                <div key={idx} className="bg-white border border-slate-200 px-3 py-2 rounded-lg flex items-center justify-between font-medium text-slate-700 hover:border-slate-300 transition-colors">
                  <span>{cta}</span>
                  <Plus className="w-3.5 h-3.5 text-slate-400 cursor-pointer hover:text-slate-600" />
                </div>
              ))}
            </div>
          </div>

          {/* Thông điệp cốt lõi */}
          <div className="space-y-2 pt-1">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Thông điệp cốt lõi</span>
            <div className="relative">
              <textarea 
                rows={4} 
                className="w-full bg-white border border-slate-200 p-3 rounded-lg outline-none focus:border-indigo-500 font-medium leading-relaxed resize-none text-slate-700"
                defaultValue="Chúng tôi giúp doanh nghiệp nhỏ phát triển mạnh mẽ thông qua giải pháp marketing đơn giản, hiệu quả và tiết kiệm chi phí."
              />
              <span className="absolute bottom-2.5 right-3 text-[10px] text-slate-400 font-mono">96/200 ký tự</span>
            </div>
          </div>
        </div>

        {/* Khối 3: Phong cách hình ảnh */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center font-mono text-[11px]">3</span>
            <h3>Phong cách hình ảnh</h3>
          </div>
          <p className="text-[11px] text-slate-400">Xác định phong cách hình ảnh đại diện cho thương hiệu.</p>

          {/* Phong cách chủ đạo */}
          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Phong cách chủ đạo</span>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { name: "Tối giản", img: "https://images.unsplash.com/photo-1544816155-12df9643f363?w=120&auto=format&fit=crop&q=60" },
                { name: "Hiện đại", img: "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=120&auto=format&fit=crop&q=60" },
                { name: "Ấm áp", img: "https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=120&auto=format&fit=crop&q=60" },
                { name: "Năng động", img: "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=120&auto=format&fit=crop&q=60" }
              ].map((style) => (
                <div 
                  key={style.name}
                  onClick={() => setSelectedStyle(style.name)}
                  className={`border rounded-lg overflow-hidden cursor-pointer transition-all pb-1.5 text-center relative ${
                    selectedStyle === style.name ? 'border-indigo-600 ring-2 ring-indigo-500/10' : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <img src={style.img} alt={style.name} className="w-full h-14 object-cover" />
                  <span className="text-[10px] font-bold block mt-1 text-slate-800">{style.name}</span>
                  {selectedStyle === style.name && (
                    <div className="absolute top-1 left-1 bg-indigo-600 text-white rounded-full p-0.5"><Check className="w-2.5 h-2.5" /></div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Màu sắc chủ đạo */}
          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Màu sắc chủ đạo</span>
            <div className="flex gap-2 justify-between">
              {[
                { hex: "#4F46E5", label: "#4F46E5" },
                { hex: "#10B981", label: "#10B981" },
                { hex: "#F59E0B", label: "#F59E0B" },
                { hex: "#6B7280", label: "#6B7280" },
                { hex: "#F8FAFC", label: "#F8FAFC", border: true }
              ].map((color, i) => (
                <div key={i} className="text-center space-y-1 flex-1">
                  <div style={{ backgroundColor: color.hex }} className={`h-6 rounded-md w-full ${color.border ? 'border border-slate-200' : ''}`} />
                  <span className="text-[9px] font-mono text-slate-400 block tracking-tight">{color.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Loại hình ảnh */}
          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Loại hình ảnh</span>
            <div className="flex flex-wrap gap-1.5 font-bold">
              {["Ảnh thực tế", "Đồ họa minh họa", "Icon", "3D Render"].map((type) => (
                <button
                  key={type}
                  onClick={() => setSelectedImgType(type)}
                  className={`px-3 py-1 rounded-md border text-[11px] transition-all ${
                    selectedImgType === type 
                      ? 'bg-indigo-50 border-indigo-300 text-indigo-700 shadow-xs' 
                      : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {type === selectedImgType && "✓ "} {type}
                </button>
              ))}
            </div>
          </div>

          {/* Quy tắc hình ảnh */}
          <div className="space-y-2 pt-1">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Quy tắc hình ảnh</span>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2 text-slate-600 font-medium">
              <div className="flex items-start gap-2"><Check className="w-3.5 h-3.5 text-indigo-600 mt-0.5 shrink-0" /> <span>Ưu tiên hình ảnh ánh sáng, ít chi tiết rối</span></div>
              <div className="flex items-start gap-2"><Check className="w-3.5 h-3.5 text-indigo-600 mt-0.5 shrink-0" /> <span>Sử dụng không gian trắng hợp lý</span></div>
              <div className="flex items-start gap-2"><Check className="w-3.5 h-3.5 text-indigo-600 mt-0.5 shrink-0" /> <span>Hình ảnh thể hiện sự tin cậy và chuyên nghiệp</span></div>
            </div>
          </div>

        </div>
      </div>

      {/* Grid dưới: Chia thành 2 cột khối lớn (Sản phẩm / Dịch vụ & Tài liệu tham khảo) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 text-xs">
        
        {/* Khối 4: Sản phẩm / Dịch vụ (Chiếm 7 cột) */}
        <div className="lg:col-span-7 bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center font-mono text-[11px]">4</span>
            <h3>Sản phẩm / Dịch vụ</h3>
          </div>
          <p className="text-[11px] text-slate-400">Mô tả chi tiết sản phẩm hoặc dịch vụ của bạn.</p>

          <div className="grid grid-cols-1 sm:grid-cols-12 gap-4 items-start">
            {/* List sản phẩm chính bên trái */}
            <div className="sm:col-span-6 space-y-2">
              <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Sản phẩm / Dịch vụ chính</span>
              <div className="space-y-1.5">
                {[
                  "Phần mềm quản lý nội dung",
                  "Dịch vụ marketing tổng thể",
                  "Tư vấn chiến lược thương hiệu",
                  "Đào tạo marketing online"
                ].map((prod, index) => (
                  <div key={index} className="flex items-center justify-between border border-slate-200 px-3 py-2 rounded-lg bg-white group hover:border-slate-300">
                    <div className="flex items-center gap-2 font-medium text-slate-700">
                      <AlignLeft className="w-3.5 h-3.5 text-slate-400 cursor-move" />
                      <span>{prod}</span>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-1 text-slate-400 hover:text-slate-600"><Edit3 className="w-3 h-3" /></button>
                      <button className="p-1 text-slate-400 hover:text-indigo-600"><Bookmark className="w-3 h-3" /></button>
                    </div>
                  </div>
                ))}
              </div>
              <button className="text-[11px] text-indigo-600 font-bold hover:underline flex items-center gap-1 pt-1">
                <Plus className="w-3.5 h-3.5" /> Thêm sản phẩm / dịch vụ
              </button>
            </div>

            {/* Lợi ích nổi bật & Đối tượng mục tiêu bên phải */}
            <div className="sm:col-span-6 space-y-4">
              <div className="space-y-2">
                <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Lợi ích nổi bật</span>
                <div className="space-y-1.5 text-slate-600 font-medium">
                  {["Tiết kiệm thời gian và chi phí", "Dễ sử dụng, không cần kỹ thuật", "Hỗ trợ tận tâm 24/7", "Kết quả đo lường được", "Tăng trưởng bền vững"].map((benefit, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-indigo-50 rounded-full flex items-center justify-center text-indigo-600 text-[10px] font-bold">✓</div>
                      <span>{benefit}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Đối tượng khách hàng mục tiêu */}
              <div className="space-y-2">
                <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Đối tượng khách hàng mục tiêu</span>
                <div className="flex flex-wrap gap-1.5">
                  {["Doanh nghiệp nhỏ", "Startup", "Shop online", "Freelancer"].map((tag) => (
                    <span key={tag} className="px-2.5 py-1 bg-indigo-50/60 text-indigo-700 rounded-md font-bold text-[10px] border border-indigo-100/40">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Khối 5: Tài liệu tham khảo (Chiếm 5 cột) */}
        <div className="lg:col-span-5 bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center font-mono text-[11px]">5</span>
            <h3>Tài liệu tham khảo</h3>
          </div>
          <p className="text-[11px] text-slate-400">Cung cấp tài liệu tham khảo để AI hiểu rõ hơn về thương hiệu.</p>

          {/* Tài liệu thương hiệu */}
          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Tài liệu thương hiệu</span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {[
                { name: "Brand Guideline.pdf", size: "2.4 MB", type: "pdf" },
                { name: "Voice & Tone Guide.docx", size: "1.1 MB", type: "doc" },
                { name: "Brand Presentation.pptx", size: "5.7 MB", type: "ppt" }
              ].map((doc, idx) => (
                <div key={idx} className="border border-slate-200 p-2.5 rounded-lg bg-white relative hover:border-slate-300 transition-colors flex flex-col justify-between min-h-[64px]">
                  <div className="flex items-start gap-1.5">
                    <div className="w-5 h-5 rounded bg-red-50 text-red-600 flex items-center justify-center text-[8px] font-black uppercase tracking-tight shrink-0">{doc.type}</div>
                    <div className="overflow-hidden">
                      <div className="font-bold text-slate-800 truncate text-[10px]">{doc.name}</div>
                      <div className="text-[9px] text-slate-400 font-mono mt-0.5">{doc.size}</div>
                    </div>
                  </div>
                </div>
              ))}
              
              {/* Thêm tài liệu dnd upload zone view */}
              <div className="border border-dashed border-slate-200 p-2 rounded-lg bg-slate-50 flex flex-col items-center justify-center text-center text-[9px] text-slate-400 hover:bg-slate-100/50 cursor-pointer transition">
                <Upload className="w-3.5 h-3.5 text-slate-400 mb-1" />
                <span className="font-bold text-slate-600">Thêm tài liệu</span>
                <span className="text-[8px] scale-90 mt-0.5">PDF, DOCX, PPTX</span>
              </div>
            </div>
          </div>

          {/* Website tham khảo */}
          <div className="space-y-1.5">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Website tham khảo</span>
            <div className="bg-white border border-slate-200 px-3 py-1.5 rounded-lg flex items-center justify-between text-indigo-600 font-medium">
              <span>https://yourbrand.com</span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400 cursor-pointer hover:text-indigo-600" />
            </div>
          </div>

          {/* Ghi chú thêm */}
          <div className="space-y-1.5">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Ghi chú thêm</span>
            <div className="relative">
              <textarea 
                rows={3} 
                className="w-full bg-white border border-slate-200 p-3 rounded-lg outline-none focus:border-indigo-500 font-medium leading-relaxed resize-none text-slate-700"
                defaultValue="Luôn tham khảo brand guideline trước khi tạo nội dung. Ưu tiên thông điệp về giá trị và lợi ích cho khách hàng."
              />
              <span className="absolute bottom-2.5 right-3 text-[10px] text-slate-400 font-mono">96/500 ký tự</span>
            </div>
          </div>
        </div>

      </div>

    </AdminSidebarLayout>
  );
}

// ============================================================================
// CÁC MÀN HÌNH PHỤ TRỢ CORE HỆ THỐNG GIỮ NGUYÊN HOẠT ĐỘNG
// ============================================================================
function ScreenDashboard({ onNav }: { onNav: (s: number) => void }) {
  return (
    <div className="bg-white p-6 rounded-xl border border-slate-200 space-y-4">
      <h2 className="text-sm font-bold">Màn hình Core Dashboard (M1)</h2>
      <button onClick={() => onNav(13)} className={`px-4 py-1.5 text-xs font-bold rounded ${ACCENT_BG}`}>Truy cập Brand Voice</button>
    </div>
  );
}
function ScreenCreateContent({ onBack, onSubmit }: { onBack: () => void, onSubmit: () => void }) { return <div className="p-4 bg-white border rounded">Create Content Work</div>; }
function ScreenWorkspace({ onBack, onGoToReview, onGoToAuto }: { onBack: () => void, onGoToReview: () => void, onGoToAuto: () => void }) { return <div className="p-4 bg-white border rounded">Workspace Content</div>; }
function ScreenReviewMode({ onBack }: { onBack: () => void }) { return <div className="p-4 bg-white border rounded">Review Diff</div>; }
function ScreenAutoMode({ onBack }: { onBack: () => void }) { return <div className="p-4 bg-white border rounded">Auto Pilot Mode</div>; }
function ScreenMobileView() { return <div className="p-4 bg-white border rounded">Mobile Preview</div>; }
function ScreenDashboardV2({ onNav }: { onNav: (s: number) => void }) { return <div className="p-4 bg-white border rounded">Dashboard Advanced V2</div>; }
function ScreenTemplatesMau({ onNav }: { onNav: (s: number) => void }) { return <div className="p-4 bg-white border rounded">Templates Layout</div>; }
function ScreenBrandProfile({ onNav }: { onNav: (s: number) => void }) { return <div className="p-4 bg-white border rounded">Brand Profile Config</div>; }
function ScreenTichHopKenh({ onNav }: { onNav: (s: number) => void }) { return <div className="p-4 bg-white border rounded">Integrations Webhooks</div>; }
function ScreenBaoCaoHieuQua({ onNav }: { onNav: (s: number) => void }) { return <div className="p-4 bg-white border rounded">Analytics Reports</div>; }
function ScreenCaiDatHeThong({ onNav }: { onNav: (s: number) => void }) { return <div className="p-4 bg-white border rounded">System Settings</div>; }