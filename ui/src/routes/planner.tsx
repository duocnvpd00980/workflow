"use client";

import React, { useState, useMemo } from "react";
import { createFileRoute } from '@tanstack/react-router';
import {
  format, startOfMonth, endOfMonth, startOfWeek, endOfWeek,
  addDays, isSameMonth, isSameDay, subMonths, isToday, addMonths, subWeeks, addWeeks
} from "date-fns";
import { vi } from "date-fns/locale";
import { 
  ChevronLeft, ChevronRight, Search, Calendar,
  X, Pencil, Trash2, Check, Plus, FolderOpen, Clock, Layers, RefreshCw, Zap
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type Channel = "facebook" | "instagram" | "linkedin" | "tiktok";
type Status = "scheduled" | "published" | "draft" | "approved";
type PublishMode = "once" | "recurring" | "queue";

interface Post {
  id: string;
  title: string;
  date: Date;
  time: string;
  channel: Channel;
  status: Status;
  publishMode: PublishMode; // Trả lại chế độ xuất bản
  contentPreview?: string;
}

const MOCK_POOL_POSTS: Post[] = [
  { id: "p1", title: "Khởi động Chiến dịch Khuyến mãi Mùa hè", date: new Date(), time: "09:00", channel: "facebook", status: "approved", publishMode: "once", contentPreview: "Nội dung bài viết chạy chiến dịch mùa hè hoành tráng..." },
  { id: "p2", title: "Video Teaser Sản phẩm Công nghệ Mới", date: new Date(), time: "14:00", channel: "tiktok", status: "draft", publishMode: "queue", contentPreview: "Ý tưởng video tiktok review nhanh tính năng..." },
  { id: "p3", title: "Infographic: 10 mẹo tối ưu hóa chi phí vận hành", date: new Date(), time: "10:30", channel: "instagram", status: "approved", publishMode: "recurring", contentPreview: "Bộ ảnh thiết kế chia sẻ kiến thức hữu ích..." },
  { id: "p4", title: "Bản tin ngành hàng tuần - Xu hướng 2026", date: new Date(), time: "08:00", channel: "linkedin", status: "draft", publishMode: "once", contentPreview: "Bài viết phân tích chuyên sâu thị trường SaaS toàn cầu..." },
];

const INITIAL_SCHEDULED_POSTS: Post[] = [
  { id: "1", title: "Ghi chú Cập nhật Hệ thống API", date: new Date(2026, 5, 6), time: "09:00", channel: "linkedin", status: "scheduled", publishMode: "once" },
  { id: "2", title: "Mini-game tương tác cuối tuần", date: new Date(2026, 5, 6), time: "19:30", channel: "facebook", status: "scheduled", publishMode: "recurring" },
  { id: "3", title: "Hình ảnh Feedback Khách hàng", date: new Date(2026, 5, 12), time: "11:00", channel: "instagram", status: "published", publishMode: "queue" },
];

const CHANNEL_STYLE = {
  facebook: "bg-blue-500/10 text-blue-600 border-blue-200 hover:bg-blue-500/20",
  instagram: "bg-pink-500/10 text-pink-600 border-pink-200 hover:bg-pink-500/20",
  linkedin: "bg-indigo-500/10 text-indigo-600 border-indigo-200 hover:bg-indigo-500/20",
  tiktok: "bg-slate-900/10 text-slate-900 border-slate-300 hover:bg-slate-900/20",
};

const CHANNEL_DOT = {
  facebook: "bg-blue-500",
  instagram: "bg-pink-500",
  linkedin: "bg-indigo-500",
  tiktok: "bg-slate-900",
};

const STATUS_BADGE = {
  draft: "bg-slate-100 text-slate-600",
  approved: "bg-amber-100 text-amber-700",
  scheduled: "bg-blue-100 text-blue-700",
  published: "bg-emerald-100 text-emerald-700",
};

// Style cho Chế độ xuất bản bài đăng
const PUBLISH_MODE_DETAILS = {
  once: { label: "Một lần", color: "bg-sky-50 text-sky-700 border-sky-200", icon: <Zap size={12} /> },
  recurring: { label: "Lặp lại", color: "bg-purple-50 text-purple-700 border-purple-200", icon: <RefreshCw size={12} /> },
  queue: { label: "Hàng đợi", color: "bg-teal-50 text-teal-700 border-teal-200", icon: <Layers size={12} /> },
};

export const Route = createFileRoute('/planner')({
  component: CalendarDashboard,
});

export default function CalendarDashboard() {
  const [scheduledPosts, setScheduledPosts] = useState<Post[]>(INITIAL_SCHEDULED_POSTS);
  const [poolPosts, setPoolPosts] = useState<Post[]>(MOCK_POOL_POSTS);
  
  const [currentDate, setCurrentDate] = useState<Date>(new Date(2026, 5, 6)); 
  const [selectedChannel, setSelectedChannel] = useState<string>("all");
  const [selectedModeFilter, setSelectedModeFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
  const [isQuickCreateOpen, setIsQuickCreateOpen] = useState(false);
  const [quickCreateDate, setQuickCreateDate] = useState<string>("");
  const [quickCreateTab, setQuickCreateTab] = useState<"pool" | "new">("pool");

  // Bộ lọc dữ liệu Kho nhanh
  const filteredPool = useMemo(() => {
    return poolPosts.filter(p => {
      const matchesSearch = p.title.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesChannel = selectedChannel === "all" || p.channel === selectedChannel;
      const matchesMode = selectedModeFilter === "all" || p.publishMode === selectedModeFilter;
      return matchesSearch && matchesChannel && matchesMode && (p.status === "draft" || p.status === "approved");
    });
  }, [poolPosts, searchQuery, selectedChannel, selectedModeFilter]);

  // Bộ lọc dữ liệu bài đã lên lịch
  const filteredScheduled = useMemo(() => {
    return scheduledPosts.filter(p => {
      const matchesChannel = selectedChannel === "all" || p.channel === selectedChannel;
      const matchesMode = selectedModeFilter === "all" || p.publishMode === selectedModeFilter;
      return matchesChannel && matchesMode;
    });
  }, [scheduledPosts, selectedChannel, selectedModeFilter]);

  // Lấy các bài viết của ngày hiện tại đang click chọn để hiển thị timeline trên mobile
  const activeDayPosts = useMemo(() => {
    return filteredScheduled.filter(p => isSameDay(p.date, currentDate))
      .sort((a, b) => a.time.localeCompare(b.time));
  }, [filteredScheduled, currentDate]);

  // Drag & Drop cho Desktop
  const handleDragStart = (e: React.DragEvent, post: Post) => {
    e.dataTransfer.setData("text/plain", post.id);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDropOnDay = (e: React.DragEvent, targetDate: Date) => {
    e.preventDefault();
    const postId = e.dataTransfer.getData("text/plain");
    const foundPost = poolPosts.find(p => p.id === postId);

    if (foundPost) {
      setSelectedPost({
        ...foundPost,
        date: targetDate,
        time: "09:00",
        status: "scheduled"
      });
    }
  };

  const handleSavePostConfig = (finalPost: Post) => {
    if (poolPosts.some(p => p.id === finalPost.id)) {
      setPoolPosts(prev => prev.filter(p => p.id !== finalPost.id));
      setScheduledPosts(prev => [...prev, finalPost]);
    } else {
      setScheduledPosts(prev => prev.map(p => p.id === finalPost.id ? finalPost : p));
    }
    setSelectedPost(null);
    toast.success(`Đã xếp lịch bài viết thành công!`);
  };

  const handleQuickCreateSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    
    if (quickCreateTab === "new") {
      const newPost: Post = {
        id: Math.random().toString(36).substr(2, 9),
        title: formData.get("title") as string,
        date: new Date(quickCreateDate),
        time: formData.get("time") as string || "09:00",
        channel: formData.get("channel") as Channel,
        publishMode: formData.get("publishMode") as PublishMode,
        status: "scheduled"
      };
      setScheduledPosts(prev => [...prev, newPost]);
      toast.success("Đã tạo mới và lên lịch bài viết!");
    } else {
      const selectedPoolId = formData.get("poolPostId") as string;
      const foundPoolPost = poolPosts.find(p => p.id === selectedPoolId);
      if (foundPoolPost) {
        const scheduled: Post = {
          ...foundPoolPost,
          date: new Date(quickCreateDate),
          time: formData.get("time") as string || "09:00",
          publishMode: formData.get("publishMode") as PublishMode, // cập nhật hoặc giữ nguyên mode mới chọn
          status: "scheduled"
        };
        setPoolPosts(prev => prev.filter(p => p.id !== selectedPoolId));
        setScheduledPosts(prev => [...prev, scheduled]);
        toast.success("Đã lấy bài từ Kho lên lịch thành công!");
      }
    }
    setIsQuickCreateOpen(false);
  };

  // UI LỊCH TUẦN NGANG GỌN GÀNG (MOBILE ONLY)
  const renderMobileWeeklyStrip = () => {
    const weekStart = startOfWeek(currentDate, { weekStartsOn: 0 });
    const days = [];

    for (let i = 0; i < 7; i++) {
      const day = addDays(weekStart, i);
      const isSelected = isSameDay(day, currentDate);
      const hasPosts = filteredScheduled.some(p => isSameDay(p.date, day));

      days.push(
        <button
          key={day.toString()}
          onClick={() => setCurrentDate(day)}
          className={cn(
            "flex-1 flex flex-col items-center py-2 rounded-xl transition-all relative",
            isSelected ? "bg-slate-950 text-white shadow-md font-bold scale-105" : "bg-background hover:bg-muted/50"
          )}
        >
          <span className="text-[10px] font-medium uppercase opacity-60 mb-0.5">
            {format(day, "eee", { locale: vi }).replace("Thử ", "T")}
          </span>
          <span className="text-sm font-bold font-mono">
            {format(day, "d")}
          </span>
          {hasPosts && !isSelected && (
            <span className="absolute bottom-1 w-1 h-1 bg-blue-600 rounded-full" />
          )}
        </button>
      );
    }

    return (
      <div className="block lg:hidden bg-background border rounded-2xl p-3.5 shadow-sm space-y-3">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-1.5">
            <Calendar size={15} className="text-slate-500" />
            <span className="text-xs font-bold text-slate-800">Lịch tuần hiện tại</span>
          </div>
          <div className="flex gap-1">
            <button onClick={() => setCurrentDate(subWeeks(currentDate, 1))} className="p-1 bg-muted rounded-md text-slate-700"><ChevronLeft size={14}/></button>
            <button onClick={() => setCurrentDate(addWeeks(currentDate, 1))} className="p-1 bg-muted rounded-md text-slate-700"><ChevronRight size={14}/></button>
          </div>
        </div>
        <div className="flex gap-1 justify-between bg-muted/30 p-1 rounded-xl border border-muted/50">
          {days}
        </div>
      </div>
    );
  };

  // UI LỊCH THÁNG LƯỚI Ô VUÔNG (DESKTOP ONLY)
  const renderDesktopMonthGrid = () => {
    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(monthStart);
    const startDate = startOfWeek(monthStart);
    const endDate = endOfWeek(monthEnd);

    const rows = [];
    let days = [];
    let day = startDate;

    const weekdaysHeader = (
      <div className="grid grid-cols-7 text-center border-b bg-muted/30 text-[11px] font-bold uppercase tracking-wider text-muted-foreground py-2">
        {["CN", "T2", "T3", "T4", "T5", "T6", "T7"].map(d => <div key={d}>{d}</div>)}
      </div>
    );

    while (day <= endDate) {
      for (let i = 0; i < 7; i++) {
        const cloneDay = day;
        const dayPosts = filteredScheduled.filter(p => isSameDay(p.date, cloneDay));
        const isCurrentMonth = isSameMonth(cloneDay, monthStart);

        days.push(
          <div
            key={cloneDay.toString()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => handleDropOnDay(e, cloneDay)}
            onClick={() => {
              setQuickCreateDate(format(cloneDay, "yyyy-MM-dd"));
              setIsQuickCreateOpen(true);
            }}
            className={cn(
              "flex-1 min-h-[125px] p-2 border-r border-b border-muted/50 transition-colors relative cursor-pointer hover:bg-muted/10",
              isCurrentMonth ? "bg-background" : "bg-muted/10 opacity-40"
            )}
          >
            <span className={cn(
              "text-xs font-bold px-1.5 py-0.5 rounded-md",
              isToday(cloneDay) ? "bg-slate-900 text-white" : "text-muted-foreground"
            )}>
              {format(cloneDay, "d")}
            </span>
            
            <div className="flex flex-col gap-1.5 mt-2" onClick={(e) => e.stopPropagation()}>
              {dayPosts.map(p => (
                <div
                  key={p.id}
                  onClick={() => setSelectedPost(p)}
                  className={cn("text-[11px] font-semibold p-1 px-1.5 rounded-md border truncate shadow-2xs transition-all flex flex-col gap-0.5", CHANNEL_STYLE[p.channel])}
                >
                  <div className="flex items-center justify-between text-[9px] font-mono opacity-80">
                    <span>{p.time}</span>
                    <span className="uppercase text-[8px] tracking-tight">{PUBLISH_MODE_DETAILS[p.publishMode].label}</span>
                  </div>
                  <div className="truncate font-sans">{p.title}</div>
                </div>
              ))}
            </div>
          </div>
        );
        day = addDays(day, 1);
      }
      rows.push(<div key={day.toString()} className="flex w-full">{days}</div>);
      days = [];
    }
    return (
      <div className="hidden lg:flex flex-col border border-muted/60 rounded-xl overflow-hidden bg-background shadow-xs">
        {weekdaysHeader}
        {rows}
      </div>
    );
  };

  return (
    <div className="max-w-[1400px] mx-auto p-3 sm:p-4 space-y-4 font-sans text-slate-900 antialiased">
      
      {/* HEADER CONTROL BAR TÁI CẤU TRÚC GỌN GÀNG CHO CẢ MOBILE */}
      <div className="bg-background border rounded-2xl p-3.5 shadow-2xs space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          {/* Tháng năm hiển thị vừa vặn, tinh tế */}
          <div className="flex items-center gap-2">
            <h1 className="text-base sm:text-lg font-black text-slate-900 font-mono tracking-tight">
              Tháng {format(currentDate, "MM / yyyy", { locale: vi })}
            </h1>
            <div className="flex items-center border rounded-xl p-0.5 bg-muted/50">
              <button onClick={() => setCurrentDate(prev => subMonths(prev, 1))} className="p-1 hover:bg-background rounded-lg text-slate-600"><ChevronLeft size={15}/></button>
              <button onClick={() => setCurrentDate(new Date())} className="text-[10px] font-bold px-2.5 py-1 hover:bg-background rounded-lg">Hôm nay</button>
              <button onClick={() => setCurrentDate(prev => addMonths(prev, 1))} className="p-1 hover:bg-background rounded-lg text-slate-600"><ChevronRight size={15}/></button>
            </div>
          </div>

          <div className="flex items-center gap-1.5 w-full sm:w-auto justify-between sm:justify-end">
            <select
              value={selectedChannel}
              onChange={(e) => setSelectedChannel(e.target.value)}
              className="text-xs bg-muted/60 border rounded-xl p-2 px-3 outline-none font-bold text-slate-700 max-w-[150px] sm:max-w-none"
            >
              <option value="all">Tất cả kênh</option>
              <option value="facebook">Facebook</option>
              <option value="instagram">Instagram</option>
              <option value="linkedin">LinkedIn</option>
              <option value="tiktok">TikTok</option>
            </select>

            <select
              value={selectedModeFilter}
              onChange={(e) => setSelectedModeFilter(e.target.value)}
              className="text-xs bg-muted/60 border rounded-xl p-2 px-3 outline-none font-bold text-slate-700"
            >
              <option value="all">Tất cả chế độ</option>
              <option value="once">Chế độ: Một lần</option>
              <option value="recurring">Chế độ: Lặp lại</option>
              <option value="queue">Chế độ: Hàng đợi</option>
            </select>

            <button
              onClick={() => {
                setQuickCreateDate(format(currentDate, "yyyy-MM-dd"));
                setIsQuickCreateOpen(true);
              }}
              className="block lg:hidden p-2 bg-slate-950 hover:bg-slate-800 text-white rounded-xl shrink-0 transition-colors shadow-sm"
            >
              <Plus size={16}/>
            </button>
          </div>
        </div>
      </div>

      {/* WORKSPACE CONTENT GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        
        {/* PANEL TRÁI: KHO CONTENT (DESKTOP ONLY) */}
        <div className="hidden lg:flex lg:col-span-4 bg-muted/10 border rounded-2xl p-4 flex-col h-[calc(100vh-190px)] min-h-[550px]">
          <div className="mb-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-1.5"><FolderOpen size={15}/> Kho Bài Đã Duyệt</h2>
              <span className="text-[10px] bg-slate-200 text-slate-700 font-bold px-2 py-0.5 rounded-full font-mono">{filteredPool.length} bài</span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">Giữ chuột kéo card thả vào ô lịch mong muốn</p>
          </div>

          <div className="relative mb-3">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Tìm kiếm nội dung kho nhanh..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs pl-8 pr-3 py-1.5 bg-background border rounded-lg focus:outline-none"
            />
          </div>

          <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
            {filteredPool.map(p => (
              <div
                key={p.id}
                draggable
                onDragStart={(e) => handleDragStart(e, p)}
                className="bg-background border rounded-xl p-3 shadow-2xs hover:shadow-md transition-all cursor-grab active:cursor-grabbing border-l-4"
                style={{ borderLeftColor: p.channel === 'facebook' ? '#1877F2' : p.channel === 'instagram' ? '#E4405F' : p.channel === 'linkedin' ? '#0A66C2' : '#000000' }}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded", STATUS_BADGE[p.status])}>
                    {p.status === 'approved' ? 'Đã duyệt' : 'Nháp'}
                  </span>
                  
                  {/* Trả lại hiển thị chế độ bài viết trên kho nhanh */}
                  <span className={cn("text-[9px] px-1.5 py-0.5 border rounded-sm flex items-center gap-1 font-medium", PUBLISH_MODE_DETAILS[p.publishMode].color)}>
                    {PUBLISH_MODE_DETAILS[p.publishMode].icon}
                    {PUBLISH_MODE_DETAILS[p.publishMode].label}
                  </span>
                </div>
                <h4 className="text-xs font-bold text-slate-900 line-clamp-1">{p.title}</h4>
                {p.contentPreview && <p className="text-[11px] text-muted-foreground line-clamp-2 mt-1 bg-muted/20 p-1.5 rounded font-mono">{p.contentPreview}</p>}
              </div>
            ))}
          </div>
        </div>

        {/* PANEL PHẢI: LỊCH TRÌNH CHÍNH (DYNAMIC RESPONSIVE) */}
        <div className="lg:col-span-8 space-y-3">
          {renderMobileWeeklyStrip()}
          {renderDesktopMonthGrid()}

          {/* TIMELINE LIST MOBILE CHỈN CHU */}
          <div className="block lg:hidden space-y-2.5">
            <h3 className="text-xs font-bold text-slate-500 flex items-center gap-1.5 px-1 uppercase tracking-wider">
              <Clock size={13}/> Lịch trình ngày {format(currentDate, "dd/MM/yyyy")}
            </h3>

            {activeDayPosts.length === 0 ? (
              <div className="text-center py-12 bg-background border rounded-2xl p-4 text-xs text-muted-foreground border-dashed">
                Trống lịch trình. Bấm nút dấu cộng (+) phía trên để lên lịch nhanh cho ngày này.
              </div>
            ) : (
              <div className="space-y-2">
                {activeDayPosts.map(p => (
                  <div
                    key={p.id}
                    onClick={() => setSelectedPost(p)}
                    className="bg-background border rounded-xl p-3.5 shadow-2xs flex items-center justify-between gap-3 border-l-4 active:scale-[0.99] transition-transform"
                    style={{ borderLeftColor: p.channel === 'facebook' ? '#1877F2' : p.channel === 'instagram' ? '#E4405F' : p.channel === 'linkedin' ? '#0A66C2' : '#000000' }}
                  >
                    <div className="flex items-start gap-3 min-w-0">
                      <span className="font-mono text-xs font-black text-slate-900 bg-muted px-2 py-1 rounded-lg shrink-0 h-fit mt-0.5">
                        {p.time}
                      </span>
                      <div className="min-w-0 space-y-1">
                        <h4 className="text-xs font-bold text-slate-900 line-clamp-1">{p.title}</h4>
                        <div className="flex items-center flex-wrap gap-2">
                          <span className="text-[10px] text-muted-foreground font-bold uppercase font-mono">{p.channel}</span>
                          <span className={cn("text-[9px] px-1.5 py-0.2 border rounded-sm flex items-center gap-1 font-medium", PUBLISH_MODE_DETAILS[p.publishMode].color)}>
                            {PUBLISH_MODE_DETAILS[p.publishMode].icon}
                            {PUBLISH_MODE_DETAILS[p.publishMode].label}
                          </span>
                        </div>
                      </div>
                    </div>
                    <ChevronRight className="text-muted-foreground/40 shrink-0" size={16} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>

      {/* POPUP CẤU HÌNH CHI TIẾT BÀI ĐĂNG (TRỌN VẸN LOGIC CHẾ ĐỘ XUẤT BẢN) */}
      {selectedPost && (
        <PostConfigModal 
          post={selectedPost} 
          onClose={() => setSelectedPost(null)} 
          onSave={handleSavePostConfig}
          onDelete={(id) => {
            setScheduledPosts(prev => prev.filter(p => p.id !== id));
            setSelectedPost(null);
            toast.success("Đã gỡ lịch đăng bài!");
          }}
        />
      )}

      {/* POPUP TẠO/CHỌN NHANH TRÊN Ô TRỐNG */}
      {isQuickCreateOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 animate-in fade-in duration-150">
          <div className="bg-background border-t sm:border rounded-t-3xl sm:rounded-2xl w-full max-w-md p-5 shadow-xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b pb-2">
              <h3 className="text-sm font-black text-slate-900">Lên lịch bài ngày {format(new Date(quickCreateDate), "dd/MM") || quickCreateDate}</h3>
              <button onClick={() => setIsQuickCreateOpen(false)} className="text-muted-foreground p-1"><X size={18}/></button>
            </div>
            
            <div className="flex bg-muted p-0.5 rounded-xl text-xs font-bold">
              <button type="button" onClick={() => setQuickCreateTab("pool")} className={cn("flex-1 py-2 rounded-lg transition-colors", quickCreateTab === "pool" ? "bg-background text-slate-900 shadow-2xs" : "text-muted-foreground")}>Lấy từ Kho bài duyệt</button>
              <button type="button" onClick={() => setQuickCreateTab("new")} className={cn("flex-1 py-2 rounded-lg transition-colors", quickCreateTab === "new" ? "bg-background text-slate-900 shadow-2xs" : "text-muted-foreground")}>Tạo mới tinh</button>
            </div>

            <form onSubmit={handleQuickCreateSubmit} className="space-y-4 text-xs">
              {quickCreateTab === "pool" ? (
                <div className="space-y-1">
                  <label className="font-bold text-slate-500">Chọn bài viết sẵn có trong Kho</label>
                  <select name="poolPostId" required className="w-full border bg-muted/30 rounded-xl p-3 font-semibold text-slate-900 outline-none">
                    {poolPosts.map(p => (
                      <option key={p.id} value={p.id}>[{p.channel.toUpperCase()} - {PUBLISH_MODE_DETAILS[p.publishMode].label}] {p.title}</option>
                    ))}
                    {poolPosts.length === 0 && <option value="">(Kho content trống rỗng)</option>}
                  </select>
                </div>
              ) : (
                <>
                  <div className="space-y-1">
                    <label className="font-bold text-slate-500">Tiêu đề bài viết</label>
                    <input type="text" name="title" required placeholder="Nhập tiêu đề ngắn..." className="w-full border bg-muted/30 rounded-xl p-3 outline-none font-medium" />
                  </div>
                  <div className="space-y-1">
                    <label className="font-bold text-slate-500">Mạng xã hội tích hợp</label>
                    <select name="channel" className="w-full border bg-muted/30 rounded-xl p-3 font-bold outline-none">
                      <option value="facebook">Facebook</option>
                      <option value="instagram">Instagram</option>
                      <option value="linkedin">LinkedIn</option>
                      <option value="tiktok">TikTok</option>
                    </select>
                  </div>
                </>
              )}
              
              {/* PHẢI CÓ: Chọn chế độ xuất bản khi tạo nhanh */}
              <div className="space-y-1">
                <label className="font-bold text-slate-500">Chế độ xuất bản bài đăng</label>
                <select name="publishMode" defaultValue="once" className="w-full border bg-muted/30 rounded-xl p-3 font-bold text-slate-900 outline-none">
                  <option value="once">Một lần (Lên lịch chính xác giờ)</option>
                  <option value="recurring">Lặp lại (Theo chu kỳ lặp)</option>
                  <option value="queue">Hàng đợi (Tự xếp hàng luân phiên)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="font-bold text-slate-500">Khung giờ vàng phát hành</label>
                <input type="time" name="time" defaultValue="09:00" className="w-full border bg-muted/30 rounded-xl p-3 font-mono text-sm outline-none" />
              </div>

              <div className="flex gap-2 pt-2">
                <button type="submit" className="w-full py-3 bg-slate-950 hover:bg-slate-900 text-white font-black rounded-xl shadow-md transition-all">
                  Xác nhận lưu vào lịch trình
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// MODAL CẤU HÌNH CHI TIẾT ĐỒNG BỘ ĐẦY ĐỦ THÔNG TIN
function PostConfigModal({ post, onClose, onSave, onDelete }: { post: Post; onClose: () => void; onSave: (p: Post) => void; onDelete: (id: string) => void }) {
  const [title, setTitle] = useState(post.title);
  const [dateStr, setDateStr] = useState(format(post.date, "yyyy-MM-dd"));
  const [time, setTime] = useState(post.time);
  const [channel, setChannel] = useState<Channel>(post.channel);
  const [publishMode, setPublishMode] = useState<PublishMode>(post.publishMode); // Trả lại State cho Chế độ xuất bản

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 animate-in fade-in duration-100">
      <div className="bg-background border-t sm:border rounded-t-3xl sm:rounded-2xl w-full max-w-md p-5 shadow-2xl flex flex-col gap-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center border-b pb-2">
          <h3 className="text-sm font-black text-slate-900">Chi tiết cấu hình bài phát sóng</h3>
          <button onClick={onClose} className="text-muted-foreground p-1"><X size={18}/></button>
        </div>

        <div className="space-y-3.5 text-xs">
          <div className="space-y-1">
            <label className="font-bold text-slate-500">Tiêu đề bài đăng</label>
            <input type="text" value={title} onChange={e => setTitle(e.target.value)} className="w-full border bg-muted/30 rounded-xl p-3 font-bold text-slate-900 outline-none" />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <label className="font-bold text-slate-500">Ngày đăng</label>
              <input type="date" value={dateStr} onChange={e => setDateStr(e.target.value)} className="w-full border bg-muted/30 rounded-xl p-3 font-mono outline-none" />
            </div>
            <div className="space-y-1">
              <label className="font-bold text-slate-500">Giờ phát sóng</label>
              <input type="time" value={time} onChange={e => setTime(e.target.value)} className="w-full border bg-muted/30 rounded-xl p-3 font-mono outline-none" />
            </div>
          </div>

          <div className="space-y-1">
            <label className="font-bold text-slate-500">Kênh truyền thông tích hợp</label>
            <select value={channel} onChange={e => setChannel(e.target.value as Channel)} className="w-full border bg-muted/30 rounded-xl p-3 capitalize font-bold text-slate-900 outline-none">
              <option value="facebook">Facebook</option>
              <option value="instagram">Instagram</option>
              <option value="linkedin">LinkedIn</option>
              <option value="tiktok">TikTok</option>
            </select>
          </div>

          {/* TRẢ LẠI TRƯỜNG CHỌN CHẾ ĐỘ XUẤT BẢN TRONG CHI TIẾT CARD BÀI VIẾT */}
          <div className="space-y-1">
            <label className="font-bold text-slate-500">Chế độ xuất bản bài đăng</label>
            <select value={publishMode} onChange={e => setPublishMode(e.target.value as PublishMode)} className="w-full border bg-muted/30 rounded-xl p-3 font-bold text-slate-900 outline-none">
              <option value="once">Một lần</option>
              <option value="recurring">Lặp lại</option>
              <option value="queue">Hàng đợi</option>
            </select>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row justify-between pt-3 border-t gap-2 mt-2">
          <button onClick={() => onDelete(post.id)} className="w-full sm:w-auto px-3 py-2.5 bg-red-50 hover:bg-red-100 text-red-600 font-bold rounded-xl text-xs flex items-center justify-center gap-1 transition-colors">
            <Trash2 size={14}/> Gỡ lịch bài đăng
          </button>
          <div className="flex gap-2 w-full sm:w-auto">
            <button type="button" onClick={onClose} className="flex-1 sm:flex-none px-4 py-2.5 bg-muted font-bold rounded-xl text-slate-700 text-xs text-center">Đóng</button>
            <button 
              type="button"
              onClick={() => onSave({ ...post, title, date: new Date(dateStr), time, channel, publishMode })} 
              className="flex-1 sm:flex-none px-5 py-2.5 bg-slate-950 hover:bg-slate-900 text-white font-black rounded-xl text-xs text-center shadow-md transition-colors"
            >
              Cập nhật
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}