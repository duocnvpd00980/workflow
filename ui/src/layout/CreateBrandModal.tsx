"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  X, Globe, Building2, Plus, Check, Rocket,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/config";

// ─── Types ────────────────────────────────────────────────────────────────────

interface BrandOptionResponse {
  id: string;
  name: string;
  is_default: boolean;
}

interface BrandOption {
  id: string;
  name: string;
  active: boolean;
}

const AVATAR_COLORS = [
  { bg: "#E6F1FB", text: "#0C447C" },
  { bg: "#EEEDFE", text: "#3C3489" },
  { bg: "#E1F5EE", text: "#085041" },
  { bg: "#FAECE7", text: "#712B13" },
];

function getInitials(name: string) {
  return name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

// ─── Shared input class ───────────────────────────────────────────────────────
const inputCls = [
  "w-full h-9 px-3 rounded-lg border border-zinc-200 bg-zinc-50",
  "text-[13px] text-zinc-800 placeholder:text-zinc-400",
  "focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400",
  "transition-all",
].join(" ");

// ─── FieldLabel ───────────────────────────────────────────────────────────────
function FieldLabel({
  icon: Icon,
  children,
  required = false,
}: {
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  required?: boolean;
}) {
  return (
    <label className="flex items-center gap-1 text-[11px] font-medium text-zinc-500 mb-1.5">
      <Icon className="h-3 w-3" />
      {children}
      {required && <span className="text-red-500 ml-0.5">*</span>}
    </label>
  );
}

// ─── Main Modal ───────────────────────────────────────────────────────────────
export function CreateBrandModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated?: (brand: BrandOption) => void;
}) {
  // ── FETCH BRAND OPTIONS ──
  const { data: brands = [], isLoading } = useQuery<BrandOption[]>({
    queryKey: ["brand-voices", "options"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/brand-voices/options`, {
        headers: { accept: "application/json" },
      });
      if (!res.ok) throw new Error("Không thể tải danh sách brand");
      const rawData: BrandOptionResponse[] = await res.json();
      return rawData.map((item) => ({
        id: item.id,
        name: item.name,
        active: item.is_default,
      }));
    },
    placeholderData: (previousData) => previousData,
    enabled: open,
  });

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");

  const [loading, setLoading] = useState(false);
  const newNameRef = useRef<HTMLInputElement>(null);

  // Reset khi đóng
  useEffect(() => {
    if (!open) {
      const t = setTimeout(() => {
        setSelectedId(null);
        setShowNewForm(false);
        setNewName("");
        setWebsiteUrl("");
        setLoading(false);
      }, 300);
      return () => clearTimeout(t);
    }
  }, [open]);

  useEffect(() => {
    if (showNewForm) setTimeout(() => newNameRef.current?.focus(), 50);
  }, [showNewForm]);

  useEffect(() => {
    if (!open || loading) return;
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [open, loading, onClose]);

  if (!open) return null;

  const currentBrandName = selectedId
    ? brands.find((b) => b.id === selectedId)?.name ?? ""
    : newName.trim();

  const hasCompany = !!selectedId || (showNewForm && newName.trim().length > 0);
  const hasUrl = websiteUrl.trim().length > 0;
  const canSubmit = hasCompany && hasUrl && !loading;

  const handleSelectBrand = (id: string) => {
    if (showNewForm) {
      setShowNewForm(false);
      setNewName("");
    }
    setSelectedId((prev) => (prev === id ? null : id));
  };

  const handleToggleNew = () => {
    if (showNewForm) {
      setShowNewForm(false);
      setNewName("");
    } else {
      setSelectedId(null);
      setShowNewForm(true);
    }
  };

    const handleCreate = async () => {
    if (!canSubmit || loading) return;
    setLoading(true);

    try {
      const payload: Record<string, any> = {
        business_name: currentBrandName,  // ← Luôn gửi, API bắt buộc
      };

      // Trong handleCreate, clean URL trước khi gửi
      const cleanUrl = websiteUrl.trim().replace(/\/$/, "");
      if (!cleanUrl.startsWith("http")) {
        // Auto-fix nếu user nhập thiếu
        payload.website_url = "https://" + cleanUrl;
      } else {
        payload.website_url = cleanUrl;
      }

      if (selectedId) {
        payload.business_id = selectedId;
      } else {
        payload.owner_id = "string";  // ← Lấy từ auth context
      }

      const voiceRes = await fetch(`${API_BASE}/brand-voices`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!voiceRes.ok) {
        const err = await voiceRes.json();
        throw new Error(err.detail || "Tạo brand voice thất bại");
      }

      const voiceData = await voiceRes.json();

      onCreated?.(voiceData);
      onClose();

      toast.success(`Đang tạo Brand Voice cho ${currentBrandName}`, {
        description: "AI đang phân tích và extract giọng thương hiệu",
      });
    } catch (err: any) {
      toast.error(err.message || "Có lỗi xảy ra");
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4"
      onClick={() => {
        if (!loading) onClose();
      }}
    >
      <div
        className="w-full max-w-sm bg-white rounded-2xl shadow-2xl border border-zinc-200/60 flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ─────────────────────────────────────────────── */}
        <div className="px-5 pt-5 pb-4 flex items-start justify-between gap-3 border-b border-zinc-100 shrink-0">
          <div>
            <p className="text-[15px] font-semibold text-zinc-900 leading-tight">
              Tạo Brand Voice
            </p>
            <p className="text-[12.5px] text-zinc-400 mt-0.5">
              Chọn công ty hoặc tạo mới
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

        {/* ── Scrollable body ─────────────────────────────────────── */}
        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-4">
          {/* ── Section: Công ty ─────────────────────────────────── */}
          <div>
            <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wide mb-2">
              Công ty
            </p>

            {isLoading ? (
              <div className="py-4 text-center text-[12px] text-zinc-400">
                Đang tải...
              </div>
            ) : (
              <div className="space-y-1.5">
                {brands.map((brand, i) => {
                  const colors = AVATAR_COLORS[i % AVATAR_COLORS.length];
                  const checked = selectedId === brand.id;
                  return (
                    <button
                      key={brand.id}
                      onClick={() => handleSelectBrand(brand.id)}
                      className={cn(
                        "w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-left transition-all",
                        checked
                          ? "border-zinc-900 bg-zinc-50"
                          : "border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50/60"
                      )}
                    >
                      <div
                        className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-[11px] font-semibold"
                        style={{ background: colors.bg, color: colors.text }}
                      >
                        {getInitials(brand.name)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] font-medium text-zinc-800 leading-none truncate">
                          {brand.name}
                        </p>
                      </div>
                      <div
                        className={cn(
                          "w-[18px] h-[18px] rounded-full border-[1.5px] flex items-center justify-center shrink-0 transition-all",
                          checked
                            ? "bg-zinc-900 border-zinc-900"
                            : "border-zinc-300"
                        )}
                      >
                        {checked && <Check className="h-2.5 w-2.5 text-white" />}
                      </div>
                    </button>
                  );
                })}

                {/* Tạo mới */}
                <button
                  onClick={handleToggleNew}
                  className={cn(
                    "w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-left transition-all",
                    showNewForm
                      ? "border-zinc-900 bg-zinc-50"
                      : "border-dashed border-zinc-300 hover:border-zinc-400 hover:bg-zinc-50/60"
                  )}
                >
                  <div className="w-7 h-7 rounded-lg bg-zinc-100 flex items-center justify-center shrink-0">
                    <Plus className="h-3.5 w-3.5 text-zinc-500" />
                  </div>
                  <span className="flex-1 text-[13px] text-zinc-500">
                    Tạo công ty mới
                  </span>
                  <div
                    className={cn(
                      "w-[18px] h-[18px] rounded-full border-[1.5px] flex items-center justify-center shrink-0 transition-all",
                      showNewForm
                        ? "bg-zinc-900 border-zinc-900"
                        : "border-zinc-300"
                    )}
                  >
                    {showNewForm && <Check className="h-2.5 w-2.5 text-white" />}
                  </div>
                </button>

                {showNewForm && (
                  <div className="ml-1 pl-3 border-l-2 border-zinc-200 space-y-2.5 pt-1">
                    <div>
                      <FieldLabel icon={Building2} required>
                        Tên công ty
                      </FieldLabel>
                      <input
                        ref={newNameRef}
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        placeholder="VD: Zest Foods"
                        className={inputCls}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="h-px bg-zinc-100" />

          {/* ── URL Section — bắt buộc ────────────────────────────── */}
          <div>
            <FieldLabel icon={Globe} required>
              Facebook URL
            </FieldLabel>
            <input
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
              placeholder="https://www.facebook.com/zestfoods"
              className={inputCls}
            />
            <p className="text-[10.5px] text-zinc-400 mt-1">
              Nhập link Facebook Page để AI phân tích giọng thương hiệu
            </p>
          </div>
        </div>

        {/* ── Footer ──────────────────────────────────────────────── */}
        <div className="px-5 pb-5 pt-3 shrink-0 border-t border-zinc-100">
          <button
            onClick={handleCreate}
            disabled={!canSubmit}
            className={cn(
              "w-full h-10 rounded-xl text-white text-[13.5px] font-semibold transition-all",
              "flex items-center justify-center gap-2",
              "bg-zinc-900 hover:bg-zinc-800 active:scale-[0.98]",
              "disabled:opacity-35 disabled:cursor-not-allowed"
            )}
          >
            <Rocket className="h-4 w-4" />
            {loading ? "Đang tạo..." : "Tạo Brand Voice"}
          </button>
        </div>
      </div>
    </div>
  );
}