"use client";

import { useState } from "react";
import { X, ArrowLeft, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { type Template } from "./types";
import { StepTemplate } from "./StepTemplate";
import { StepGenerate } from "./StepGenerate";

interface Props {
  open: boolean;
  onClose: () => void;
}

const TEMPLATE_EMOJI: Record<string, string> = {
  blog: "📝",
  email: "📧",
  social: "📱",
  video: "🎥",
  improve: "📄",
  rewrite: "🔄",
  summarize: "📋",
  tone: "🎭",
  expand: "📈",
  simplify: "🎯",
};

export function CreateModal({ open, onClose }: Props) {
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(
    null
  );

  const handleClose = () => {
    setSelectedTemplate(null);
    onClose();
  };

  const handleBack = () => {
    setSelectedTemplate(null);
  };

  const step = selectedTemplate ? 2 : 1;
  const emoji = selectedTemplate
    ? TEMPLATE_EMOJI[selectedTemplate.group] ?? "⚡"
    : null;
  const title =
    step === 1 ? "Tạo nội dung mới" : selectedTemplate?.label || "";

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg p-0 border-zinc-200/80 shadow-2xl">
        {/* Custom Header */}
        <DialogHeader className="px-5 py-4 border-b border-zinc-100 flex flex-row items-center justify-between space-y-0 gap-2.5">
          <div className="flex items-center gap-2.5 flex-1 min-w-0">
            {step === 2 && (
              <button
                onClick={handleBack}
                className="h-7 w-7 rounded-lg flex items-center justify-center text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-colors shrink-0"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            )}

            <div className="flex items-center gap-2 flex-1 min-w-0">
              {step === 1 ? (
                <>
                  <Zap className="h-4 w-4 text-zinc-700 shrink-0" />
                  <DialogTitle className="text-[14px]">{title}</DialogTitle>
                </>
              ) : (
                <>
                  <span className="text-base leading-none shrink-0">{emoji}</span>
                  <DialogTitle className="text-[14px] truncate">
                    {title}
                  </DialogTitle>
                </>
              )}
            </div>
          </div>

          {/* Step indicator */}
          <div className="flex items-center gap-1 shrink-0">
            {[1, 2].map((s) => (
              <div
                key={s}
                className={cn(
                  "h-1.5 rounded-full transition-all duration-300",
                  s === step ? "w-4 bg-zinc-900" : "w-1.5 bg-zinc-200"
                )}
              />
            ))}
          </div>
        </DialogHeader>

        {/* Body */}
        {step === 1 ? (
          <StepTemplate onSelect={setSelectedTemplate} />
        ) : (
          <StepGenerate
            template={selectedTemplate!}
            onBack={handleBack}
            onClose={handleClose}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}