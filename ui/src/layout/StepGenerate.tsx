"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Zap, Loader2, AlertCircle, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Switch } from "@/components/ui/switch";
import { type Template } from "./types";
import { API_BASE } from "@/config";
import { useSearch } from "@tanstack/react-router";

// ─── API CONFIG ───

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }

  return res.json();
}

// ─── RESPONSE TYPES ───

interface ClarificationOption {
  id: string;
  title: string;
  preview: string;
}

interface ClarificationResponse {
  status: "requires_clarification";
  clarification_type: "options" | "rewrite";
  message: string;
  options?: ClarificationOption[] | null;
}

interface QueuedResponse {
  session_id: string;
  status: "queued";
  message: string;
}

type StartResponse = ClarificationResponse | QueuedResponse;

// ─── ZOD SCHEMA ───
const formSchema = z.object({
  prompt: z.string().min(1, "Vui lòng nhập chủ đề"),
  length: z.enum(["short", "medium", "long"]),
  tone: z.enum(["professional", "friendly", "humorous"]),
  language: z.enum(["vi", "en"]),
  brandVoice: z.enum(["default", "custom"]),
  ragDocs: z.array(z.string()),
  framework: z.enum(["free", "aida", "pas"]),
  includeCta: z.boolean(),
});

type FormData = z.infer<typeof formSchema>;

// ─── TEMPLATE → GROUP/FUNCTION MAPPING ───
const TEMPLATE_MAP: Record<string, { group: "blog_web" | "email_sale" | "social_media"; function: string }> = {
  // Blog & Web
  "blog-post": { group: "blog_web", function: "blog_post" },
  "product-description": { group: "blog_web", function: "product_description" },
  "website-copy": { group: "blog_web", function: "website_copy" },
  "meta-seo": { group: "blog_web", function: "meta_seo" },
  "faq": { group: "blog_web", function: "faq" },
  // Email & Sale
  "email-marketing": { group: "email_sale", function: "email_marketing" },
  "sales-page": { group: "email_sale", function: "sales_page" },
  "product-launch": { group: "email_sale", function: "product_launch" },
  // Social Media
  "social-post": { group: "social_media", function: "social_post" },
  "caption-set": { group: "social_media", function: "caption_set" },
  "hashtag-set": { group: "social_media", function: "hashtag_set" },
};

interface Props {
  template: Template;
  onBack: () => void;
  onClose: () => void;
}

const RAG_DOCS_OPTIONS = [
  { value: "guideline", label: "Brand Guideline" },
  { value: "research", label: "Research Docs" },
  { value: "product", label: "Product Info" },
];

export function StepGenerate({ template, onBack, onClose }: Props) {
  const queryClient = useQueryClient();
  const [lastFormData, setLastFormData] = useState<FormData | null>(null);
  const search = useSearch({ strict: false });
  const brandId = (search as Record<string, string>).brand;

  const [clarification, setClarification] = useState<{
    type: "options" | "rewrite";
    message: string;
    options?: ClarificationOption[];
  } | null>(null);

  // ─── REACT HOOK FORM ───
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      prompt: "",
      length: "medium",
      tone: "professional",
      language: "vi",
      brandVoice: "default",
      ragDocs: ["guideline", "research"],
      framework: "free",
      includeCta: true,
    },
  });

  const ragDocs = watch("ragDocs");
  const brandVoice = watch("brandVoice");
  const includeCta = watch("includeCta");

  // ─── LẤY GROUP/FUNCTION TỪ TEMPLATE ───
  const templateConfig = TEMPLATE_MAP[template.id] || { group: "blog_web" as const, function: "blog_post" };

  // ─── MUTATION ───
  const startMutation = useMutation({
    mutationFn: (vars: { data: FormData; selectedOptionText?: string }) =>
      api<StartResponse>("/marketing/start", {
        method: "POST",
        body: JSON.stringify({
          request: vars.data.prompt,
          brand_id: brandId,
          group: templateConfig.group,        // ✅ Từ template
          function: templateConfig.function,   // ✅ Từ template
          auto_mode: false,
          selected_option_text: vars.selectedOptionText,
        }),
      }),
    onSuccess: (data) => {
      if (data.status === "requires_clarification") {
        setClarification({
          type: data.clarification_type,
          message: data.message,
          options: data.options ?? [],
        });
        return;
      }

      queryClient.invalidateQueries({ queryKey: ["marketing-sessions"] });
      onClose();
    },
  });

  const onSubmit = (data: FormData) => {
    setLastFormData(data);
    setClarification(null);
    startMutation.mutate({ data });
  };

  const handleSelectOption = (optionText: string) => {
    if (!lastFormData) return;
    startMutation.mutate({ data: lastFormData, selectedOptionText: optionText });
  };

  const handleEditPrompt = () => {
    setClarification(null);
  };

  const isSubmitting = startMutation.isPending;
  const submitError = startMutation.error;

  // ─── HANDLERS ───
  const handleRagDocsChange = (value: string, checked: boolean) => {
    const current = watch("ragDocs");
    setValue(
      "ragDocs",
      checked ? [...current, value] : current.filter((d) => d !== value),
      { shouldValidate: true }
    );
  };

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="flex flex-col max-h-[80vh]"
    >
      {/* Scrollable Content */}
      <div className="overflow-y-auto p-5 space-y-5 flex-1">
        {clarification?.type === "options" ? (
          <div className="space-y-4">
            <p className="text-sm text-zinc-700">{clarification.message}</p>
            <div className="grid gap-3">
              {clarification?.options?.map((option, idx) => (
                <button
                  key={idx}
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => handleSelectOption(option.title)}
                  className="text-left rounded-lg border border-zinc-200 p-3.5 hover:border-zinc-900 hover:shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <p className="text-sm font-medium text-zinc-900">
                    {option.title}
                  </p>
                  {option.preview && (
                    <p className="text-xs text-zinc-500 mt-1">
                      {option.preview}
                    </p>
                  )}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {clarification?.type === "rewrite" && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 mb-4">
                <p className="text-sm text-amber-800">
                  {clarification.message}
                </p>
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="prompt">
                Prompt <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="prompt"
                autoFocus
                rows={3}
                placeholder={`Nhập chủ đề cho ${template.label}...`}
                className="resize-none"
                disabled={isSubmitting}
                {...register("prompt")}
              />
              {errors.prompt && (
                <p className="text-xs text-red-500">{errors.prompt.message}</p>
              )}
            </div>

            {/* Basic Options Grid */}
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="length" className="text-xs">
                  Độ dài
                </Label>
                <select
                  id="length"
                  disabled={isSubmitting}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:ring-offset-1 disabled:opacity-50"
                  {...register("length")}
                >
                  <option value="short">Ngắn</option>
                  <option value="medium">Vừa</option>
                  <option value="long">Dài</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="tone" className="text-xs">
                  Tone
                </Label>
                <select
                  id="tone"
                  disabled={isSubmitting}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:ring-offset-1 disabled:opacity-50"
                  {...register("tone")}
                >
                  <option value="professional">Chuyên nghiệp</option>
                  <option value="friendly">Thân thiện</option>
                  <option value="humorous">Hài hước</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="language" className="text-xs">
                  Ngôn ngữ
                </Label>
                <select
                  id="language"
                  disabled={isSubmitting}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:ring-offset-1 disabled:opacity-50"
                  {...register("language")}
                >
                  <option value="vi">Tiếng Việt</option>
                  <option value="en">English</option>
                </select>
              </div>
            </div>

            {/* Advanced Options */}
            <Accordion type="single" collapsible>
              <AccordionItem value="advanced" className="border-0">
                <AccordionTrigger className="text-sm py-2 hover:no-underline">
                  <span className="flex items-center gap-1.5">
                    ⚙️ Tùy chọn nâng cao
                  </span>
                </AccordionTrigger>
                <AccordionContent className="space-y-4 pb-2">
                  <div className="space-y-2">
                    <Label className="text-xs">Brand Voice</Label>
                    <div className="flex gap-4">
                      {["default", "custom"].map((value) => (
                        <label
                          key={value}
                          className="flex items-center gap-2 text-sm cursor-pointer"
                        >
                          <input
                            type="radio"
                            value={value}
                            checked={brandVoice === value}
                            onChange={() =>
                              setValue("brandVoice", value as "default" | "custom", {
                                shouldValidate: true,
                              })
                            }
                            disabled={isSubmitting}
                            className="w-4 h-4 cursor-pointer disabled:cursor-not-allowed"
                          />
                          <span>
                            {value === "default" ? "Mặc định" : "Tùy chỉnh"}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs">Knowledge Base</Label>
                    <div className="space-y-1.5">
                      {RAG_DOCS_OPTIONS.map(({ value, label }) => (
                        <label
                          key={value}
                          className="flex items-center gap-2 text-sm cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={ragDocs.includes(value)}
                            onChange={(e) => handleRagDocsChange(value, e.target.checked)}
                            disabled={isSubmitting}
                            className="w-4 h-4 cursor-pointer rounded disabled:cursor-not-allowed"
                          />
                          <span>{label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="framework" className="text-xs">
                      Framework
                    </Label>
                    <select
                      id="framework"
                      disabled={isSubmitting}
                      className="w-full h-8 rounded-md border border-input bg-background px-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:ring-offset-1 disabled:opacity-50"
                      {...register("framework")}
                    >
                      <option value="free">Tự do</option>
                      <option value="aida">AIDA</option>
                      <option value="pas">PAS</option>
                    </select>
                  </div>

                  <div className="flex items-center justify-between">
                    <Label htmlFor="includeCta" className="text-xs">
                      Include CTA
                    </Label>
                    <Switch
                      id="includeCta"
                      checked={includeCta}
                      onCheckedChange={(checked) =>
                        setValue("includeCta", checked, { shouldValidate: true })
                      }
                      disabled={isSubmitting}
                    />
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </>
        )}

        {submitError && (
          <div className="flex items-start gap-2 text-sm text-red-600 bg-red-50 p-3 rounded-lg">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>
              {submitError instanceof Error
                ? submitError.message
                : "Đã xảy ra lỗi khi tạo nội dung"}
            </span>
          </div>
        )}
      </div>

      {/* Sticky Footer */}
      <div className="border-t border-zinc-100 px-5 py-3.5 flex justify-end gap-2 shrink-0 bg-white">
        {clarification ? (
          <Button
            type="button"
            variant="ghost"
            onClick={handleEditPrompt}
            disabled={isSubmitting}
            className="gap-1.5"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Sửa lại prompt
          </Button>
        ) : (
          <>
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="gap-1.5 min-w-[120px]"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Đang tạo...
                </>
              ) : (
                <>
                  <Zap className="h-3.5 w-3.5" />
                  Generate
                </>
              )}
            </Button>
          </>
        )}
      </div>
    </form>
  );
}