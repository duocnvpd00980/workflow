"use client";

import { createFileRoute } from '@tanstack/react-router';
import { 
  Search, Filter, FileText, Image as ImageIcon, FileSpreadsheet, Code, 
  Download, Copy, Share2, Calendar, HardDrive, ChevronRight,
  LayoutGrid, List, Pencil, Trash2, CalendarPlus, ArrowUpDown
} from "lucide-react";
import { useState, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// Định nghĩa kiểu dữ liệu đồng bộ với hệ thống Planner
type Channel = "facebook" | "instagram" | "linkedin" | "tiktok";
type ContentStatus = "draft" | "approved" | "scheduled" | "published";

interface Artifact {
  id: string;
  name: string;
  type: string;
  extension: string;
  size: string;
  createdAt: string;
  generatedBy: string;
  jobRef: string;
  channel: Channel;
  status: ContentStatus;
  previewContent?: string;
  previewUrl?: string;
}

const INITIAL_ARTIFACTS: Artifact[] = [
  {
    id: "ART-0092",
    name: "Kịch_bản_Video_Tiktok_Tháng_6.md",
    type: "document",
    extension: "Markdown",
    size: "14.2 KB",
    createdAt: "2026-06-02T14:30:00Z",
    generatedBy: "Writer Agent",
    jobRef: "JOB-9921-A",
    channel: "tiktok",
    status: "approved",
    previewContent: "# KỊCH BẢN VIDEO TIKTOK - XU HƯỚNG AI 2026\n\n## Hook (3 giây đầu):\n\"Bạn có biết 90% Marketer sẽ mất việc nếu không biết công cụ này?\"\n\n## Body:\n- Bước 1: Giới thiệu Agent Command Dashboard...\n- Bước 2: Hướng dẫn cấu hình Sub-Agent...",
  },
  {
    id: "ART-0085",
    name: "Banner_Quang_Cao_SaaS_Creative.png",
    type: "image",
    extension: "PNG Image",
    size: "2.4 MB",
    createdAt: "2026-06-02T11:15:00Z",
    generatedBy: "Designer Agent",
    jobRef: "JOB-9855-C",
    channel: "facebook",
    status: "draft",
    previewUrl: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500&auto=format&fit=crop&q=60",
  },
  {
    id: "ART-0071",
    name: "Bai_Viet_LinkedIn_Growth_Hack.md",
    type: "document",
    extension: "Markdown",
    size: "4.5 KB",
    createdAt: "2026-06-01T23:12:00Z",
    generatedBy: "Writer Agent",
    jobRef: "JOB-9701-F",
    channel: "linkedin",
    status: "scheduled",
    previewContent: "Chia sẻ về tư duy tăng trưởng (Growth Hacking) trong kỷ nguyên AI tự động hóa...",
  },
  {
    id: "ART-0060",
    name: "Post_Instagram_Review_Product.png",
    type: "image",
    extension: "PNG Image",
    size: "1.8 MB",
    createdAt: "2026-05-31T10:05:00Z",
    generatedBy: "Designer Agent",
    jobRef: "JOB-9511-X",
    channel: "instagram",
    status: "published",
    previewUrl: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500&auto=format&fit=crop&q=60",
  }
];

const CHANNEL_META = {
  facebook: { label: "Facebook", color: "text-blue-500", bg: "bg-blue-500/10" },
  instagram: { label: "Instagram", color: "text-pink-500", bg: "bg-pink-500/10" },
  linkedin: { label: "LinkedIn", color: "text-indigo-600", bg: "bg-indigo-600/10" },
  tiktok: { label: "TikTok", color: "text-foreground", bg: "bg-foreground/10" },
};

const STATUS_META = {
  draft: { label: "Bản nháp", class: "bg-slate-500/10 text-slate-600" },
  approved: { label: "Đã duyệt", class: "bg-amber-500/10 text-amber-600" },
  scheduled: { label: "Đã lên lịch", class: "bg-blue-500/10 text-blue-600" },
  published: { label: "Đã đăng", class: "bg-emerald-500/10 text-emerald-600" },
};

export const Route = createFileRoute('/artifacts')({
  component: ArtifactsPage,
});

export default function ArtifactsPage() {
  const [artifacts, setArtifacts] = useState<Artifact[]>(INITIAL_ARTIFACTS);
  const [searchTerm, setSearchTerm] = useState("");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [filters, setFilters] = useState({ channel: "all", status: "all", type: "all" });
  const [sortBy, setSortBy] = useState("newest");

  // Bộ lọc nâng cao theo yêu cầu UX
  const filteredArtifacts = useMemo(() => {
    return artifacts.filter(art => {
      const matchesSearch = art.name.toLowerCase().includes(searchTerm.toLowerCase()) || art.id.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesChannel = filters.channel === "all" || art.channel === filters.channel;
      const matchesStatus = filters.status === "all" || art.status === filters.status;
      const matchesType = filters.type === "all" || art.type === filters.type;
      return matchesSearch && matchesChannel && matchesStatus && matchesType;
    }).sort((a, b) => {
      if (sortBy === "newest") return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      if (sortBy === "name") return a.name.localeCompare(b.name);
      return 0;
    });
  }, [artifacts, searchTerm, filters, sortBy]);

  const renderFileIcon = (type: string) => {
    switch (type) {
      case "document": return <FileText size={16} className="text-blue-500" />;
      case "image": return <ImageIcon size={16} className="text-purple-500" />;
      case "spreadsheet": return <FileSpreadsheet size={16} className="text-emerald-500" />;
      case "code": return <Code size={16} className="text-amber-500" />;
      default: return <FileText size={16} className="text-muted-foreground" />;
    }
  };

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("Bạn có chắc chắn muốn xóa nội dung này khỏi kho?")) {
      setArtifacts(prev => prev.filter(a => a.id !== id));
      toast.success("Đã xóa nội dung thành công!");
    }
  };

  const handleQuickSchedule = (art: Artifact, e: React.MouseEvent) => {
    e.stopPropagation();
    toast.info(`Mở popup đặt lịch cho: ${art.name}. Hệ thống sẽ pre-fill kênh ${art.channel}.`);
  };

  return (
    <div className="space-y-4 max-w-[1200px] mx-auto w-full p-4">

      {/* FILTER CONTROLS BAR */}
      <div className="bg-background  flex flex-col gap-3 lg:flex-row items-center justify-between ">
        <div className="flex items-center gap-2 border p-1 rounded-lg bg-background shadow-xs">
          <button 
            onClick={() => setViewMode("grid")}
            className={cn("p-1.5 rounded-md transition-colors", viewMode === "grid" ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground")}
          >
            <LayoutGrid size={15} />
          </button>
          <button 
            onClick={() => setViewMode("list")}
            className={cn("p-1.5 rounded-md transition-colors", viewMode === "list" ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground")}
          >
            <List size={15} />
          </button>
        </div>
        <div className="relative w-full lg:w-72">
          
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Tìm theo tên hoặc mã nội dung..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-muted/40 border rounded-lg focus:outline-none focus:ring-2 focus:ring-ring transition-all"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto">
          <select 
            value={filters.channel} 
            onChange={(e) => setFilters(p => ({ ...p, channel: e.target.value }))}
            className="text-xs bg-muted/40 border rounded-lg p-1.5 outline-none font-semibold text-muted-foreground focus:text-foreground"
          >
            <option value="all">Tất cả kênh</option>
            <option value="facebook">Facebook</option>
            <option value="instagram">Instagram</option>
            <option value="linkedin">LinkedIn</option>
            <option value="tiktok">TikTok</option>
          </select>

          <select 
            value={filters.status} 
            onChange={(e) => setFilters(p => ({ ...p, status: e.target.value }))}
            className="text-xs bg-muted/40 border rounded-lg p-1.5 outline-none font-semibold text-muted-foreground focus:text-foreground"
          >
            <option value="all">Tất cả trạng thái</option>
            <option value="draft">Bản nháp</option>
            <option value="approved">Đã duyệt</option>
            <option value="scheduled">Đã lên lịch</option>
            <option value="published">Đã đăng</option>
          </select>

          <select 
            value={sortBy} 
            onChange={(e) => setSortBy(e.target.value)}
            className="text-xs bg-muted/40 border rounded-lg p-1.5 outline-none font-semibold text-muted-foreground focus:text-foreground ml-auto lg:ml-0"
          >
            <option value="newest">Mới nhất</option>
            <option value="name">Tên file A-Z</option>
          </select>
        </div>
      </div>

      {/* RENDER DẠNG CARD GRID */}
      {viewMode === "grid" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredArtifacts.map((art) => (
            <Sheet key={art.id}>
              <div className="bg-background border rounded-xl p-4 flex flex-col justify-between hover:shadow-md transition-all group relative">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded-full", STATUS_META[art.status].class)}>
                      {STATUS_META[art.status].label}
                    </span>
                    <Badge variant="outline" className={cn("text-[10px] font-semibold font-mono", CHANNEL_META[art.channel].bg, CHANNEL_META[art.channel].color)}>
                      {CHANNEL_META[art.channel].label}
                    </Badge>
                  </div>

                  <SheetTrigger asChild>
                    <div className="cursor-pointer space-y-2">
                      <div className="flex items-start gap-2">
                        {renderFileIcon(art.type)}
                        <h3 className="font-bold text-foreground text-sm line-clamp-1 group-hover:text-primary transition-colors pr-4">{art.name}</h3>
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-3 bg-muted/20 p-2 rounded-lg font-mono text-[11px]">
                        {art.type === "image" ? "[Hình ảnh trực quan]" : art.previewContent}
                      </p>
                    </div>
                  </SheetTrigger>
                </div>

                <div className="mt-4 pt-3 border-t flex items-center justify-between text-[11px] text-muted-foreground">
                  <span className="font-mono">{art.size} • {new Date(art.createdAt).toLocaleDateString("vi-VN")}</span>
                  
                  {/* Nhóm nút Hành động (Action Buttons) */}
                  <div className="flex items-center gap-1 opacity-90 sm:opacity-0 group-hover:opacity-100 transition-opacity">
                    <SheetTrigger asChild>
                      <button className="p-1.5 hover:bg-muted text-muted-foreground hover:text-foreground rounded-md transition-colors" title="Sửa">
                        <Pencil size={13} />
                      </button>
                    </SheetTrigger>
                    <button 
                      onClick={(e) => handleQuickSchedule(art, e)}
                      className="p-1.5 hover:bg-primary/10 text-primary rounded-md transition-colors" 
                      title="Lên lịch đăng bài"
                    >
                      <CalendarPlus size={13} />
                    </button>
                    <button 
                      onClick={(e) => handleDelete(art.id, e)}
                      className="p-1.5 hover:bg-destructive/10 text-destructive rounded-md transition-colors" 
                      title="Xóa"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              </div>
              <RenderDetailDrawer art={art} renderFileIcon={renderFileIcon} />
            </Sheet>
          ))}
        </div>
      ) : (
        /* RENDER DẠNG LIST VIEW */
        <div className="border bg-background rounded-xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="bg-muted/40 border-b text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                  <th className="p-3 pl-4">Tên sản phẩm</th>
                  <th className="p-3">Kênh</th>
                  <th className="p-3">Trạng thái</th>
                  <th className="p-3 text-right">Kích thước</th>
                  <th className="p-3 text-center w-24">Hành động</th>
                </tr>
              </thead>
              <tbody className="divide-y text-muted-foreground font-medium">
                {filteredArtifacts.map((art) => (
                  <Sheet key={art.id}>
                    <tr className="hover:bg-muted/30 cursor-pointer transition-colors group">
                      <td className="p-3 pl-4">
                        <SheetTrigger asChild>
                          <div className="flex items-center gap-3 min-w-0">
                            {renderFileIcon(art.type)}
                            <div className="min-w-0 truncate">
                              <p className="font-semibold text-foreground group-hover:text-primary transition-colors truncate text-sm">{art.name}</p>
                              <p className="text-[10px] text-muted-foreground font-mono">Mã: {art.id} • {art.extension}</p>
                            </div>
                          </div>
                        </SheetTrigger>
                      </td>
                      <td className="p-3">
                        <span className={cn("px-2 py-0.5 rounded text-[10px] font-bold font-mono", CHANNEL_META[art.channel].bg, CHANNEL_META[art.channel].color)}>
                          {CHANNEL_META[art.channel].label}
                        </span>
                      </td>
                      <td className="p-3">
                        <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded-full", STATUS_META[art.status].class)}>
                          {STATUS_META[art.status].label}
                        </span>
                      </td>
                      <td className="p-3 text-right font-mono text-muted-foreground">{art.size}</td>
                      <td className="p-3 text-center">
                        <div className="flex items-center justify-center gap-1" onClick={(e) => e.stopPropagation()}>
                          <button onClick={(e) => handleQuickSchedule(art, e)} className="p-1 hover:bg-primary/10 text-primary rounded" title="Lên lịch">
                            <CalendarPlus size={13} />
                          </button>
                          <button onClick={(e) => handleDelete(art.id, e)} className="p-1 hover:bg-destructive/10 text-destructive rounded" title="Xóa">
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                    <RenderDetailDrawer art={art} renderFileIcon={renderFileIcon} />
                  </Sheet>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// COMPONENT ĐUÔI DRAWER CHI TIẾT ĐỒNG BỘ SHADCN
function RenderDetailDrawer({ art, renderFileIcon }: { art: Artifact, renderFileIcon: (t: string) => React.ReactNode }) {
  return (
    <SheetContent className="w-full sm:max-w-[420px] rounded-l-[20px] p-6 flex flex-col h-full gap-4">
      <SheetHeader className="border-b pb-3 shrink-0">
        <div className="flex items-center justify-between w-full pr-6">
          <span className="text-[10px] font-mono font-bold text-muted-foreground bg-muted border px-1.5 py-0.5 rounded">{art.id}</span>
          <span className="text-[11px] font-mono text-muted-foreground">{art.size}</span>
        </div>
        <SheetTitle className="text-sm font-bold text-foreground tracking-tight line-clamp-2 text-left pt-1">
          {art.name}
        </SheetTitle>
      </SheetHeader>

      <div className="flex-1 overflow-y-auto space-y-4 min-h-0 flex flex-col">
        <div className="grid grid-cols-2 gap-2 bg-muted/30 p-3 border rounded-xl text-[11px] text-muted-foreground font-medium">
          <div className="space-y-1">
            <p className="text-[9px] uppercase font-bold text-muted-foreground/70">Kênh đăng tải</p>
            <p className={cn("font-bold font-mono", CHANNEL_META[art.channel].color)}>{CHANNEL_META[art.channel].label}</p>
          </div>
          <div className="space-y-1">
            <p className="text-[9px] uppercase font-bold text-muted-foreground/70">Trạng thái kho</p>
            <p className="font-bold text-foreground">{STATUS_META[art.status].label}</p>
          </div>
          <div className="space-y-1 col-span-2 pt-1 border-t flex items-center gap-1.5">
            <Calendar size={11}/>
            <span>Ngày tạo: {new Date(art.createdAt).toLocaleDateString("vi-VN")}</span>
          </div>
        </div>

        <div className="flex-1 border bg-muted/10 rounded-xl overflow-hidden flex flex-col min-h-[240px] relative">
          {art.type === "image" && art.previewUrl ? (
            <div className="w-full h-full flex items-center justify-center p-2 bg-muted/30">
              <img src={art.previewUrl} alt={art.name} className="max-w-full max-h-full object-contain rounded border bg-background" />
            </div>
          ) : (
            <pre className="w-full h-full p-4 font-mono text-[10.5px] text-foreground bg-background whitespace-pre-wrap overflow-y-auto leading-relaxed shadow-inner">
              {art.previewContent}
            </pre>
          )}
        </div>
      </div>

      <div className="pt-3 border-t mt-auto grid grid-cols-3 gap-2 shrink-0">
        <button 
          onClick={() => {
            navigator.clipboard.writeText(art.previewContent || art.name);
            toast.success("Đã sao chép vào bộ nhớ tạm!");
          }}
          className="h-8 text-[11px] bg-muted hover:bg-muted/80 text-foreground font-semibold rounded-lg flex items-center justify-center gap-1 transition-colors outline-none"
        >
          <Copy size={13}/> Sao chép
        </button>
        <button className="h-8 text-[11px] bg-muted hover:bg-muted/80 text-foreground font-semibold rounded-lg flex items-center justify-center gap-1 transition-colors outline-none">
          <Pencil size={13}/> Sửa bài
        </button>
        <button className="h-8 text-[11px] bg-primary hover:bg-primary/90 text-primary-foreground font-semibold rounded-lg flex items-center justify-center gap-1 transition-colors outline-none shadow-xs">
          <CalendarPlus size={13}/> Lên lịch
        </button>
      </div>
    </SheetContent>
  );
}