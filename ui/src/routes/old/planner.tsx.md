



"use client";


"use client";

import React, { useState, useMemo, useCallback } from "react";
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, addDays, isSameMonth, isSameDay, addMonths, subMonths, isToday } from "date-fns";
import { vi } from "date-fns/locale";


import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/planner copy')({
  component: ContentPlannerPage,
})

// ─── Icons (inline SVG, no deps) ───────────────────────────────────────────

const IconSearch = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
);
const IconChevronLeft = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
);
const IconChevronRight = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6" /></svg>
);
const IconCalendar = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>
);
const IconList = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" /><line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" /></svg>
);
const IconClock = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
);
const IconFacebook = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" /></svg>
);
const IconGlobe = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></svg>
);
const IconInstagram = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5" /><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" /><line x1="17.5" y1="6.5" x2="17.51" y2="6.5" /></svg>
);
const IconX = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
);
const IconPencil = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" /><path d="m15 5 4 4" /></svg>
);
const IconCopy = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
);
const IconRocket = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" /><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" /><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0" /><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" /></svg>
);
const IconTrash = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18" /><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" /><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" /></svg>
);

const IconFilter = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" /></svg>
);
const IconCheck = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
);
const IconAlert = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
);
const IconSpinner = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="animate-spin"><path d="M21 12a9 9 0 1 1-6.219-8.56" /></svg>
);

// ─── Types ─────────────────────────────────────────────────────────────────

type Channel = "facebook" | "website" | "instagram";
type Status = "scheduled" | "pending" | "draft" | "failed";
type ViewMode = "month" | "week" | "list";

interface Post {
  id: string;
  title: string;
  date: Date;
  time: string;
  channel: Channel;
  status: Status;
}

// ─── Demo Data ─────────────────────────────────────────────────────────────

const DEMO_POSTS: Post[] = [
  { id: "1", title: "Summer Sale Launch", date: new Date(2026, 5, 6), time: "09:00", channel: "facebook", status: "scheduled" },
  { id: "2", title: "Blog: AI Trends", date: new Date(2026, 5, 6), time: "14:00", channel: "website", status: "scheduled" },
  { id: "3", title: "Product Teaser", date: new Date(2026, 5, 8), time: "10:30", channel: "instagram", status: "pending" },
  { id: "4", title: "Weekly Newsletter", date: new Date(2026, 5, 9), time: "08:00", channel: "website", status: "draft" },
  { id: "5", title: "Flash Sale Alert", date: new Date(2026, 5, 10), time: "19:30", channel: "facebook", status: "scheduled" },
  { id: "6", title: "Customer Story", date: new Date(2026, 5, 12), time: "11:00", channel: "instagram", status: "scheduled" },
  { id: "7", title: "API Update Notes", date: new Date(2026, 5, 15), time: "16:00", channel: "website", status: "failed" },
  { id: "8", title: "Holiday Campaign", date: new Date(2026, 5, 18), time: "09:00", channel: "facebook", status: "draft" },
  { id: "9", title: "Behind the Scenes", date: new Date(2026, 5, 20), time: "13:00", channel: "instagram", status: "pending" },
  { id: "10", title: "Monthly Recap", date: new Date(2026, 5, 25), time: "17:00", channel: "website", status: "scheduled" },
  { id: "11", title: "New Feature Drop", date: new Date(2026, 5, 28), time: "10:00", channel: "facebook", status: "scheduled" },
];

// ─── Helpers ───────────────────────────────────────────────────────────────

const CHANNEL_META: Record<Channel, { label: string; icon: React.ReactNode; color: string; bg: string }> = {
  facebook: { label: "Facebook", icon: <IconFacebook size={12} />, color: "#1877F2", bg: "#E7F0FE" },
  website: { label: "Website", icon: <IconGlobe size={12} />, color: "#0EA5E9", bg: "#E0F2FE" },
  instagram: { label: "Instagram", icon: <IconInstagram size={12} />, color: "#E4405F", bg: "#FCE7F3" },
};

const STATUS_META: Record<Status, { label: string; dot: string; bg: string; text: string }> = {
  scheduled: { label: "Scheduled", dot: "#22c55e", bg: "#f0fdf4", text: "#166534" },
  pending: { label: "Pending", dot: "#f59e0b", bg: "#fffbeb", text: "#92400e" },
  draft: { label: "Draft", dot: "#6b7280", bg: "#f9fafb", text: "#374151" },
  failed: { label: "Failed", dot: "#ef4444", bg: "#fef2f2", text: "#991b1b" },
};



function getStatusBadge(status: Status) {
  const meta = STATUS_META[status];
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      fontSize: 11, fontWeight: 500, padding: "2px 8px", borderRadius: 999,
      background: meta.bg, color: meta.text,
    }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: meta.dot }} />
      {meta.label}
    </span>
  );
}

// ─── Sub-Components ────────────────────────────────────────────────────────

function ViewToggle({ view, onChange }: { view: ViewMode; onChange: (v: ViewMode) => void }) {
  const options: { key: ViewMode; label: string; icon: React.ReactNode }[] = [
    { key: "month", label: "Month", icon: <IconCalendar size={14} /> },
    { key: "week", label: "Week", icon: <IconCalendar size={14} /> },
    { key: "list", label: "List", icon: <IconList size={14} /> },
  ];
  return (
    <div style={{ display: "flex", gap: 2, background: "#f3f4f6", padding: 2, borderRadius: 8 }}>
      {options.map((opt) => (
        <button
          key={opt.key}
          onClick={() => onChange(opt.key)}
          style={{
            display: "flex", alignItems: "center", gap: 4,
            padding: "6px 12px", borderRadius: 6, border: "none",
            fontSize: 13, fontWeight: 500, cursor: "pointer",
            background: view === opt.key ? "#fff" : "transparent",
            color: view === opt.key ? "#111827" : "#6b7280",
            boxShadow: view === opt.key ? "0 1px 2px rgba(0,0,0,0.06)" : "none",
            transition: "all 0.15s ease",
          }}
        >
          {opt.icon} {opt.label}
        </button>
      ))}
    </div>
  );
}

function FilterPill({ label, active, count, onClick }: { label: string; active: boolean; count: number; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: 6,
        padding: "5px 12px", borderRadius: 8, border: "1px solid",
        fontSize: 12, fontWeight: 500, cursor: "pointer",
        background: active ? "#111827" : "#fff",
        color: active ? "#fff" : "#374151",
        borderColor: active ? "#111827" : "#e5e7eb",
        transition: "all 0.15s ease",
      }}
    >
      {label}
      <span style={{
        display: "inline-flex", alignItems: "center", justifyContent: "center",
        minWidth: 18, height: 18, padding: "0 5px", borderRadius: 999,
        fontSize: 11, fontWeight: 600,
        background: active ? "rgba(255,255,255,0.2)" : "#f3f4f6",
        color: active ? "#fff" : "#6b7280",
      }}>
        {count}
      </span>
    </button>
  );
}

function ChannelFilter({ channels, selected, onToggle }: { channels: Channel[]; selected: Set<Channel>; onToggle: (c: Channel) => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <span style={{ fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5, color: "#9ca3af", paddingLeft: 4 }}>
        Channels
      </span>
      {channels.map((ch) => {
        const meta = CHANNEL_META[ch];
        const isActive = selected.has(ch);
        return (
          <button
            key={ch}
            onClick={() => onToggle(ch)}
            style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "6px 10px", borderRadius: 6, border: "none",
              fontSize: 13, fontWeight: 500, cursor: "pointer", textAlign: "left",
              background: isActive ? meta.bg : "transparent",
              color: isActive ? meta.color : "#6b7280",
              transition: "all 0.15s ease",
            }}
          >
            {meta.icon}
            {meta.label}
            {isActive && <IconCheck size={12} />}
          </button>
        );
      })}
    </div>
  );
}

// function PostCard({ post, onClick }: { post: Post; onClick: () => void }) {
//   const meta = CHANNEL_META[post.channel];
//   const statusMeta = STATUS_META[post.status];
//   return (
//     <button
//       onClick={onClick}
//       style={{
//         display: "flex", flexDirection: "column", gap: 4,
//         width: "100%", padding: "8px 10px", borderRadius: 8,
//         border: "1px solid #e5e7eb", background: "#fff",
//         cursor: "pointer", textAlign: "left",
//         transition: "all 0.12s ease",
//       }}
//       onMouseEnter={(e) => {
//         (e.currentTarget as HTMLButtonElement).style.borderColor = "#d1d5db";
//         (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 1px 3px rgba(0,0,0,0.04)";
//       }}
//       onMouseLeave={(e) => {
//         (e.currentTarget as HTMLButtonElement).style.borderColor = "#e5e7eb";
//         (e.currentTarget as HTMLButtonElement).style.boxShadow = "none";
//       }}
//     >
//       <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
//         <span style={{ color: meta.color }}>{meta.icon}</span>
//         <span style={{ fontSize: 11, fontWeight: 500, color: "#6b7280" }}>{post.time}</span>
//       </div>
//       <span style={{ fontSize: 12, fontWeight: 600, color: "#111827", lineHeight: 1.35, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
//         {post.title}
//       </span>
//       <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 2 }}>
//         <span style={{ width: 6, height: 6, borderRadius: "50%", background: statusMeta.dot }} />
//         <span style={{ fontSize: 10, fontWeight: 500, color: "#9ca3af" }}>{statusMeta.label}</span>
//       </div>
//     </button>
//   );
// }

function Drawer({ post, onClose, onEdit, onDuplicate, onPublishNow, onDelete }: {
  post: Post | null;
  onClose: () => void;
  onEdit: (post: Post) => void;
  onDuplicate: (post: Post) => void;
  onPublishNow: (post: Post) => void;
  onDelete: (post: Post) => void;
}) {
  if (!post) return null;
  const meta = CHANNEL_META[post.channel];
  // const statusMeta = STATUS_META[post.status];

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.25)", zIndex: 40,
          animation: "fadeIn 0.15s ease",
        }}
      />
      <div
        style={{
          position: "fixed", top: 0, right: 0, bottom: 0, width: 380,
          background: "#fff", zIndex: 50,
          boxShadow: "-4px 0 24px rgba(0,0,0,0.08)",
          display: "flex", flexDirection: "column",
          animation: "slideIn 0.2s cubic-bezier(0.16,1,0.3,1)",
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 20px", borderBottom: "1px solid #f3f4f6" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#111827" }}>Post Details</span>
          <button onClick={onClose} style={{ padding: 4, borderRadius: 6, border: "none", background: "transparent", cursor: "pointer", color: "#9ca3af" }}>
            <IconX size={18} />
          </button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px", display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Title */}
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "#111827", margin: 0, lineHeight: 1.3 }}>{post.title}</h2>
          </div>

          {/* Status */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={{ fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5, color: "#9ca3af" }}>Status</span>
            <div>{getStatusBadge(post.status)}</div>
          </div>

          {/* Channel */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={{ fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5, color: "#9ca3af" }}>Channel</span>
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", borderRadius: 8, background: meta.bg, color: meta.color, fontSize: 13, fontWeight: 600, width: "fit-content" }}>
              {meta.icon} {meta.label}
            </div>
          </div>

          {/* Publish Time */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={{ fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5, color: "#9ca3af" }}>Publish</span>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, color: "#374151" }}>
              <IconCalendar size={16} />
              <span>{format(post.date, "dd/MM/yyyy")}</span>
              <span style={{ color: "#d1d5db" }}>|</span>
              <IconClock size={16} />
              <span>{post.time}</span>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={{ fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5, color: "#9ca3af" }}>Actions</span>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <ActionButton icon={<IconPencil size={14} />} label="Edit" onClick={() => onEdit(post)} />
              <ActionButton icon={<IconCopy size={14} />} label="Duplicate" onClick={() => onDuplicate(post)} />
              <ActionButton icon={<IconRocket size={14} />} label="Publish Now" primary onClick={() => onPublishNow(post)} />
              <ActionButton icon={<IconTrash size={14} />} label="Delete" danger onClick={() => onDelete(post)} />
            </div>
          </div>
        </div>
      </div>
      <style>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
      `}</style>
    </>
  );
}

function ActionButton({ icon, label, onClick, primary, danger }: { icon: React.ReactNode; label: string; onClick: () => void; primary?: boolean; danger?: boolean }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: 10,
        width: "100%", padding: "10px 14px", borderRadius: 8,
        border: "1px solid", fontSize: 13, fontWeight: 500,
        cursor: "pointer", textAlign: "left",
        background: primary ? "#111827" : danger ? "#fef2f2" : "#fff",
        color: primary ? "#fff" : danger ? "#dc2626" : "#374151",
        borderColor: primary ? "#111827" : danger ? "#fecaca" : "#e5e7eb",
        transition: "all 0.12s ease",
      }}
      onMouseEnter={(e) => {
        if (!primary) (e.currentTarget as HTMLButtonElement).style.background = danger ? "#fee2e2" : "#f9fafb";
      }}
      onMouseLeave={(e) => {
        if (!primary) (e.currentTarget as HTMLButtonElement).style.background = danger ? "#fef2f2" : "#fff";
      }}
    >
      {icon} {label}
    </button>
  );
}

// ─── Month View ──────────────────────────────────────────────────────────────

function MonthView({ currentDate, posts, onPostClick }: { currentDate: Date; posts: Post[]; onPostClick: (p: Post) => void }) {
  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(monthStart);
  const calendarStart = startOfWeek(monthStart, { weekStartsOn: 1 });
  const calendarEnd = endOfWeek(monthEnd, { weekStartsOn: 1 });

  const days: Date[] = [];
  let day = calendarStart;
  while (day <= calendarEnd) {
    days.push(day);
    day = addDays(day, 1);
  }

  const weekDays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Weekday headers */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 1, marginBottom: 8 }}>
        {weekDays.map((wd) => (
          <div key={wd} style={{ padding: "8px 0", textAlign: "center", fontSize: 11, fontWeight: 600, color: "#9ca3af", textTransform: "uppercase", letterSpacing: 0.5 }}>
            {wd}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gridAutoRows: "1fr", gap: 1, flex: 1, minHeight: 0 }}>
        {days.map((d, i) => {
          const dayPosts = posts.filter((p) => isSameDay(p.date, d));
          const inMonth = isSameMonth(d, currentDate);
          const today = isToday(d);
          return (
            <div
              key={i}
              style={{
                minHeight: 100,
                padding: "6px 8px",
                background: inMonth ? "#fff" : "#f9fafb",
                border: "1px solid #f3f4f6",
                borderRadius: 6,
                display: "flex", flexDirection: "column", gap: 4,
                overflow: "hidden",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{
                  fontSize: 13, fontWeight: 600,
                  color: today ? "#fff" : inMonth ? "#111827" : "#d1d5db",
                  background: today ? "#111827" : "transparent",
                  width: 26, height: 26, borderRadius: "50%",
                  display: "inline-flex", alignItems: "center", justifyContent: "center",
                }}>
                  {format(d, "d")}
                </span>
                {dayPosts.length > 0 && (
                  <span style={{ fontSize: 10, fontWeight: 600, color: "#9ca3af" }}>{dayPosts.length}</span>
                )}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 3, overflow: "hidden" }}>
                {dayPosts.slice(0, 3).map((post) => (
                  <button
                    key={post.id}
                    onClick={() => onPostClick(post)}
                    style={{
                      display: "flex", alignItems: "center", gap: 5,
                      padding: "3px 7px", borderRadius: 5,
                      border: "none", background: CHANNEL_META[post.channel].bg,
                      cursor: "pointer", textAlign: "left",
                      fontSize: 11, fontWeight: 500, color: CHANNEL_META[post.channel].color,
                      whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                      transition: "opacity 0.1s",
                    }}
                    title={post.title}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "0.8"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}
                  >
                    <span style={{ flexShrink: 0 }}>{CHANNEL_META[post.channel].icon}</span>
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{post.title}</span>
                  </button>
                ))}
                {dayPosts.length > 3 && (
                  <span style={{ fontSize: 10, color: "#9ca3af", paddingLeft: 4 }}>+{dayPosts.length - 3} more</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Week View ───────────────────────────────────────────────────────────────

function WeekView({ currentDate, posts, onPostClick }: { currentDate: Date; posts: Post[]; onPostClick: (p: Post) => void }) {
  const weekStart = startOfWeek(currentDate, { weekStartsOn: 1 });
  const weekDays: Date[] = [];
  for (let i = 0; i < 7; i++) weekDays.push(addDays(weekStart, i));

  const hours = Array.from({ length: 14 }, (_, i) => i + 7); // 7:00 - 20:00

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Day headers */}
      <div style={{ display: "grid", gridTemplateColumns: "60px repeat(7, 1fr)", gap: 1, marginBottom: 8, flexShrink: 0 }}>
        <div />
        {weekDays.map((d) => {
          const today = isToday(d);
          return (
            <div key={d.toISOString()} style={{ textAlign: "center", padding: "8px 0" }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#9ca3af", textTransform: "uppercase" }}>{format(d, "EEE")}</div>
              <div style={{
                fontSize: 16, fontWeight: 700,
                color: today ? "#fff" : "#111827",
                background: today ? "#111827" : "transparent",
                width: 32, height: 32, borderRadius: "50%",
                display: "inline-flex", alignItems: "center", justifyContent: "center",
                marginTop: 4,
              }}>
                {format(d, "d")}
              </div>
            </div>
          );
        })}
      </div>

      {/* Time grid */}
      <div style={{ flex: 1, overflowY: "auto", display: "grid", gridTemplateColumns: "60px repeat(7, 1fr)", gap: 1 }}>
        {hours.map((h) => (
          <React.Fragment key={h}>
            <div style={{ fontSize: 11, fontWeight: 500, color: "#9ca3af", textAlign: "right", paddingRight: 8, paddingTop: 8, borderTop: "1px solid #f3f4f6" }}>
              {h}:00
            </div>
            {weekDays.map((d) => {
              const hourPosts = posts.filter((p) => isSameDay(p.date, d) && parseInt(p.time.split(":")[0]) === h);
              return (
                <div key={`${d.toISOString()}-${h}`} style={{ borderTop: "1px solid #f3f4f6", padding: "4px 6px", minHeight: 56, background: isToday(d) ? "#fafafa" : "#fff" }}>
                  {hourPosts.map((post) => (
                    <button
                      key={post.id}
                      onClick={() => onPostClick(post)}
                      style={{
                        display: "flex", alignItems: "center", gap: 4,
                        width: "100%", padding: "4px 8px", borderRadius: 5,
                        border: "none", background: CHANNEL_META[post.channel].bg,
                        cursor: "pointer", fontSize: 11, fontWeight: 500,
                        color: CHANNEL_META[post.channel].color,
                        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                        marginBottom: 2,
                      }}
                      title={post.title}
                    >
                      {CHANNEL_META[post.channel].icon}
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{post.title}</span>
                    </button>
                  ))}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// ─── List View ───────────────────────────────────────────────────────────────

function ListView({ posts, onPostClick }: { posts: Post[]; onPostClick: (p: Post) => void }) {
  const grouped = useMemo(() => {
    const map = new Map<string, Post[]>();
    posts.forEach((p) => {
      const key = format(p.date, "yyyy-MM-dd");
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(p);
    });
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [posts]);

  if (grouped.length === 0) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 12, color: "#9ca3af" }}>
        <IconCalendar size={40} />
        <span style={{ fontSize: 14, fontWeight: 500 }}>No posts match your filters</span>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, paddingRight: 8 }}>
      {grouped.map(([dateKey, dayPosts]) => {
        const date = new Date(dateKey + "T00:00:00");
        const today = isToday(date);
        return (
          <div key={dateKey}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, paddingBottom: 8, borderBottom: "1px solid #f3f4f6" }}>
              <span style={{
                fontSize: 14, fontWeight: 700,
                color: today ? "#fff" : "#111827",
                background: today ? "#111827" : "transparent",
                width: 32, height: 32, borderRadius: "50%",
                display: "inline-flex", alignItems: "center", justifyContent: "center",
              }}>
                {format(date, "d")}
              </span>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#111827" }}>{format(date, "EEEE")}</div>
                <div style={{ fontSize: 11, color: "#9ca3af" }}>{format(date, "MMMM yyyy")}</div>
              </div>
              <span style={{ marginLeft: "auto", fontSize: 11, fontWeight: 600, color: "#9ca3af", padding: "2px 8px", background: "#f3f4f6", borderRadius: 999 }}>
                {dayPosts.length} post{dayPosts.length > 1 ? "s" : ""}
              </span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {dayPosts.map((post) => (
                <button
                  key={post.id}
                  onClick={() => onPostClick(post)}
                  style={{
                    display: "flex", alignItems: "center", gap: 14,
                    padding: "12px 16px", borderRadius: 10,
                    border: "1px solid #e5e7eb", background: "#fff",
                    cursor: "pointer", textAlign: "left",
                    transition: "all 0.12s ease",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.borderColor = "#d1d5db";
                    (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 1px 3px rgba(0,0,0,0.04)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.borderColor = "#e5e7eb";
                    (e.currentTarget as HTMLButtonElement).style.boxShadow = "none";
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 70 }}>
                    <IconClock size={14} />
                    <span style={{ fontSize: 13, fontWeight: 500, color: "#6b7280" }}>{post.time}</span>
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "#111827", marginBottom: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {post.title}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: CHANNEL_META[post.channel].color, fontWeight: 500 }}>
                        {CHANNEL_META[post.channel].icon} {CHANNEL_META[post.channel].label}
                      </span>
                      <span style={{ width: 3, height: 3, borderRadius: "50%", background: "#d1d5db" }} />
                      {getStatusBadge(post.status)}
                    </div>
                  </div>
                  <IconChevronRight size={16} />
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────

export default function ContentPlannerPage() {
  const [currentDate, setCurrentDate] = useState(new Date(2026, 5, 1));
  const [view, setView] = useState<ViewMode>("month");
  const [search, setSearch] = useState("");
  const [selectedStatuses, setSelectedStatuses] = useState<Set<Status>>(new Set());
  const [selectedChannels, setSelectedChannels] = useState<Set<Channel>>(new Set(["facebook", "website", "instagram"]));
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
  const [posts, setPosts] = useState<Post[]>(DEMO_POSTS);
  const loading = false;
  
  const [error, setError] = useState<string | null>(null);

  const allChannels: Channel[] = ["facebook", "website", "instagram"];
  const allStatuses: Status[] = ["scheduled", "pending", "draft", "failed"];

  const filteredPosts = useMemo(() => {
    return posts.filter((p) => {
      const matchSearch = p.title.toLowerCase().includes(search.toLowerCase());
      const matchStatus = selectedStatuses.size === 0 || selectedStatuses.has(p.status);
      const matchChannel = selectedChannels.has(p.channel);
      return matchSearch && matchStatus && matchChannel;
    });
  }, [posts, search, selectedStatuses, selectedChannels]);

  const statusCounts = useMemo(() => {
    const counts: Record<Status, number> = { scheduled: 0, pending: 0, draft: 0, failed: 0 };
    posts.forEach((p) => counts[p.status]++);
    return counts;
  }, [posts]);

  const toggleStatus = useCallback((s: Status) => {
    setSelectedStatuses((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  }, []);

  const toggleChannel = useCallback((c: Channel) => {
    setSelectedChannels((prev) => {
      const next = new Set(prev);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });
  }, []);

  const handleEdit = useCallback((post: Post) => {
    // Navigate to editor or open inline edit
    console.log("Edit", post.id);
    setSelectedPost(null);
  }, []);

  const handleDuplicate = useCallback((post: Post) => {
    const newPost: Post = {
      ...post,
      id: Date.now().toString(),
      title: post.title + " (Copy)",
      status: "draft",
    };
    setPosts((prev) => [...prev, newPost]);
    setSelectedPost(null);
  }, []);

  const handlePublishNow = useCallback((post: Post) => {
    setPosts((prev) => prev.map((p) => p.id === post.id ? { ...p, status: "scheduled" as Status } : p));
    setSelectedPost(null);
  }, []);

  const handleDelete = useCallback((post: Post) => {
    setPosts((prev) => prev.filter((p) => p.id !== post.id));
    setSelectedPost(null);
  }, []);

  const navigateMonth = useCallback((dir: "prev" | "next") => {
    setCurrentDate((prev) => dir === "prev" ? subMonths(prev, 1) : addMonths(prev, 1));
  }, []);

  const navigateWeek = useCallback((dir: "prev" | "next") => {
    setCurrentDate((prev) => dir === "prev" ? addDays(prev, -7) : addDays(prev, 7));
  }, []);

  const navigateToday = useCallback(() => {
    setCurrentDate(new Date());
  }, []);

  const monthLabel = format(currentDate, "MMMM yyyy", { locale: vi });

  // ─── Render ──────────────────────────────────────────────────────────────

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#fff", fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" }}>
      {/* ── Toolbar ─────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "16px 24px", borderBottom: "1px solid #f3f4f6", flexShrink: 0, flexWrap: "wrap" }}>
        {/* Search */}
        <div style={{ position: "relative", flex: "0 0 280px" }}>
          <IconSearch size={16} />
          <input
            type="text"
            placeholder="Search posts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: "100%", padding: "8px 12px 8px 34px", borderRadius: 8,
              border: "1px solid #e5e7eb", fontSize: 13, outline: "none",
              background: "#f9fafb", color: "#111827",
              transition: "border-color 0.15s, box-shadow 0.15s",
            }}
            onFocus={(e) => { e.currentTarget.style.borderColor = "#111827"; e.currentTarget.style.boxShadow = "0 0 0 3px rgba(17,24,39,0.08)"; }}
            onBlur={(e) => { e.currentTarget.style.borderColor = "#e5e7eb"; e.currentTarget.style.boxShadow = "none"; }}
          />
        </div>

        <div style={{ width: 1, height: 24, background: "#e5e7eb" }} />

        {/* Status Filters */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <IconFilter size={14} />
          {allStatuses.map((s) => (
            <FilterPill
              key={s}
              label={STATUS_META[s].label}
              active={selectedStatuses.has(s)}
              count={statusCounts[s]}
              onClick={() => toggleStatus(s)}
            />
          ))}
        </div>

        <div style={{ flex: 1 }} />

        {/* Date Navigation */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <button onClick={() => view === "month" ? navigateMonth("prev") : navigateWeek("prev")} style={{ padding: 6, borderRadius: 6, border: "1px solid #e5e7eb", background: "#fff", cursor: "pointer", color: "#6b7280", display: "flex", alignItems: "center" }}>
            <IconChevronLeft size={16} />
          </button>
          <button onClick={navigateToday} style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #e5e7eb", background: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600, color: "#374151" }}>
            Today
          </button>
          <button onClick={() => view === "month" ? navigateMonth("next") : navigateWeek("next")} style={{ padding: 6, borderRadius: 6, border: "1px solid #e5e7eb", background: "#fff", cursor: "pointer", color: "#6b7280", display: "flex", alignItems: "center" }}>
            <IconChevronRight size={16} />
          </button>
          <span style={{ fontSize: 15, fontWeight: 700, color: "#111827", minWidth: 140, textAlign: "center" }}>{monthLabel}</span>
        </div>

        <div style={{ width: 1, height: 24, background: "#e5e7eb" }} />

        {/* View Toggle */}
        <ViewToggle view={view} onChange={setView} />
      </div>

      {/* ── Main Content ────────────────────────────────────────── */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left Panel */}
        <div style={{ width: 220, flexShrink: 0, borderRight: "1px solid #f3f4f6", padding: "16px 12px", display: "flex", flexDirection: "column", gap: 20, overflowY: "auto" }}>
          <ChannelFilter channels={allChannels} selected={selectedChannels} onToggle={toggleChannel} />
        </div>

        {/* Right Panel - Calendar */}
        <div style={{ flex: 1, padding: "16px 24px 24px", overflow: "auto" }}>
          {loading ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 12, color: "#9ca3af" }}>
              <IconSpinner size={32} />
              <span style={{ fontSize: 14, fontWeight: 500 }}>Loading calendar...</span>
            </div>
          ) : error ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 12, color: "#ef4444" }}>
              <IconAlert size={32} />
              <span style={{ fontSize: 14, fontWeight: 500 }}>{error}</span>
              <button onClick={() => setError(null)} style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid #fecaca", background: "#fef2f2", color: "#dc2626", fontSize: 12, fontWeight: 500, cursor: "pointer" }}>
                Retry
              </button>
            </div>
          ) : filteredPosts.length === 0 ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16, color: "#9ca3af" }}>
              <div style={{ width: 64, height: 64, borderRadius: 16, background: "#f3f4f6", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <IconCalendar size={28} />
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 15, fontWeight: 600, color: "#374151", marginBottom: 4 }}>No posts found</div>
                <div style={{ fontSize: 13, color: "#9ca3af" }}>Try adjusting your filters or search query</div>
              </div>
              <button
                onClick={() => { setSearch(""); setSelectedStatuses(new Set()); setSelectedChannels(new Set(["facebook", "website", "instagram"])); }}
                style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 16px", borderRadius: 8, border: "1px solid #e5e7eb", background: "#fff", fontSize: 13, fontWeight: 500, color: "#374151", cursor: "pointer" }}
              >
                <IconX size={14} /> Clear filters
              </button>
            </div>
          ) : (
            <>
              {view === "month" && <MonthView currentDate={currentDate} posts={filteredPosts} onPostClick={setSelectedPost} />}
              {view === "week" && <WeekView currentDate={currentDate} posts={filteredPosts} onPostClick={setSelectedPost} />}
              {view === "list" && <ListView posts={filteredPosts} onPostClick={setSelectedPost} />}
            </>
          )}
        </div>
      </div>

      {/* ── Drawer ──────────────────────────────────────────────── */}
      {selectedPost && (
        <Drawer
          post={selectedPost}
          onClose={() => setSelectedPost(null)}
          onEdit={handleEdit}
          onDuplicate={handleDuplicate}
          onPublishNow={handlePublishNow}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}