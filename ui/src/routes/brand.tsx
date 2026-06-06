/**
 * ScreenBrandVoice — Redesigned with P0 Audit Fixes
 * • Clean title ("Brand Engine" 1 line)
 * • Sticky save: bottom on mobile, top-right on desktop
 * • Collapsible sections with clear 1-2-3-4-5 numbering
 * • Simplified top bar (Save + Menu only)
 * • Integrated with async backend core & TanStack Query
 */

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  ChevronDown,
  ChevronRight,
  Save,
  MoreVertical,
  X,
  Loader2,
} from "lucide-react";

// ─── Shadcn UI Components ───────────────────────────────────────────────────
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { API_BASE } from "@/config";

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

const DEFAULT_BRAND_ID = "default-brand-uuid-001";

const COMPONENT_DEFAULT_DATA: BrandProfileSchema = {
  positioning:
    "Hệ thống AI Marketing tự động hóa chuỗi cung ứng nội dung cho doanh nghiệp.",
  audience: "SMEs, Chủ shop online, Marketers tại Việt Nam",
  brand_voice_rules: {
    forbidden_words: ["cam kết 100%", "tuyệt đối"],
    tone_patterns: ["Thân thiện", "Chuyên nghiệp"],
    cta_patterns: [
      "Trải nghiệm ngay hôm nay!",
      "Khám phá giải pháp tối ưu cho doanh nghiệp",
    ],
  },
  messaging: {
    pain_points: ["Tiết kiệm 80% thời gian design", "Đồng bộ nhận diện 100% các kênh"],
    objections: [
      {
        objection: "Giá cao?",
        counter: "Tiết kiệm nhân sự vận hành lâu dài",
      },
    ],
    proof_points: ["Hơn 12 năm kinh nghiệm lập trình hệ thống web production"],
  },
  content_examples: {
    blog_post: null,
    social_post:
      "Chào anh em, hệ thống Content Factory đã chính thức tích hợp luồng Crawl4AI cực mượt...",
    ad_copy: null,
    landing_page: null,
  },
  visual_identity: {
    style_description: "A24 Cinematic Aesthetic, đắt tiền, tối giản, tương phản cao",
    color_palette: ["#4F46E5", "#10B981", "#F59E0B"],
    mood: "Expensive Silence",
  },
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
    rawTextContent,
  } = Route.useSearch();

  const [expanded, setExpanded] = useState<Record<number, boolean>>({
  1: false,
  2: false,
  3: false,
  4: false,
  5: false,
});

  const [lastSaved, setLastSaved] = useState<string | null>(null);

  // ── TanStack Query (Fetch profile from Async DB) ──────────────────────────
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
      queryClient.invalidateQueries({
        queryKey: brandProfileKeys.detail(DEFAULT_BRAND_ID),
      });
      setLastSaved("now");
      setTimeout(() => setLastSaved(null), 2000);
    },
  });

  const mineMutation = useMutation({
    mutationFn: async () => {
      const params = new URLSearchParams({
        brand_name: brandName || "New Brand",
        document_type: documentType,
      });
      if (websiteUrl) params.append("website_url", websiteUrl);
      if (rawTextContent) params.append("raw_text_content", rawTextContent);

      const res = await fetch(
        `${API_BASE}/brand-profile/mine?${params.toString()}`,
        {
          method: "POST",
        }
      );
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Lỗi khai phá RAG");
      }
      const dataJson = await res.json();
      return dataJson.draft_profile as BrandProfileSchema;
    },
    onSuccess: (minedDraft) => {
      queryClient.setQueryData(
        brandProfileKeys.detail(DEFAULT_BRAND_ID),
        minedDraft
      );
      navigate({ search: (prev: any): any => ({ ...prev, syncOpen: undefined }) } as any);
    },
    onError: (error: any) => {
      alert(`Thất bại: ${error.message}`);
    },
  });

  if (isLoading || !data) {
    return (
      <div className="flex items-center justify-center py-32 gap-2 text-muted-foreground text-xs font-medium">
        <Loader2 className="w-4 h-4 animate-spin" /> Đang đồng bộ cấu hình...
      </div>
    );
  }

  const updateField = (patch: Partial<BrandProfileSchema>) => {
    queryClient.setQueryData(brandProfileKeys.detail(DEFAULT_BRAND_ID), {
      ...data,
      ...patch,
    });
  };

  const updateNestedField = (block: keyof BrandProfileSchema, patch: any) => {
    queryClient.setQueryData(brandProfileKeys.detail(DEFAULT_BRAND_ID), {
      ...data,
      [block]: { ...(data[block] as object), ...patch },
    });
  };

  const toggleSection = (id: number) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // ─── Section Component ──────────────────────────────────────────────────────
  const Section = ({
    id,
    title,
    children,
  }: {
    id: number;
    title: string;
    children: React.ReactNode;
  }) => (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
      <button
        onClick={() => toggleSection(id)}
        className="w-full flex items-center gap-3 px-5 py-4 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
      >
        {expanded[id as keyof typeof expanded] ? (
          <ChevronDown size={18} className="text-slate-600 dark:text-slate-400 flex-shrink-0" />
        ) : (
          <ChevronRight size={18} className="text-slate-600 dark:text-slate-400 flex-shrink-0" />
        )}
        <div className="flex items-baseline gap-3 text-left">
          <span className="text-xs font-bold text-slate-500 dark:text-slate-400 font-mono">
            {id}.
          </span>
          <h3 className="font-medium text-slate-900 dark:text-slate-100 text-sm">
            {title}
          </h3>
        </div>
      </button>

      {expanded[id as keyof typeof expanded] && (
        <div className="px-5 py-4 border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 space-y-4">
          {children}
        </div>
      )}
    </div>
  );

  // ─── Tag Input Component ────────────────────────────────────────────────────
  const TagInput = ({
    tags,
    onAdd,
    onRemove,
    placeholder,
    variant = "outline",
  }: {
    tags: string[];
    onAdd: (tag: string) => void;
    onRemove: (index: number) => void;
    placeholder: string;
    variant?: "outline" | "destructive" | "secondary";
  }) => (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {tags.map((tag, i) => (
          <Badge
            key={i}
            variant={variant}
            className="text-xs font-medium pl-2.5 pr-1.5 py-0.5"
          >
            {tag}
            <button
              type="button"
              className="ml-1.5 rounded-full hover:opacity-70"
              onClick={() => onRemove(i)}
            >
              <X className="w-2.5 h-2.5" />
            </button>
          </Badge>
        ))}
      </div>
      <Input
        placeholder={placeholder}
        className="h-8 text-xs"
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

  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 flex flex-col">
      {/* ── STICKY HEADER (Desktop: Top-right Save + Menu) ── */}
      <div className="sticky top-0 z-20 bg-white dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div>
          
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Quản lý ngữ cảnh cho Multi-Agent
            </p>
          </div>

          <div className="hidden sm:flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-9 text-xs"
              onClick={() =>
                navigate({ search: (prev: any) => ({ ...prev, previewOpen: true }) } as any)
              }
            >
              Preview JSON
            </Button>
            <Button
              variant="secondary"
              size="sm"
              className="h-9 text-xs"
              onClick={() =>
                navigate({ search: (prev: any) => ({ ...prev, syncOpen: true }) } as any)
              }
            >
              Mine Data
            </Button>
            <Button
              size="sm"
              className="h-9 text-xs font-semibold"
              disabled={saveMutation.isPending}
              onClick={() => saveMutation.mutate(data)}
            >
              {saveMutation.isPending && (
                <Loader2 className="w-3 h-3 animate-spin mr-1" />
              )}
              <Save className="w-4 h-4 mr-1" />
              Save
            </Button>
            <Button variant="ghost" size="sm" className="h-9 px-2">
              <MoreVertical className="w-4 h-4" />
            </Button>
          </div>

          {/* Mobile Menu */}
          <div className="sm:hidden flex items-center gap-1">
            <Button variant="ghost" size="sm" className="h-8 px-2">
              <MoreVertical className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* ── MAIN CONTENT ── */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 pb-32 sm:pb-8 space-y-4">
          {/* Page Intro */}
          <div className="mb-8">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Define how AI agents speak, write, and convert for your brand.
            </p>
          </div>

          {/* ─── Section 1: Voice & Tone ─── */}
          <Section id={1} title="Voice & Tone">
            <div className="space-y-5">
              <div>
                <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 block">
                  Positioning
                </Label>
                <Textarea
                  rows={2}
                  value={data.positioning || ""}
                  onChange={(e) => updateField({ positioning: e.target.value })}
                  placeholder="Define your core brand positioning..."
                  className="text-xs font-medium"
                />
              </div>

              <div>
                <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-3 block">
                  Tone Patterns
                </Label>
                <TagInput
                  tags={data.brand_voice_rules?.tone_patterns || []}
                  onAdd={(tag) =>
                    updateNestedField("brand_voice_rules", {
                      tone_patterns: [
                        ...(data.brand_voice_rules?.tone_patterns || []),
                        tag,
                      ],
                    })
                  }
                  onRemove={(idx) =>
                    updateNestedField("brand_voice_rules", {
                      tone_patterns: data.brand_voice_rules.tone_patterns.filter(
                        (_, j) => j !== idx
                      ),
                    })
                  }
                  placeholder="Add tone descriptor + Enter..."
                  variant="outline"
                />
              </div>

              <div>
                <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-3 block">
                  Forbidden Words
                </Label>
                <TagInput
                  tags={data.brand_voice_rules?.forbidden_words || []}
                  onAdd={(tag) =>
                    updateNestedField("brand_voice_rules", {
                      forbidden_words: [
                        ...(data.brand_voice_rules?.forbidden_words || []),
                        tag,
                      ],
                    })
                  }
                  onRemove={(idx) =>
                    updateNestedField("brand_voice_rules", {
                      forbidden_words: data.brand_voice_rules.forbidden_words.filter(
                        (_, j) => j !== idx
                      ),
                    })
                  }
                  placeholder="Add forbidden word + Enter..."
                  variant="destructive"
                />
              </div>
            </div>
          </Section>

          {/* ─── Section 2: Messaging ─── */}
          <Section id={2} title="Messaging Architecture">
            <div className="space-y-5">
              <div>
                <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-3 block">
                  Pain Points
                </Label>
                <TagInput
                  tags={data.messaging?.pain_points || []}
                  onAdd={(tag) =>
                    updateNestedField("messaging", {
                      pain_points: [...(data.messaging?.pain_points || []), tag],
                    })
                  }
                  onRemove={(idx) =>
                    updateNestedField("messaging", {
                      pain_points: data.messaging.pain_points.filter(
                        (_, j) => j !== idx
                      ),
                    })
                  }
                  placeholder="Add customer pain point + Enter..."
                  variant="secondary"
                />
              </div>

              <div>
                <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-3 block">
                  Proof Points
                </Label>
                <TagInput
                  tags={data.messaging?.proof_points || []}
                  onAdd={(tag) =>
                    updateNestedField("messaging", {
                      proof_points: [
                        ...(data.messaging?.proof_points || []),
                        tag,
                      ],
                    })
                  }
                  onRemove={(idx) =>
                    updateNestedField("messaging", {
                      proof_points: data.messaging.proof_points.filter(
                        (_, j) => j !== idx
                      ),
                    })
                  }
                  placeholder="Add proof point + Enter..."
                  variant="secondary"
                />
              </div>
            </div>
          </Section>

          {/* ─── Section 3: Visual Identity ─── */}
          <Section id={3} title="Visual Identity">
            <div className="space-y-5">
              <div>
                <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 block">
                  Style Description
                </Label>
                <Input
                  value={data.visual_identity?.style_description || ""}
                  onChange={(e) =>
                    updateNestedField("visual_identity", {
                      style_description: e.target.value,
                    })
                  }
                  placeholder="E.g., Ultra-realistic, cinematic, high contrast..."
                  className="h-9 text-xs"
                />
              </div>

              <div>
                <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 block">
                  Mood
                </Label>
                <Input
                  value={data.visual_identity?.mood || ""}
                  onChange={(e) =>
                    updateNestedField("visual_identity", { mood: e.target.value })
                  }
                  placeholder="E.g., Luxurious, minimalist, energetic..."
                  className="h-9 text-xs"
                />
              </div>

              <div>
                <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-3 block">
                  Color Palette
                </Label>
                <div className="flex flex-wrap gap-2 mb-3">
                  {(data.visual_identity?.color_palette || []).map((hex, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 px-2 py-1 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
                    >
                      <div
                        style={{ backgroundColor: hex }}
                        className="w-5 h-5 rounded border border-slate-300 dark:border-slate-600"
                      />
                      <span className="text-xs font-mono text-slate-600 dark:text-slate-400">
                        {hex}
                      </span>
                      <button
                        type="button"
                        className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                        onClick={() =>
                          updateNestedField("visual_identity", {
                            color_palette: data.visual_identity.color_palette.filter(
                              (_, j) => j !== i
                            ),
                          })
                        }
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
                <Input
                  placeholder="#HEX + Enter"
                  className="h-8 text-xs max-w-xs"
                  onKeyDown={(e) => {
                    const el = e.currentTarget;
                    if (e.key === "Enter" && el.value.startsWith("#")) {
                      updateNestedField("visual_identity", {
                        color_palette: [
                          ...(data.visual_identity?.color_palette || []),
                          el.value.trim(),
                        ],
                      });
                      el.value = "";
                    }
                  }}
                />
              </div>
            </div>
          </Section>

          {/* ─── Section 4: Audience & CTA ─── */}
          <Section id={4} title="Audience & Conversion">
            <div className="space-y-5">
              <div>
                <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 block">
                  Target Audience
                </Label>
                <Textarea
                  rows={2}
                  value={data.audience || ""}
                  onChange={(e) => updateField({ audience: e.target.value })}
                  placeholder="Describe your target audience..."
                  className="text-xs font-medium"
                />
              </div>

              <div>
                <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-3 block">
                  CTA Patterns
                </Label>
                <TagInput
                  tags={data.brand_voice_rules?.cta_patterns || []}
                  onAdd={(tag) =>
                    updateNestedField("brand_voice_rules", {
                      cta_patterns: [
                        ...(data.brand_voice_rules?.cta_patterns || []),
                        tag,
                      ],
                    })
                  }
                  onRemove={(idx) =>
                    updateNestedField("brand_voice_rules", {
                      cta_patterns: data.brand_voice_rules.cta_patterns.filter(
                        (_, j) => j !== idx
                      ),
                    })
                  }
                  placeholder="Add CTA structure + Enter..."
                  variant="outline"
                />
              </div>
            </div>
          </Section>

          {/* ─── Section 5: Content Examples ─── */}
          <Section id={5} title="Content Examples">
            <div className="space-y-5">
              <div>
                <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 block">
                  Social Post Example
                </Label>
                <Textarea
                  rows={3}
                  value={data.content_examples?.social_post || ""}
                  onChange={(e) =>
                    updateNestedField("content_examples", {
                      social_post: e.target.value,
                    })
                  }
                  placeholder="Paste your brand voice example..."
                  className="text-xs font-mono"
                />
              </div>

              <div>
                <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 block">
                  Blog Post Example
                </Label>
                <Textarea
                  rows={3}
                  value={data.content_examples?.blog_post || ""}
                  onChange={(e) =>
                    updateNestedField("content_examples", {
                      blog_post: e.target.value,
                    })
                  }
                  placeholder="Paste blog content example..."
                  className="text-xs font-mono"
                />
              </div>

              <div>
                <Label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 block">
                  Ad Copy Example
                </Label>
                <Textarea
                  rows={2}
                  value={data.content_examples?.ad_copy || ""}
                  onChange={(e) =>
                    updateNestedField("content_examples", { ad_copy: e.target.value })
                  }
                  placeholder="Paste ad copy example..."
                  className="text-xs font-mono"
                />
              </div>
            </div>
          </Section>
        </div>
      </div>

      {/* ── STICKY BOTTOM SAVE BAR (Mobile) ── */}
      <div className="sm:hidden fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 px-4 py-4">
        <Button
          size="lg"
          className="w-full font-semibold"
          disabled={saveMutation.isPending}
          onClick={() => saveMutation.mutate(data)}
        >
          {saveMutation.isPending && (
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
          )}
          <Save className="w-4 h-4 mr-2" />
          Save Changes
        </Button>
        <div className="flex items-center justify-between mt-3 text-xs">
          <button
            onClick={() =>
              navigate({ search: ((prev) => ({ ...prev, syncOpen: true })) as any })
            }
            className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
          >
            Mine Data
          </button>
          <button
            onClick={() =>
              navigate({ search: ((prev) => ({ ...prev, previewOpen: true })) as any })
            }
            className="text-slate-500 dark:text-slate-400 hover:underline"
          >
            Preview JSON
          </button>
          <span className="text-slate-400 dark:text-slate-500">
            {lastSaved === "now" ? "Saved!" : ""}
          </span>
        </div>
      </div>

      {/* ── MODAL 1: MINE DATA ── */}
      <Dialog
        open={!!syncOpen}
        onOpenChange={(open) =>
          navigate({
            search: ((prev) => ({ ...prev, syncOpen: open ? true : undefined })) as any,
          })
        }
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold">Mine Brand Data</DialogTitle>
            <DialogDescription className="text-xs">
              Extract brand context from various sources using Groq JSON Mode.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 pt-2">
            <div className="space-y-1">
              <Label className="text-xs font-semibold">Brand Name</Label>
              <Input
                value={brandName}
                onChange={(e) =>
                  navigate({
                    search: ((prev) => ({ ...prev, brandName: e.target.value })) as any,
                  })
                }
                placeholder="E.g., Holo AI, VinFast..."
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Document Type</Label>
              <Select
                value={documentType}
                onValueChange={(val) =>
                  navigate({
                    search: ((prev) => ({ ...prev, documentType: val })) as any,
                  })
                }
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="Select document type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="brand_guideline">Brand Guideline</SelectItem>
                  <SelectItem value="competitor_analysis">Competitor Analysis</SelectItem>
                  <SelectItem value="product_brief">Product Brief</SelectItem>
                  <SelectItem value="campaign_brief">Campaign Brief</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Website URL</Label>
              <Input
                value={websiteUrl}
                onChange={(e) =>
                  navigate({
                    search: ((prev) => ({ ...prev, websiteUrl: e.target.value })) as any,
                  })
                }
                placeholder="https://example.com..."
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Raw Text Content</Label>
              <Textarea
                rows={3}
                value={rawTextContent}
                onChange={(e) =>
                    navigate({
                      search: ((prev: any) => ({ ...prev, rawTextContent: e.target.value })) as any
                    })
                  }
                placeholder="Paste brand guideline or content..."
                className="text-xs"
              />
            </div>

            <Button
              className="w-full h-9 text-xs font-bold"
              disabled={mineMutation.isPending}
              onClick={() => mineMutation.mutate()}
            >
              {mineMutation.isPending && (
                <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
              )}
              Extract & Import
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ── MODAL 2: PREVIEW PAYLOAD ── */}
      <Dialog
        open={!!previewOpen}
        onOpenChange={(open) =>
          navigate({
            search: ((prev) => ({ ...prev, previewOpen: open ? true : undefined })) as any,
          })
        }
      >
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold">
              Payload Preview
            </DialogTitle>
            <DialogDescription className="text-xs">
              JSON structure ready for agent processing.
            </DialogDescription>
          </DialogHeader>
          <div className="pt-2">
            <pre className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-3 text-[10px] font-mono overflow-auto max-h-96 whitespace-pre-wrap leading-relaxed">
              {JSON.stringify(
                { active_brand_profile_blueprint: data },
                null,
                2
              )}
            </pre>
          </div>
          <Button
            variant="secondary"
            size="sm"
            className="w-full mt-2"
            onClick={() =>
              navigate({
                search: ((prev) => ({ ...prev, previewOpen: undefined })) as any,
              })
            }
          >
            Close
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}