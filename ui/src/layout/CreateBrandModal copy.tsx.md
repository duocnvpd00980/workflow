"use client";

import { useState, useEffect } from "react";
import { X, Globe, Building2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import type { Brand } from "./BrandItem";

// Simulate background research task
// Thay bằng API call thật sau
async function runResearchTask(brand: Brand): Promise<void> {
  return new Promise((resolve) => {
    // Giả lập 4–8 giây research
    const ms = 4000 + Math.random() * 4000;
    setTimeout(resolve, ms);
  });
}

export function CreateBrandModal({
  open,
  onClose,
  onCreated,
}: {
  open:      boolean;
  onClose:   () => void;
  onCreated: (brand: Brand) => void;
}) {
  const [name,    setName]    = useState("");
  const [website, setWebsite] = useState("");
  const [loading, setLoading] = useState(false);

  // Reset form khi đóng
  useEffect(() => {
    if (!open) {
      const t = setTimeout(() => {
        setName(""); setWebsite(""); setLoading(false);
      }, 300);
      return () => clearTimeout(t);
    }
  }, [open]);

  // Escape để đóng
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => { if (e.key === "Escape" && !loading) onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [open, loading, onClose]);

  if (!open) return null;

  const canSubmit = name.trim().length > 0;

  const handleCreate = async () => {
    if (!canSubmit || loading) return;
    setLoading(true);

    // 1. Tạo brand NGAY — user không phải đợi
    const newBrand: Brand = {
      id:          Date.now().toString(),
      name:        name.trim(),
      website:     website.trim() || undefined,
      active:      true,
      researching: true,   // đang research nền
    };

    onCreated(newBrand);  // đẩy vào list liền
    onClose();            // đóng modal

    // 2. Toast thông báo đang chạy nền
    toast.loading(`Đang research "${newBrand.name}"...`, {
      id:          `research-${newBrand.id}`,
      description: "AI đang quét web và tạo Brand Voice",
    });

    // 3. Task chạy nền — user tự do làm việc khác
    try {
      await runResearchTask(newBrand);

      // 4. Done → dismiss loading, show success
      toast.success(`Research "${newBrand.name}" xong!`, {
        id:          `research-${newBrand.id}`,
        description: "Brand Voice đã sẵn sàng",
        duration:    5000,
        action: {
          label:   "Xem Brand",
          onClick: () => {
            // navigate tới /brands/:id
            window.location.href = `/brands/${newBrand.id}`;
          },
        },
      });

      // 5. Cập nhật brand: tắt researching flag
      // Dùng custom event để Sidebar lắng nghe update
      window.dispatchEvent(
        new CustomEvent("brand:research-done", { detail: { id: newBrand.id } })
      );

    } catch {
      toast.error(`Research "${newBrand.name}" thất bại`, {
        id:          `research-${newBrand.id}`,
        description: "Vui lòng thử lại sau",
      });
      window.dispatchEvent(
        new CustomEvent("brand:research-done", { detail: { id: newBrand.id } })
      );
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4"
      onClick={() => { if (!loading) onClose(); }}
    >
      <div
        className="w-full max-w-sm bg-white rounded-2xl shadow-2xl border border-zinc-200/60 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 pt-5 pb-4 flex items-start justify-between gap-3">
          <div>
            <p className="text-[15px] font-semibold text-zinc-900 leading-tight">
              Thêm Brand mới
            </p>
            <p className="text-[12.5px] text-zinc-400 mt-0.5">
              AI sẽ tự research và tạo Brand Voice sau
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            className="h-7 w-7 flex items-center justify-center rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-colors shrink-0 disabled:opacity-40"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Fields */}
        <div className="px-5 pb-5 space-y-3.5">

          {/* Tên brand */}
          <div>
            <label className="flex items-center gap-1 text-[12px] font-medium text-zinc-600 mb-1.5">
              <Building2 className="h-3 w-3" />
              Tên doanh nghiệp
              <span className="text-red-500 ml-0.5">*</span>
            </label>
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleCreate(); }}
              placeholder="VD: Acme Corp"
              disabled={loading}
              className={cn(
                "w-full h-9 px-3 rounded-lg border border-zinc-200 bg-zinc-50",
                "text-[13px] text-zinc-800 placeholder:text-zinc-400",
                "focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400",
                "transition-all disabled:opacity-50"
              )}
            />
          </div>

          {/* Website */}
          <div>
            <label className="flex items-center gap-1 text-[12px] font-medium text-zinc-600 mb-1.5">
              <Globe className="h-3 w-3" />
              Website
              <span className="text-[11px] text-zinc-400 font-normal ml-1">(để AI research chính xác hơn)</span>
            </label>
            <input
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleCreate(); }}
              placeholder="https://example.com"
              disabled={loading}
              className={cn(
                "w-full h-9 px-3 rounded-lg border border-zinc-200 bg-zinc-50",
                "text-[13px] text-zinc-800 placeholder:text-zinc-400",
                "focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400",
                "transition-all disabled:opacity-50"
              )}
            />
          </div>

          {/* CTA */}
          <button
            onClick={handleCreate}
            disabled={!canSubmit || loading}
            className={cn(
              "w-full h-10 rounded-xl text-white text-[13.5px] font-semibold transition-colors",
              "flex items-center justify-center gap-2 mt-1",
              "bg-zinc-900 hover:bg-zinc-800",
              "disabled:opacity-40 disabled:cursor-not-allowed"
            )}
          >
            Tạo Brand
          </button>

          <p className="text-center text-[11px] text-zinc-400">
            Brand được tạo ngay • AI research chạy nền
          </p>
        </div>
      </div>
    </div>
  );
}