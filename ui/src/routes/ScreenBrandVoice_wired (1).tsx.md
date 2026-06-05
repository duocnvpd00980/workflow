/**
 * ScreenBrandVoice — API-wired version
 *
 * All changes from the static mock:
 * 1. useEffect on mount  → GET /api/brand-voice
 * 2. Every selector/input → local state synced from API response
 * 3. "Lưu thay đổi"      → PUT /api/brand-voice (partial payload)
 * 4. "Xem trước"         → shows derived rag-context in a modal
 * 5. "Thêm / Xoá" items  → update local state, saved on save
 * 6. Loading + error states with inline feedback
 *
 * Drop this file in as a replacement for the ScreenBrandVoice function
 * in your existing brand.tsx. Everything else in that file stays the same.
 */

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Volume2, Eye, Check, Plus, AlignLeft, Edit3, Bookmark,
  Smile, MessageSquare, Flame, Upload, ExternalLink,
  Loader2, AlertCircle, X, RotateCcw, Save,
} from "lucide-react";

// ─── Config ──────────────────────────────────────────────────────────────────
const API_BASE = "/api"; // change if your FastAPI runs on a different origin

const ACCENT_BG = "bg-indigo-600 hover:bg-indigo-700 text-white";

// ─── Tiny API client ──────────────────────────────────────────────────────────
async function apiFetch(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...((options.headers as object) ?? {}) },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// ─── Types ────────────────────────────────────────────────────────────────────
interface RefDoc { name: string; size: string; type: string; }

interface BrandVoiceData {
  tone_of_voice:    string;
  voice_rules:      string[];
  cta_style:        string;
  cta_samples:      string[];
  core_message:     string;
  visual_style:     string;
  brand_colors:     string[];
  image_type:       string;
  image_rules:      string[];
  products:         string[];
  benefits:         string[];
  target_audience:  string[];
  reference_urls:   string[];
  reference_notes:  string;
  reference_docs:   RefDoc[];
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SaveToast({ status }: { status: "idle" | "saving" | "saved" | "error" }) {
  if (status === "idle") return null;
  const map = {
    saving: { bg: "bg-amber-50 border-amber-200 text-amber-700", icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />, label: "Đang lưu..." },
    saved:  { bg: "bg-emerald-50 border-emerald-200 text-emerald-700", icon: <Check className="w-3.5 h-3.5" />, label: "Đã lưu!" },
    error:  { bg: "bg-red-50 border-red-200 text-red-600", icon: <AlertCircle className="w-3.5 h-3.5" />, label: "Lưu thất bại" },
  };
  const { bg, icon, label } = map[status];
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-bold ${bg}`}>
      {icon} {label}
    </span>
  );
}

function PreviewModal({ data, onClose }: { data: Record<string, unknown>; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="font-black text-sm text-slate-900">RAG Context Preview</h3>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-700"><X className="w-4 h-4" /></button>
        </div>
        <p className="text-xs text-slate-500">Đây là context mà AI workflow sẽ nhận được khi generate content.</p>
        <pre className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-[10px] font-mono text-slate-700 overflow-auto max-h-80 leading-relaxed whitespace-pre-wrap">
          {JSON.stringify(data, null, 2)}
        </pre>
        <button onClick={onClose} className={`w-full py-2 text-xs font-bold rounded-lg ${ACCENT_BG}`}>Đóng</button>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export function ScreenBrandVoice({ ONNav }: { ONNav: (s: number) => void }) {
  // ── State ──────────────────────────────────────────────────────────────────
  const [data, setData]           = useState<BrandVoiceData | null>(null);
  const [loadErr, setLoadErr]     = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [preview, setPreview]     = useState<Record<string, unknown> | null>(null);
  const [newCta, setNewCta]       = useState("");
  const [newProduct, setNewProduct] = useState("");
  const [editingCta, setEditingCta] = useState<number | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout>>();

  // ── Load on mount ──────────────────────────────────────────────────────────
  useEffect(() => {
    apiFetch("/brand-voice")
      .then((res) => setData(res.data))
      .catch((e)  => setLoadErr(e.message));
  }, []);

  // ── Auto-clear "saved" toast ───────────────────────────────────────────────
  useEffect(() => {
    if (saveStatus === "saved") {
      saveTimer.current = setTimeout(() => setSaveStatus("idle"), 2500);
    }
    return () => clearTimeout(saveTimer.current);
  }, [saveStatus]);

  // ── Save handler ───────────────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    if (!data) return;
    setSaveStatus("saving");
    try {
      const res = await apiFetch("/brand-voice", {
        method: "PUT",
        body: JSON.stringify(data),
      });
      setData(res.data);
      setSaveStatus("saved");
    } catch (e: unknown) {
      console.error(e);
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
    }
  }, [data]);

  // ── Preview handler ────────────────────────────────────────────────────────
  const handlePreview = async () => {
    // Save first so preview reflects current UI state
    if (data) {
      try {
        await apiFetch("/brand-voice", { method: "PUT", body: JSON.stringify(data) });
      } catch (_) { /* show preview anyway */ }
    }
    try {
      const res = await apiFetch("/brand-voice/rag-context");
      setPreview(res.data);
    } catch (e: unknown) {
      alert("Không thể tải RAG context: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  // ── Reset handler ──────────────────────────────────────────────────────────
  const handleReset = async () => {
    if (!confirm("Reset toàn bộ Brand Voice về mặc định?")) return;
    try {
      const res = await apiFetch("/brand-voice/reset", { method: "POST" });
      setData(res.data);
      setSaveStatus("saved");
    } catch (e: unknown) {
      alert("Reset thất bại: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  // ── Field updater helper ───────────────────────────────────────────────────
  const update = (patch: Partial<BrandVoiceData>) => setData((d) => d ? { ...d, ...patch } : d);

  // ─────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────

  if (loadErr) return (
    <div className="flex flex-col items-center justify-center py-24 gap-4 text-center">
      <AlertCircle className="w-8 h-8 text-red-400" />
      <p className="text-sm font-bold text-slate-700">Không thể tải Brand Voice</p>
      <p className="text-xs text-slate-500 max-w-xs">{loadErr}</p>
      <button onClick={() => window.location.reload()} className="px-4 py-2 text-xs font-bold bg-slate-100 rounded-lg hover:bg-slate-200">
        Thử lại
      </button>
    </div>
  );

  if (!data) return (
    <div className="flex items-center justify-center py-24 gap-3 text-slate-500">
      <Loader2 className="w-5 h-5 animate-spin" />
      <span className="text-sm font-medium">Đang tải Brand Voice...</span>
    </div>
  );

  return (
    <>
      {preview && <PreviewModal data={preview} onClose={() => setPreview(null)} />}

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-lg font-black tracking-tight text-slate-900 flex items-center gap-2">
            <Volume2 className="w-5 h-5 text-indigo-600" /> Brand Voice
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">Thiết lập giọng văn, phong cách và thông điệp thương hiệu của bạn.</p>
        </div>
        <div className="flex items-center gap-2 self-end sm:self-auto flex-wrap justify-end">
          <SaveToast status={saveStatus} />
          <button
            onClick={handleReset}
            className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-500 hover:bg-slate-50 shadow-xs flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset
          </button>
          <button
            onClick={handlePreview}
            className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-slate-50 shadow-xs flex items-center gap-1.5"
          >
            <Eye className="w-3.5 h-3.5" /> Xem trước
          </button>
          <button
            onClick={handleSave}
            disabled={saveStatus === "saving"}
            className={`px-4 py-1.5 text-xs font-bold rounded-lg shadow-sm flex items-center gap-1.5 ${ACCENT_BG} disabled:opacity-60`}
          >
            {saveStatus === "saving"
              ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Đang lưu...</>
              : <><Save className="w-3.5 h-3.5" /> Lưu thay đổi</>
            }
          </button>
        </div>
      </div>

      {/* ── 3-column grid ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 text-xs">

        {/* ── Block 1: Giọng văn & Tone ──────────────────────────────────── */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center font-mono text-[11px]">1</span>
            <h3>Giọng văn & Tone</h3>
          </div>
          <p className="text-[11px] text-slate-400">Chọn giọng văn phù hợp với thương hiệu của bạn.</p>

          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Tone of Voice</span>
            <div className="space-y-2">
              {[
                { name: "Thân thiện",       desc: "Gần gũi, tự nhiên, dễ hiểu",        emoji: "😊" },
                { name: "Chuyên nghiệp",    desc: "Trang trọng, đáng tin cậy",          emoji: "💼" },
                { name: "Truyền cảm hứng",  desc: "Tích cực, động viên, thúc đẩy",      emoji: "✨" },
                { name: "Hài hước",         desc: "Vui vẻ, dí dỏm, sáng tạo",           emoji: "😆" },
                { name: "Tối giản",         desc: "Ngắn gọn, rõ ràng, súc tích",         emoji: "📝" },
              ].map((tone) => (
                <div
                  key={tone.name}
                  onClick={() => update({ tone_of_voice: tone.name })}
                  className={`p-3 rounded-lg border transition-all cursor-pointer flex items-start gap-3 ${
                    data.tone_of_voice === tone.name
                      ? "border-indigo-600 bg-indigo-50/20 ring-1 ring-indigo-600"
                      : "border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  <input type="radio" readOnly checked={data.tone_of_voice === tone.name} className="text-indigo-600 mt-0.5" />
                  <div>
                    <div className="font-bold text-slate-900 flex items-center gap-1">
                      <span>{tone.emoji}</span> {tone.name}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{tone.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Voice rules */}
          <div className="space-y-2 pt-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Quy tắc giọng văn</span>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2 text-slate-600 font-medium">
              {data.voice_rules.map((rule, i) => (
                <div key={i} className="flex items-start gap-2 group">
                  <Check className="w-3.5 h-3.5 text-indigo-600 mt-0.5 shrink-0" />
                  <span className="flex-1">{rule}</span>
                  <button
                    onClick={() => update({ voice_rules: data.voice_rules.filter((_, j) => j !== i) })}
                    className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-300 hover:text-red-500 transition"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
              <div className="text-right text-[10px] text-slate-400 font-mono pt-1">
                {data.voice_rules.length}/10 quy tắc
              </div>
            </div>
          </div>
        </div>

        {/* ── Block 2: CTA & Thông điệp ──────────────────────────────────── */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center font-mono text-[11px]">2</span>
            <h3>CTA & Thông điệp</h3>
          </div>
          <p className="text-[11px] text-slate-400">Thiết lập các CTA và thông điệp cốt lõi.</p>

          {/* CTA Style */}
          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">CTA Style</span>
            <div className="grid grid-cols-3 gap-2 text-center font-bold">
              {[
                { name: "Mềm mại",   icon: Smile },
                { name: "Trung tính", icon: MessageSquare },
                { name: "Mạnh mẽ",   icon: Flame },
              ].map(({ name, icon: Icon }) => (
                <button
                  key={name}
                  onClick={() => update({ cta_style: name })}
                  className={`py-2 rounded-lg border text-[11px] flex items-center justify-center gap-1 transition-all ${
                    data.cta_style === name
                      ? "bg-indigo-50 text-indigo-700 border-indigo-300 shadow-xs"
                      : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  <Icon className="w-3 h-3" /> {name}
                </button>
              ))}
            </div>
          </div>

          {/* CTA Samples */}
          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">CTA Mẫu</span>
            <div className="space-y-1.5">
              {data.cta_samples.map((cta, i) => (
                <div key={i} className="bg-white border border-slate-200 px-3 py-2 rounded-lg flex items-center justify-between font-medium text-slate-700 group hover:border-slate-300">
                  {editingCta === i ? (
                    <input
                      autoFocus
                      className="flex-1 outline-none text-xs bg-transparent"
                      defaultValue={cta}
                      onBlur={(e) => {
                        const v = e.target.value.trim();
                        if (v) {
                          const next = [...data.cta_samples];
                          next[i] = v;
                          update({ cta_samples: next });
                        }
                        setEditingCta(null);
                      }}
                      onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }}
                    />
                  ) : (
                    <>
                      <span onClick={() => setEditingCta(i)} className="cursor-text flex-1">{cta}</span>
                      <button
                        onClick={() => update({ cta_samples: data.cta_samples.filter((_, j) => j !== i) })}
                        className="opacity-0 group-hover:opacity-100 p-1 text-slate-300 hover:text-red-500"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </>
                  )}
                </div>
              ))}
              {/* Add new CTA */}
              <div className="flex gap-1.5">
                <input
                  value={newCta}
                  onChange={(e) => setNewCta(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && newCta.trim()) {
                      update({ cta_samples: [...data.cta_samples, newCta.trim()] });
                      setNewCta("");
                    }
                  }}
                  placeholder="Thêm CTA mới..."
                  className="flex-1 border border-slate-200 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-indigo-400"
                />
                <button
                  onClick={() => {
                    if (newCta.trim()) {
                      update({ cta_samples: [...data.cta_samples, newCta.trim()] });
                      setNewCta("");
                    }
                  }}
                  className="px-2 py-1.5 bg-indigo-50 text-indigo-600 border border-indigo-100 rounded-lg hover:bg-indigo-100"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Core message */}
          <div className="space-y-2 pt-1">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Thông điệp cốt lõi</span>
            <div className="relative">
              <textarea
                rows={4}
                value={data.core_message}
                onChange={(e) => update({ core_message: e.target.value })}
                className="w-full bg-white border border-slate-200 p-3 rounded-lg outline-none focus:border-indigo-500 font-medium leading-relaxed resize-none text-slate-700"
              />
              <span className="absolute bottom-2.5 right-3 text-[10px] text-slate-400 font-mono">
                {data.core_message.length}/200 ký tự
              </span>
            </div>
          </div>
        </div>

        {/* ── Block 3: Phong cách hình ảnh ───────────────────────────────── */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center font-mono text-[11px]">3</span>
            <h3>Phong cách hình ảnh</h3>
          </div>

          {/* Visual style */}
          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Phong cách chủ đạo</span>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { name: "Tối giản", img: "https://images.unsplash.com/photo-1544816155-12df9643f363?w=120&auto=format&fit=crop&q=60" },
                { name: "Hiện đại", img: "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=120&auto=format&fit=crop&q=60" },
                { name: "Ấm áp",   img: "https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=120&auto=format&fit=crop&q=60" },
                { name: "Năng động", img: "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=120&auto=format&fit=crop&q=60" },
              ].map((s) => (
                <div
                  key={s.name}
                  onClick={() => update({ visual_style: s.name })}
                  className={`border rounded-lg overflow-hidden cursor-pointer transition-all pb-1.5 text-center relative ${
                    data.visual_style === s.name ? "border-indigo-600 ring-2 ring-indigo-500/10" : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <img src={s.img} alt={s.name} className="w-full h-14 object-cover" />
                  <span className="text-[10px] font-bold block mt-1 text-slate-800">{s.name}</span>
                  {data.visual_style === s.name && (
                    <div className="absolute top-1 left-1 bg-indigo-600 text-white rounded-full p-0.5">
                      <Check className="w-2.5 h-2.5" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Brand colors */}
          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Màu sắc chủ đạo</span>
            <div className="flex gap-2 justify-between">
              {data.brand_colors.map((hex, i) => (
                <div key={i} className="text-center space-y-1 flex-1">
                  <div style={{ backgroundColor: hex }} className="h-6 rounded-md w-full border border-slate-200/60" />
                  <span className="text-[9px] font-mono text-slate-400 block">{hex}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Image type */}
          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Loại hình ảnh</span>
            <div className="flex flex-wrap gap-1.5 font-bold">
              {["Ảnh thực tế", "Đồ họa minh họa", "Icon", "3D Render"].map((t) => (
                <button
                  key={t}
                  onClick={() => update({ image_type: t })}
                  className={`px-3 py-1 rounded-md border text-[11px] transition-all ${
                    data.image_type === t
                      ? "bg-indigo-50 border-indigo-300 text-indigo-700 shadow-xs"
                      : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {data.image_type === t && "✓ "}{t}
                </button>
              ))}
            </div>
          </div>

          {/* Image rules */}
          <div className="space-y-2 pt-1">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Quy tắc hình ảnh</span>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2 text-slate-600 font-medium">
              {data.image_rules.map((rule, i) => (
                <div key={i} className="flex items-start gap-2 group">
                  <Check className="w-3.5 h-3.5 text-indigo-600 mt-0.5 shrink-0" />
                  <span className="flex-1">{rule}</span>
                  <button
                    onClick={() => update({ image_rules: data.image_rules.filter((_, j) => j !== i) })}
                    className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-300 hover:text-red-500"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Bottom 2-col grid ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 text-xs">

        {/* ── Block 4: Sản phẩm / Dịch vụ ───────────────────────────────── */}
        <div className="lg:col-span-7 bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center font-mono text-[11px]">4</span>
            <h3>Sản phẩm / Dịch vụ</h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-12 gap-4 items-start">
            {/* Product list */}
            <div className="sm:col-span-6 space-y-2">
              <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Sản phẩm / Dịch vụ chính</span>
              <div className="space-y-1.5">
                {data.products.map((prod, i) => (
                  <div key={i} className="flex items-center justify-between border border-slate-200 px-3 py-2 rounded-lg bg-white group hover:border-slate-300">
                    <div className="flex items-center gap-2 font-medium text-slate-700">
                      <AlignLeft className="w-3.5 h-3.5 text-slate-300" />
                      <span>{prod}</span>
                    </div>
                    <button
                      onClick={() => update({ products: data.products.filter((_, j) => j !== i) })}
                      className="opacity-0 group-hover:opacity-100 p-1 text-slate-300 hover:text-red-500"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex gap-1.5">
                <input
                  value={newProduct}
                  onChange={(e) => setNewProduct(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && newProduct.trim()) {
                      update({ products: [...data.products, newProduct.trim()] });
                      setNewProduct("");
                    }
                  }}
                  placeholder="Thêm sản phẩm..."
                  className="flex-1 border border-slate-200 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-indigo-400"
                />
                <button
                  onClick={() => {
                    if (newProduct.trim()) {
                      update({ products: [...data.products, newProduct.trim()] });
                      setNewProduct("");
                    }
                  }}
                  className="px-2 py-1.5 bg-indigo-50 text-indigo-600 border border-indigo-100 rounded-lg hover:bg-indigo-100"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Benefits + Target audience */}
            <div className="sm:col-span-6 space-y-4">
              <div className="space-y-2">
                <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Lợi ích nổi bật</span>
                <div className="space-y-1.5 text-slate-600 font-medium">
                  {data.benefits.map((b, i) => (
                    <div key={i} className="flex items-center gap-2 group">
                      <div className="w-4 h-4 bg-indigo-50 rounded-full flex items-center justify-center text-indigo-600 text-[10px] font-bold shrink-0">✓</div>
                      <span className="flex-1">{b}</span>
                      <button
                        onClick={() => update({ benefits: data.benefits.filter((_, j) => j !== i) })}
                        className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-300 hover:text-red-500"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Đối tượng khách hàng</span>
                <div className="flex flex-wrap gap-1.5">
                  {data.target_audience.map((tag, i) => (
                    <span
                      key={i}
                      className="group px-2.5 py-1 bg-indigo-50/60 text-indigo-700 rounded-md font-bold text-[10px] border border-indigo-100/40 flex items-center gap-1 cursor-default"
                    >
                      {tag}
                      <button
                        onClick={() => update({ target_audience: data.target_audience.filter((_, j) => j !== i) })}
                        className="opacity-0 group-hover:opacity-100 text-indigo-400 hover:text-red-500"
                      >
                        <X className="w-2.5 h-2.5" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── Block 5: Tài liệu tham khảo ───────────────────────────────── */}
        <div className="lg:col-span-5 bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center font-mono text-[11px]">5</span>
            <h3>Tài liệu tham khảo</h3>
          </div>

          {/* Reference docs */}
          <div className="space-y-2">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Tài liệu thương hiệu</span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {data.reference_docs.map((doc, i) => (
                <div key={i} className="border border-slate-200 p-2.5 rounded-lg bg-white hover:border-slate-300 group flex flex-col justify-between min-h-[64px]">
                  <div className="flex items-start gap-1.5">
                    <div className="w-5 h-5 rounded bg-red-50 text-red-600 flex items-center justify-center text-[8px] font-black uppercase shrink-0">{doc.type}</div>
                    <div className="overflow-hidden">
                      <div className="font-bold text-slate-800 truncate text-[10px]">{doc.name}</div>
                      <div className="text-[9px] text-slate-400 font-mono mt-0.5">{doc.size}</div>
                    </div>
                  </div>
                </div>
              ))}
              <div className="border border-dashed border-slate-200 p-2 rounded-lg bg-slate-50 flex flex-col items-center justify-center text-center text-[9px] text-slate-400 hover:bg-slate-100/50 cursor-pointer transition">
                <Upload className="w-3.5 h-3.5 text-slate-400 mb-1" />
                <span className="font-bold text-slate-600">Thêm tài liệu</span>
                <span className="text-[8px] scale-90 mt-0.5">PDF, DOCX, PPTX</span>
              </div>
            </div>
          </div>

          {/* Website */}
          <div className="space-y-1.5">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Website tham khảo</span>
            <div className="bg-white border border-slate-200 px-3 py-1.5 rounded-lg flex items-center justify-between">
              <input
                value={data.reference_urls[0] ?? ""}
                onChange={(e) => update({ reference_urls: [e.target.value] })}
                className="text-indigo-600 font-medium text-xs outline-none bg-transparent flex-1 min-w-0"
              />
              <ExternalLink className="w-3.5 h-3.5 text-slate-400 cursor-pointer hover:text-indigo-600 shrink-0" />
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <span className="font-bold text-slate-500 block text-[10px] uppercase tracking-wide">Ghi chú thêm</span>
            <div className="relative">
              <textarea
                rows={3}
                value={data.reference_notes}
                onChange={(e) => update({ reference_notes: e.target.value })}
                className="w-full bg-white border border-slate-200 p-3 rounded-lg outline-none focus:border-indigo-500 font-medium leading-relaxed resize-none text-slate-700"
              />
              <span className="absolute bottom-2.5 right-3 text-[10px] text-slate-400 font-mono">
                {data.reference_notes.length}/500 ký tự
              </span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
