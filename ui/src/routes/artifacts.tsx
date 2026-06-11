"use client";

import { createFileRoute } from '@tanstack/react-router';
import {
  Search, FileText, Image as ImageIcon, FileSpreadsheet, Code,
  Copy, Calendar, CalendarPlus, LayoutGrid, List, Pencil, Trash2,
  RefreshCw, AlertCircle, Inbox
} from "lucide-react";
import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ─── Config ──────────────────────────────────────────────────────────────────
const API_BASE = "http://localhost:8000/api/v1";

// ─── Types từ API ─────────────────────────────────────────────────────────────
interface DraftContent {
  content: string;
  metadata: {
    platform: string;
    type: string;
  };
  version: number;
  versions: Array<{
    version: number;
    content: string;
    metadata: { platform: string; type: string };
    action: string;
  }>;
}

interface SessionListItem {
  session_id: string;
  status: "running" | "paused" | "completed" | "error";
  request: string | null;
  draft: DraftContent | null;
  publish_status: string | null;
  approved: boolean;
  usage: {
    total_tokens: number;
    total_cost: number;
    calls: Array<{ node: string; tokens: number }>;
  } | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

interface SessionListResponse {
  items: SessionListItem[];
  total: number;
  limit: number;
  offset: number;
}

// ─── Map platform API → channel UI ───────────────────────────────────────────
type Channel = "facebook" | "instagram" | "linkedin" | "tiktok" | "other";

function toChannel(platform?: string): Channel {
  const p = (platform ?? "").toLowerCase();
  if (p.includes("facebook")) return "facebook";
  if (p.includes("instagram")) return "instagram";
  if (p.includes("linkedin")) return "linkedin";
  if (p.includes("tiktok")) return "tiktok";
  return "other";
}

// ─── Map publish_status / status API → ContentStatus UI ──────────────────────
type ContentStatus = "draft" | "approved" | "scheduled" | "published" | "error";

function toStatus(item: SessionListItem): ContentStatus {
  if (item.status === "error") return "error";
  if (item.publish_status === "published") return "published";
  if (item.publish_status === "pending") return "scheduled";
  if (item.approved) return "approved";
  return "draft";
}

// ─── Meta maps ────────────────────────────────────────────────────────────────
const CHANNEL_META: Record<Channel, { label: string; color: string; bg: string }> = {
  facebook:  { label: "Facebook",  color: "text-blue-500",    bg: "bg-blue-500/10"    },
  instagram: { label: "Instagram", color: "text-pink-500",    bg: "bg-pink-500/10"    },
  linkedin:  { label: "LinkedIn",  color: "text-indigo-600",  bg: "bg-indigo-600/10"  },
  tiktok:    { label: "TikTok",    color: "text-foreground",  bg: "bg-foreground/10"  },
  other:     { label: "Khác",      color: "text-slate-500",   bg: "bg-slate-500/10"   },
};

const STATUS_META: Record<ContentStatus, { label: string; class: string }> = {
  draft:     { label: "Bản nháp",    class: "bg-slate-500/10 text-slate-600"   },
  approved:  { label: "Đã duyệt",    class: "bg-amber-500/10 text-amber-600"   },
  scheduled: { label: "Đã lên lịch", class: "bg-blue-500/10 text-blue-600"     },
  published: { label: "Đã đăng",     class: "bg-emerald-500/10 text-emerald-600" },
  error:     { label: "Lỗi",         class: "bg-red-500/10 text-red-600"       },
};

// ─── Route ────────────────────────────────────────────────────────────────────
export const Route = createFileRoute('/artifacts')({
  component: ArtifactsPage,
});

// ─── Main Component ───────────────────────────────────────────────────────────
export default function ArtifactsPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [filters, setFilters] = useState({ channel: "all", status: "all" });
  const [sortBy, setSortBy] = useState("newest");

  // ─── Query: Lấy danh sách bài viết từ API ─────────────────────────────────
  const {
    data: sessionList,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useQuery<SessionListResponse>({
    queryKey: ["marketing", "sessions", { limit: 100, offset: 0 }],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: "100", offset: "0" });
      const res = await fetch(`${API_BASE}/marketing/sessions?${params.toString()}`);
      if (!res.ok) throw new Error("Không thể tải danh sách bài viết");
      return await res.json();
    },
    staleTime: 30_000,
  });

  // ─── Filter + sort client-side ────────────────────────────────────────────
  const filteredItems = useMemo(() => {
    const items = sessionList?.items ?? [];
    return items
      .filter((item) => {
        const channel = toChannel(item.draft?.metadata?.platform);
        const status = toStatus(item);
        const search = searchTerm.toLowerCase();

        const matchSearch =
          !search ||
          item.session_id.toLowerCase().includes(search) ||
          (item.request ?? "").toLowerCase().includes(search) ||
          (item.draft?.content ?? "").toLowerCase().includes(search);

        const matchChannel = filters.channel === "all" || channel === filters.channel;
        const matchStatus  = filters.status  === "all" || status  === filters.status;

        return matchSearch && matchChannel && matchStatus;
      })
      .sort((a, b) => {
        if (sortBy === "newest") return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        if (sortBy === "oldest") return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        return 0;
      });
  }, [sessionList, searchTerm, filters, sortBy]);

  const renderFileIcon = (platform?: string) => {
    const ch = toChannel(platform);
    switch (ch) {
      case "instagram": return <ImageIcon size={16} className="text-purple-500 shrink-0" />;
      case "tiktok":    return <Code       size={16} className="text-amber-500 shrink-0"  />;
      default:          return <FileText   size={16} className="text-blue-500 shrink-0"   />;
    }
  };

  const handleQuickSchedule = (item: SessionListItem, e: React.MouseEvent) => {
    e.stopPropagation();
    const ch = toChannel(item.draft?.metadata?.platform);
    toast.info(`Mở popup đặt lịch cho session ${item.session_id}. Kênh: ${CHANNEL_META[ch].label}`);
  };

  // ─── States: loading / error / empty ──────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-muted-foreground">
        <RefreshCw size={24} className="animate-spin" />
        <p className="text-sm">Đang tải danh sách bài viết...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-destructive">
        <AlertCircle size={24} />
        <p className="text-sm font-medium">Không thể tải dữ liệu từ server</p>
        <button
          onClick={() => refetch()}
          className="text-xs px-3 py-1.5 rounded-lg bg-destructive/10 hover:bg-destructive/20 transition-colors"
        >
          Thử lại
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-[1200px] mx-auto w-full p-4">

      {/* FILTER CONTROLS BAR */}
      <div className="bg-background flex flex-col gap-3 lg:flex-row items-center justify-between">
        {/* View mode toggle */}
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

        {/* Search */}
        <div className="relative w-full lg:w-72">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Tìm theo session ID hoặc nội dung..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-muted/40 border rounded-lg focus:outline-none focus:ring-2 focus:ring-ring transition-all"
          />
        </div>

        {/* Filters */}
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
            <option value="error">Lỗi</option>
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="text-xs bg-muted/40 border rounded-lg p-1.5 outline-none font-semibold text-muted-foreground focus:text-foreground ml-auto lg:ml-0"
          >
            <option value="newest">Mới nhất</option>
            <option value="oldest">Cũ nhất</option>
          </select>

          {/* Refetch button */}
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-1.5 rounded-lg border bg-muted/40 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground disabled:opacity-50"
            title="Làm mới"
          >
            <RefreshCw size={14} className={cn(isFetching && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Total count */}
      <p className="text-xs text-muted-foreground font-mono">
        Hiển thị <span className="font-bold text-foreground">{filteredItems.length}</span> / {sessionList?.total ?? 0} bài viết
      </p>

      {/* EMPTY STATE */}
      {filteredItems.length === 0 && (
        <div className="flex flex-col items-center justify-center h-48 gap-3 text-muted-foreground border rounded-xl bg-muted/10">
          <Inbox size={28} />
          <p className="text-sm">Không có bài viết nào phù hợp</p>
        </div>
      )}

      {/* GRID VIEW */}
      {viewMode === "grid" && filteredItems.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredItems.map((item) => {
            const channel = toChannel(item.draft?.metadata?.platform);
            const status  = toStatus(item);
            const content = item.draft?.content ?? item.request ?? "(Chưa có nội dung)";

            return (
              <Sheet key={item.session_id}>
                <div className="bg-background border rounded-xl p-4 flex flex-col justify-between hover:shadow-md transition-all group relative">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded-full", STATUS_META[status].class)}>
                        {STATUS_META[status].label}
                      </span>
                      <Badge variant="outline" className={cn("text-[10px] font-semibold font-mono", CHANNEL_META[channel].bg, CHANNEL_META[channel].color)}>
                        {CHANNEL_META[channel].label}
                      </Badge>
                    </div>

                    <SheetTrigger asChild>
                      <div className="cursor-pointer space-y-2">
                        <div className="flex items-start gap-2">
                          {renderFileIcon(item.draft?.metadata?.platform)}
                          <h3 className="font-bold text-foreground text-sm line-clamp-1 group-hover:text-primary transition-colors pr-4">
                            {item.request ?? `Session ${item.session_id}`}
                          </h3>
                        </div>
                        <p className="text-xs text-muted-foreground line-clamp-3 bg-muted/20 p-2 rounded-lg font-mono text-[11px]">
                          {content}
                        </p>
                      </div>
                    </SheetTrigger>
                  </div>

                  <div className="mt-4 pt-3 border-t flex items-center justify-between text-[11px] text-muted-foreground">
                    <span className="font-mono">
                      {item.usage?.total_tokens ?? 0} tokens • {new Date(item.created_at).toLocaleDateString("vi-VN")}
                    </span>
                    <div className="flex items-center gap-1 opacity-90 sm:opacity-0 group-hover:opacity-100 transition-opacity">
                      <SheetTrigger asChild>
                        <button className="p-1.5 hover:bg-muted text-muted-foreground hover:text-foreground rounded-md transition-colors" title="Xem chi tiết">
                          <Pencil size={13} />
                        </button>
                      </SheetTrigger>
                      <button
                        onClick={(e) => handleQuickSchedule(item, e)}
                        className="p-1.5 hover:bg-primary/10 text-primary rounded-md transition-colors"
                        title="Lên lịch đăng bài"
                      >
                        <CalendarPlus size={13} />
                      </button>
                    </div>
                  </div>
                </div>
                <RenderDetailDrawer item={item} renderFileIcon={renderFileIcon} />
              </Sheet>
            );
          })}
        </div>
      )}

      {/* LIST VIEW */}
      {viewMode === "list" && filteredItems.length > 0 && (
        <div className="border bg-background rounded-xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="bg-muted/40 border-b text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                  <th className="p-3 pl-4">Yêu cầu / Nội dung</th>
                  <th className="p-3">Kênh</th>
                  <th className="p-3">Trạng thái</th>
                  <th className="p-3 text-right">Tokens</th>
                  <th className="p-3 text-right">Ngày tạo</th>
                  <th className="p-3 text-center w-20">Hành động</th>
                </tr>
              </thead>
              <tbody className="divide-y text-muted-foreground font-medium">
                {filteredItems.map((item) => {
                  const channel = toChannel(item.draft?.metadata?.platform);
                  const status  = toStatus(item);

                  return (
                    <Sheet key={item.session_id}>
                      <tr className="hover:bg-muted/30 cursor-pointer transition-colors group">
                        <td className="p-3 pl-4">
                          <SheetTrigger asChild>
                            <div className="flex items-center gap-3 min-w-0">
                              {renderFileIcon(item.draft?.metadata?.platform)}
                              <div className="min-w-0 truncate">
                                <p className="font-semibold text-foreground group-hover:text-primary transition-colors truncate text-sm">
                                  {item.request ?? "(Không có yêu cầu)"}
                                </p>
                                <p className="text-[10px] text-muted-foreground font-mono">
                                  ID: {item.session_id} • {item.draft?.metadata?.type ?? "—"}
                                </p>
                              </div>
                            </div>
                          </SheetTrigger>
                        </td>
                        <td className="p-3">
                          <span className={cn("px-2 py-0.5 rounded text-[10px] font-bold font-mono", CHANNEL_META[channel].bg, CHANNEL_META[channel].color)}>
                            {CHANNEL_META[channel].label}
                          </span>
                        </td>
                        <td className="p-3">
                          <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded-full", STATUS_META[status].class)}>
                            {STATUS_META[status].label}
                          </span>
                        </td>
                        <td className="p-3 text-right font-mono text-muted-foreground">
                          {item.usage?.total_tokens ?? 0}
                        </td>
                        <td className="p-3 text-right font-mono text-muted-foreground">
                          {new Date(item.created_at).toLocaleDateString("vi-VN")}
                        </td>
                        <td className="p-3 text-center">
                          <div className="flex items-center justify-center gap-1" onClick={(e) => e.stopPropagation()}>
                            <button
                              onClick={(e) => handleQuickSchedule(item, e)}
                              className="p-1 hover:bg-primary/10 text-primary rounded"
                              title="Lên lịch"
                            >
                              <CalendarPlus size={13} />
                            </button>
                          </div>
                        </td>
                      </tr>
                      <RenderDetailDrawer item={item} renderFileIcon={renderFileIcon} />
                    </Sheet>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Detail Drawer ─────────────────────────────────────────────────────────────
function RenderDetailDrawer({
  item,
  renderFileIcon,
}: {
  item: SessionListItem;
  renderFileIcon: (platform?: string) => React.ReactNode;
}) {
  const channel = toChannel(item.draft?.metadata?.platform);
  const status  = toStatus(item);
  const content = item.draft?.content ?? item.request ?? "(Chưa có nội dung)";

  return (
    <SheetContent className="w-full sm:max-w-[420px] rounded-l-[20px] p-6 flex flex-col h-full gap-4">
      <SheetHeader className="border-b pb-3 shrink-0">
        <div className="flex items-center justify-between w-full pr-6">
          <span className="text-[10px] font-mono font-bold text-muted-foreground bg-muted border px-1.5 py-0.5 rounded">
            {item.session_id}
          </span>
          <span className="text-[11px] font-mono text-muted-foreground">
            v{item.draft?.version ?? 1}
          </span>
        </div>
        <SheetTitle className="text-sm font-bold text-foreground tracking-tight line-clamp-2 text-left pt-1">
          {item.request ?? `Session ${item.session_id}`}
        </SheetTitle>
      </SheetHeader>

      <div className="flex-1 overflow-y-auto space-y-4 min-h-0 flex flex-col">
        {/* Meta grid */}
        <div className="grid grid-cols-2 gap-2 bg-muted/30 p-3 border rounded-xl text-[11px] text-muted-foreground font-medium">
          <div className="space-y-1">
            <p className="text-[9px] uppercase font-bold text-muted-foreground/70">Kênh đăng tải</p>
            <p className={cn("font-bold font-mono", CHANNEL_META[channel].color)}>
              {CHANNEL_META[channel].label}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-[9px] uppercase font-bold text-muted-foreground/70">Trạng thái</p>
            <p className="font-bold text-foreground">{STATUS_META[status].label}</p>
          </div>
          <div className="space-y-1">
            <p className="text-[9px] uppercase font-bold text-muted-foreground/70">Tokens dùng</p>
            <p className="font-bold text-foreground font-mono">{item.usage?.total_tokens ?? 0}</p>
          </div>
          <div className="space-y-1">
            <p className="text-[9px] uppercase font-bold text-muted-foreground/70">Phiên bản</p>
            <p className="font-bold text-foreground font-mono">v{item.draft?.version ?? 1}</p>
          </div>
          <div className="space-y-1 col-span-2 pt-1 border-t flex items-center gap-1.5">
            <Calendar size={11} />
            <span>Ngày tạo: {new Date(item.created_at).toLocaleDateString("vi-VN")}</span>
          </div>
          {item.error && (
            <div className="col-span-2 pt-1 border-t text-red-500 flex items-center gap-1.5">
              <span className="text-[9px] uppercase font-bold">Lỗi:</span>
              <span className="font-mono">{item.error}</span>
            </div>
          )}
        </div>

        {/* Content preview */}
        <div className="flex-1 border bg-muted/10 rounded-xl overflow-hidden flex flex-col min-h-[240px]">
          <pre className="w-full h-full p-4 font-mono text-[10.5px] text-foreground bg-background whitespace-pre-wrap overflow-y-auto leading-relaxed shadow-inner">
            {content}
          </pre>
        </div>

        {/* Version history */}
        {(item.draft?.versions?.length ?? 0) > 1 && (
          <div className="border rounded-xl p-3 space-y-2">
            <p className="text-[10px] uppercase font-bold text-muted-foreground/70">Lịch sử phiên bản</p>
            {item.draft!.versions.map((v) => (
              <div key={v.version} className="flex items-center gap-2 text-[11px] text-muted-foreground">
                <span className="font-mono font-bold text-foreground">v{v.version}</span>
                <span className="bg-muted px-1.5 py-0.5 rounded font-mono">{v.action}</span>
                <span className="truncate">{v.content.slice(0, 60)}…</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="pt-3 border-t mt-auto grid grid-cols-3 gap-2 shrink-0">
        <button
          onClick={() => {
            navigator.clipboard.writeText(content);
            toast.success("Đã sao chép vào bộ nhớ tạm!");
          }}
          className="h-8 text-[11px] bg-muted hover:bg-muted/80 text-foreground font-semibold rounded-lg flex items-center justify-center gap-1 transition-colors outline-none"
        >
          <Copy size={13} /> Sao chép
        </button>
        <button className="h-8 text-[11px] bg-muted hover:bg-muted/80 text-foreground font-semibold rounded-lg flex items-center justify-center gap-1 transition-colors outline-none">
          <Pencil size={13} /> Sửa bài
        </button>
        <button className="h-8 text-[11px] bg-primary hover:bg-primary/90 text-primary-foreground font-semibold rounded-lg flex items-center justify-center gap-1 transition-colors outline-none shadow-xs">
          <CalendarPlus size={13} /> Lên lịch
        </button>
      </div>
    </SheetContent>
  );
}