"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Zap, Loader2, AlertCircle } from "lucide-react";
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

// ─── API CONFIG ───
const API_BASE = "http://localhost:8000/api/v1";

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

interface StartResponse {
  session_id: string;
  status: string;
  draft: Record<string, unknown> | null;
  usage: Record<string, unknown> | null;
  error: string | null;
}

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

export function StepGenerate({ template, onClose }: Props) {
  const queryClient = useQueryClient();

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

  // Watch values for controlled components
  const ragDocs = watch("ragDocs");
  const brandVoice = watch("brandVoice");
  const includeCta = watch("includeCta");

  // ─── MUTATION ───
  const startMutation = useMutation({
    mutationFn: (data: FormData) =>
      api<StartResponse>("/marketing/start", {
        method: "POST",
        body: JSON.stringify({
          request: data.prompt,
          brand_id: "default", // TODO: thay bằng brand_id thật từ context/auth
          auto_mode: false,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketing-sessions"] });
      onClose();
    },
  });

  const onSubmit = (data: FormData) => {
    startMutation.mutate(data);
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
        {/* Prompt Field */}
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
          {/* Length */}
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

          {/* Tone */}
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

          {/* Language */}
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
              {/* Brand Voice */}
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
                        onChange={() => setValue("brandVoice", value as "default" | "custom", { shouldValidate: true })}
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

              {/* RAG Docs */}
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

              {/* Framework */}
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

              {/* Include CTA */}
              <div className="flex items-center justify-between">
                <Label htmlFor="includeCta" className="text-xs">
                  Include CTA
                </Label>
                <Switch
                  id="includeCta"
                  checked={includeCta}
                  onCheckedChange={(checked) => setValue("includeCta", checked, { shouldValidate: true })}
                  disabled={isSubmitting}
                />
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        {/* Error Display */}
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
      </div>
    </form>
  );
}