"use client"


import {
  Mail, Smartphone, Target, FileText
} from "lucide-react"

// ─── API CONFIG ───
export const API_BASE = "http://localhost:8000/api/v1"


export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })

  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `HTTP ${res.status}`)
  }

  return res.json()
}

// ─── BACKEND TYPES ───
export type BackendStatus = "running" | "paused" | "completed" | "error"
export type PublishStatus = "pending" | "published" | "failed" | "dead_letter"

export interface SessionListItem {
  session_id: string
  status: BackendStatus
  request: string
  draft: { content?: string; metadata?: Record<string, unknown> } | null
  publish_status: PublishStatus | null
  approved: boolean | null
  usage: Record<string, unknown> | null
  error: string | null
  created_at: string
  updated_at: string
}

export interface SessionListResponse {
  items: SessionListItem[]
  total?: number
}

export interface SessionDetailResponse {
  session_id: string
  status: BackendStatus
  draft: { content?: string; metadata?: Record<string, unknown> } | null
  publish_status: PublishStatus | null
  approved: boolean | null
  usage: Record<string, unknown> | null
  error: string | null
}

export interface ChatEditResponse {
  draft: string
  usage: Record<string, unknown>
  changes?: Array<{ type: string; old: string; new: string }>
}

export interface VersionHistoryResponse {
  session_id: string
  versions: Array<{
    version: number
    content: string
    metadata: Record<string, unknown>
    action: string
    instruction?: string
  }>
  current_version: number
}

export interface ResumeRequest {
  action: "approve" | "reject" | "edit"
  content?: string
}

export interface ResumeResponse {
  session_id: string
  status: BackendStatus
  draft: Record<string, unknown> | null
  publish_status: string | null
  approved: boolean | null
}

// ─── FRONTEND TYPES ───
export type ContentItem = {
  id: string
  icon: "email" | "social" | "ads" | "blog"
  title: string
  type: string
  status: "draft" | "published" | "scheduled"
  preview: string
  time: string
  author?: string
  channel?: string
  content?: string
  backendStatus?: BackendStatus
  approved?: boolean
  publishStatus?: PublishStatus | null
}

export interface ChatSidebarProps {
  sessionId: string
  draftContent: string
  onUpdate: (newContent: string) => void
  isOpen: boolean
  onClose: () => void
  onEnterEditMode?: () => void
  onStreamingChange?: (isStreaming: boolean) => void
  onStreamToken?: (token: string, accumulated: string) => void
  onStreamDone?: (finalContent: string) => void
}

// ─── CONSTANTS ───
export const STATUS_STYLES = {
  draft: "bg-amber-50/60 text-amber-700 border-amber-200/60 dark:bg-amber-950/20 dark:text-amber-400 dark:border-amber-900/50",
  published: "bg-emerald-50/60 text-emerald-700 border-emerald-200/60 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-900/50",
  scheduled: "bg-blue-50/60 text-blue-700 border-blue-200/60 dark:bg-blue-950/20 dark:text-blue-400 dark:border-blue-900/50",
} as const

export const STATUS_LABELS = { draft: "Bản nháp", published: "Đã đăng", scheduled: "Lên lịch" } as const

export const ICON_BG = {
  email: "bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400",
  social: "bg-pink-50 text-pink-600 dark:bg-pink-950/50 dark:text-pink-400",
  ads: "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400",
  blog: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400",
} as const

export const TYPE_ICONS = {
  email: Mail, social: Smartphone, ads: Target, blog: FileText,
} as const

export const FILTERS = [
  { label: "Tất cả", value: "all" },
  { label: "Email", value: "Email" },
  { label: "Social", value: "Social" },
  { label: "Ads", value: "Ads" },
  { label: "Blog", value: "Blog" },
] as const

export const QUICK_PROMPTS = [
  { label: "Thêm CTA mạnh hơn", icon: "⚡" },
  { label: "Viết ngắn gọn hơn", icon: "✂️" },
  { label: "Tone thân thiện hơn", icon: "😊" },
  { label: "Thêm dẫn chứng cụ thể", icon: "📊" },
]

// ─── HELPERS: Map backend → frontend ───
export function detectType(request: string): ContentItem["icon"] {
  const r = request.toLowerCase()
  if (r.includes("email") || r.includes("mail")) return "email"
  if (r.includes("social") || r.includes("facebook") || r.includes("instagram")) return "social"
  if (r.includes("ads") || r.includes("google") || r.includes("quảng cáo")) return "ads"
  return "blog"
}

export function mapStatus(status: BackendStatus, publishStatus: PublishStatus | null, approved: boolean | null): ContentItem["status"] {
  if (status === "error" || status === "running") return "draft"
  if (publishStatus === "published") return "published"
  if (publishStatus === "pending" && approved) return "scheduled"
  return "draft"
}

export function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diff < 60) return "Vừa xong"
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`
  if (diff < 604800) return `${Math.floor(diff / 86400)} ngày trước`
  return date.toLocaleDateString("vi-VN")
}

export function generatePreview(content: string | undefined): string {
  if (!content) return "Không có nội dung"
  const text = content.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim()
  return text.slice(0, 120) + (text.length > 120 ? "..." : "")
}

export function mapSessionToContentItem(session: SessionListItem): ContentItem {
  const icon = detectType(session.request)
  const typeMap: Record<string, string> = { email: "Email", social: "Social", ads: "Ads", blog: "Blog" }

  return {
    id: session.session_id,
    icon,
    title: session.request.slice(0, 80) || "Không có tiêu đề",
    type: typeMap[icon],
    status: mapStatus(session.status, session.publish_status, session.approved),
    preview: generatePreview(session.draft?.content),
    time: formatTime(session.created_at),
    author: session.draft?.metadata?.author as string || "AI Assistant",
    channel: session.draft?.metadata?.channel as string || "Auto-generated",
    content: session.draft?.content || undefined,
    backendStatus: session.status,
    approved: session.approved || false,
    publishStatus: session.publish_status,
  }
}

