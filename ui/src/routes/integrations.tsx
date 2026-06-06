"use client";

import { createFileRoute } from '@tanstack/react-router';
import { 
  Globe, 
  Shield, 
  RefreshCw, 
  ExternalLink, 
  Settings2, 
  AlertCircle, 
  HelpCircle, 
  ShoppingBag, 
  Video 
} from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export const Route = createFileRoute('/integrations')({
  component: PageIntegrations,
});

export default function PageIntegrations() {
  // Mở rộng mock data đa dạng kênh để giao diện thực tế và đầy đủ hơn
  const channels = [
    { 
      id: "ch-fb",
      name: "Facebook Fanpage", 
      desc: "Tự động đăng bài viết kèm hình ảnh/video lên dòng thời gian của trang.", 
      status: "Đã kết nối", 
      account: "Tiệm Bánh ABC (Page ID: 8932)", 
      icon: Globe, 
      active: true,
      lastSync: "2 giờ trước",
      scope: ["manage_pages", "publish_to_groups"]
    },
    { 
      id: "ch-wp",
      name: "WordPress CMS Web", 
      desc: "Đẩy bài viết chuẩn SEO trực tiếp vào mục lưu nháp (Draft) hoặc xuất bản.", 
      status: "Chưa cấu hình", 
      account: "Chưa liên kết tài khoản", 
      icon: Shield, 
      active: false,
      lastSync: "---",
      scope: []
    },
    { 
      id: "ch-sh",
      name: "Shopify Store", 
      desc: "Đồng bộ mô tả sản phẩm thông minh tạo bởi AI sang danh mục sản phẩm.", 
      status: "Đã kết nối", 
      account: "abc-bakery.myshopify.com", 
      icon: ShoppingBag, 
      active: true,
      lastSync: "1 ngày trước",
      scope: ["write_products", "read_collection_listings"]
    },
    { 
      id: "ch-tt",
      name: "TikTok Creator", 
      desc: "Đẩy kịch bản và video ngắn đã dựng tự động vào mục lưu nháp của kênh.", 
      status: "Chưa cấu hình", 
      account: "Chưa liên kết tài khoản", 
      icon: Video, 
      active: false,
      lastSync: "---",
      scope: []
    }
  ];

  return (
    <div className="space-y-5 max-w-[1000px] mx-auto w-full">
      
       {/* Page Intro */}
          <div className="mb-8">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Define how AI agents speak, write, and convert for your brand.
            </p>
          </div>

      {/* ─── CẤU TRÚC GRID CÁC KÊNH KẾT NỐI ─── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {channels.map((ch) => {
          const Icon = ch.icon;
          return (
            <Sheet key={ch.id}>
              <div className={cn(
                "bg-white p-5 rounded-xl border flex flex-col justify-between gap-4 transition-all hover:shadow-xs",
                ch.active ? "border-slate-200" : "border-slate-200/60 opacity-85 hover:opacity-100"
              )}>
                
                {/* Khối thông tin phía trên của Thẻ */}
                <div className="flex justify-between items-start gap-3">
                  <div className="flex gap-3 items-start min-w-0">
                    <div className={cn(
                      "w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5",
                      ch.active ? 'bg-indigo-50 text-indigo-600 border border-indigo-100' : 'bg-slate-50 text-slate-400 border'
                    )}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="min-w-0 space-y-1">
                      <h3 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                        {ch.name}
                      </h3>
                      <p className="text-[11px] text-slate-400 leading-normal pr-2 font-medium line-clamp-2">{ch.desc}</p>
                    </div>
                  </div>
                  
                  <Badge className={cn(
                    "border-none font-bold text-[10px] px-1.5 py-0 shrink-0",
                    ch.active ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-50" : "bg-slate-100 text-slate-400 hover:bg-slate-100"
                  )}>
                    {ch.status}
                  </Badge>
                </div>

                {/* Thanh trạng thái tài khoản liên kết / Nút gọi Drawer */}
                <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-100 text-[11px] flex justify-between items-center text-slate-600 gap-3">
                  <span className="font-semibold truncate max-w-[200px] text-slate-700 font-mono">{ch.account}</span>
                  
                  {/* Bọc nút tác vụ bằng SheetTrigger */}
                  <SheetTrigger asChild>
                    <button className="text-indigo-600 font-bold hover:text-indigo-700 flex items-center gap-1 shrink-0 text-[11px] bg-white border px-2 py-1 rounded-lg shadow-2xs hover:bg-slate-50 transition-colors outline-none">
                      {ch.active ? <Settings2 className="w-3 h-3 text-indigo-500" /> : <ExternalLink className="w-3 h-3 text-slate-400" />}
                      <span>{ch.active ? 'Cấu hình' : 'Liên kết'}</span>
                    </button>
                  </SheetTrigger>
                </div>

              </div>

              {/* ─── DRAWER CẤU HÌNH CHI TIẾT TỪNG KÊNH PHÂN PHỐI ─── */}
              <SheetContent className="w-full sm:max-w-[400px] rounded-l-[20px] md:rounded-l-xl p-6 flex flex-col h-full gap-5">
                <SheetHeader className="border-b pb-3 shrink-0">
                  <div className="flex items-center justify-between w-full pr-6">
                    <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">Tham số cấu hình</span>
                    <Badge className={cn("border-none font-bold text-[9px] px-1.5 py-0", ch.active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-400")}>
                      {ch.status}
                    </Badge>
                  </div>
                  <SheetTitle className="text-sm font-bold text-slate-800 text-left pt-1 flex items-center gap-2">
                    <Icon className="w-4 h-4 text-indigo-600" />
                    <span>Cấu hình {ch.name}</span>
                  </SheetTitle>
                </SheetHeader>

                {/* Nội dung chi tiết cổng API / Phân quyền */}
                <div className="flex-1 overflow-y-auto space-y-4 min-h-0 flex flex-col text-xs">
                  
                  {/* Thông tin kết nối đồng bộ */}
                  <div className="space-y-2 bg-slate-50/60 p-3 border border-slate-100 rounded-xl text-[11px] text-slate-600 font-medium">
                    <div className="flex justify-between">
                      <span>Tài khoản đồng bộ:</span>
                      <span className="text-slate-900 font-bold font-mono">{ch.account}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Lần kiểm tra gần nhất:</span>
                      <span className="text-slate-900 font-mono">{ch.lastSync}</span>
                    </div>
                  </div>

                  {/* Khối quản lý Token / Quyền truy cập */}
                  <div className="space-y-2.5 border p-4 rounded-xl bg-white shadow-2xs">
                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Phạm vi quyền hạn (OAuth Scopes)</label>
                    {ch.active && ch.scope.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {ch.scope.map((s, idx) => (
                          <span key={idx} className="bg-slate-100 text-slate-600 text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded border border-slate-200/40">{s}</span>
                        ))}
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-slate-400 bg-slate-50 p-2 rounded-lg border border-dashed">
                        <AlertCircle size={12} />
                        <span className="text-[11px] font-medium">Chưa cấp bất kỳ quyền xuất bản nào.</span>
                      </div>
                    )}
                  </div>

                  {/* Khung tài liệu hướng dẫn nhanh dạng Alert */}
                  <div className="bg-indigo-50/40 border border-indigo-100 rounded-xl p-4 space-y-2 shrink-0">
                    <div className="flex items-center gap-1.5 text-indigo-900 font-bold text-[11px]">
                      <HelpCircle size={13} className="text-indigo-600 shrink-0" />
                      <span>Hướng dẫn tự động hóa</span>
                    </div>
                    <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
                      Khi bài viết ở trạng thái <strong className="text-emerald-600">Hoàn tất</strong> tại luồng xử lý của Agent, hệ thống sẽ kích hoạt webhook và đẩy tự động sang API của nền tảng này theo phân cấu hình trên.
                    </p>
                  </div>

                </div>

                {/* Hệ thống nút hành động điều phối đáy Drawer */}
                <div className="pt-3 border-t mt-auto space-y-2 shrink-0">
                  {ch.active ? (
                    <>
                      <button 
                        onClick={() => {
                          toast.success(`Đã làm mới kết nối đến kênh ${ch.name}!`);
                        }}
                        className="w-full h-8 text-[11px] bg-white border hover:bg-slate-50 text-slate-700 font-bold rounded-lg flex items-center justify-center gap-1.5 transition-colors shadow-2xs outline-none"
                      >
                        <RefreshCw size={12} className="text-slate-500" /> Làm mới token đồng bộ
                      </button>
                      <button 
                        onClick={() => {
                          toast.error("Đã hủy liên kết kênh phân phối.");
                        }}
                        className="w-full h-8 text-[11px] bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold rounded-lg flex items-center justify-center gap-1.5 transition-colors outline-none"
                      >
                        Ngắt kết nối ứng dụng
                      </button>
                    </>
                  ) : (
                    <button 
                      onClick={() => {
                        toast.info(`Đang chuyển hướng đến cổng xác thực OAuth2 của ${ch.name}...`);
                      }}
                      className="w-full h-8 text-[11px] bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-lg flex items-center justify-center gap-1.5 transition-colors shadow-xs outline-none"
                    >
                      <ExternalLink size={12} /> Bắt đầu liên kết tài khoản
                    </button>
                  )}
                </div>

              </SheetContent>
            </Sheet>
          );
        })}
      </div>

    </div>
  );
}