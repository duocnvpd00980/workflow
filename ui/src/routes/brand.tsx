/**
 * ScreenBrandVoice — Notion-style Single Stream (No Cards)
 * RESTORED ALL 5 BLOCKS: Optimized for ultra-low code density & high stability.
 */

import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { 
  Volume2, Check, X, RotateCcw, Eye, Search, Save, 
  AlignLeft, Upload, ExternalLink, HelpCircle 
} from "lucide-react";

// ─── Shadcn UI Components ───────────────────────────────────────────────────
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";

const API_BASE = "http://localhost:8000/api/v1";
const brandVoiceKeys = { detail: () => ["brand-voice", "detail"] as const };

// ─── Types ────────────────────────────────────────────────────────────────────
export interface RefDoc { name: string; size: string; type: string; }

export interface BrandVoiceData {
  tone_of_voice:    string;
  voice_rules:      string[];
  cta_style:        string;
  cta_samples:      string[];
  core_message:     string;
  visual_style:     string;
  brand_colors:     string[];
  image_type:       string;
  image_rules:      string[];
  products:         string[];
  benefits:         string[];
  target_audience:  string[];
  reference_urls:   string[];
  reference_notes:  string;
  reference_docs:   RefDoc[];
}

const MOCK_DEFAULT_DATA: BrandVoiceData = {
  tone_of_voice: "Thân thiện",
  voice_rules: ["Sử dụng đại từ nhân xưng 'Mày/Tao' hoặc 'Tôi/Bạn' linh hoạt", "Không dùng từ ngữ quá hàn lâm"],
  cta_style: "Mềm mại",
  cta_samples: ["Trải nghiệm ngay hôm nay!", "Khám phá giải pháp tối ưu cho doanh nghiệp"],
  core_message: "Hệ thống AI Marketing tự động hóa chuỗi cung ứng nội dung cho doanh nghiệp.",
  visual_style: "Tối giản",
  brand_colors: ["#4F46E5", "#10B981", "#F59E0B"],
  image_type: "Ảnh thực tế",
  image_rules: ["Chụp góc Dutch angle nhẹ", "Độ sâu trường ảnh (Depth of Field) mỏng", "Ánh sáng tương phản Chiaroscuro"],
  products: ["Gói Setup AI Automation", "Phần mềm Tạo Banner Tự Động"],
  benefits: ["Tiết kiệm 80% thời gian design", "Đồng bộ nhận diện 100% các kênh"],
  target_audience: ["SMEs", "Chủ shop online", "Marketers"],
  reference_urls: ["https://holo-ai.vn"],
  reference_notes: "Cần lưu ý giữ đúng palette màu thương hiệu.",
  reference_docs: [
    { name: "Brand_Guideline_2026.pdf", size: "4.2 MB", type: "PDF" },
    { name: "Product_Specs.docx", size: "1.8 MB", type: "DOCX" }
  ]
};

// ─── Route Definition ────────────────────────────────────────────────────────
export const Route = createFileRoute("/brand")({
  validateSearch: (search: Record<string, unknown>) => ({
    syncOpen: (search.syncOpen as boolean) || undefined,
    previewOpen: (search.previewOpen as boolean) || undefined,
    q: (search.q as string) || "",
  }),
  component: ScreenBrandVoice,
});

export function ScreenBrandVoice() {
  const queryClient = useQueryClient();
  const navigate = useNavigate({ from: Route.fullPath });
  const { syncOpen, previewOpen, q: searchParamQ } = Route.useSearch();

  // ── TanStack Query ──────────────────────────────────────────────────────────
  const { data, isLoading } = useQuery<BrandVoiceData>({
    queryKey: brandVoiceKeys.detail(),
    queryFn: async () => {
      try {
        const res = await fetch(`${API_BASE}/brand-voice`).then(r => r.json());
        return { ...MOCK_DEFAULT_DATA, ...res.data };
      } catch {
        return MOCK_DEFAULT_DATA;
      }
    },
    staleTime: 5 * 60 * 1000,
  });

  // ── Mutations ──────────────────────────────────────────────────────────────
  const saveMutation = useMutation({
    mutationFn: async (payload: BrandVoiceData) => {
      const res = await fetch(`${API_BASE}/brand-voice`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).then(r => r.json());
      return res.data;
    },
    onSuccess: (updatedData) => {
      queryClient.setQueryData(brandVoiceKeys.detail(), updatedData);
    },
  });

  const syncMutation = useMutation({
    mutationFn: async (queryKeyword: string) => {
      try {
        const res = await fetch(`${API_BASE}/brand-voice/sync-from-rag?query=${encodeURIComponent(queryKeyword)}`, {
          method: "POST"
        }).then(r => r.json());
        return res.data;
      } catch {
        return { ...data, core_message: `Dữ liệu đồng bộ tự động từ RAG cho từ khóa: ${queryKeyword}` };
      }
    },
    onSuccess: (updatedData) => {
      queryClient.setQueryData(brandVoiceKeys.detail(), updatedData);
      navigate({ search: (prev) => ({ ...prev, syncOpen: undefined }) });
    },
  });

  if (isLoading || !data) {
    return (
      <div className="flex items-center justify-center py-32 gap-2 text-muted-foreground text-xs font-medium">
        <Loader2 className="w-4 h-4 animate-spin text-primary" /> Đang tối ưu luồng dữ liệu...
      </div>
    );
  }

  const updateField = (patch: Partial<BrandVoiceData>) => {
    queryClient.setQueryData(brandVoiceKeys.detail(), { ...data, ...patch });
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-12 bg-background text-foreground antialiased ">
      
      {/* ── STICKY TOP BAR (Hành động phẳng) ── */}
      <div className="sticky top-0 bg-background/90 backdrop-blur-md z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-muted">
        <div>
          <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
            <Volume2 className="w-5 h-5 text-primary" /> Brand Engine Configuration
          </h1>
          <p className="text-xs text-muted-foreground mt-1">Luồng thiết lập ngữ cảnh phẳng Notion-style, triệt tiêu card.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="h-8 text-xs text-muted-foreground" onClick={() => updateField(MOCK_DEFAULT_DATA)}>
            <RotateCcw className="w-3.5 h-3.5 mr-1" /> Mặc định
          </Button>
          <Button variant="ghost" size="sm" className="h-8 text-xs text-muted-foreground" onClick={() => navigate({ search: (prev) => ({ ...prev, previewOpen: true }) })}>
            <Eye className="w-3.5 h-3.5 mr-1" /> Payload
          </Button>
          <Button variant="secondary" size="sm" className="h-8 text-xs font-semibold" onClick={() => navigate({ search: (prev) => ({ ...prev, syncOpen: true }) })}>
            <Search className="w-3.5 h-3.5 mr-1" /> Auto RAG
          </Button>
          <Button size="sm" className="h-8 text-xs font-semibold px-4 shadow-sm" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate(data)}>
            {saveMutation.isPending && <Loader2 className="w-3 h-3 animate-spin mr-1" />}
            Lưu SQLite
          </Button>
        </div>
      </div>

      {/* ── BLOCK 1: TONE OF VOICE ── */}
      <section className="space-y-4">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-bold text-primary font-mono">01.</span>
          <h2 className="text-base font-bold tracking-tight">Giọng văn & Định hướng nội dung</h2>
        </div>
        
        <div className="pl-6 space-y-4">
          <RadioGroup
            value={data.tone_of_voice || "Thân thiện"}
            onValueChange={(val) => updateField({ tone_of_voice: val })}
            className="grid grid-cols-1 sm:grid-cols-2 gap-2"
          >
            {[
              { id: "Thân thiện", title: "😊 Thân thiện", desc: "Gần gũi, tự nhiên, dễ hiểu" },
              { id: "Chuyên nghiệp", title: "💼 Chuyên nghiệp", desc: "Trang trọng, uy tín, chính xác" },
              { id: "Truyền cảm hứng", title: "✨ Truyền cảm hứng", desc: "Tích cực, thúc đẩy hành động" },
              { id: "Hài hước", title: "😆 Hài hước", desc: "Vui vẻ, dí dỏm, tạo trend" },
            ].map((t) => (
              <Label
                key={t.id}
                className={`flex items-start gap-3 p-3 rounded-lg border border-muted bg-background/50 cursor-pointer transition-all hover:border-slate-300 ${
                  data.tone_of_voice === t.id ? "border-primary ring-1 ring-primary/20 bg-primary/[0.02]" : ""
                }`}
              >
                <RadioGroupItem value={t.id} className="mt-0.5" />
                <div>
                  <span className="font-semibold text-xs text-slate-800 block">{t.title}</span>
                  <span className="text-[11px] text-muted-foreground block mt-0.5">{t.desc}</span>
                </div>
              </Label>
            ))}
          </RadioGroup>

          <div className="space-y-2 pt-1">
            <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Quy tắc viết text bắt buộc</Label>
            <div className="flex flex-wrap gap-1.5">
              {(data.voice_rules || []).map((rule, i) => (
                <Badge key={i} variant="outline" className="text-xs font-medium pl-2.5 pr-1.5 py-0.5 border-slate-200 bg-slate-50 text-slate-600 rounded-md">
                  {rule}
                  <button type="button" className="ml-1.5 p-0.5 rounded-full hover:bg-slate-200 text-slate-400 hover:text-slate-600" onClick={() => updateField({ voice_rules: data.voice_rules.filter((_, j) => j !== i) })}>
                    <X className="w-2.5 h-2.5" />
                  </button>
                </Badge>
              ))}
            </div>
            <Input
              placeholder="Gõ quy tắc mới rồi nhấn Enter..." className="h-8 text-xs max-w-md focus-visible:ring-primary/30"
              onKeyDown={(e) => {
                const el = e.currentTarget;
                if (e.key === "Enter" && el.value.trim()) {
                  updateField({ voice_rules: [...(data.voice_rules || []), el.value.trim()] });
                  el.value = "";
                }
              }}
            />
          </div>
        </div>
      </section>

      {/* ── BLOCK 2: CTA & CORE MESSAGE ── */}
      <section className="space-y-4 pt-2 border-t border-muted">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-bold text-primary font-mono">02.</span>
          <h2 className="text-base font-bold tracking-tight">Thông điệp & Lời kêu gọi (CTA)</h2>
        </div>

        <div className="pl-6 space-y-4">
          <div className="space-y-2">
            <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Thông điệp cốt lõi (Core Slogan)</Label>
            <Textarea
              rows={2} value={data.core_message || ""}
              onChange={(e) => updateField({ core_message: e.target.value })}
              placeholder="Nhập giá trị cốt lõi để bot định hình bài viết..." className="text-xs focus-visible:ring-primary/30 font-medium leading-relaxed"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Danh sách cấu trúc CTA mẫu</Label>
            <div className="space-y-1 max-w-xl">
              {(data.cta_samples || []).map((cta, i) => (
                <div key={i} className="flex items-center justify-between py-1 px-2 border border-transparent hover:border-slate-200 rounded-md bg-slate-50/60 text-xs text-slate-700 font-medium group">
                  <span className="truncate">{cta}</span>
                  <Button size="icon" variant="ghost" className="w-5 h-5 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive" onClick={() => updateField({ cta_samples: data.cta_samples.filter((_, j) => j !== i) })}>
                    <X className="w-3 h-3" />
                  </Button>
                </div>
              ))}
            </div>
            <Input
              placeholder="Thêm CTA mẫu + Enter..." className="h-8 text-xs max-w-md"
              onKeyDown={(e) => {
                const el = e.currentTarget;
                if (e.key === "Enter" && el.value.trim()) {
                  updateField({ cta_samples: [...(data.cta_samples || []), el.value.trim()] });
                  el.value = "";
                }
              }}
            />
          </div>
        </div>
      </section>

      {/* ── BLOCK 3: VISUAL IDENTITY ── */}
      <section className="space-y-4 pt-2 border-t border-muted">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-bold text-primary font-mono">03.</span>
          <h2 className="text-base font-bold tracking-tight">Hệ thống nhận diện hình ảnh (Diffusion / ControlNet)</h2>
        </div>

        <div className="pl-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Loại hình đồ họa</Label>
              <div className="flex flex-wrap gap-1">
                {["Ảnh thực tế", "Đồ họa phẳng", "3D Render", "Tối giản Vector"].map((t) => (
                  <Button
                    key={t} size="sm" variant={data.image_type === t ? "secondary" : "outline"}
                    className={`h-7 text-xs px-3 font-medium ${data.image_type === t ? "border-primary/30 text-primary bg-primary/[0.03]" : ""}`} 
                    onClick={() => updateField({ image_type: t })}
                  >
                    {t}
                  </Button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Bảng màu Brand (Hex)</Label>
              <div className="flex items-center gap-2">
                {(data.brand_colors || []).map((hex, i) => (
                  <div key={i} className="flex items-center gap-1.5 border border-muted rounded px-1.5 py-0.5 bg-slate-50">
                    <div style={{ backgroundColor: hex }} className="w-3 h-3 rounded-sm shadow-inner" />
                    <span className="text-[10px] font-mono text-slate-500">{hex}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Cấu trúc prompt mặc định (Cinematic Style)</Label>
            <div className="bg-slate-50 text-slate-600 rounded-lg p-3 text-xs font-mono space-y-1 border border-slate-100">
              {(data.image_rules || []).map((rule, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-primary/40 font-bold">•</span>
                  <span>{rule}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── BLOCK 4: PRODUCTS & TARGET AUDIENCE ── */}
      <section className="space-y-4 pt-2 border-t border-muted">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-bold text-primary font-mono">04.</span>
          <h2 className="text-base font-bold tracking-tight">Sản phẩm & Đối tượng mục tiêu</h2>
        </div>

        <div className="pl-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            
            {/* Sản phẩm */}
            <div className="space-y-2">
              <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Danh mục sản phẩm áp dụng</Label>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {(data.products || []).map((prod, i) => (
                  <div key={i} className="flex items-center gap-2 py-1 px-1.5 text-xs text-slate-700 font-medium group">
                    <AlignLeft className="w-3.5 h-3.5 text-muted-foreground" />
                    <span className="flex-1 truncate">{prod}</span>
                    <button type="button" className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive" onClick={() => updateField({ products: data.products.filter((_, j) => j !== i) })}>
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
              <Input
                placeholder="Thêm tên sản phẩm..." className="h-8 text-xs max-w-xs"
                onKeyDown={(e) => {
                  const el = e.currentTarget;
                  if (e.key === "Enter" && el.value.trim()) {
                    updateField({ products: [...(data.products || []), el.value.trim()] });
                    el.value = "";
                  }
                }}
              />
            </div>

            {/* Target & Benefits */}
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Lợi ích cốt lõi</Label>
                <ul className="text-xs space-y-1 text-slate-600 font-medium">
                  {(data.benefits || []).map((b, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <span className="w-1 h-1 rounded-full bg-emerald-500" />
                      <span className="truncate">{b}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="space-y-1.5">
                <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Phân khúc khách hàng mục tiêu</Label>
                <div className="flex flex-wrap gap-1">
                  {(data.target_audience || []).map((tag, i) => (
                    <Badge key={i} variant="outline" className="text-[10px] px-2 py-0 border-slate-200 bg-slate-50 font-bold text-slate-500">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ── BLOCK 5: REFERENCE DOCUMENTS ── */}
      <section className="space-y-4 pt-2 border-t border-muted">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-bold text-primary font-mono">05.</span>
          <h2 className="text-base font-bold tracking-tight">Tài liệu tham khảo nguồn (RAG Input)</h2>
        </div>

        <div className="pl-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            
            {/* File đính kèm */}
            <div className="space-y-2">
              <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Tài liệu hướng dẫn đã tải lên</Label>
              <div className="space-y-1.5">
                {(data.reference_docs || []).map((doc, i) => (
                  <div key={i} className="flex items-center justify-between p-2 border border-slate-100 rounded-lg bg-slate-50/50 text-[11px] font-medium">
                    <div className="flex items-center gap-2 overflow-hidden">
                      <span className="text-[9px] font-black bg-red-100 text-red-700 px-1 py-0.5 rounded">{doc.type}</span>
                      <span className="text-slate-700 font-semibold truncate">{doc.name}</span>
                    </div>
                    <span className="text-[10px] font-mono text-muted-foreground shrink-0">{doc.size}</span>
                  </div>
                ))}
                <div className="border border-dashed border-slate-200 p-2 rounded-lg text-center text-xs text-muted-foreground hover:bg-slate-50 cursor-pointer transition flex items-center justify-center gap-1.5 font-semibold">
                  <Upload className="w-3.5 h-3.5 text-primary" />
                  Tải lên tệp mới
                </div>
              </div>
            </div>

            {/* URL cào */}
            <div className="space-y-2">
              <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Đường dẫn Website tham khảo</Label>
              <div className="flex items-center gap-2 p-1.5 border border-slate-200 rounded-lg bg-background shadow-sm">
                <Input
                  className="h-6 text-xs border-0 p-0 focus-visible:ring-0 text-primary font-medium"
                  value={data.reference_urls?.[0] || ""}
                  onChange={(e) => updateField({ reference_urls: [e.target.value] })}
                />
                <ExternalLink className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
              </div>
              <p className="text-[10px] text-muted-foreground font-medium leading-normal">
                Hệ thống sẽ tự động cào cấu trúc dữ liệu sitemap khi chạy tiến trình tự động hóa tiếp theo.
              </p>
            </div>

          </div>
        </div>
      </section>

      {/* ── MODAL 1: ĐỒNG BỘ RAG PIPELINE ── */}
      <Dialog open={!!syncOpen} onOpenChange={(open) => navigate({ search: (prev) => ({ ...prev, syncOpen: open ? true : undefined }) })}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold">Kích hoạt Auto-Sync từ RAG</DialogTitle>
            <DialogDescription className="text-xs">
              Hệ thống quét Vector DB qua từ khóa, tự động phân tích cấu trúc cấu hình và ghi đè thẳng vào SQLite.
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center space-x-2 pt-2">
            <Input
              value={searchParamQ}
              onChange={(e) => navigate({ search: (prev) => ({ ...prev, q: e.target.value }) })}
              placeholder="Ví dụ: guideline, campaign brief..." className="h-9 text-xs"
            />
            <Button size="sm" disabled={syncMutation.isPending} onClick={() => syncMutation.mutate(searchParamQ)}>
              {syncMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Quét ngay"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ── MODAL 2: XEM TRƯỚC RAG CONTEXT PREVIEW ── */}
      <Dialog open={!!previewOpen} onOpenChange={(open) => navigate({ search: (prev) => ({ ...prev, previewOpen: open ? true : undefined }) })}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold">RAG Context Preview</DialogTitle>
            <DialogDescription className="text-xs">
              Cấu trúc JSON thô payload sẽ được truyền thẳng vào Prompt Engine khi sinh Banner/Video.
            </DialogDescription>
          </DialogHeader>
          <div className="pt-2">
            <pre className="bg-muted text-slate-800 border rounded-lg p-3 text-[10px] font-mono overflow-auto max-h-72 whitespace-pre-wrap leading-relaxed">
              {JSON.stringify({ brand_identity_context: data }, null, 2)}
            </pre>
          </div>
          <Button variant="secondary" size="sm" className="w-full mt-2" onClick={() => navigate({ search: (prev) => ({ ...prev, previewOpen: undefined }) })}>
            Đóng bảng xem trước
          </Button>
        </DialogContent>
      </Dialog>

    </div>
  );
}

// Helper component xử lý loading icon nội bộ chống crash
function Loader2({ className, ...props }: React.ComponentProps<"svg">) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`animate-spin ${className}`} {...props}>
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}