"use client";

import React, { useState, useMemo, useCallback } from "react";
import {
  format, startOfMonth, endOfMonth, startOfWeek, endOfWeek,
  addDays, isSameMonth, isSameDay, subMonths,
  isToday, addWeeks, addMonths,
} from "date-fns";

// =============================================================================
// BIỂU TƯỢNG (SVG inline - không phụ thuộc)
// =============================================================================

const I = {
  Search: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>,
  ChevronLeft: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>,
  ChevronRight: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6"/></svg>,
  ChevronDown: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>,
  Calendar: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>,
  List: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>,
  Clock: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  Facebook: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="currentColor"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg>,
  Globe: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>,
  Instagram: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="20" rx="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg>,
  X: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>,
  Pencil: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>,
  Copy: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>,
  Rocket: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>,
  Trash: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>,
  Filter: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>,
  Check: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg>,
  Alert: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
  Spinner: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="spin"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>,
  Repeat: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/></svg>,
  Zap: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>,
  Bell: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>,
  Settings: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>,
  Play: ({s=16}:any) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>,
};

// =============================================================================
// KIỂU DỮ LIỆU
// =============================================================================

type Channel = "facebook" | "website" | "instagram";
type Status = "scheduled" | "pending" | "draft" | "failed";
type ViewMode = "month" | "week" | "list";

type ScheduleMode = "once" | "repeat" | "auto_queue";
type RepeatFrequency = "daily" | "weekly" | "monthly";
type QueueStrategy = "earliest" | "balanced" | "engagement";

interface ScheduleConfig {
  mode: ScheduleMode;
  publishAt?: string;
  repeat?: {
    frequency: RepeatFrequency;
    until?: string;
  };
  autoQueue?: {
    start: string;
    end: string;
    strategy: QueueStrategy;
  };
}

interface AutomationConfig {
  autoPublish: boolean;
  retry: {
    enabled: boolean;
    attempts: number;
    delay: number;
  };
  notifyFailure: boolean;
}

interface Post {
  id: string;
  title: string;
  date: Date;
  time: string;
  channel: Channel;
  status: Status;
  schedule?: ScheduleConfig;
  automation?: AutomationConfig;
}

// =============================================================================
// DỮ LIỆU MINH HỌA
// =============================================================================

const DEMO_POSTS: Post[] = [
  { id: "1", title: "Khởi động Khuyến mãi Mùa hè", date: new Date(2026, 5, 6), time: "09:00", channel: "facebook", status: "scheduled" },
  { id: "2", title: "Blog: Xu hướng AI", date: new Date(2026, 5, 6), time: "14:00", channel: "website", status: "scheduled" },
  { id: "3", title: "Teaser sản phẩm", date: new Date(2026, 5, 8), time: "10:30", channel: "instagram", status: "pending" },
  { id: "4", title: "Bản tin hàng tuần", date: new Date(2026, 5, 9), time: "08:00", channel: "website", status: "draft" },
  { id: "5", title: "Cảnh báo Khuyến mãi Nhanh", date: new Date(2026, 5, 10), time: "19:30", channel: "facebook", status: "scheduled" },
  { id: "6", title: "Câu chuyện khách hàng", date: new Date(2026, 5, 12), time: "11:00", channel: "instagram", status: "scheduled" },
  { id: "7", title: "Ghi chú Cập nhật API", date: new Date(2026, 5, 15), time: "16:00", channel: "website", status: "failed" },
  { id: "8", title: "Chiến dịch Ngày lễ", date: new Date(2026, 5, 18), time: "09:00", channel: "facebook", status: "draft" },
  { id: "9", title: "Hậu trường", date: new Date(2026, 5, 20), time: "13:00", channel: "instagram", status: "pending" },
  { id: "10", title: "Tóm tắt hàng tháng", date: new Date(2026, 5, 25), time: "17:00", channel: "website", status: "scheduled" },
  { id: "11", title: "Ra mắt tính năng mới", date: new Date(2026, 5, 28), time: "10:00", channel: "facebook", status: "scheduled" },
];

// =============================================================================
// MỆNH GIÁ PHONG CÁCH
// =============================================================================

const C = {
  text: { primary: "#111827", secondary: "#374151", muted: "#6b7280", subtle: "#9ca3af" },
  border: "#e5e7eb", borderLight: "#f3f4f6",
  bg: { page: "#fff", subtle: "#f9fafb", hover: "#f3f4f6" },
  accent: "#111827",
  channel: {
    facebook: { color: "#1877F2", bg: "#E7F0FE" },
    website: { color: "#0EA5E9", bg: "#E0F2FE" },
    instagram: { color: "#E4405F", bg: "#FCE7F3" },
  },
  status: {
    scheduled: { dot: "#22c55e", bg: "#f0fdf4", text: "#166534" },
    pending: { dot: "#f59e0b", bg: "#fffbeb", text: "#92400e" },
    draft: { dot: "#6b7280", bg: "#f9fafb", text: "#374151" },
    failed: { dot: "#ef4444", bg: "#fef2f2", text: "#991b1b" },
  },
  danger: "#dc2626", dangerBg: "#fef2f2", dangerBorder: "#fecaca",
};

const S = {
  row: { display: "flex", alignItems: "center" } as React.CSSProperties,
  col: { display: "flex", flexDirection: "column" } as React.CSSProperties,
  sectionLabel: { fontSize: 10, fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: 0.5, color: C.text.subtle } as React.CSSProperties,
  input: {
    padding: "7px 10px", borderRadius: 6, border: `1px solid ${C.border}`,
    fontSize: 13, outline: "none", background: C.bg.subtle, color: C.text.primary,
    transition: "border-color 0.15s, box-shadow 0.15s",
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  } as React.CSSProperties,
  btn: {
    display: "flex", alignItems: "center", gap: 8,
    padding: "8px 14px", borderRadius: 8, border: `1px solid ${C.border}`,
    fontSize: 13, fontWeight: 500, cursor: "pointer",
    background: C.bg.page, color: C.text.secondary,
    transition: "all 0.12s ease", fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  } as React.CSSProperties,
  btnPrimary: { background: C.accent, color: "#fff", borderColor: C.accent } as React.CSSProperties,
  btnDanger: { background: C.dangerBg, color: C.danger, borderColor: C.dangerBorder } as React.CSSProperties,
  tag: { display: "inline-flex", alignItems: "center", gap: 4, padding: "3px 8px", borderRadius: 5, fontSize: 11, fontWeight: 500, whiteSpace: "nowrap" as const, overflow: "hidden", textOverflow: "ellipsis" } as React.CSSProperties,
};

// =============================================================================
// HỖ TRỢ
// =============================================================================

function getChannelMeta(ch: Channel) {
  const m = C.channel[ch];
  const icons: Record<Channel, React.ReactNode> = {
    facebook: <I.Facebook s={12} />,
    website: <I.Globe s={12} />,
    instagram: <I.Instagram s={12} />,
  };
  const labels: Record<Channel, string> = {
    facebook: "Facebook",
    website: "Trang web",
    instagram: "Instagram",
  };
  return { ...m, icon: icons[ch], label: labels[ch] };
}

function getStatusBadge(st: Status) {
  const m = C.status[st];
  const labels: Record<Status, string> = {
    scheduled: "Đã lên lịch",
    pending: "Đang chờ",
    draft: "Bản nháp",
    failed: "Thất bại",
  };
  return (
    <span style={{ ...S.tag, background: m.bg, color: m.text, padding: "2px 8px" }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: m.dot, flexShrink: 0 }} />
      {labels[st]}
    </span>
  );
}

// =============================================================================
// NGUYÊN THỦY UI CHUNG
// =============================================================================

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label style={{ ...S.row, gap: 10, cursor: "pointer" }}>
      <button
        onClick={() => onChange(!checked)}
        style={{
          width: 36, height: 20, borderRadius: 10, border: "none",
          background: checked ? C.accent : "#d1d5db", cursor: "pointer",
          position: "relative", transition: "background 0.15s ease", flexShrink: 0,
        }}
      >
        <span style={{
          position: "absolute", top: 2, left: checked ? 18 : 2,
          width: 16, height: 16, borderRadius: "50%", background: "#fff",
          transition: "left 0.15s ease", boxShadow: "0 1px 2px rgba(0,0,0,0.15)",
        }} />
      </button>
      <span style={{ fontSize: 13, fontWeight: 500, color: C.text.secondary }}>{label}</span>
    </label>
  );
}

function SectionHeader({ title, icon, open, onToggle }: { title: string; icon: React.ReactNode; open: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      style={{ ...S.row, gap: 8, width: "100%", padding: "10px 0", border: "none", background: "transparent", cursor: "pointer", color: C.text.primary }}
    >
      <span style={{ color: C.text.subtle, transition: "transform 0.15s ease", transform: open ? "rotate(180deg)" : "rotate(0deg)" }}>
        <I.ChevronDown s={14} />
      </span>
      <span style={{ color: C.text.subtle }}>{icon}</span>
      <span style={{ fontSize: 13, fontWeight: 700 }}>{title}</span>
    </button>
  );
}

function InputRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ ...S.row, gap: 12, justifyContent: "space-between" }}>
      <span style={{ fontSize: 12, fontWeight: 500, color: C.text.secondary, minWidth: 80 }}>{label}</span>
      {children}
    </div>
  );
}

// =============================================================================
// PHẦN LỊCH
// =============================================================================

function ScheduleSection({ config, onChange }: {
  config: ScheduleConfig | undefined;
  onChange: (c: ScheduleConfig) => void;
}) {
  const mode = config?.mode ?? "once";
  const setMode = (m: ScheduleMode) => onChange({ ...config, mode: m } as ScheduleConfig);

  const modes: { key: ScheduleMode; label: string; icon: React.ReactNode }[] = [
    { key: "once", label: "Xuất bản một lần", icon: <I.Play s={13} /> },
    { key: "repeat", label: "Lặp lại", icon: <I.Repeat s={13} /> },
    { key: "auto_queue", label: "Hàng đợi tự động", icon: <I.Zap s={13} /> },
  ];

  const getRepeatPreview = (): string[] => {
    if (!config?.repeat) return [];
    const base = config.publishAt ? new Date(config.publishAt) : new Date();
    const out: string[] = [];
    for (let i = 0; i < 5; i++) {
      let d = new Date(base);
      if (config.repeat!.frequency === "daily") d = addDays(d, i + 1);
      else if (config.repeat!.frequency === "weekly") d = addWeeks(d, i + 1);
      else d = addMonths(d, i + 1);
      out.push(format(d, "dd/MM/yyyy"));
      if (config.repeat!.until && d > new Date(config.repeat!.until)) break;
    }
    return out;
  };

  const getQueuePreview = (): string[] => {
    if (!config?.autoQueue) return [];
    const base = new Date();
    const out: string[] = [];
    for (let i = 0; i < 5; i++) {
      const d = addDays(base, i + 1);
      const slot = config.autoQueue!.strategy === "earliest" ? "09:00" :
                   config.autoQueue!.strategy === "engagement" ? "19:00" : "14:00";
      out.push(`${format(d, "dd/MM/yyyy")} @ ${slot}`);
    }
    return out;
  };

  return (
    <div style={{ ...S.col, gap: 14 }}>
      <div className="schedule-modes-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>
        {modes.map((m) => (
          <button
            key={m.key}
            onClick={() => setMode(m.key)}
            style={{
              ...S.col, alignItems: "center", gap: 4,
              padding: "10px 8px", borderRadius: 8,
              border: `1px solid ${mode === m.key ? C.accent : C.border}`,
              background: mode === m.key ? C.accent : C.bg.page,
              color: mode === m.key ? "#fff" : C.text.muted,
              cursor: "pointer", fontSize: 12, fontWeight: 600,
              transition: "all 0.12s ease",
            }}
          >
            {m.icon}
            {m.label}
          </button>
        ))}
      </div>

      {mode === "once" && (
        <div style={{ ...S.col, gap: 10 }}>
          <InputRow label="Ngày">
            <input
              type="date"
              value={config?.publishAt ? format(new Date(config.publishAt), "yyyy-MM-dd") : ""}
              onChange={(e) => onChange({ ...config, mode: "once", publishAt: e.target.value ? new Date(e.target.value).toISOString() : undefined } as ScheduleConfig)}
              style={{ ...S.input, width: 160 }}
              className="responsive-input"
            />
          </InputRow>
          <InputRow label="Giờ">
            <input
              type="time"
              value={config?.publishAt ? format(new Date(config.publishAt), "HH:mm") : ""}
              onChange={(e) => {
                const date = config?.publishAt ? new Date(config.publishAt) : new Date();
                const [h, min] = e.target.value.split(":").map(Number);
                date.setHours(h, min);
                onChange({ ...config, mode: "once", publishAt: date.toISOString() } as ScheduleConfig);
              }}
              style={{ ...S.input, width: 120 }}
              className="responsive-input"
            />
          </InputRow>
        </div>
      )}

      {mode === "repeat" && (
        <div style={{ ...S.col, gap: 10 }}>
          <InputRow label="Tần suất">
            <select
              value={config?.repeat?.frequency ?? "weekly"}
              onChange={(e) => onChange({
                ...config, mode: "repeat",
                repeat: { ...config?.repeat, frequency: e.target.value as RepeatFrequency },
              } as ScheduleConfig)}
              style={{ ...S.input, width: 140 }}
              className="responsive-input"
            >
              <option value="daily">Hàng ngày</option>
              <option value="weekly">Hàng tuần</option>
              <option value="monthly">Hàng tháng</option>
            </select>
          </InputRow>
          <InputRow label="Cho đến">
            <input
              type="date"
              value={config?.repeat?.until ? format(new Date(config.repeat.until), "yyyy-MM-dd") : ""}
              onChange={(e) => onChange({
                ...config, mode: "repeat",
                repeat: { ...config?.repeat, until: e.target.value },
              } as ScheduleConfig)}
              style={{ ...S.input, width: 160 }}
              className="responsive-input"
            />
          </InputRow>
          <div style={{ ...S.col, gap: 6, padding: "10px 12px", borderRadius: 8, background: C.bg.subtle }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: C.text.subtle }}>5 lần xuất hiện tiếp theo</span>
            {getRepeatPreview().map((d, i) => (
              <span key={i} style={{ fontSize: 12, color: C.text.secondary }}>• {d}</span>
            ))}
            {getRepeatPreview().length === 0 && <span style={{ fontSize: 12, color: C.text.subtle, fontStyle: "italic" }}>Đặt ngày để xem trước</span>}
          </div>
        </div>
      )}

      {mode === "auto_queue" && (
        <div style={{ ...S.col, gap: 10 }}>
          <div className="queue-hours-row" style={{ ...S.row, gap: 10 }}>
            <InputRow label="Bắt đầu">
              <input
                type="time"
                value={config?.autoQueue?.start ?? "09:00"}
                onChange={(e) => onChange({
                  ...config, mode: "auto_queue",
                  autoQueue: { ...config?.autoQueue, start: e.target.value },
                } as ScheduleConfig)}
                style={{ ...S.input, width: 100 }}
                className="responsive-input"
              />
            </InputRow>
            <InputRow label="Kết thúc">
              <input
                type="time"
                value={config?.autoQueue?.end ?? "20:00"}
                onChange={(e) => onChange({
                  ...config, mode: "auto_queue",
                  autoQueue: { ...config?.autoQueue, end: e.target.value },
                } as ScheduleConfig)}
                style={{ ...S.input, width: 100 }}
                className="responsive-input"
              />
            </InputRow>
          </div>
          <InputRow label="Chiến lược">
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
              {(["earliest", "balanced", "engagement"] as QueueStrategy[]).map((s) => {
                const strategyLabels: Record<QueueStrategy, string> = {
                  earliest: "Sớm nhất",
                  balanced: "Cân bằng",
                  engagement: "Tương tác cao",
                };
                return (
                  <button
                    key={s}
                    onClick={() => onChange({
                      ...config, mode: "auto_queue",
                      autoQueue: { ...config?.autoQueue, strategy: s },
                    } as ScheduleConfig)}
                    style={{
                      padding: "5px 10px", borderRadius: 6,
                      border: `1px solid ${config?.autoQueue?.strategy === s ? C.accent : C.border}`,
                      background: config?.autoQueue?.strategy === s ? C.accent : C.bg.page,
                      color: config?.autoQueue?.strategy === s ? "#fff" : C.text.muted,
                      fontSize: 11, fontWeight: 600, cursor: "pointer",
                      transition: "all 0.12s ease",
                    }}
                  >
                    {strategyLabels[s]}
                  </button>
                );
              })}
            </div>
          </InputRow>
          <div style={{ ...S.col, gap: 6, padding: "10px 12px", borderRadius: 8, background: C.bg.subtle }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: C.text.subtle }}>Các slot được tạo</span>
            {getQueuePreview().map((d, i) => (
              <span key={i} style={{ fontSize: 12, color: C.text.secondary }}>• {d}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// PHẦN TỰ ĐỘNG HÓA
// =============================================================================

function AutomationSection({ config, onChange }: {
  config: AutomationConfig | undefined;
  onChange: (c: AutomationConfig) => void;
}) {
  const auto = config ?? { autoPublish: false, retry: { enabled: false, attempts: 3, delay: 15 }, notifyFailure: false };

  return (
    <div style={{ ...S.col, gap: 14 }}>
      <Toggle checked={auto.autoPublish} onChange={(v) => onChange({ ...auto, autoPublish: v })} label="Xuất bản tự động" />
      <Toggle checked={auto.retry.enabled} onChange={(v) => onChange({ ...auto, retry: { ...auto.retry, enabled: v } })} label="Thử lại nếu thất bại" />
      {auto.retry.enabled && (
        <div className="automation-retry-box" style={{ ...S.col, gap: 10, padding: "12px 14px", borderRadius: 8, background: C.bg.subtle, marginLeft: 46 }}>
          <InputRow label="Nỗ lực">
            <input
              type="number" min={1} max={10}
              value={auto.retry.attempts}
              onChange={(e) => onChange({ ...auto, retry: { ...auto.retry, attempts: parseInt(e.target.value) || 1 } })}
              style={{ ...S.input, width: 60, textAlign: "center" }}
            />
          </InputRow>
          <InputRow label="Độ trễ">
            <div style={{ ...S.row, gap: 6 }}>
              <input
                type="number" min={5} max={120} step={5}
                value={auto.retry.delay}
                onChange={(e) => onChange({ ...auto, retry: { ...auto.retry, delay: parseInt(e.target.value) || 15 } })}
                style={{ ...S.input, width: 70, textAlign: "center" }}
              />
              <span style={{ fontSize: 12, color: C.text.muted }}>phút</span>
            </div>
          </InputRow>
        </div>
      )}
      <Toggle checked={auto.notifyFailure} onChange={(v) => onChange({ ...auto, notifyFailure: v })} label="Thông báo khi thất bại" />
    </div>
  );
}

// =============================================================================
// NÚT HÀNH ĐỘNG
// =============================================================================

function ActionBtn({ icon, label, onClick, primary, danger }: { icon: React.ReactNode; label: string; onClick: () => void; primary?: boolean; danger?: boolean }) {
  const base = { ...S.btn, width: "100%" };
  let finalStyle: React.CSSProperties = { ...base };
  if (primary) finalStyle = { ...finalStyle, ...S.btnPrimary };
  if (danger) finalStyle = { ...finalStyle, ...S.btnDanger };

  return (
    <button onClick={onClick} style={finalStyle}>
      {icon}
      <span>{label}</span>
    </button>
  );
}

// =============================================================================
// NGĂN KÉO
// =============================================================================

function Drawer({ post, onClose, onEdit, onDuplicate, onPublishNow, onDelete, onUpdatePost }: {
  post: Post | null;
  onClose: () => void;
  onEdit: (post: Post) => void;
  onDuplicate: (post: Post) => void;
  onPublishNow: (post: Post) => void;
  onDelete: (post: Post) => void;
  onUpdatePost: (post: Post) => void;
}) {
  if (!post) return null;

  const chMeta = getChannelMeta(post.channel);
  const [openSections, setOpenSections] = useState({ overview: true, schedule: true, automation: false, actions: true });
  const toggleSection = (k: keyof typeof openSections) => setOpenSections((p) => ({ ...p, [k]: !p[k] }));

  const [draftSchedule, setDraftSchedule] = useState<ScheduleConfig | undefined>(post.schedule);
  const [draftAutomation, setDraftAutomation] = useState<AutomationConfig | undefined>(post.automation);

  React.useEffect(() => {
    setDraftSchedule(post.schedule);
    setDraftAutomation(post.automation);
  }, [post.id, post.schedule, post.automation]);

  const handleSave = () => {
    onUpdatePost({ ...post, schedule: draftSchedule, automation: draftAutomation });
  };

  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.25)", zIndex: 40, animation: "fadeIn 0.15s ease" }} />
      <div className="drawer-container" style={{
        position: "fixed", top: 0, right: 0, bottom: 0, width: 420,
        background: C.bg.page, zIndex: 50,
        boxShadow: "-4px 0 24px rgba(0,0,0,0.08)",
        display: "flex", flexDirection: "column",
        animation: "slideIn 0.2s cubic-bezier(0.16,1,0.3,1)",
      }}>
        <div style={{ ...S.row, justifyContent: "space-between", padding: "16px 20px", borderBottom: `1px solid ${C.borderLight}` }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: C.text.primary }}>Chi tiết bài đăng</span>
          <button onClick={onClose} style={{ padding: 4, borderRadius: 6, border: "none", background: "transparent", cursor: "pointer", color: C.text.subtle }}>
            <I.X s={18} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "0 20px 20px", display: "flex", flexDirection: "column", gap: 4 }}>

          {/* PHẦN: Tổng quan */}
          <SectionHeader title="Tổng quan" icon={<I.Calendar s={14} />} open={openSections.overview} onToggle={() => toggleSection("overview")} />
          {openSections.overview && (
            <div style={{ ...S.col, gap: 16, paddingBottom: 16, borderBottom: `1px solid ${C.borderLight}` }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: C.text.primary, margin: 0, lineHeight: 1.3 }}>{post.title}</h2>
              <div style={{ ...S.col, gap: 8 }}>
                <span style={S.sectionLabel}>Trạng thái</span>
                <div>{getStatusBadge(post.status)}</div>
              </div>
              <div style={{ ...S.col, gap: 8 }}>
                <span style={S.sectionLabel}>Kênh</span>
                <span style={{ ...S.row, gap: 8, padding: "6px 12px", borderRadius: 8, background: chMeta.bg, color: chMeta.color, fontSize: 13, fontWeight: 600, width: "fit-content" }}>
                  {chMeta.icon} {chMeta.label}
                </span>
              </div>
              <div style={{ ...S.col, gap: 8 }}>
                <span style={S.sectionLabel}>Xuất bản</span>
                <div style={{ ...S.row, gap: 8, fontSize: 14, color: C.text.secondary }}>
                  <I.Calendar s={16} />
                  <span>{format(post.date, "dd/MM/yyyy")}</span>
                  <span style={{ color: C.border }}>|</span>
                  <I.Clock s={16} />
                  <span>{post.time}</span>
                </div>
              </div>
            </div>
          )}

          {/* PHẦN: Lịch */}
          <SectionHeader title="Lịch" icon={<I.Repeat s={14} />} open={openSections.schedule} onToggle={() => toggleSection("schedule")} />
          {openSections.schedule && (
            <div style={{ paddingBottom: 16, borderBottom: `1px solid ${C.borderLight}` }}>
              <ScheduleSection config={draftSchedule} onChange={setDraftSchedule} />
            </div>
          )}

          {/* PHẦN: Tự động hóa */}
          <SectionHeader title="Tự động hóa" icon={<I.Zap s={14} />} open={openSections.automation} onToggle={() => toggleSection("automation")} />
          {openSections.automation && (
            <div style={{ paddingBottom: 16, borderBottom: `1px solid ${C.borderLight}` }}>
              <AutomationSection config={draftAutomation} onChange={setDraftAutomation} />
            </div>
          )}

          {/* PHẦN: Hành động */}
          <SectionHeader title="Hành động" icon={<I.Settings s={14} />} open={openSections.actions} onToggle={() => toggleSection("actions")} />
          {openSections.actions && (
            <div style={{ ...S.col, gap: 6, paddingBottom: 16 }}>
              <ActionBtn icon={<I.Pencil s={14} />} label="Chỉnh sửa" onClick={() => onEdit(post)} />
              <ActionBtn icon={<I.Copy s={14} />} label="Sao chép" onClick={() => onDuplicate(post)} />
              <ActionBtn icon={<I.Rocket s={14} />} label="Xuất bản ngay" primary onClick={() => onPublishNow(post)} />
              <ActionBtn icon={<I.Trash s={14} />} label="Xóa" danger onClick={() => onDelete(post)} />
            </div>
          )}
        </div>

        <div style={{ padding: "12px 20px", borderTop: `1px solid ${C.borderLight}`, background: C.bg.subtle }}>
          <button onClick={handleSave} style={{ ...S.btn, ...S.btnPrimary, width: "100%", justifyContent: "center" }}>
            <I.Check s={14} /> Lưu thay đổi
          </button>
        </div>
      </div>
    </>
  );
}


import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/planner')({
  component: CalendarDashboard,
})

// =============================================================================
// THÀNH PHẦN BẢNG ĐIỀU KHIỂN LỊCH CHÍNH
// =============================================================================

export default function CalendarDashboard() {
  const [posts, setPosts] = useState<Post[]>(DEMO_POSTS);
  const [currentDate, setCurrentDate] = useState<Date>(new Date(2026, 5, 6));
  const [viewMode, setViewMode] = useState<ViewMode>("month");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedChannel, setSelectedChannel] = useState<string>("all");
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);

  const handlePrev = () => {
    if (viewMode === "month") setCurrentDate(subMonths(currentDate, 1));
    else if (viewMode === "week") setCurrentDate(addWeeks(currentDate, -1));
  };

  const handleNext = () => {
    if (viewMode === "month") setCurrentDate(addMonths(currentDate, 1));
    else if (viewMode === "week") setCurrentDate(addWeeks(currentDate, 1));
  };

  const filteredPosts = useMemo(() => {
    return posts.filter(post => {
      const matchesSearch = post.title.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesChannel = selectedChannel === "all" || post.channel === selectedChannel;
      return matchesSearch && matchesChannel;
    });
  }, [posts, searchQuery, selectedChannel]);

  const handleUpdatePost = useCallback((updatedPost: Post) => {
    setPosts(prev => prev.map(p => p.id === updatedPost.id ? updatedPost : p));
    setSelectedPost(updatedPost);
  }, []);

  const handleDuplicate = useCallback((post: Post) => {
    const duplicated: Post = {
      ...post,
      id: Math.random().toString(36).substr(2, 9),
      title: `${post.title} (Bản sao)`,
      status: "draft"
    };
    setPosts(prev => [...prev, duplicated]);
    setSelectedPost(null);
  }, []);

  const handlePublishNow = useCallback((post: Post) => {
    setPosts(prev => prev.map(p => p.id === post.id ? { ...p, status: "scheduled" as Status } : p));
    setSelectedPost(null);
    alert(`Đang xuất bản "${post.title}" ngay!`);
  }, []);

  const handleDelete = useCallback((post: Post) => {
    if (confirm("Bạn có chắc chắn muốn xóa bài đăng này không?")) {
      setPosts(prev => prev.filter(p => p.id !== post.id));
      setSelectedPost(null);
    }
  }, []);

  const renderMonthCells = () => {
    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(monthStart);
    const startDate = startOfWeek(monthStart);
    const endDate = endOfWeek(monthEnd);

    const rows = [];
    let days = [];
    let day = startDate;

    while (day <= endDate) {
      for (let i = 0; i < 7; i++) {
        const cloneDay = day;
        const dayPosts = filteredPosts.filter(p => isSameDay(p.date, cloneDay));
        const isCurrentMonth = isSameMonth(cloneDay, monthStart);

        days.push(
          <div
            key={cloneDay.toString()}
            style={{
              flex: 1, minHeight: 100, padding: 6,
              borderRight: `1px solid ${C.borderLight}`, borderBottom: `1px solid ${C.borderLight}`,
              background: isCurrentMonth ? C.bg.page : C.bg.subtle,
              opacity: isCurrentMonth ? 1 : 0.5,
              position: "relative"
            }}
            className="calendar-day-cell"
          >
            <span style={{
              fontSize: 12, fontWeight: 600,
              color: isToday(cloneDay) ? "#fff" : C.text.primary,
              background: isToday(cloneDay) ? C.accent : "transparent",
              padding: isToday(cloneDay) ? "2px 6px" : "0", borderRadius: 4
            }}>
              {format(cloneDay, "d")}
            </span>
            <div style={{ ...S.col, gap: 4, marginTop: 6 }} className="calendar-posts-container">
              {dayPosts.map(p => {
                const meta = getChannelMeta(p.channel);
                return (
                  <div
                    key={p.id}
                    onClick={() => setSelectedPost(p)}
                    style={{
                      ...S.tag, background: meta.bg, color: meta.color,
                      cursor: "pointer", width: "100%", display: "block"
                    }}
                    className="calendar-post-badge"
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      {meta.icon}
                      <span className="post-title-text" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.title}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
        day = addDays(day, 1);
      }
      rows.push(
        <div key={day.toString()} style={{ display: "flex", width: "100%" }}>
          {days}
        </div>
      );
      days = [];
    }
    return <div style={{ display: "flex", flexDirection: "column", borderLeft: `1px solid ${C.borderLight}`, borderTop: `1px solid ${C.borderLight}` }}>{rows}</div>;
  };

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif", maxWidth: 1200, margin: "0 auto" }} className="dashboard-root">
      {/* Thanh điều khiển trên cùng */}
      <div className="controls-header" style={{ ...S.row, justifyContent: "space-between", marginBottom: 20, gap: 12, flexWrap: "wrap" }}>
        <div className="header-nav-group" style={{ ...S.row, gap: 12 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: C.text.primary, margin: 0 }}>
            {format(currentDate, "MMMM yyyy")}
          </h1>
          <div style={{ ...S.row, gap: 4, border: `1px solid ${C.border}`, borderRadius: 8, padding: 2 }}>
            <button onClick={handlePrev} style={{ ...S.btn, padding: 6, border: "none" }}><I.ChevronLeft s={16} /></button>
            <button onClick={() => setCurrentDate(new Date())} style={{ ...S.btn, padding: "6px 12px", border: "none" }}>Hôm nay</button>
            <button onClick={handleNext} style={{ ...S.btn, padding: 6, border: "none" }}><I.ChevronRight s={16} /></button>
          </div>
        </div>

        {/* Bộ lọc */}
        <div className="filters-group" style={{ ...S.row, gap: 8, flexWrap: "wrap" }}>
          <div style={{ ...S.row, gap: 6, position: "relative" }} className="search-wrapper">
            <input
              type="text"
              placeholder="Tìm kiếm bài đăng..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ ...S.input, paddingLeft: 30, width: 180 }}
              className="responsive-input"
            />
            <span style={{ position: "absolute", left: 8, color: C.text.subtle, display: "flex" }}><I.Search s={14} /></span>
          </div>

          <select
            value={selectedChannel}
            onChange={(e) => setSelectedChannel(e.target.value)}
            style={S.input}
            className="responsive-input"
          >
            <option value="all">Tất cả kênh</option>
            <option value="facebook">Facebook</option>
            <option value="website">Trang web</option>
            <option value="instagram">Instagram</option>
          </select>

          <div style={{ ...S.row, gap: 2, border: `1px solid ${C.border}`, borderRadius: 8, padding: 2 }} className="viewmode-group">
            {(["month", "week", "list"] as ViewMode[]).map(mode => {
              const modeLabels: Record<ViewMode, string> = {
                month: "Tháng",
                week: "Tuần",
                list: "Danh sách",
              };
              return (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  style={{
                    ...S.btn, border: "none", padding: "6px 12px", borderRadius: 6,
                    background: viewMode === mode ? C.bg.hover : "transparent",
                    fontWeight: viewMode === mode ? 600 : 500
                  }}
                >
                  {modeLabels[mode]}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Khu vực nội dung chính */}
      <div className="main-calendar-card" style={{ background: C.bg.page, borderRadius: 12, boxShadow: "0 1px 3px rgba(0,0,0,0.05)", overflowX: "auto" }}>
        <div style={{ minWidth: 640 }}>
          {viewMode === "month" && renderMonthCells()}
        </div>
        
        {viewMode !== "month" && (
          <div style={{ padding: 40, textAlign: "center", color: C.text.muted, fontSize: 14 }}>
            Chế độ xem <b>{viewMode === "week" ? "tuần" : "danh sách"}</b> đang được phát triển nâng cao. Hãy dùng bộ lọc và lịch <b>Tháng</b> hiện tại.
          </div>
        )}
      </div>

      {/* Ngăn kéo trượt sang một bên */}
      <Drawer
        post={selectedPost}
        onClose={() => setSelectedPost(null)}
        onEdit={(p) => alert(`Chỉnh sửa: ${p.title}`)}
        onDuplicate={handleDuplicate}
        onPublishNow={handlePublishNow}
        onDelete={handleDelete}
        onUpdatePost={handleUpdatePost}
      />

      {/* CÁC TRUY VẤN PHƯƠNG TIỆN ĐÁP ỨNG TOÀN CẦU */}
      <style>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

        /* Tối ưu hóa dành cho thiết bị di động & máy tính bảng */
        @media (max-width: 768px) {
          .dashboard-root { padding: 12px !important; }
          .controls-header { flex-direction: column !important; alignItems: flex-start !important; gap: 16px !important; }
          .header-nav-group, .filters-group { width: 100% !important; justify-content: space-between !important; }
          .search-wrapper, .responsive-input { flex: 1 !important; width: 100% !important; }
          .viewmode-group { width: 100% !important; justify-content: display-flex !important; display: flex !important; }
          .viewmode-group button { flex: 1 !important; text-align: center !important; justify-content: center !important; }
          
          /* Điều chỉnh ô lịch cho khả năng tương thích với màn hình nhỏ */
          .calendar-day-cell { min-height: 75px !important; padding: 4px !important; }
          .calendar-post-badge { padding: 2px 4px !important; font-size: 10px !important; }
          .post-title-text { display: none !important; /* Ẩn văn bản dài trên di động, biểu tượng vẫn giữ nguyên */ }
          .calendar-post-badge div { justify-content: center !important; }

          /* Điều chỉnh ngăn kéo cho đáp ứng */
          .drawer-container { width: 100% !important; max-width: 100% !important; }
          .schedule-modes-grid { grid-template-columns: 1fr !important; gap: 8px !important; }
          .automation-retry-box { margin-left: 0 !important; }
          .queue-hours-row { flex-direction: column !important; align-items: stretch !important; }
        }
      `}</style>
    </div>
  );
}