"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import {
  CONTENT_GROUPS,
  TOOL_GROUPS,
  SUB_TEMPLATES,
  type ContentGroup,
  type Template,
} from "./types";

interface Props {
  onSelect: (template: Template) => void;
}

export function StepTemplate({ onSelect }: Props) {
  const [expandedGroup, setExpandedGroup] = useState<ContentGroup | null>(null);

  const handleGroupClick = (id: ContentGroup) => {
    setExpandedGroup((prev) => (prev === id ? null : id));
  };

  return (
    <div className="p-5 space-y-5">
      {/* Content groups */}
      <div>
        <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider mb-3">
          Chọn loại nội dung
        </p>
        <div className="grid grid-cols-4 gap-2">
          {CONTENT_GROUPS.map((g) => (
            <button
              key={g.id}
              onClick={() => handleGroupClick(g.id)}
              className={cn(
                "flex flex-col items-center justify-center gap-1.5 rounded-xl border py-3 px-2 transition-all duration-150",
                expandedGroup === g.id
                  ? "border-zinc-900 bg-zinc-900 text-white"
                  : "border-zinc-200 bg-white hover:border-zinc-300 hover:bg-zinc-50 text-zinc-700"
              )}
            >
              <span className="text-xl leading-none">{g.emoji}</span>
              <span className="text-[11px] font-semibold leading-tight text-center">{g.label}</span>
              <span
                className={cn(
                  "text-[10px] leading-tight text-center",
                  expandedGroup === g.id ? "text-zinc-300" : "text-zinc-400"
                )}
              >
                {g.sub}
              </span>
            </button>
          ))}
        </div>

        {/* Sub-templates for content group */}
        {expandedGroup && CONTENT_GROUPS.some((g) => g.id === expandedGroup) && (
          <div className="mt-2 grid grid-cols-2 gap-1.5 animate-in fade-in slide-in-from-top-1 duration-150">
            {SUB_TEMPLATES[expandedGroup].map((t) => (
              <button
                key={t.id}
                onClick={() => onSelect(t)}
                className="flex items-center h-9 px-3 rounded-lg border border-zinc-200 bg-white hover:border-zinc-900 hover:bg-zinc-50 transition-all text-left text-[13px] text-zinc-700 font-medium"
              >
                {t.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Tool groups */}
      <div>
        <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider mb-3">
          Hoặc công cụ chỉnh sửa
        </p>
        <div className="grid grid-cols-3 gap-2">
          {TOOL_GROUPS.map((g) => (
            <button
              key={g.id}
              onClick={() => handleGroupClick(g.id)}
              className={cn(
                "flex items-center gap-2.5 h-10 px-3 rounded-xl border transition-all duration-150 text-left",
                expandedGroup === g.id
                  ? "border-zinc-900 bg-zinc-900 text-white"
                  : "border-zinc-200 bg-white hover:border-zinc-300 hover:bg-zinc-50 text-zinc-700"
              )}
            >
              <span className="text-base leading-none">{g.emoji}</span>
              <span className="text-[12.5px] font-medium">{g.label}</span>
            </button>
          ))}
        </div>

        {/* Sub-templates for tool group */}
        {expandedGroup && TOOL_GROUPS.some((g) => g.id === expandedGroup) && (
          <div className="mt-2 animate-in fade-in slide-in-from-top-1 duration-150">
            {SUB_TEMPLATES[expandedGroup].map((t) => (
              <button
                key={t.id}
                onClick={() => onSelect(t)}
                className="flex items-center h-9 px-3 rounded-lg border border-zinc-200 bg-white hover:border-zinc-900 hover:bg-zinc-50 transition-all text-left text-[13px] text-zinc-700 font-medium w-full"
              >
                {t.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}