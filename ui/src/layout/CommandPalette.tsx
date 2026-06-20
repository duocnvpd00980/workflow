"use client";

import { useState, useEffect } from "react";
import { Search, X, Clock, FileText, BookOpen, Zap } from "lucide-react";
import { recentSearches, mockSearchResults } from "./mock";
import type { Brand } from "./BrandItem";
import { useQueryClient } from "@tanstack/react-query";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function CommandPalette({ open, onClose }: Props) {
  const [query, setQuery] = useState("");
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // Reset query when closed
  useEffect(() => { if (!open) setQuery(""); }, [open]);

  if (!open) return null;

  const hasQuery = query.trim().length > 0;
 
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/30 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl mx-4 bg-white rounded-xl shadow-2xl border border-zinc-200/80 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-100">
          <Search className="h-4 w-4 text-zinc-400 shrink-0" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Tìm kiếm content, brand, task..."
            className="flex-1 text-[14px] text-zinc-800 placeholder:text-zinc-400 outline-none bg-transparent"
          />
          {query && (
            <button onClick={() => setQuery("")} className="text-zinc-400 hover:text-zinc-600 transition-colors">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
          <button onClick={onClose} className="text-zinc-400 hover:text-zinc-600 transition-colors ml-1">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Results */}
        <div className="max-h-[60vh] overflow-y-auto py-2">
          {!hasQuery ? (
            <div className="px-3 pb-2">
              <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider px-2 py-1.5">
                Gần đây
              </p>
              {recentSearches.map((s) => (
                <button key={s} className="w-full flex items-center gap-2.5 h-9 px-2 rounded-md hover:bg-zinc-50 transition-colors text-left">
                  <Clock className="h-3.5 w-3.5 text-zinc-400 shrink-0" />
                  <span className="text-[13px] text-zinc-600">{s}</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="px-3 space-y-1">
              <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider px-2 py-1.5 flex items-center gap-1.5">
                <FileText className="h-3 w-3" /> Content
              </p>
              {mockSearchResults.content.map((r) => (
                <button key={r.id} className="w-full flex items-center h-9 px-2 rounded-md hover:bg-zinc-50 transition-colors text-left">
                  <span className="text-[13px] text-zinc-700">{r.label}</span>
                </button>
              ))}

              <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider px-2 py-1.5 flex items-center gap-1.5 mt-1">
                🏢 Brands
              </p>
              {mockSearchResults.brands.map((r) => (
                <button key={r.id} className="w-full flex items-center h-9 px-2 rounded-md hover:bg-zinc-50 transition-colors text-left">
                  <span className="text-[13px] text-zinc-700">{r.label}</span>
                </button>
              ))}

              <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider px-2 py-1.5 flex items-center gap-1.5 mt-1">
                <BookOpen className="h-3 w-3" /> RAG
              </p>
              {mockSearchResults.rag.map((r) => (
                <button key={r.id} className="w-full flex items-center h-9 px-2 rounded-md hover:bg-zinc-50 transition-colors text-left">
                  <span className="text-[13px] text-zinc-700">{r.label}</span>
                </button>
              ))}

              <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider px-2 py-1.5 flex items-center gap-1.5 mt-1">
                <Zap className="h-3 w-3" /> Tasks
              </p>
              {mockSearchResults.tasks.map((r) => (
                <button key={r.id} className="w-full flex items-center h-9 px-2 rounded-md hover:bg-zinc-50 transition-colors text-left">
                  <span className="text-[13px] text-zinc-700">{r.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-zinc-100 px-4 py-2 flex items-center gap-3">
          <span className="text-[11px] text-zinc-400">
            <kbd className="font-mono bg-zinc-100 px-1 rounded text-[10px]">↑↓</kbd> điều hướng
          </span>
          <span className="text-[11px] text-zinc-400">
            <kbd className="font-mono bg-zinc-100 px-1 rounded text-[10px]">↵</kbd> chọn
          </span>
          <span className="text-[11px] text-zinc-400">
            <kbd className="font-mono bg-zinc-100 px-1 rounded text-[10px]">Esc</kbd> đóng
          </span>
        </div>
      </div>
    </div>
  );
}