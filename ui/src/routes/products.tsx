"use client";

import { useState, useRef, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Globe,
  Search,
  Trash2,
  Loader2,
  MapPin,
  Users,
  DollarSign,
  Bed,
  Wifi,
  Wind,
  Image as ImageIcon,
  ChevronRight,
  X,
  Filter,
  ExternalLink,
  Book,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { createFileRoute } from "@tanstack/react-router";
import { API_BASE } from "@/config";
import { useNavigate } from "@tanstack/react-router";


// ─── Types ────────────────────────────────────────────────
interface HotelRoomOut {
  id: number;
  name: string;
  slug: string;
  source_url: string;
  room_type?: string;
  bed_type?: string;
  capacity?: number;
  area_sqm?: number;
  price_per_night?: number;
  currency: string;
  description?: string;
  amenities: string[];
  image_urls: string[];
  status: string;
  created_at: string;
}

interface HotelCrawlOut {
  total: number;
  rooms: HotelRoomOut[];
  message: string;
}

interface HotelSearchOut {
  query: string;
  total: number;
  rooms: HotelRoomOut[];
}

interface HotelStats {
  total_vectors: number;
  total_rooms: number;
}

// ─── Constants ────────────────────────────────────────────
const ROOM_TYPE_META: Record<string, { label: string; color: string }> = {
  standard: { label: "Standard", color: "bg-blue-50 text-blue-600" },
  deluxe: { label: "Deluxe", color: "bg-purple-50 text-purple-600" },
  suite: { label: "Suite", color: "bg-emerald-50 text-emerald-600" },
  vip: { label: "VIP", color: "bg-orange-50 text-orange-600" },
};

const AMENITY_ICONS: Record<string, React.ReactNode> = {
  wifi: <Wifi size={14} />,
  ac: <Wind size={14} />,
  tv: <ImageIcon size={14} />,
};

// ─── API ──────────────────────────────────────────────────
const api = {
  crawl: async (url: string): Promise<HotelCrawlOut> => {
    const r = await fetch(`${API_BASE}/hotel/crawl/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      throw new Error(e.detail ?? "Crawl thất bại");
    }
    return r.json();
  },

  search: async (
    query: string,
    k: number = 5,
    room_type?: string,
    max_price?: number,
    min_capacity?: number,
  ): Promise<HotelSearchOut> => {
    const r = await fetch(`${API_BASE}/hotel/search/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        k,
        room_type: room_type || null,
        max_price: max_price || null,
        min_capacity: min_capacity || null,
      }),
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      throw new Error(e.detail ?? "Tìm kiếm thất bại");
    }
    return r.json();
  },

  list: async (): Promise<HotelRoomOut[]> => {
    const r = await fetch(`${API_BASE}/hotel/rooms/`);
    if (!r.ok) throw new Error("Lỗi tải danh sách");
    return r.json();
  },

  stats: async (): Promise<HotelStats> => {
    const r = await fetch(`${API_BASE}/hotel/stats/`);
    if (!r.ok) throw new Error("Lỗi tải stats");
    return r.json();
  },

  delete: async (roomId: number) => {
    const r = await fetch(`${API_BASE}/hotel/rooms/${roomId}/`, {
      method: "DELETE",
    });
    if (!r.ok) throw new Error("Xóa thất bại");
  },
};

// ─── Helpers ──────────────────────────────────────────────
const isUrl = (s: string) => /^https?:\/\/.+/.test(s.trim());

const formatPrice = (price?: number, currency?: string) => {
  if (!price) return "Liên hệ";
  const fmt = new Intl.NumberFormat("vi-VN").format(price);
  return `${fmt} ${currency || "VND"}/đêm`;
};

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
};

// ─── Room Detail Panel ─────────────────────────────────────
function RoomDetailPanel({
  room,
  onClose,
}: {
  room: HotelRoomOut;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity animate-in fade-in duration-300"
        onClick={onClose}
      />

      <div className="relative bg-white h-full w-full max-w-md md:max-w-lg shadow-2xl flex flex-col z-10 border-l border-slate-200 animate-in slide-in-from-right duration-300 ease-out">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 shrink-0">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">{room.name}</h2>
            {room.source_url && (
              <a
                href={room.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[10px] text-slate-400 hover:text-indigo-600 flex items-center gap-1 mt-1"
              >
                <ExternalLink size={10} />
                Xem nguồn
              </a>
            )}
          </div>
          <button
            onClick={onClose}
            className="h-7 w-7 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1 px-5 py-5 space-y-5">
          {/* Images */}
          {room.image_urls && room.image_urls.length > 0 && (
            <div className="space-y-2">
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">
                Hình ảnh
              </p>
              <div className="flex gap-2">
                {room.image_urls.slice(0, 4).map((url, i) => (
                  <a
                    key={i}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="h-40 bg-slate-100 rounded border border-slate-200 hover:border-indigo-300 transition-colors flex items-center justify-center text-[10px] text-slate-400 truncate p-1"
                    title={url}
                  >
                    <img src={url} />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Room Info */}
          <div className="grid grid-cols-2 gap-3">
            {room.room_type && (
              <InfoCard
                label="Loại phòng"
                value={ROOM_TYPE_META[room.room_type]?.label || room.room_type}
              />
            )}
            {room.bed_type && (
              <InfoCard label="Giường" value={room.bed_type} icon={<Bed size={12} />} />
            )}
            {room.capacity && (
              <InfoCard
                label="Sức chứa"
                value={`${room.capacity} người`}
                icon={<Users size={12} />}
              />
            )}
            {room.area_sqm && (
              <InfoCard label="Diện tích" value={`${room.area_sqm}m²`} />
            )}
          </div>

          {/* Price */}
          {room.price_per_night && (
            <div className="bg-gradient-to-r from-emerald-50 to-emerald-100/50 p-3 rounded-lg border border-emerald-200">
              <p className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wide mb-1">
                Giá
              </p>
              <p className="text-sm font-bold text-emerald-900">
                {formatPrice(room.price_per_night, room.currency)}
              </p>
            </div>
          )}

          {/* Description */}
          {room.description && (
            <div className="bg-slate-50/50 p-3 rounded-lg border border-slate-100">
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide mb-1">
                Mô tả
              </p>
              <p className="text-xs text-slate-600 leading-relaxed">{room.description}</p>
            </div>
          )}

          {/* Amenities */}
          {room.amenities && room.amenities.length > 0 && (
            <div className="bg-slate-50/50 p-3 rounded-lg border border-slate-100">
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide mb-2">
                Tiện nghi
              </p>
              <div className="flex flex-wrap gap-1.5">
                {room.amenities.map((amenity) => (
                  <span
                    key={amenity}
                    className="inline-flex items-center gap-1 text-[11px] px-2 py-1 bg-white border border-slate-200 rounded-md text-slate-600"
                  >
                    {AMENITY_ICONS[amenity.toLowerCase()] || <Wifi size={11} />}
                    {amenity}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="text-[10px] text-slate-400 space-y-1 pt-2 border-t border-slate-100">
            <p>ID: {room.id}</p>
            <p>Slug: {room.slug}</p>
            <p>Tạo: {formatDate(room.created_at)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="bg-slate-50 p-2 rounded border border-slate-100">
      <p className="text-[9px] font-semibold text-slate-400 uppercase mb-1">{label}</p>
      <div className="flex items-center gap-1">
        {icon && <span className="text-slate-400">{icon}</span>}
        <p className="text-xs font-medium text-slate-700">{value}</p>
      </div>
    </div>
  );
}

// ─── Route ────────────────────────────────────────────────
export const Route = createFileRoute("/products")({
  component: HotelPage,
});

export default function HotelPage() {
  const qc = useQueryClient();



  const navigate = useNavigate();


  const [urlInput, setUrlInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRoom, setSelectedRoom] = useState<HotelRoomOut | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteRoomId, setDeleteRoomId] = useState<number | null>(null);

  // Filters
  const [roomType, setRoomType] = useState<string>("");
  const [maxPrice, setMaxPrice] = useState<string>("");
  const [minCapacity, setMinCapacity] = useState<string>("");

  // Queries
  const { data: rooms = [], isLoading: isLoadingRooms } = useQuery({
    queryKey: ["hotel-rooms"],
    queryFn: api.list,
    refetchInterval: 10_000,
  });

  const { data: stats } = useQuery({
    queryKey: ["hotel-stats"],
    queryFn: api.stats,
    refetchInterval: 30_000,
  });

  // Mutations
  const crawlMutation = useMutation({
    mutationFn: (url: string) => api.crawl(url),
    onSuccess: (data) => {
      toast.success(`Crawl thành công ${data.total} phòng`);
      setUrlInput("");
      qc.invalidateQueries({ queryKey: ["hotel-rooms"] });
      qc.invalidateQueries({ queryKey: ["hotel-stats"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const searchMutation = useMutation({
    mutationFn: () =>
      api.search(
        searchQuery,
        5,
        roomType || undefined,
        maxPrice ? parseFloat(maxPrice) : undefined,
        minCapacity ? parseInt(minCapacity) : undefined,
      ),
    onSuccess: (data) => {
      toast.success(`Tìm thấy ${data.total} phòng`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: api.delete,
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ["hotel-rooms"] });
      const prev = qc.getQueryData<HotelRoomOut[]>(["hotel-rooms"]);
      qc.setQueryData<HotelRoomOut[]>(
        ["hotel-rooms"],
        (old = []) => old.filter((r) => r.id !== id),
      );
      return { prev };
    },
    onError: (_e, _id, ctx) => {
      qc.setQueryData(["hotel-rooms"], ctx?.prev);
      toast.error("Xóa thất bại");
    },
    onSuccess: () => {
      toast.success("Đã xóa phòng");
      setDeleteDialogOpen(false);
      setDeleteRoomId(null);
      setSelectedRoom(null);
      qc.invalidateQueries({ queryKey: ["hotel-stats"] });
    },
  });

  // Computed
  const urlError = urlInput.trim() !== "" && !isUrl(urlInput);
  const isCrawling = crawlMutation.isPending;
  const isSearching = searchMutation.isPending;

  const displayedRooms =
    searchQuery.trim() || roomType || maxPrice || minCapacity
      ? searchMutation.data?.rooms || []
      : rooms;

  const isEmpty = !isLoadingRooms && displayedRooms.length === 0;

  const handleCrawl = () => {
    if (!urlInput.trim() || !isUrl(urlInput)) return;
    crawlMutation.mutate(urlInput.trim());
  };

  const handleSearch = () => {
    if (!searchQuery.trim()) return;
    searchMutation.mutate();
  };

  const handleRoomClick = (room: HotelRoomOut) => {
    setSelectedRoom(room);
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* ─── TOOLBAR ──────────────────────────────────────────── */}

       <div className="flex items-center gap-1  sm:flex shrink-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate({ to: "/knowledge" })}
            className="h-8 text-xs text-slate-600 hover:text-slate-900 gap-1"
          >
            <Sparkles size={13} />
            <span>Thương hiệu</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate({ to: "/products" })}
            className="h-8 text-xs text-slate-600 hover:text-slate-900 gap-1"
          >
            <Book size={13} />
            <span>Sản phẩm & dịch vụ</span>
          </Button>
        </div>

      <div className="h-14 border-b border-slate-200 flex items-center gap-2 px-4 shrink-0 bg-white">
        {/* Crawl URL Input */}
        <div className="flex-1 hidden sm:flex items-start gap-2 min-w-0 max-w-sm">
          <div className="relative flex-1">
            <Globe size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <Input
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCrawl()}
              placeholder="https://hotel.com/rooms"
              className={`pl-7 h-8 text-xs bg-slate-50 border-slate-200 ${urlError ? "border-rose-500 bg-rose-50" : ""
                }`}
              disabled={isCrawling}
            />
            {urlError && <p className="text-[10px] text-rose-600 mt-0.5">URL không hợp lệ</p>}
          </div>
          <Button
            size="sm"
            onClick={handleCrawl}
            disabled={isCrawling || !urlInput.trim() || urlError}
            className="h-8 text-xs shrink-0 gap-1 bg-indigo-600 hover:bg-indigo-700"
          >
            {isCrawling ? <Loader2 size={13} className="animate-spin" /> : <Globe size={13} />}
            <span className="hidden md:inline">Crawl</span>
          </Button>
        </div>

        {/* Divider */}
        {displayedRooms.length > 0 && <div className="h-4 w-px bg-slate-200 hidden sm:block" />}

        {/* Search */}
        {displayedRooms.length > 0 && (
          <div className="hidden sm:flex items-center gap-1.5 flex-1 max-w-xs">
            <div className="relative flex-1">
              <Search size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Tìm phòng…"
                className="pl-7 h-8 text-xs bg-slate-50 border-slate-200"
                disabled={isSearching}
              />
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={handleSearch}
              disabled={isSearching || !searchQuery.trim()}
              className="h-8 text-xs shrink-0 gap-1"
            >
              {isSearching ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
            </Button>
          </div>
        )}

        {/* Stats */}
        {stats && (
          <span className="text-xs font-medium text-slate-500 shrink-0 ml-2 hidden sm:block">
            {stats.total_rooms} phòng
          </span>
        )}
      </div>

      {/* ─── MOBILE TOOLBAR ───────────────────────────────────── */}
      <div className="sm:hidden flex flex-col gap-2 px-4 py-2 border-b border-slate-200 bg-white shrink-0">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Globe size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <Input
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCrawl()}
              placeholder="https://hotel.com"
              className={`pl-7 h-8 text-xs bg-slate-50 border-slate-200 ${urlError ? "border-rose-500 bg-rose-50" : ""
                }`}
              disabled={isCrawling}
            />
          </div>
          <Button
            size="sm"
            onClick={handleCrawl}
            disabled={isCrawling || !urlInput.trim() || urlError}
            className="h-8 text-xs shrink-0 bg-indigo-600 hover:bg-indigo-700"
          >
            {isCrawling ? <Loader2 size={13} className="animate-spin" /> : "Crawl"}
          </Button>
        </div>
        {urlError && <p className="text-[10px] text-rose-600">URL không hợp lệ</p>}

        {displayedRooms.length > 0 && (
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Tìm phòng…"
                className="pl-7 h-8 text-xs bg-slate-50 border-slate-200"
                disabled={isSearching}
              />
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={handleSearch}
              disabled={isSearching || !searchQuery.trim()}
              className="h-8 text-xs shrink-0"
            >
              {isSearching ? <Loader2 size={13} /> : <Search size={13} />}
            </Button>
          </div>
        )}



       
      </div>

      {/* ─── FILTERS ──────────────────────────────────────────── */}
      {displayedRooms.length > 0 && (
        <div className="border-b border-slate-200 px-4 py-3 bg-slate-50/50 shrink-0">
          <div className="flex items-center gap-2 flex-wrap max-w-[1100px] mx-auto">
            <Filter size={13} className="text-slate-400" />
            <select
              value={roomType}
              onChange={(e) => setRoomType(e.target.value)}
              className="h-7 px-2 text-xs border border-slate-200 rounded bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Tất cả loại</option>
              {Object.entries(ROOM_TYPE_META).map(([key, meta]) => (
                <option key={key} value={key}>
                  {meta.label}
                </option>
              ))}
            </select>

            <Input
              type="number"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
              placeholder="Giá tối đa"
              className="h-7 px-2 text-xs max-w-[100px]"
            />

            <Input
              type="number"
              value={minCapacity}
              onChange={(e) => setMinCapacity(e.target.value)}
              placeholder="Tối thiểu người"
              className="h-7 px-2 text-xs max-w-[100px]"
            />

            {(roomType || maxPrice || minCapacity) && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setRoomType("");
                  setMaxPrice("");
                  setMinCapacity("");
                }}
                className="h-7 text-xs text-slate-500 hover:text-slate-900"
              >
                Xóa bộ lọc
              </Button>
            )}
          </div>
        </div>
      )}

      {/* ─── CONTENT ──────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full px-4 py-4 max-w-[1100px]">
          {isEmpty && (
            <div className="flex flex-col items-center justify-center text-center py-12">
              <div className="h-12 w-12 rounded-lg bg-slate-100 flex items-center justify-center mb-3">
                <MapPin size={20} className="text-slate-400" />
              </div>
              <h3 className="text-sm font-medium text-slate-900 mb-1">Chưa có phòng nào</h3>
              <p className="text-xs text-slate-500 mb-4 max-w-xs">
                Nhập URL khách sạn để crawl và quản lý danh sách phòng
              </p>
            </div>
          )}

          {isLoadingRooms && (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-20 bg-slate-100 rounded-lg animate-pulse" />
              ))}
            </div>
          )}

          {!isLoadingRooms && displayedRooms.length > 0 && (
            <div className="divide-y divide-slate-200 border border-slate-200 rounded-lg overflow-hidden bg-white">
              {displayedRooms.map((room) => {
                const meta = ROOM_TYPE_META[room.room_type || "standard"] || ROOM_TYPE_META.standard;
                return (
                  <div
                    key={room.id}
                    onClick={() => handleRoomClick(room)}
                    className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors ${selectedRoom?.id === room.id ? "bg-indigo-50/50" : "hover:bg-slate-50/50"
                      }`}
                  >
                    {/* Thumbnail */}
                    {room.image_urls && room.image_urls.length > 0 ? (
                      <img
                        src={room.image_urls[0]}
                        alt={room.name}
                        className="h-16 w-20 rounded object-cover bg-slate-100 shrink-0"
                      />
                    ) : (
                      <div className="h-16 w-20 rounded bg-slate-100 flex items-center justify-center shrink-0">
                        <ImageIcon size={20} className="text-slate-300" />
                      </div>
                    )}

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate">{room.name}</p>
                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                        <Badge className={`${meta.color} border-none text-[10px]`}>
                          {meta.label}
                        </Badge>
                        {room.capacity && (
                          <span className="text-xs text-slate-500 flex items-center gap-0.5">
                            <Users size={12} /> {room.capacity} người
                          </span>
                        )}
                        {room.area_sqm && (
                          <span className="text-xs text-slate-500">{room.area_sqm}m²</span>
                        )}
                        {room.price_per_night && (
                          <span className="text-xs font-semibold text-emerald-600">
                            {formatPrice(room.price_per_night, room.currency)}
                          </span>
                        )}
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1">
                        Tạo: {formatDate(room.created_at)}
                      </p>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRoomClick(room);
                        }}
                        className="h-8 px-2 flex items-center gap-1 rounded text-[11px] text-indigo-600 bg-indigo-50 hover:bg-indigo-100 transition-colors hidden sm:flex"
                        title="Xem chi tiết"
                      >
                        <ChevronRight size={11} />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteRoomId(room.id);
                          setDeleteDialogOpen(true);
                        }}
                        disabled={deleteMutation.isPending}
                        className="h-8 w-8 flex items-center justify-center rounded hover:bg-rose-50 text-slate-300 hover:text-rose-500 transition-colors shrink-0 disabled:opacity-50"
                        aria-label="Xóa"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ─── ROOM DETAIL PANEL ────────────────────────────────── */}
      {selectedRoom && (
        <RoomDetailPanel room={selectedRoom} onClose={() => setSelectedRoom(null)} />
      )}

      {/* ─── DELETE DIALOG ────────────────────────────────────── */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogTitle>Xóa phòng?</AlertDialogTitle>
          <AlertDialogDescription>
            Hành động này không thể hoàn tác. Phòng sẽ bị xóa vĩnh viễn.
          </AlertDialogDescription>
          <div className="flex gap-2 justify-end pt-4">
            <AlertDialogCancel className="h-8">Hủy</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteRoomId !== null && deleteMutation.mutate(deleteRoomId)}
              disabled={deleteMutation.isPending}
              className="h-8 bg-rose-600 hover:bg-rose-700"
            >
              {deleteMutation.isPending ? "Đang xóa…" : "Xóa"}
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}