/**
 * ScreenBrandVoice — Notion-style Single Stream (No Cards)
 * INTEGRATED WITH ASYNC BACKEND CORE & DYNAMIC DOCUMENT TYPE SELECTION
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import SidebarNav from "@/layout/navbar";

const API_BASE = "http://localhost:8000/api/v1";
const brandProfileKeys = {
  detail: (brandId: string) => ["brand-profile", "detail", brandId] as const,
};

// ─── Types Matched With Backend Schema ───────────────────────────────────────
export interface BrandVoiceRules {
  forbidden_words: string[];
  tone_patterns: string[];
  cta_patterns: string[];
}

export interface BrandMessaging {
  pain_points: string[];
  objections: { objection: string; counter: string; }[];
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

const DEFAULT_BRAND_ID = "default-brand-uuid-001"; // Thay bằng brand_id thực tế từ context/route params của anh

const COMPONENT_DEFAULT_DATA: BrandProfileSchema = {
  positioning: "Hệ thống AI Marketing tự động hóa chuỗi cung ứng nội dung cho doanh nghiệp.",
  audience: "SMEs, Chủ shop online, Marketers tại Việt Nam",
  brand_voice_rules: {
    forbidden_words: ["cam kết 100%", "tuyệt đối"],
    tone_patterns: ["Thân thiện", "Chuyên nghiệp"],
    cta_patterns: ["Trải nghiệm ngay hôm nay!", "Khám phá giải pháp tối ưu cho doanh nghiệp"],
  },
  messaging: {
    pain_points: ["Tiết kiệm 80% thời gian design", "Đồng bộ nhận diện 100% các kênh"],
    objections: [{ objection: "Giá cao?", counter: "Tiết kiệm nhân sự vận hành lâu dài" }],
    proof_points: ["Hơn 12 năm kinh nghiệm lập trình hệ thống web production"],
  },
  content_examples: {
    blog_post: null,
    social_post: "Chào anh em, hệ thống Content Factory đã chính thức tích hợp luồng Crawl4AI cực mượt...",
    ad_copy: null,
    landing_page: null,
  },
  visual_identity: {
    style_description: "A24 Cinematic Aesthetic, đắt tiền, tối giản, tương phản cao",
    color_palette: ["#4F46E5", "#10B981", "#F59E0B"],
    mood: "Expensive Silence",
  }
};

// ─── Route Definition ────────────────────────────────────────────────────────
export const Route = createFileRoute("/brand")({
  validateSearch: (search: Record<string, unknown>) => ({
    syncOpen: (search.syncOpen as boolean) || undefined,
    previewOpen: (search.previewOpen as boolean) || undefined,
    documentType: (search.documentType as string) || "brand_guideline",
    brandName: (search.brandName as string) || "",
    websiteUrl: (search.websiteUrl as string) || "",
    rawTextContent: (search.rawTextContent as string) || "",
  }),
  component: ScreenBrandVoice,
});

export function ScreenBrandVoice() {
  const queryClient = useQueryClient();
  const navigate = useNavigate({ from: Route.fullPath });
  const { 
    syncOpen, 
    previewOpen, 
    documentType, 
    brandName, 
    websiteUrl, 
    rawTextContent 
  } = Route.useSearch();

  // ── TanStack Query (Lấy profile tổng từ Async DB) ──────────────────────────
  const { data, isLoading } = useQuery<BrandProfileSchema>({
    queryKey: brandProfileKeys.detail(DEFAULT_BRAND_ID),
    queryFn: async () => {
      try {
        const res = await fetch(`${API_BASE}/brand-profile/${DEFAULT_BRAND_ID}`);
        if (!res.ok) throw new Error();
        return await res.json();
      } catch {
        return COMPONENT_DEFAULT_DATA;
      }
    },
    staleTime: 5 * 60 * 1000,
  });

  // ── Mutations ──────────────────────────────────────────────────────────────
  // 1. Ghi đè cấu hình xuống database thông qua Bulk Save
  const saveMutation = useMutation({
    mutationFn: async (payload: BrandProfileSchema) => {
      const res = await fetch(`${API_BASE}/brand-profile/${DEFAULT_BRAND_ID}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return await res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: brandProfileKeys.detail(DEFAULT_BRAND_ID) });
    },
  });

  // 2. Kích hoạt bóc tách bằng Groq JSON Mode + Tag Document Type động
  const mineMutation = useMutation({
    mutationFn: async () => {
      const params = new URLSearchParams({
        brand_name: brandName || "New Brand",
        document_type: documentType,
      });
      if (websiteUrl) params.append("website_url", websiteUrl);
      if (rawTextContent) params.append("raw_text_content", rawTextContent);

      const res = await fetch(`${API_BASE}/brand-profile/mine?${params.toString()}`, {
        method: "POST",
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Lỗi khai phá RAG");
      }
      const dataJson = await res.json();
      return dataJson.draft_profile as BrandProfileSchema;
    },
    onSuccess: (minedDraft) => {
      queryClient.setQueryData(brandProfileKeys.detail(DEFAULT_BRAND_ID), minedDraft);
      navigate({ search: (prev) => ({ ...prev, syncOpen: undefined }) });
    },
    onError: (error: any) => {
      alert(`Thất bại: ${error.message}`);
    }
  });

  if (isLoading || !data) {
    return (
      <div className="flex items-center justify-center py-32 gap-2 text-muted-foreground text-xs font-medium">
        <Loader2 className="w-4 h-4 animate-spin text-primary" /> Đang đồng bộ cấu hình Brand Engine...
      </div>
    );
  }

  const updateField = (patch: Partial<BrandProfileSchema>) => {
    queryClient.setQueryData(brandProfileKeys.detail(DEFAULT_BRAND_ID), { ...data, ...patch });
  };

  const updateNestedField = (block: keyof BrandProfileSchema, patch: any) => {
    queryClient.setQueryData(brandProfileKeys.detail(DEFAULT_BRAND_ID), {
      ...data,
      [block]: { ...(data[block] as object), ...patch }
    });
  };

  return (
  <div className="flex">
    <SidebarNav />
   <div className="min-h-full">
     <div className="max-w-3xl mx-auto px-4 py-8 space-y-12 bg-background text-foreground antialiased">
      
      {/* ── STICKY TOP BAR ── */}
      <div className="sticky top-0 bg-background/90 backdrop-blur-md z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-muted">
        <div>
          <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
            <Volume2 className="w-5 h-5 text-primary" /> Brand Context Orchestrator
          </h1>
          <p className="text-xs text-muted-foreground mt-1">Quản lý ngữ cảnh phẳng cho Multi-Agent: Writer, Designer, Ads, Landing-Page.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="h-8 text-xs text-muted-foreground" onClick={() => queryClient.setQueryData(brandProfileKeys.detail(DEFAULT_BRAND_ID), COMPONENT_DEFAULT_DATA)}>
            <RotateCcw className="w-3.5 h-3.5 mr-1" /> Mặc định
          </Button>
          <Button variant="ghost" size="sm" className="h-8 text-xs text-muted-foreground" onClick={() => navigate({ search: (prev) => ({ ...prev, previewOpen: true }) })}>
            <Eye className="w-3.5 h-3.5 mr-1" /> Payload JSON
          </Button>
          <Button variant="secondary" size="sm" className="h-8 text-xs font-semibold" onClick={() => navigate({ search: (prev) => ({ ...prev, syncOpen: true }) })}>
            <Search className="w-3.5 h-3.5 mr-1" /> Khai phá RAG (Groq)
          </Button>
          <Button size="sm" className="h-8 text-xs font-semibold px-4 shadow-sm" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate(data)}>
            {saveMutation.isPending && <Loader2 className="w-3 h-3 animate-spin mr-1" />}
            Lưu DB
          </Button>
        </div>
      </div>

      {/* ── BLOCK 1: TONE OF VOICE & RULES ── */}
      <section className="space-y-4">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-bold text-primary font-mono">01.</span>
          <h2 className="text-base font-bold tracking-tight">Giọng văn & Định hướng thương hiệu (Writer / Ads Scope)</h2>
        </div>
        
        <div className="pl-6 space-y-4">
          <div className="space-y-2">
            <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Định vị cốt lõi (Positioning)</Label>
            <Textarea
              rows={2} value={data.positioning || ""}
              onChange={(e) => updateField({ positioning: e.target.value })}
              placeholder="Nhập định vị một dòng để Agent không bị lầm đường lạc lối..." className="text-xs font-medium leading-relaxed"
            />
          </div>

          <div className="space-y-2 pt-1">
            <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Tone mẫu được duyệt (Tone Patterns)</Label>
            <div className="flex flex-wrap gap-1.5">
              {(data.brand_voice_rules?.tone_patterns || []).map((tone, i) => (
                <Badge key={i} variant="outline" className="text-xs font-medium pl-2.5 pr-1.5 py-0.5 border-slate-200 bg-slate-50 text-slate-600 rounded-md">
                  {tone}
                  <button type="button" className="ml-1.5 p-0.5 rounded-full text-slate-400 hover:text-slate-600" 
                    onClick={() => updateNestedField("brand_voice_rules", { tone_patterns: data.brand_voice_rules.tone_patterns.filter((_, j) => j !== i) })}>
                    <X className="w-2.5 h-2.5" />
                  </button>
                </Badge>
              ))}
            </div>
            <Input
              placeholder="Thêm Tone descriptor + Enter..." className="h-8 text-xs max-w-md"
              onKeyDown={(e) => {
                const el = e.currentTarget;
                if (e.key === "Enter" && el.value.trim()) {
                  updateNestedField("brand_voice_rules", { tone_patterns: [...(data.brand_voice_rules?.tone_patterns || []), el.value.trim()] });
                  el.value = "";
                }
              }}
            />
          </div>

          <div className="space-y-2 pt-1">
            <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider text-red-500">Từ ngữ cấm sử dụng (Forbidden Words)</Label>
            <div className="flex flex-wrap gap-1.5">
              {(data.brand_voice_rules?.forbidden_words || []).map((word, i) => (
                <Badge key={i} variant="destructive" className="text-xs font-medium pl-2.5 pr-1.5 py-0.5 rounded-md">
                  {word}
                  <button type="button" className="ml-1.5 p-0.5 rounded-full text-white/70 hover:text-white" 
                    onClick={() => updateNestedField("brand_voice_rules", { forbidden_words: data.brand_voice_rules.forbidden_words.filter((_, j) => j !== i) })}>
                    <X className="w-2.5 h-2.5" />
                  </button>
                </Badge>
              ))}
            </div>
            <Input
              placeholder="Thêm từ cấm kị khi viết bài + Enter..." className="h-8 text-xs max-w-md border-red-200 focus-visible:ring-red-400"
              onKeyDown={(e) => {
                const el = e.currentTarget;
                if (e.key === "Enter" && el.value.trim()) {
                  updateNestedField("brand_voice_rules", { forbidden_words: [...(data.brand_voice_rules?.forbidden_words || []), el.value.trim()] });
                  el.value = "";
                }
              }}
            />
          </div>
        </div>
      </section>

      {/* ── BLOCK 2: MESSAGING ARCHITECTURE ── */}
      <section className="space-y-4 pt-2 border-t border-muted">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-bold text-primary font-mono">02.</span>
          <h2 className="text-base font-bold tracking-tight">Cấu trúc thông điệp & Điểm chạm khách hàng (Messaging)</h2>
        </div>

        <div className="pl-6 space-y-4">
          <div className="space-y-2">
            <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Nỗi đau của khách hàng (Pain Points)</Label>
            <div className="flex flex-wrap gap-1.5">
              {(data.messaging?.pain_points || []).map((pain, i) => (
                <Badge key={i} variant="secondary" className="text-xs font-medium pl-2.5 pr-1.5 py-0.5 rounded-md">
                  {pain}
                  <button type="button" className="ml-1.5 text-slate-400 hover:text-slate-600" 
                    onClick={() => updateNestedField("messaging", { pain_points: data.messaging.pain_points.filter((_, j) => j !== i) })}>
                    <X className="w-2.5 h-2.5" />
                  </button>
                </Badge>
              ))}
            </div>
            <Input
              placeholder="Nhập vấn đề khách hàng đang gặp phải + Enter..." className="h-8 text-xs max-w-md"
              onKeyDown={(e) => {
                const el = e.currentTarget;
                if (e.key === "Enter" && el.value.trim()) {
                  updateNestedField("messaging", { pain_points: [...(data.messaging?.pain_points || []), el.value.trim()] });
                  el.value = "";
                }
              }}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Bằng chứng thuyết phục (Proof Points)</Label>
            <div className="space-y-1">
              {(data.messaging?.proof_points || []).map((proof, i) => (
                <div key={i} className="flex items-center gap-2 text-xs font-medium text-slate-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                  <span className="flex-1">{proof}</span>
                  <button type="button" className="text-muted-foreground hover:text-destructive"
                    onClick={() => updateNestedField("messaging", { proof_points: data.messaging.proof_points.filter((_, j) => j !== i) })}>
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
            <Input
              placeholder="Thêm số liệu chứng minh uy tín + Enter..." className="h-8 text-xs max-w-md"
              onKeyDown={(e) => {
                const el = e.currentTarget;
                if (e.key === "Enter" && el.value.trim()) {
                  updateNestedField("messaging", { proof_points: [...(data.messaging?.proof_points || []), el.value.trim()] });
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
          <h2 className="text-base font-bold tracking-tight">Hệ thống nhận diện hình ảnh (Designer Scope / ComfyUI Node)</h2>
        </div>

        <div className="pl-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Đặc tả phong cách Prompt (Style Description)</Label>
              <Input
                value={data.visual_identity?.style_description || ""}
                onChange={(e) => updateNestedField("visual_identity", { style_description: e.target.value })}
                className="h-8 text-xs text-primary font-medium"
                placeholder="Ví dụ: Ultra-realistic photograph, 8k resolution..."
              />
            </div>

            <div className="space-y-2">
              <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Aesthetic Mood</Label>
              <Input
                value={data.visual_identity?.mood || ""}
                onChange={(e) => updateNestedField("visual_identity", { mood: e.target.value })}
                className="h-8 text-xs text-slate-700 font-medium"
                placeholder="Ví dụ: Dark moody cinematic..."
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Mã màu hex cốt lõi</Label>
            <div className="flex items-center gap-2">
              {(data.visual_identity?.color_palette || []).map((hex, i) => (
                <div key={i} className="flex items-center gap-1.5 border border-muted rounded px-2 py-1 bg-slate-50">
                  <div style={{ backgroundColor: hex }} className="w-3.5 h-3.5 rounded shadow-inner" />
                  <span className="text-xs font-mono text-slate-500">{hex}</span>
                  <button type="button" className="text-slate-400 hover:text-slate-600 ml-1"
                    onClick={() => updateNestedField("visual_identity", { color_palette: data.visual_identity.color_palette.filter((_, j) => j !== i) })}>
                    <X className="w-2.5 h-2.5" />
                  </button>
                </div>
              ))}
              <Input
                placeholder="#HEX + Enter" className="h-7 text-xs w-24 px-1.5"
                onKeyDown={(e) => {
                  const el = e.currentTarget;
                  if (e.key === "Enter" && el.value.trim().startsWith("#")) {
                    updateNestedField("visual_identity", { color_palette: [...(data.visual_identity?.color_palette || []), el.value.trim()] });
                    el.value = "";
                  }
                }}
              />
            </div>
          </div>
        </div>
      </section>

      {/* ── BLOCK 4: AUDIENCE & CTA PATTERNS ── */}
      <section className="space-y-4 pt-2 border-t border-muted">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-bold text-primary font-mono">04.</span>
          <h2 className="text-base font-bold tracking-tight">Phân khúc mục tiêu & Chuyển đổi (Landing-Page Scope)</h2>
        </div>

        <div className="pl-6 space-y-4">
          <div className="space-y-2">
            <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Chân dung đối tượng thụ hưởng (Audience Target)</Label>
            <Input
              value={data.audience || ""}
              onChange={(e) => updateField({ audience: e.target.value })}
              className="text-xs font-medium"
              placeholder="Mô tả tệp khách hàng tiềm năng..."
            />
          </div>

          <div className="space-y-2">
            <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Cấu trúc Call to Action mẫu</Label>
            <div className="space-y-1">
              {(data.brand_voice_rules?.cta_patterns || []).map((cta, i) => (
                <div key={i} className="flex items-center justify-between py-1 px-2 border rounded bg-slate-50 text-xs text-slate-700 font-medium group">
                  <span>{cta}</span>
                  <Button size="icon" variant="ghost" className="w-5 h-5 text-muted-foreground hover:text-destructive" 
                    onClick={() => updateNestedField("brand_voice_rules", { cta_patterns: data.brand_voice_rules.cta_patterns.filter((_, j) => j !== i) })}>
                    <X className="w-3 h-3" />
                  </Button>
                </div>
              ))}
            </div>
            <Input
              placeholder="Thêm cấu trúc CTA kích thích chuyển đổi + Enter..." className="h-8 text-xs max-w-md"
              onKeyDown={(e) => {
                const el = e.currentTarget;
                if (e.key === "Enter" && el.value.trim()) {
                  updateNestedField("brand_voice_rules", { cta_patterns: [...(data.brand_voice_rules?.cta_patterns || []), el.value.trim()] });
                  el.value = "";
                }
              }}
            />
          </div>
        </div>
      </section>

      {/* ── BLOCK 5: CONTENT EXAMPLES SOURCE ── */}
      <section className="space-y-4 pt-2 border-t border-muted">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-bold text-primary font-mono">05.</span>
          <h2 className="text-base font-bold tracking-tight">Văn bản mẫu định hướng AI Generation (Content Blueprint)</h2>
        </div>

        <div className="pl-6 space-y-4">
          <div className="space-y-2">
            <Label className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Bài viết Social mẫu (Gán Context cho Social Agent)</Label>
            <Textarea
              rows={3} value={data.content_examples?.social_post || ""}
              onChange={(e) => updateNestedField("content_examples", { social_post: e.target.value })}
              placeholder="Dán bài viết mẫu chuẩn văn phong thương hiệu nhất của anh vào đây để Groq học theo..." className="text-xs font-mono"
            />
          </div>
        </div>
      </section>

      {/* ── MODAL 1: KHAI PHÁ VÀ PHÂN TAG ĐỘNG RAG PIPELINE ── */}
      <Dialog open={!!syncOpen} onOpenChange={(open) => navigate({ search: (prev) => ({ ...prev, syncOpen: open ? true : undefined }) })}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold flex items-center gap-2">🚀 Tiến trình Khai phá Thực thể RAG</DialogTitle>
            <DialogDescription className="text-xs">
              Nhập thông tin mồi. Lõi AI sử dụng Groq JSON Mode để bóc tách thông tin dựa trên phân loại tài liệu do client chọn.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-3 pt-2">
            <div className="space-y-1">
              <Label className="text-[10px] uppercase font-bold text-muted-foreground">Tên thương hiệu mục tiêu</Label>
              <Input
                value={brandName}
                onChange={(e) => navigate({ search: (prev) => ({ ...prev, brandName: e.target.value }) })}
                placeholder="Ví dụ: Holo AI, VinFast..." className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1">
              <Label className="text-[10px] uppercase font-bold text-muted-foreground">Client Phân Loại Tài Liệu (Document Type Tag)</Label>
              <Select
                value={documentType}
                onValueChange={(val) => navigate({ search: (prev) => ({ ...prev, documentType: val }) })}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="Chọn loại tài liệu" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="brand_guideline">📖 Brand Guideline (Cốt lõi)</SelectItem>
                  <SelectItem value="competitor_analysis">📊 Phân tích đối thủ (Competitor)</SelectItem>
                  <SelectItem value="product_brief">📦 Mô tả sản phẩm (Product Brief)</SelectItem>
                  <SelectItem value="campaign_brief">🎯 Kế hoạch chiến dịch marketing</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-[10px] uppercase font-bold text-muted-foreground">Đường dẫn Seed URL (Sử dụng Crawl4AI)</Label>
              <Input
                value={websiteUrl}
                onChange={(e) => navigate({ search: (prev) => ({ ...prev, websiteUrl: e.target.value }) })}
                placeholder="https://example.com/guideline" className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1">
              <Label className="text-[10px] uppercase font-bold text-muted-foreground">Văn bản thô tiêm vào hệ thống (Injected Content)</Label>
              <Textarea
                rows={3} value={rawTextContent}
                onChange={(e) => navigate({ search: (prev) => ({ ...prev, rawTextContent: e.target.value }) })}
                placeholder="Dán toàn bộ text guideline thô hoặc thông tin bóc tách thủ công..." className="text-xs"
              />
            </div>

            <Button className="w-full h-9 text-xs font-bold" disabled={mineMutation.isPending} onClick={() => mineMutation.mutate()}>
              {mineMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : "Khai phá dữ liệu & Đè cấu trúc"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ── MODAL 2: XEM TRƯỚC PAYLOAD TRUYỀN CHO AGENTS ── */}
      <Dialog open={!!previewOpen} onOpenChange={(open) => navigate({ search: (prev) => ({ ...prev, previewOpen: open ? true : undefined }) })}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold">RAG Engine Payload Preview</DialogTitle>
            <DialogDescription className="text-xs">
              Cấu trúc JSON thô hoàn thiện, sẵn sàng phân rã thành các Scope thích hợp ném vào Context Window của LLM.
            </DialogDescription>
          </DialogHeader>
          <div className="pt-2">
            <pre className="bg-muted text-slate-800 border rounded-lg p-3 text-[10px] font-mono overflow-auto max-h-80 whitespace-pre-wrap leading-relaxed">
              {JSON.stringify({ active_brand_profile_blueprint: data }, null, 2)}
            </pre>
          </div>
          <Button variant="secondary" size="sm" className="w-full mt-2" onClick={() => navigate({ search: (prev) => ({ ...prev, previewOpen: undefined }) })}>
            Đóng bảng cấu trúc
          </Button>
        </DialogContent>
      </Dialog>

    </div>
   </div>
  </div>
  );
}

function Loader2({ className, ...props }: React.ComponentProps<"svg">) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`animate-spin ${className}`} {...props}>
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}