"use client";

import { useState, useEffect, useRef } from "react";
import {
  X, Globe, Building2, Plus, Check, Rocket,
  Sparkles, Target, Radio, Smile, Users, FileText,
  CloudUpload, Clipboard,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import type { Brand } from "./BrandItem";
import { API_BASE } from "@/config";

// ─── Types ────────────────────────────────────────────────────────────────────

export type Channel = "social" | "blog" | "email" | "ads" | "landing";
export type Tone    = "professional" | "friendly" | "creative" | "authoritative" | "humorous" | "inspiring";
export type DocTab  = "auto" | "upload" | "paste";

const CHANNELS: { value: Channel; label: string }[] = [
  { value: "social",   label: "Social" },
  { value: "blog",     label: "Blog" },
  { value: "email",    label: "Email" },
  { value: "ads",      label: "Quảng cáo" },
  
];

const TONES: { value: Tone; label: string }[] = [
  { value: "professional",  label: "Chuyên nghiệp" },
  { value: "friendly",      label: "Thân thiện" },
  { value: "creative",      label: "Sáng tạo" },
  { value: "authoritative", label: "Uy quyền" },
  { value: "humorous",      label: "Hài hước" },
  { value: "inspiring",     label: "Truyền cảm hứng" },
];

const AVATAR_COLORS = [
  { bg: "#E6F1FB", text: "#0C447C" },
  { bg: "#EEEDFE", text: "#3C3489" },
  { bg: "#E1F5EE", text: "#085041" },
  { bg: "#FAECE7", text: "#712B13" },
];

function getInitials(name: string) {
  return name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

// ─── Hardcode → thay bằng props/fetch ────────────────────────────────────────
const EXISTING_BRANDS: Brand[] = [
  { id: "b1", name: "Acme Corp",   website: "acme.com", active: true },
  { id: "b2", name: "Nova Studio", website: "nova.io",  active: true },
];

async function runResearchTask(brand: Brand): Promise<void> {
  return new Promise((r) => setTimeout(r, 4000 + Math.random() * 4000));
}

// ─── Shared input class ───────────────────────────────────────────────────────
const inputCls = [
  "w-full h-9 px-3 rounded-lg border border-zinc-200 bg-zinc-50",
  "text-[13px] text-zinc-800 placeholder:text-zinc-400",
  "focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400",
  "transition-all",
].join(" ");

// ─── SuggestButton ────────────────────────────────────────────────────────────
function SuggestButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "absolute right-2 top-1/2 -translate-y-1/2",
        "h-6 px-2 rounded-md border border-zinc-200 bg-white",
        "text-[11px] text-zinc-500 hover:text-zinc-700 hover:border-zinc-300",
        "flex items-center gap-1 transition-colors whitespace-nowrap"
      )}
    >
      <Sparkles className="h-2.5 w-2.5" /> Gợi ý
    </button>
  );
}

// ─── FieldLabel ───────────────────────────────────────────────────────────────
function FieldLabel({
  icon: Icon,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <label className="flex items-center gap-1 text-[11px] font-medium text-zinc-500 mb-1.5">
      <Icon className="h-3 w-3" />
      {children}
    </label>
  );
}

// ─── Main Modal ───────────────────────────────────────────────────────────────
export function CreateBrandModal({
  open,
  onClose,
  onCreated,
}: {
  open:      boolean;
  onClose:   () => void;
  onCreated: (brand: Brand) => void;
}) {
  // --- Company section ---
  const [selectedId,  setSelectedId]  = useState<string | null>("b1");
  const [showNewForm, setShowNewForm] = useState(false);
  const [newName,     setNewName]     = useState("");
  const [newWebsite,  setNewWebsite]  = useState("");

  // --- Voice config section ---
  const [voiceName, setVoiceName] = useState("Giọng chuyên nghiệp — Acme Corp");
  const [purpose,   setPurpose]   = useState("Tăng nhận diện và thu hút khách hàng doanh nghiệp");
  const [channels,  setChannels]  = useState<Channel[]>(["social","email", "blog"]);
  const [tone,      setTone]      = useState<Tone>("professional");
  const [audience,  setAudience]  = useState("");
  const [docTab,    setDocTab]    = useState<DocTab>("auto");
  const [docPaste,  setDocPaste]  = useState("");
  const [fileName,  setFileName]  = useState("");
  const [newAddress, setNewAddress] = useState("");
  const [newIndustry, setNewIndustry] = useState("");

  const [loading, setLoading] = useState(false);
  const newNameRef = useRef<HTMLInputElement>(null);
  const fileRef    = useRef<HTMLInputElement>(null);

  // Reset khi đóng
  useEffect(() => {
    if (!open) {
      const t = setTimeout(() => {
        setSelectedId("b1"); setShowNewForm(false);
        setNewName(""); setNewWebsite("");
        setVoiceName(""); setPurpose("");
        setChannels(["social", "blog"]); setTone("professional");
        setAudience(""); setDocTab("auto"); setDocPaste(""); setFileName("");
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
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [open, loading, onClose]);

  if (!open) return null;

  // --- Helpers ---
  const currentBrandName = selectedId
    ? EXISTING_BRANDS.find((b) => b.id === selectedId)?.name ?? ""
    : newName.trim();

  const hasCompany = !!selectedId || (showNewForm && newName.trim().length > 0);
  const canSubmit  = hasCompany && voiceName.trim().length > 0 && !loading;

  const handleSelectBrand = (id: string, name: string) => {
    if (showNewForm) { setShowNewForm(false); setNewName(""); setNewWebsite(""); }
    setSelectedId((prev) => prev === id ? null : id);
    // Auto-fill suggestions khi chọn brand
    setVoiceName(`Giọng chuyên nghiệp — ${name}`);
    setPurpose("Tăng nhận diện và thu hút khách hàng tiềm năng");
  };

  const handleToggleNew = () => {
    if (showNewForm) {
      setShowNewForm(false); setNewName(""); setNewWebsite("");
    } else {
      setSelectedId(null);
      setShowNewForm(true);
      setVoiceName(""); setPurpose("");
    }
  };

  const handleNewNameChange = (v: string) => {
    setNewName(v);
    if (v.trim()) setVoiceName(`Giọng chính — ${v.trim()}`);
  };

  const toggleChannel = (ch: Channel) =>
    setChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    );

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setFileName(f.name);
  };

  // --- Submit ---
   
 const handleCreate = async () => {
  if (!canSubmit || loading) return;
  setLoading(true);

  let businessId = selectedId;
  let businessName = currentBrandName;

  try {
    // ── Step 1: Tạo Business nếu chưa có ──


    // ── Step 2: Tạo Brand Voice ──
    const voiceRes = await fetch(`${API_BASE}/brand-voices`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        business_id:businessId, 
        business_name: businessName,
        address: "string",
        industry: "string",
        owner_id: "string",
        voice_config: {
          name: voiceName.trim(),
          purpose: purpose.trim(),
          channels: channels,
          desired_tone: tone,
          target_audience: audience.trim(),
        },
      }),
    });

    if (!voiceRes.ok) throw new Error('Tạo brand voice thất bại');

    const voiceData = await voiceRes.json();
    
    // Đóng modal + navigate ngay (không đợi research)
    onClose();
    // navigate(`/brand-voices/${voiceData.id}`);

    // Toast thông báo đang xử lý
    toast.loading(`Đang tạo Brand Voice "${voiceName}"...`, {
      id: `voice-${voiceData.id}`,
      description: "AI đang phân tích và extract giọng thương hiệu",
    });

  } catch (err: any) {
    toast.error(err.message || 'Có lỗi xảy ra');
    setLoading(false);
  }
};

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4"
      onClick={() => { if (!loading) onClose(); }}
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
              1 công ty có thể có nhiều giọng khác nhau
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
            <div className="space-y-1.5">
              {EXISTING_BRANDS.map((brand, i) => {
                const colors  = AVATAR_COLORS[i % AVATAR_COLORS.length];
                const checked = selectedId === brand.id;
                return (
                  <button
                    key={brand.id}
                    onClick={() => handleSelectBrand(brand.id, brand.name)}
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
                      {brand.website && (
                        <p className="text-[11px] text-zinc-400 mt-0.5 truncate">{brand.website}</p>
                      )}
                    </div>
                    <div className={cn(
                      "w-[18px] h-[18px] rounded-full border-[1.5px] flex items-center justify-center shrink-0 transition-all",
                      checked ? "bg-zinc-900 border-zinc-900" : "border-zinc-300"
                    )}>
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
                <span className="flex-1 text-[13px] text-zinc-500">Tạo công ty mới</span>
                <div className={cn(
                  "w-[18px] h-[18px] rounded-full border-[1.5px] flex items-center justify-center shrink-0 transition-all",
                  showNewForm ? "bg-zinc-900 border-zinc-900" : "border-zinc-300"
                )}>
                  {showNewForm && <Check className="h-2.5 w-2.5 text-white" />}
                </div>
              </button>

              {showNewForm && (
                <div className="ml-1 pl-3 border-l-2 border-zinc-200 space-y-2.5 pt-1">
                  <div>
                    <FieldLabel icon={Building2}>
                      Tên công ty <span className="text-red-500 ml-0.5">*</span>
                    </FieldLabel>
                    <input
                      ref={newNameRef}
                      value={newName}
                      onChange={(e) => handleNewNameChange(e.target.value)}
                      placeholder="VD: Zest Foods"
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <FieldLabel icon={Globe}>
                      Website{" "}
                      <span className="text-[10.5px] text-zinc-400 font-normal">(không bắt buộc)</span>
                    </FieldLabel>
                    <input
                      value={newWebsite}
                      onChange={(e) => setNewWebsite(e.target.value)}
                      placeholder="https://zestfoods.vn"
                      className={inputCls}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="h-px bg-zinc-100" />

          {/* ── Section: Cấu hình giọng ──────────────────────────── */}
          <div className="space-y-3">
            <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wide">
              Cấu hình giọng
            </p>

            {/* Tên voice */}
            <div>
              <FieldLabel icon={Sparkles}>
                Tên voice{" "}
                <span className="text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-normal">
                  AI gợi ý
                </span>
              </FieldLabel>
              <div className="relative">
                <input
                  value={voiceName}
                  onChange={(e) => setVoiceName(e.target.value)}
                  placeholder="VD: Giọng chuyên nghiệp"
                  className={cn(inputCls, "pr-16")}
                />
                <SuggestButton onClick={() => {
                  const opts = ["Giọng trẻ trung", "Giọng chuyên nghiệp", "Giọng truyền cảm hứng", "Giọng thân thiện"];
                  setVoiceName(`${opts[Math.floor(Math.random() * opts.length)]}${currentBrandName ? ` — ${currentBrandName}` : ""}`);
                }} />
              </div>
            </div>

            {/* Mục đích */}
            <div>
              <FieldLabel icon={Target}>
                Mục đích{" "}
                <span className="text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-normal">
                  AI gợi ý
                </span>
              </FieldLabel>
              <div className="relative">
                <input
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  placeholder="VD: Tăng nhận diện thương hiệu trên mạng xã hội"
                  className={cn(inputCls, "pr-16")}
                />
                <SuggestButton onClick={() => {
                  const opts = ["Tăng nhận diện thương hiệu", "Thu hút khách hàng mới", "Xây dựng cộng đồng", "Tăng chuyển đổi bán hàng"];
                  setPurpose(opts[Math.floor(Math.random() * opts.length)]);
                }} />
              </div>
            </div>

            {/* Kênh */}
            <div>
              <FieldLabel icon={Radio}>Kênh phân phối</FieldLabel>
              <div className="flex flex-wrap gap-1.5">
                {CHANNELS.map(({ value, label }) => {
                  const on = channels.includes(value);
                  return (
                    <button
                      key={value}
                      onClick={() => toggleChannel(value)}
                      className={cn(
                        "flex items-center gap-1 px-2.5 py-1 rounded-lg border text-[12px] transition-all",
                        on
                          ? "border-zinc-900 bg-zinc-50 text-zinc-800"
                          : "border-zinc-200 text-zinc-500 hover:border-zinc-300"
                      )}
                    >
                      {on && <Check className="h-2.5 w-2.5" />}
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Tone */}
            <div>
              <FieldLabel icon={Smile}>Tone giọng điệu</FieldLabel>
              <select
                value={tone}
                onChange={(e) => setTone(e.target.value as Tone)}
                className={cn(inputCls, "cursor-pointer")}
              >
                {TONES.map(({ value, label }) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>

            {/* Đối tượng */}
            <div>
              <FieldLabel icon={Users}>
                Đối tượng mục tiêu{" "}
                <span className="text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-normal">
                  AI gợi ý
                </span>
              </FieldLabel>
              <div className="relative">
                <input
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                  placeholder="VD: Startup founders, 25–40 tuổi, tech-savvy"
                  className={cn(inputCls, "pr-16")}
                />
                <SuggestButton onClick={() => {
                  const opts = [
                    "Giám đốc điều hành, 30–50 tuổi, B2B",
                    "Freelancer sáng tạo, 22–35 tuổi",
                    "Phụ huynh trẻ, 28–40 tuổi",
                    "Startup founder, 25–38 tuổi",
                  ];
                  setAudience(opts[Math.floor(Math.random() * opts.length)]);
                }} />
              </div>
            </div>

            {/* Tài liệu */}
            <div>
              <FieldLabel icon={FileText}>
                Tài liệu tham khảo{" "}
                <span className="text-[10px] bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded font-normal animate-pulse">
                  Đang research...
                </span>
              </FieldLabel>

              {/* Tab switcher */}
              <div className="flex gap-1.5 mb-2">
                {(["auto", "upload", "paste"] as DocTab[]).map((tab) => {
                  const icons = { auto: Sparkles, upload: CloudUpload, paste: Clipboard };
                  const labels = { auto: "Auto", upload: "Upload", paste: "Paste" };
                  const Icon = icons[tab];
                  return (
                    <button
                      key={tab}
                      onClick={() => setDocTab(tab)}
                      className={cn(
                        "flex-1 h-8 rounded-lg border text-[12px] flex items-center justify-center gap-1.5 transition-all",
                        docTab === tab
                          ? "border-zinc-900 bg-zinc-900 text-white"
                          : "border-zinc-200 text-zinc-500 hover:border-zinc-300"
                      )}
                    >
                      <Icon className="h-3 w-3" /> {labels[tab]}
                    </button>
                  );
                })}
              </div>

              {/* {docTab === "auto" && (
                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200 text-[12px] text-zinc-500 flex items-center gap-2">
                  <span className="animate-spin text-amber-600 text-base leading-none">⟳</span>
                  AI đang quét website và thu thập thông tin thương hiệu...
                </div>
              )} */}
              {docTab === "upload" && (
                <>
                  <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" onChange={handleFile} className="hidden" />
                  <div
                    onClick={() => fileRef.current?.click()}
                    className="p-4 rounded-lg border border-dashed border-zinc-300 bg-zinc-50 flex flex-col items-center gap-1 cursor-pointer hover:border-zinc-400 transition-colors"
                  >
                    <CloudUpload className="h-5 w-5 text-zinc-400" />
                    {fileName
                      ? <span className="text-[12px] text-zinc-700 font-medium">{fileName}</span>
                      : <>
                          <p className="text-[12px] text-zinc-500">Kéo thả hoặc <span className="text-blue-500">chọn từ máy tính</span></p>
                          <p className="text-[11px] text-zinc-400">PDF, DOCX, TXT — tối đa 20MB</p>
                        </>
                    }
                  </div>
                </>
              )}
              {docTab === "paste" && (
                <textarea
                  value={docPaste}
                  onChange={(e) => setDocPaste(e.target.value)}
                  placeholder="Dán nội dung thương hiệu vào đây..."
                  rows={4}
                  className={cn(
                    "w-full px-3 py-2 rounded-lg border border-zinc-200 bg-zinc-50 resize-none",
                    "text-[12.5px] text-zinc-800 placeholder:text-zinc-400",
                    "focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400 transition-all"
                  )}
                />
              )}
            </div>
          </div>
        </div>

        {/* ── Footer ──────────────────────────────────────────────── */}
        <div className="px-5 pb-5 pt-3 shrink-0 border-t border-zinc-100">
          <button
            onClick={handleCreate}
            // disabled={!!canSubmit}
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