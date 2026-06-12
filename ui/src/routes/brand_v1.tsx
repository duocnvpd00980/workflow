/**
 * ScreenBrandVoice — Kiến trúc tích hợp luồng Brand & Brand Profile RAG
 * • Quản lý linh hoạt: Đăng ký Owner -> Chọn/Tạo Brand -> Tự động hóa kết xuất RAG Profile.
 * • Hỗ trợ xóa thực thể thương hiệu an toàn qua Sidebar hoặc Header.
 * • Tự động đồng bộ hóa dữ liệu trạng thái qua TanStack Query & Router.
 */

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  ChevronDown,
  ChevronRight,
  X,
  Loader2,
  FileText,
  Sparkles,
  Plus,
  FolderHeart,
  Building2,
  RefreshCw,
  Trash2
} from "lucide-react";

// ─── Thành Phần UI Shadcn ──────────────────────────────────────────────────
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { API_BASE } from "@/config";

export interface Brand {
  id: string;
  name: string;
  created_at: string;
}

export interface BrandListResponse {
  brands: Brand[];
  total: number;
}

export interface BrandVoiceRules {
  forbidden_words: string[];
  tone_patterns: string[];
  cta_patterns: string[];
}

export interface BrandMessaging {
  pain_points: string[];
  objections: { objection: string; counter: string }[];
  proof_points: string[];
}

export interface ContentExamples {
  blog_post: string | null;
  social_post: string | null;
  ad_copy: string | null;
  landing_page: string | null;
}

export interface VisualIdentity {
  style_description: string;
  color_palette: string[];
  mood: string;
}

export interface BrandProfileSchema {
  positioning: string;
  audience: string;
  brand_voice_rules: BrandVoiceRules;
  messaging: BrandMessaging;
  content_examples: ContentExamples;
  visual_identity: VisualIdentity;
}

export interface RagDocument {
  id: number;
  title: string;
  document_type: string;
  status: "completed" | "pending" | "failed";
  chunk_count: number;
}

const CURRENT_OWNER_ID = "string";

export const Route = createFileRoute("/brand_v1")({
  validateSearch: (search: Record<string, unknown>) => ({
    syncOpen: (search.syncOpen as boolean) || undefined,
    selectedBrandId: (search.selectedBrandId as string) || undefined,
  }),
  component: ScreenBrandVoice,
});

export function ScreenBrandVoice() {
  const queryClient = useQueryClient();
  const navigate = useNavigate({ from: Route.fullPath });
  const { syncOpen, selectedBrandId } = Route.useSearch();

  const [isNewBrandOpen, setIsNewBrandOpen] = useState(false);
  const [newBrandName, setNewBrandName] = useState("");
  const [isPatching, setIsPatching] = useState<string | null>(null);
  const [brandToDelete, setBrandToDelete] = useState<Brand | null>(null);

  const [expanded, setExpanded] = useState<Record<number, boolean>>({
    1: true,
    2: false,
    3: false,
    4: false,
    5: false,
  });

  const [selectedDocuments, setSelectedDocuments] = useState<number[]>([]);

  const { data: brandListMeta, isLoading: isLoadingBrands } = useQuery<BrandListResponse>({
    queryKey: ["brands", "list", CURRENT_OWNER_ID],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/brand-profile?owner_id=${CURRENT_OWNER_ID}&limit=50&offset=0`);
      if (!res.ok) throw new Error("Không thể tải danh sách thương hiệu");
      return await res.json();
    },
  });

  const activeBrandId = selectedBrandId || brandListMeta?.brands[0]?.id;
  const activeBrandDetails = brandListMeta?.brands.find(b => b.id === activeBrandId);

  const { data: profileData, isLoading: isLoadingProfile } = useQuery<BrandProfileSchema>({
    queryKey: ["brand-profile", "detail", activeBrandId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/brand-profile/${activeBrandId}`);
      if (!res.ok) throw new Error("Hồ sơ thương hiệu chưa được thiết lập.");
      return await res.json();
    },
    enabled: !!activeBrandId,
    retry: false,
  });

  const { data: ragDocuments = [], isLoading: isLoadingRag } = useQuery<RagDocument[]>({
    queryKey: ["rag", "list"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/rag/`);
      if (!res.ok) throw new Error("Không thể tải danh sách tài liệu RAG");
      return await res.json();
    },
    enabled: !!syncOpen,
  });

  // ─── Mutation 1: Khởi tạo thực thể Brand mới hoàn toàn gốc ────────────────
  const createBrandMutation = useMutation({
    mutationFn: async (name: string) => {
      const res = await fetch(`${API_BASE}/brand-profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, owner_id: CURRENT_OWNER_ID }),
      });
      if (!res.ok) throw new Error("Có lỗi xảy ra trong quá trình khởi tạo Brand");
      return await res.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["brands", "list", CURRENT_OWNER_ID] });
      setIsNewBrandOpen(false);
      setNewBrandName("");
      navigate({ search: (prev: any) => ({ ...prev, selectedBrandId: data.brand_id }) } as any);
    },
    onError: (err: any) => alert(err.message),
  });

  // ─── Mutation 2: Cập nhật từng trường cấu hình (Partial Update PATCH) ──────
  const patchFieldMutation = useMutation({
    mutationFn: async ({ blockKey, payload }: { blockKey: string; payload: any }) => {
      setIsPatching(blockKey);
      const res = await fetch(`${API_BASE}/brand-profile/${activeBrandId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Cập nhật thuộc tính thất bại");
      return await res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brand-profile", "detail", activeBrandId] });
      setIsPatching(null);
    },
    onError: (err: any) => {
      alert(err.message);
      setIsPatching(null);
    },
  });

  // ─── Mutation 3: RAG Engine - Tạo tự động Profile bằng AI từ tài liệu ─────
  const generateMutation = useMutation({
    mutationFn: async (documentIds: number[]) => {
      const res = await fetch(`${API_BASE}/brand-profile/${activeBrandId}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_ids: documentIds }),
      });
      if (!res.ok) throw new Error("Trục trặc trong tiến trình phân tách tài liệu");
      return await res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brand-profile", "detail", activeBrandId] });
      setSelectedDocuments([]);
      navigate({ search: (prev: any) => ({ ...prev, syncOpen: undefined }) } as any);
    },
    onError: (err: any) => alert(`Thất bại: ${err.message}`),
  });

  // ─── Mutation 4: Xóa thực thể thương hiệu hiện tại ─────────────────────────
  const deleteBrandMutation = useMutation({
    mutationFn: async (brandId: string) => {
      const res = await fetch(`${API_BASE}/brand-profile/${brandId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Hệ thống không thể xóa thương hiệu này");
      return brandId;
    },
    onSuccess: (deletedId) => {
      queryClient.invalidateQueries({ queryKey: ["brands", "list", CURRENT_OWNER_ID] });
      if (activeBrandId === deletedId) {
        navigate({ search: (prev: any) => ({ ...prev, selectedBrandId: undefined }) } as any);
      }
      setBrandToDelete(null);
    },
    onError: (err: any) => {
      alert(err.message);
      setBrandToDelete(null);
    },
  });

  // ─── Xử lý cập nhật cục bộ qua hàm PATCH bọc tiện ích ─────────────────────
  const executePartialUpdate = (fieldOrBlock: string, updatedPayload: any) => {
    if (!activeBrandId) return;
    patchFieldMutation.mutate({
      blockKey: fieldOrBlock,
      payload: updatedPayload,
    });
  };

  const toggleSection = (id: number) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleToggleDocument = (id: number) => {
    setSelectedDocuments((prev) =>
      prev.includes(id) ? prev.filter((docId) => docId !== id) : [...prev, id]
    );
  };

  // ─── Giao Diện Thành Phần Section Layout ───────────────────────────────────
  const Section = ({ id, title, blockKey, children }: { id: number; title: string; blockKey: string; children: React.ReactNode }) => (
    <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs bg-white dark:bg-slate-900">
      <button
        onClick={() => toggleSection(id)}
        className="w-full flex items-center justify-between px-5 py-4 bg-slate-50/70 dark:bg-slate-900/50 hover:bg-slate-100/70 dark:hover:bg-slate-800/70 transition-colors"
      >
        <div className="flex items-center gap-3 text-left">
          <span className="text-xs font-bold text-slate-400 dark:text-slate-500 font-mono">
            {String(id).padStart(2, "0")}
          </span>
          <h3 className="font-semibold text-slate-800 dark:text-slate-200 text-sm tracking-tight flex items-center gap-2">
            {title}
            {isPatching === blockKey && <Loader2 className="w-3 h-3 animate-spin text-indigo-500" />}
          </h3>
        </div>
        {expanded[id] ? <ChevronDown size={16} className="text-slate-400" /> : <ChevronRight size={16} className="text-slate-400" />}
      </button>
      {expanded[id] && (
        <div className="px-5 py-5 border-t border-slate-100 dark:border-slate-800 space-y-4">
          {children}
        </div>
      )}
    </div>
  );

  // ─── Giao Diện Thành Phần Nhập Thẻ (Tag Input) ─────────────────────────────
  const TagInput = ({ tags, onAdd, onRemove, placeholder, variant = "outline" }: { tags: string[]; onAdd: (tag: string) => void; onRemove: (index: number) => void; placeholder: string; variant?: "outline" | "destructive" | "secondary" }) => (
    <div className="space-y-2.5">
      <div className="flex flex-wrap gap-1.5">
        {tags.map((tag, i) => (
          <Badge key={i} variant={variant} className="text-xs font-medium pl-2 pr-1 py-0.5 rounded-md">
            {tag}
            <button type="button" className="ml-1 rounded-full p-0.5 hover:bg-slate-200 dark:hover:bg-slate-700" onClick={() => onRemove(i)}>
              <X className="w-2.5 h-2.5" />
            </button>
          </Badge>
        ))}
      </div>
      <Input
        placeholder={placeholder}
        className="h-8 text-xs bg-slate-50/50 dark:bg-slate-950"
        onKeyDown={(e) => {
          const el = e.currentTarget;
          if (e.key === "Enter" && el.value.trim()) {
            onAdd(el.value.trim());
            el.value = "";
          }
        }}
      />
    </div>
  );

  if (isLoadingBrands) {
    return (
      <div className="flex items-center justify-center py-32 gap-2 text-muted-foreground text-xs font-medium">
        <Loader2 className="w-4 h-4 animate-spin text-indigo-500" /> Đang thiết lập cấu trúc tổ chức...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 flex antialiased">

      {/* ── SIDEBAR TRÁI: ĐIỀU HƯỚNG DANH SÁCH BRAND TỔNG HỢP ── */}
      <aside className="w-64 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 hidden md:flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-xs uppercase tracking-wider text-slate-400">
            <Building2 className="w-4 h-4 text-indigo-500" /> Thương hiệu ({brandListMeta?.total || 0})
          </div>
          <Button size="icon" variant="ghost" className="h-7 w-7 rounded-md" onClick={() => setIsNewBrandOpen(true)}>
            <Plus className="w-4 h-4" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-1 pr-1">
          {brandListMeta?.brands.map((b) => (
            <div 
              key={b.id} 
              className={`group flex items-center justify-between rounded-lg transition-all ${
                activeBrandId === b.id
                  ? "bg-indigo-50 dark:bg-indigo-950/40" 
                  : "hover:bg-slate-50 dark:hover:bg-slate-800"
              }`}
            >
              <button
                onClick={() => navigate({ search: (prev: any) => ({ ...prev, selectedBrandId: b.id }) } as any)}
                className={`flex-1 text-left px-3 py-2 text-xs font-medium truncate block transition-colors ${
                  activeBrandId === b.id
                    ? "text-indigo-600 dark:text-indigo-400 font-semibold"
                    : "text-slate-600 dark:text-slate-400"
                }`}
              >
                {b.name}
              </button>
              <Button
                size="icon"
                variant="ghost"
                className="h-7 w-7 opacity-0 group-hover:opacity-100 mr-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-all rounded-md shrink-0"
                onClick={(e) => {
                  e.stopPropagation();
                  setBrandToDelete(b);
                }}
              >
                <Trash2 className="w-3.5 h-3.5" />
              </Button>
            </div>
          ))}
        </div>
      </aside>

      {/* ── PHÂN KHU CHÍNH HIỂN THỊ HỒ SƠ CONFIG ── */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* HEADER CHỨA NÚT HÀNH ĐỘNG VÀ DROPDOWN CHO MOBILE */}
        <div className="sticky top-0 z-30 bg-white/90 dark:bg-slate-950/90 backdrop-blur-md border-b border-slate-200/80 dark:border-slate-800/80">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between md:justify-end gap-2.5">

            {/* Bộ chọn thương hiệu nhanh chỉ hiển thị trên màn hình Mobile nhỏ */}
            <div className="md:hidden flex items-center gap-2">
              <FolderHeart className="w-4 h-4 text-indigo-500" />
              <select
                value={activeBrandId || ""}
                onChange={(e) => navigate({ search: (prev: any) => ({ ...prev, selectedBrandId: e.target.value }) } as any)}
                className="bg-transparent text-xs font-bold text-slate-800 dark:text-slate-200 outline-none max-w-[140px]"
              >
                {brandListMeta?.brands.map((b) => (
                  <option key={b.id} value={b.id} className="dark:bg-slate-900">{b.name}</option>
                ))}
              </select>
              <button onClick={() => setIsNewBrandOpen(true)} className="p-1 rounded bg-slate-100 dark:bg-slate-800">
                <Plus className="w-3 h-3" />
              </button>
            </div>

            <div className="flex items-center gap-2">
              {/* Nút Xóa Thương Hiệu Hiện Tại */}
              {activeBrandDetails && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 text-xs text-slate-500 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
                  onClick={() => setBrandToDelete(activeBrandDetails)}
                >
                  <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                  <span className="hidden sm:inline">Xóa thương hiệu</span>
                </Button>
              )}

              <Button
                variant="outline"
                size="sm"
                disabled={!activeBrandId}
                className="h-8 text-xs font-semibold border-slate-200 bg-white hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 text-slate-800 dark:text-slate-200 shadow-xs"
                onClick={() => navigate({ search: (prev: any) => ({ ...prev, syncOpen: true }) } as any)}
              >
                <Sparkles className="w-3.5 h-3.5 mr-1.5 text-indigo-500 fill-indigo-500/10" />
                Tài liệu
              </Button>
            </div>
          </div>
        </div>

        {/* KHU VỰC HIỂN THỊ CHI TIẾT CÁC Ô BIỂU MẪU CẤU HÌNH */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 pb-24 space-y-4">

            {!activeBrandId ? (
              <div className="text-center py-20 border border-dashed rounded-xl text-xs text-slate-400">
                Chưa có thương hiệu nào tồn tại. Vui lòng nhấn nút dấu cộng (+) ở thanh menu để khởi tạo.
              </div>
            ) : isLoadingProfile ? (
              <div className="flex items-center justify-center py-20 text-xs gap-2 text-slate-400">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-500" /> Đang đồng bộ hóa kho định chế...
              </div>
            ) : !profileData ? (
              <div className="text-center py-16 border border-dashed rounded-xl bg-white dark:bg-slate-900 p-8 space-y-3">
                <p className="text-xs text-slate-400">Thương hiệu này hiện chưa được thiết lập kiến trúc nhận diện AI Voice.</p>
                <Button size="sm" className="h-8 text-xs bg-indigo-600 text-white" onClick={() => navigate({ search: (prev: any) => ({ ...prev, syncOpen: true }) } as any)}>
                  <Sparkles className="w-3.5 h-3.5 mr-1.5" /> Quét tài liệu RAG ngay
                </Button>
              </div>
            ) : (
              <>
                {/* ─── Phần 1: Giọng Điệu & Tông ─── */}
                <Section id={1} title="Giọng Điệu & Tông" blockKey="positioning">
                  <div className="space-y-4">
                    <div>
                      <Label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5 block">Định Vị Thương Hiệu</Label>
                      <Textarea
                        rows={2}
                        defaultValue={profileData.positioning || ""}
                        onBlur={(e) => executePartialUpdate("positioning", { positioning: e.target.value })}
                        placeholder="Xác định định vị cốt lõi của thương hiệu..."
                        className="text-xs font-medium bg-slate-50/50 dark:bg-slate-950 focus-visible:bg-white transition-colors"
                      />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2 block">Mẫu Tông Ngôn Ngữ</Label>
                        <TagInput
                          tags={profileData.brand_voice_rules?.tone_patterns || []}
                          onAdd={(tag) => executePartialUpdate("brand_voice_rules", { tone_patterns: [...(profileData.brand_voice_rules?.tone_patterns || []), tag] })}
                          onRemove={(idx) => executePartialUpdate("brand_voice_rules", { tone_patterns: profileData.brand_voice_rules.tone_patterns.filter((_, j) => j !== idx) })}
                          placeholder="Thêm mô tả tông + Enter..."
                        />
                      </div>
                      <div>
                        <Label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2 block">Thuật Ngữ Bị Cấm</Label>
                        <TagInput
                          tags={profileData.brand_voice_rules?.forbidden_words || []}
                          onAdd={(tag) => executePartialUpdate("brand_voice_rules", { forbidden_words: [...(profileData.brand_voice_rules?.forbidden_words || []), tag] })}
                          onRemove={(idx) => executePartialUpdate("brand_voice_rules", { forbidden_words: profileData.brand_voice_rules.forbidden_words.filter((_, j) => j !== idx) })}
                          placeholder="Từ ngữ cấm dùng + Enter..."
                          variant="destructive"
                        />
                      </div>
                    </div>
                  </div>
                </Section>

                {/* ─── Phần 2: Kiến Trúc Thông Điệp ─── */}
                <Section id={2} title="Kiến Trúc Thông Điệp" blockKey="messaging">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2 block">Điểm Đau Của Khách Hàng (Pain Points)</Label>
                      <TagInput
                        tags={profileData.messaging?.pain_points || []}
                        onAdd={(tag) => executePartialUpdate("messaging", { pain_points: [...(profileData.messaging?.pain_points || []), tag] })}
                        onRemove={(idx) => executePartialUpdate("messaging", { pain_points: profileData.messaging.pain_points.filter((_, j) => j !== idx) })}
                        placeholder="Thêm nỗi đau khách hàng + Enter..."
                        variant="secondary"
                      />
                    </div>
                    <div>
                      <Label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2 block">Bằng Chứng Thuyết Phục (Proof Points)</Label>
                      <TagInput
                        tags={profileData.messaging?.proof_points || []}
                        onAdd={(tag) => executePartialUpdate("messaging", { proof_points: [...(profileData.messaging?.proof_points || []), tag] })}
                        onRemove={(idx) => executePartialUpdate("messaging", { proof_points: profileData.messaging.proof_points.filter((_, j) => j !== idx) })}
                        placeholder="Chứng chỉ, số liệu uy tín + Enter..."
                        variant="secondary"
                      />
                    </div>
                  </div>
                </Section>

                {/* ─── Phần 3: Nhận Diện Hình Ảnh ─── */}
                <Section id={3} title="Nhận Diện Hình Ảnh" blockKey="visual_identity">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-4">
                      <div>
                        <Label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5 block">Phong Cách Thiết Kế (Style)</Label>
                        <Input
                          defaultValue={profileData.visual_identity?.style_description || ""}
                          onBlur={(e) => executePartialUpdate("visual_identity", { style_description: e.target.value })}
                          placeholder="Tối giản, sang trọng..."
                          className="h-9 text-xs bg-slate-50/50"
                        />
                      </div>
                      <div>
                        <Label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5 block">Không Khí Chủ Đạo (Mood)</Label>
                        <Input
                          defaultValue={profileData.visual_identity?.mood || ""}
                          onBlur={(e) => executePartialUpdate("visual_identity", { mood: e.target.value })}
                          placeholder="Cinematic, Hiện đại..."
                          className="h-9 text-xs bg-slate-50/50"
                        />
                      </div>
                    </div>
                    <div>
                      <Label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2 block">Bảng Màu Thương Hiệu</Label>
                      <div className="flex flex-wrap gap-1.5 mb-2">
                        {(profileData.visual_identity?.color_palette || []).map((hex, i) => (
                          <div key={i} className="flex items-center gap-1 pl-1.5 pr-1 py-1 rounded border bg-slate-50 dark:bg-slate-900 text-[11px] font-mono">
                            <div style={{ backgroundColor: hex }} className="w-3 h-3 rounded-xs" />
                            <span>{hex}</span>
                            <button onClick={() => executePartialUpdate("visual_identity", { color_palette: profileData.visual_identity.color_palette.filter((_, j) => j !== i) })}>
                              <X className="w-3 h-3 text-slate-400" />
                            </button>
                          </div>
                        ))}
                      </div>
                      <Input
                        placeholder="Mã #HEX + Enter"
                        className="h-8 text-xs"
                        onKeyDown={(e) => {
                          const el = e.currentTarget;
                          if (e.key === "Enter" && el.value.startsWith("#")) {
                            executePartialUpdate("visual_identity", { color_palette: [...(profileData.visual_identity?.color_palette || []), el.value.trim()] });
                            el.value = "";
                          }
                        }}
                      />
                    </div>
                  </div>
                </Section>

                {/* ─── Phần 4: Đối Tượng & Định Hướng Chuyển Đổi ─── */}
                <Section id={4} title="Đối Tượng & Định Hướng Chuyển Đổi" blockKey="audience">
                  <div className="space-y-4">
                    <div>
                      <Label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5 block">Chân Dung Đối Tượng Mục Tiêu</Label>
                      <Textarea
                        rows={2}
                        defaultValue={profileData.audience || ""}
                        onBlur={(e) => executePartialUpdate("audience", { audience: e.target.value })}
                        placeholder="Mô tả phân khúc đối tượng đích..."
                        className="text-xs font-medium bg-slate-50/50"
                      />
                    </div>
                    <div>
                      <Label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2 block">Cấu Trúc Lời Kêu Gọi Hành Động (CTA Mẫu)</Label>
                      <TagInput
                        tags={profileData.brand_voice_rules?.cta_patterns || []}
                        onAdd={(tag) => executePartialUpdate("brand_voice_rules", { cta_patterns: [...(profileData.brand_voice_rules?.cta_patterns || []), tag] })}
                        onRemove={(idx) => executePartialUpdate("brand_voice_rules", { cta_patterns: profileData.brand_voice_rules.cta_patterns.filter((_, j) => j !== idx) })}
                        placeholder="Thêm CTA hành động mẫu + Enter..."
                      />
                    </div>
                  </div>
                </Section>

                {/* ─── Phần 5: Thư Viện Nội Dung Mẫu ─── */}
                <Section id={5} title="Thư Viện Nội Dung Mẫu" blockKey="content_examples">
                  <div className="space-y-4">
                    <div>
                      <Label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5 block">Mẫu Nội Dung Mạng Xã Hội (Social Post)</Label>
                      <Textarea
                        rows={3}
                        defaultValue={profileData.content_examples?.social_post || ""}
                        onBlur={(e) => executePartialUpdate("content_examples", { social_post: e.target.value })}
                        className="text-xs font-mono bg-slate-50/50"
                      />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5 block">Mẫu Văn Bản Blog</Label>
                        <Textarea
                          rows={3}
                          defaultValue={profileData.content_examples?.blog_post || ""}
                          onBlur={(e) => executePartialUpdate("content_examples", { blog_post: e.target.value })}
                          className="text-xs font-mono bg-slate-50/50"
                        />
                      </div>
                      <div>
                        <Label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5 block">Mẫu Tiêu Đề Quảng Cáo (Ad Copy)</Label>
                        <Textarea
                          rows={3}
                          defaultValue={profileData.content_examples?.ad_copy || ""}
                          onBlur={(e) => executePartialUpdate("content_examples", { ad_copy: e.target.value })}
                          className="text-xs font-mono bg-slate-50/50"
                        />
                      </div>
                    </div>
                  </div>
                </Section>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── MODAL 1: KHỞI TẠO BRAND MỚI ── */}
      <Dialog open={isNewBrandOpen} onOpenChange={setIsNewBrandOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold">Tạo Thương Hiệu Mới</DialogTitle>
            <DialogDescription className="text-xs">Định danh một thực thể kinh doanh độc lập để AI phân tích cấu trúc.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 pt-2">
            <Input
              placeholder="Ví dụ: VinFast Vietnam, Highland Coffee..."
              value={newBrandName}
              onChange={(e) => setNewBrandName(e.target.value)}
              className="h-9 text-xs"
            />
            <Button
              className="w-full h-9 text-xs font-bold bg-indigo-600 text-white"
              disabled={!newBrandName.trim() || createBrandMutation.isPending}
              onClick={() => createBrandMutation.mutate(newBrandName)}
            >
              {createBrandMutation.isPending && <Loader2 className="w-3 h-3 animate-spin mr-2" />}
              Khai sinh thương hiệu
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ── MODAL 2: KHAI PHÁ TỪ TÀI LIỆU KIẾN THỨC (LUỒNG RAG) ── */}
      <Dialog open={!!syncOpen} onOpenChange={(open) => navigate({ search: (prev) => ({ ...prev, syncOpen: open ? true : undefined }) } as any)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold flex items-center gap-2">
              <FileText className="w-4 h-4 text-indigo-500" /> Khai Phá Từ Tài Liệu RAG
            </DialogTitle>
            <DialogDescription className="text-xs">Trích xuất tri thức từ các nguồn tài liệu thô được chỉ định để tự động điền các ô cấu hình phía sau.</DialogDescription>
          </DialogHeader>
          <div className="space-y-2 pt-2 max-h-[300px] overflow-y-auto pr-1">
            {isLoadingRag ? (
              <div className="flex items-center justify-center py-10 text-xs gap-2 text-slate-500">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Đang liên kết kho lưu trữ...
              </div>
            ) : (
              ragDocuments.map((doc) => {
                const isChecked = selectedDocuments.includes(doc.id);
                return (
                  <div
                    key={doc.id}
                    onClick={() => handleToggleDocument(doc.id)}
                    className={`flex items-start gap-3 p-3 rounded-lg border transition-all cursor-pointer ${
                      isChecked 
                        ? "border-indigo-600 bg-indigo-50/30 dark:bg-indigo-950/20" 
                        : "border-slate-200 dark:border-slate-800 hover:bg-slate-50"
                    }`}
                  >
                    <Checkbox 
                      id={`doc-${doc.id}`} 
                      checked={isChecked} 
                      onCheckedChange={() => handleToggleDocument(doc.id)} 
                      className="mt-0.5" 
                    />
                    <div className="flex-1 space-y-0.5">
                      <div className="flex items-center justify-between gap-2">
                        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 cursor-pointer select-none truncate block">
                          {doc.title}
                        </label>
                        <Badge variant="secondary" className="text-[10px] px-1.5 py-0 scale-90 origin-right capitalize">
                          {doc.document_type}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-slate-400">
                        {doc.chunk_count} đoạn mã • Trạng thái:{" "}
                        <span className={doc.status === "completed" ? "text-emerald-500 font-medium" : "text-amber-500"}>
                          {doc.status}
                        </span>
                      </p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
          
          <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => navigate({ search: (prev) => ({ ...prev, syncOpen: undefined }) } as any)}
            >
              Hủy
            </Button>
            <Button
              size="sm"
              className="h-8 text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700"
              disabled={selectedDocuments.length === 0 || generateMutation.isPending}
              onClick={() => generateMutation.mutate(selectedDocuments)}
            >
              {generateMutation.isPending && <Loader2 className="w-3 h-3 animate-spin mr-1.5" />}
              Bắt đầu trích xuất AI
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ── MODAL 3: XÁC NHẬN XÓA THƯƠNG HIỆU ── */}
      <Dialog open={!!brandToDelete} onOpenChange={(open) => !open && setBrandToDelete(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold text-rose-600 flex items-center gap-2">
              <Trash2 className="w-4 h-4" /> Xác nhận xóa thương hiệu
            </DialogTitle>
            <DialogDescription className="text-xs pt-1">
              Hành động này sẽ xóa vĩnh viễn thương hiệu{" "}
              <strong className="text-slate-800 dark:text-slate-200">"{brandToDelete?.name}"</strong>{" "}
              và toàn bộ dữ liệu cấu hình AI Voice liên quan. Thao tác này không thể hoàn tác.
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center justify-end gap-2 pt-4">
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => setBrandToDelete(null)}
              disabled={deleteBrandMutation.isPending}
            >
              Hủy bỏ
            </Button>
            <Button
              variant="destructive"
              size="sm"
              className="h-8 text-xs font-semibold bg-rose-600 text-white hover:bg-rose-700"
              onClick={() => brandToDelete && deleteBrandMutation.mutate(brandToDelete.id)}
              disabled={deleteBrandMutation.isPending}
            >
              {deleteBrandMutation.isPending && <Loader2 className="w-3 h-3 animate-spin mr-1.5" />}
              Xác nhận xóa
            </Button>
          </div>
        </DialogContent>
      </Dialog>

    </div>
  );
}