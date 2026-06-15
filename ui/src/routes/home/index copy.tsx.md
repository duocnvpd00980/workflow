"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { useNavigate } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import {
  Mail, Smartphone, Target, FileText, Inbox,
  ChevronLeft, ChevronRight, RefreshCw, Trash2,
  Archive, Edit3, ArrowLeft, User, Radio, Clock, Plus,
  AlertCircle, Loader2, CheckCircle2, XCircle, MessageSquare,
  Send, History, Eye, ChevronDown, ChevronUp, Sparkles,
  RotateCcw, Bot, StopCircle, Clipboard, Check, X,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { createFileRoute } from "@tanstack/react-router"
import { Message, MessageContent, MessageResponse } from "@/components/ai-elements/message"
import { useMarketingRewrite } from "@/hooks/useMarketingRewrite"

// ─── API CONFIG ───
const API_BASE = "http://localhost:8000/api/v1"

async function api<T>(path: string, options?: RequestInit): Promise<T> {
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
type BackendStatus = "running" | "paused" | "completed" | "error"
type PublishStatus = "pending" | "published" | "failed" | "dead_letter"

interface SessionListItem {
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

interface SessionListResponse {
  items: SessionListItem[]
  total?: number
}

interface SessionDetailResponse {
  session_id: string
  status: BackendStatus
  draft: { content?: string; metadata?: Record<string, unknown> } | null
  publish_status: PublishStatus | null
  approved: boolean | null
  usage: Record<string, unknown> | null
  error: string | null
}

interface ChatEditResponse {
  draft: string
  usage: Record<string, unknown>
  changes?: Array<{ type: string; old: string; new: string }>
}

interface VersionHistoryResponse {
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

interface ResumeRequest {
  action: "approve" | "reject" | "edit"
  content?: string
}

interface ResumeResponse {
  session_id: string
  status: BackendStatus
  draft: Record<string, unknown> | null
  publish_status: string | null
  approved: boolean | null
}

// ─── FRONTEND TYPES ───
type ContentItem = {
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

interface ChatSidebarProps {
  sessionId: string
  draftContent: string
  onUpdate: (newContent: string) => void
  isOpen: boolean
  onClose: () => void
  onEnterEditMode?: () => void
  onStreamingChange?: (isStreaming: boolean) => void
  /** Called for every token — so DetailView can stream into the editor in real-time */
  onStreamToken?: (token: string, accumulated: string) => void
  /** Called when streaming fully completes */
  onStreamDone?: (finalContent: string) => void
}

// ─── CONSTANTS ───
const STATUS_STYLES = {
  draft: "bg-amber-50/60 text-amber-700 border-amber-200/60 dark:bg-amber-950/20 dark:text-amber-400 dark:border-amber-900/50",
  published: "bg-emerald-50/60 text-emerald-700 border-emerald-200/60 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-900/50",
  scheduled: "bg-blue-50/60 text-blue-700 border-blue-200/60 dark:bg-blue-950/20 dark:text-blue-400 dark:border-blue-900/50",
} as const

const STATUS_LABELS = { draft: "Bản nháp", published: "Đã đăng", scheduled: "Lên lịch" } as const

const ICON_BG = {
  email: "bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400",
  social: "bg-pink-50 text-pink-600 dark:bg-pink-950/50 dark:text-pink-400",
  ads: "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400",
  blog: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400",
} as const

const TYPE_ICONS = {
  email: Mail, social: Smartphone, ads: Target, blog: FileText,
} as const

const FILTERS = [
  { label: "Tất cả", value: "all" },
  { label: "Email", value: "Email" },
  { label: "Social", value: "Social" },
  { label: "Ads", value: "Ads" },
  { label: "Blog", value: "Blog" },
] as const

const QUICK_PROMPTS = [
  { label: "Thêm CTA mạnh hơn", icon: "⚡" },
  { label: "Viết ngắn gọn hơn", icon: "✂️" },
  { label: "Tone thân thiện hơn", icon: "😊" },
  { label: "Thêm dẫn chứng cụ thể", icon: "📊" },
]

// ─── HELPERS: Map backend → frontend ───
function detectType(request: string): ContentItem["icon"] {
  const r = request.toLowerCase()
  if (r.includes("email") || r.includes("mail")) return "email"
  if (r.includes("social") || r.includes("facebook") || r.includes("instagram")) return "social"
  if (r.includes("ads") || r.includes("google") || r.includes("quảng cáo")) return "ads"
  return "blog"
}

function mapStatus(status: BackendStatus, publishStatus: PublishStatus | null, approved: boolean | null): ContentItem["status"] {
  if (status === "error" || status === "running") return "draft"
  if (publishStatus === "published") return "published"
  if (publishStatus === "pending" && approved) return "scheduled"
  return "draft"
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diff < 60) return "Vừa xong"
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`
  if (diff < 604800) return `${Math.floor(diff / 86400)} ngày trước`
  return date.toLocaleDateString("vi-VN")
}

function generatePreview(content: string | undefined): string {
  if (!content) return "Không có nội dung"
  const text = content.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim()
  return text.slice(0, 120) + (text.length > 120 ? "..." : "")
}

function mapSessionToContentItem(session: SessionListItem): ContentItem {
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

// ─── SHARED COMPONENTS ───
function StatusBadge({ status }: { status: ContentItem["status"] }) {
  return (
    <Badge variant="outline" className={cn("text-[11px] font-medium px-2 py-0.5 rounded-full select-none", STATUS_STYLES[status])}>
      {STATUS_LABELS[status]}
    </Badge>
  )
}

function TypeIcon({ icon, className }: { icon: ContentItem["icon"]; className?: string }) {
  const Icon = TYPE_ICONS[icon] || Mail
  return (
    <span className={cn("inline-flex items-center justify-center w-7 h-7 rounded-lg flex-shrink-0 transition-transform duration-250 group-hover:scale-105", ICON_BG[icon], className)}>
      <Icon className="h-3.5 w-3.5" />
    </span>
  )
}

// ─── LIST VIEW ───
function ListView({
  items,
  onSelect,
  onRefresh,
  onDelete,
  onArchive,
  isDeleting,
  deletingIds,
}: {
  items: ContentItem[]
  onSelect: (id: string) => void
  onRefresh: () => void
  onDelete: (ids: string[]) => void
  onArchive: (ids: string[]) => void
  isDeleting: boolean
  deletingIds: Set<string>
}) {
  const [filter, setFilter] = useState("all")
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const filtered = filter === "all" ? items : items.filter((i) => i.type === filter)

  const toggleOne = (id: string, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (checked) next.add(id)
      else next.delete(id)
      return next
    })
  }

  const toggleAll = (checked: boolean) => {
    setSelected(checked ? new Set(filtered.map((i) => i.id)) : new Set())
  }

  const isAllChecked = filtered.length > 0 && selected.size === filtered.length

  const handleDelete = () => {
    if (selected.size === 0) return
    onDelete(Array.from(selected))
    setSelected(new Set())
  }

  const handleArchive = () => {
    if (selected.size === 0) return
    onArchive(Array.from(selected))
    setSelected(new Set())
  }

  return (
    <div className="flex flex-col h-full bg-background/50">
      {/* TOOLBAR */}
      <div className="shrink-0 flex items-center justify-between px-4 h-12 border-b border-border/60 bg-background gap-2 select-none">
        <div className="flex items-center gap-1">
          <div className="w-6 h-6 flex items-center justify-center">
            <Checkbox
              className="h-3.5 w-3.5 rounded-[4px]"
              checked={isAllChecked}
              onCheckedChange={(c) => toggleAll(!!c)}
            />
          </div>
          <Separator orientation="vertical" className="h-4 mx-1.5" />
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs gap-1.5 text-muted-foreground hover:bg-muted/80"
            onClick={onRefresh}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Làm mới</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs gap-1.5 text-muted-foreground hover:bg-muted/80"
            onClick={handleArchive}
            disabled={selected.size === 0}
          >
            <Archive className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Lưu trữ</span>
          </Button>
          {selected.size > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs gap-1.5 text-destructive hover:bg-destructive/10 hover:text-destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Xóa ({selected.size})</span>
            </Button>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-muted-foreground hidden sm:inline font-medium">
            {filtered.length} nội dung
          </span>
          <div className="flex items-center border border-border/60 rounded-lg overflow-hidden bg-background">
            <Button variant="ghost" size="icon" className="h-7 w-7 rounded-none hover:bg-muted" disabled>
              <ChevronLeft className="h-3.5 w-3.5" />
            </Button>
            <Separator orientation="vertical" className="h-3" />
            <Button variant="ghost" size="icon" className="h-7 w-7 rounded-none hover:bg-muted" disabled>
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>

      {/* FILTER BAR */}
      <div className="shrink-0 flex items-center gap-1.5 px-4 h-11 border-b border-border/40 bg-muted/20 overflow-x-auto scrollbar-none select-none">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={cn(
              "inline-flex items-center px-3 h-6 rounded-full text-xs font-medium whitespace-nowrap transition-all duration-150",
              filter === f.value
                ? "bg-foreground text-background shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground hover:bg-accent/80"
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* SCROLLABLE LIST */}
      <div className="flex-1 overflow-y-auto divide-y divide-border/30">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground py-12">
            <Inbox className="h-9 w-9 opacity-30 stroke-[1.5]" />
            <p className="text-xs font-medium">Không có nội dung nào</p>
          </div>
        ) : (
          filtered.map((item) => {
            const isChecked = selected.has(item.id)
            const isItemDeleting = deletingIds.has(item.id)
            return (
              <div
                key={item.id}
                onClick={() => !isItemDeleting && onSelect(item.id)}
                className={cn(
                  "group flex items-center gap-3.5 px-4 h-14 cursor-pointer hover:bg-muted/40 transition-colors select-none",
                  isChecked && "bg-muted/30",
                  (isItemDeleting || isDeleting) && "opacity-50 pointer-events-none"
                )}
              >
                <div
                  onClick={(e) => e.stopPropagation()}
                  className="w-5 h-5 flex items-center justify-center"
                >
                  <Checkbox
                    className={cn(
                      "h-3.5 w-3.5 rounded-[4px] transition-all duration-150",
                      "opacity-100 sm:opacity-0 sm:group-hover:opacity-100",
                      isChecked && "sm:opacity-100"
                    )}
                    checked={isChecked}
                    onCheckedChange={(c) => toggleOne(item.id, !!c)}
                    disabled={isItemDeleting}
                  />
                </div>

                <TypeIcon icon={item.icon} />

                <div className="flex-1 min-w-0 flex items-baseline gap-2.5">
                  <span className="text-[13.5px] font-medium text-foreground truncate max-w-[240px] sm:max-w-none">
                    {item.title}
                  </span>
                  <StatusBadge status={item.status} />
                  <span className="text-xs text-muted-foreground truncate hidden md:block font-normal max-w-sm">
                    {item.preview}
                  </span>
                </div>

                <span className="text-[11px] text-muted-foreground/80 font-medium whitespace-nowrap shrink-0">
                  {item.time}
                </span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

// ─── CHAT SIDEBAR TYPES ───
interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  isStreaming?: boolean
}

// ─── CHAT SIDEBAR: Copy Button ───
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <button
      onClick={copy}
      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
      title="Copy"
    >
      {copied
        ? <Check className="h-3 w-3 text-emerald-500" />
        : <Clipboard className="h-3 w-3" />
      }
    </button>
  )
}

// ─── CHAT SIDEBAR: Blinking cursor ───
function StreamingCursor() {
  return (
    <span className="inline-block w-[2px] h-[1em] bg-foreground/70 ml-[1px] align-middle animate-[blink_0.9s_step-end_infinite]" />
  )
}

// ─── CHAT SIDEBAR: Apply button ───
function ApplyButton({ content, onApply }: { content: string; onApply: (c: string) => void }) {
  const [applied, setApplied] = useState(false)
  const handleApply = () => {
    onApply(content)
    setApplied(true)
    setTimeout(() => setApplied(false), 2000)
  }
  return (
    <button
      onClick={handleApply}
      className={cn(
        "text-[11px] font-medium px-2.5 py-1 rounded-md transition-all duration-150",
        applied
          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
          : "bg-primary/10 text-primary hover:bg-primary/20"
      )}
    >
      {applied ? "✓ Đã áp dụng" : "Áp dụng vào bài"}
    </button>
  )
}

// ─── CHAT SIDEBAR: Chat bubble ───
function ChatBubble({
  message,
  onApply,
}: {
  message: ChatMessage
  onApply?: (content: string) => void
}) {
  const isAssistant = message.role === "assistant"

  return (
    <div className={cn("flex gap-2.5", isAssistant ? "items-start" : "items-start flex-row-reverse")}>
      <div className={cn(
        "shrink-0 w-6 h-6 rounded-full flex items-center justify-center mt-0.5",
        isAssistant
          ? "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-400"
          : "bg-muted text-muted-foreground"
      )}>
        {isAssistant ? <Bot className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
      </div>

      <div className={cn("group flex flex-col gap-1.5 max-w-[88%]", !isAssistant && "items-end")}>
        <div className={cn(
          "relative rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed whitespace-pre-wrap",
          isAssistant
            ? "bg-muted/60 dark:bg-muted/40 text-foreground rounded-tl-sm"
            : "bg-primary text-primary-foreground rounded-tr-sm"
        )}>
          {message.content || (message.isStreaming && (
            <span className="text-muted-foreground/50 text-[12px]">Đang viết...</span>
          ))}
          {message.isStreaming && <StreamingCursor />}

          {isAssistant && message.content && !message.isStreaming && (
            <div className="absolute -top-2 right-2">
              <CopyButton text={message.content} />
            </div>
          )}
        </div>

        {/* No apply button — content streams directly into the editor */}
      </div>
    </div>
  )
}

// ─── CHAT SIDEBAR COMPONENT ───
export function ChatSidebar({
  sessionId,
  draftContent,
  onUpdate,
  isOpen,
  onClose,
  onStreamingChange,
  onStreamToken,
  onStreamDone,
}: ChatSidebarProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [showScrollBtn, setShowScrollBtn] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const statusMsgIdRef = useRef<string | null>(null)

  // Single hook instance — forward tokens to parent (DetailView editor)
  const { rewrite, isStreaming, stop, reset } = useMarketingRewrite({
    sessionId,
    draft: draftContent,
    onToken: (token, accumulated) => {
      // Forward every token to DetailView so the editor streams in real-time
      onStreamToken?.(token, accumulated)
    },
    onDone: (finalContent) => {
      // Mark the status bubble as done
      const id = statusMsgIdRef.current
      if (id) {
        setMessages(prev =>
          prev.map(m =>
            m.id === id
              ? { ...m, content: "✓ Đã cập nhật nội dung", isStreaming: false }
              : m
          )
        )
        statusMsgIdRef.current = null
      }
      onStreamDone?.(finalContent)
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50)
    },
  })

  // Notify parent of streaming state
  useEffect(() => {
    onStreamingChange?.(isStreaming)
  }, [isStreaming, onStreamingChange])

  // Reset on close
  useEffect(() => {
    if (!isOpen) {
      stop()
      reset()
      setMessages([])
      setInput("")
      statusMsgIdRef.current = null
    }
  }, [isOpen, stop, reset])

  const handleScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    setShowScrollBtn(el.scrollHeight - el.scrollTop - el.clientHeight > 80)
  }, [])

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isStreaming) return

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text.trim(),
    }
    // Status bubble — short status text only, no content rewrite shown here
    const statusMsgId = crypto.randomUUID()
    const statusMsg: ChatMessage = {
      id: statusMsgId,
      role: "assistant",
      content: "Đang sửa nội dung...",
      isStreaming: true,
    }

    statusMsgIdRef.current = statusMsgId
    setMessages(prev => [...prev, userMsg, statusMsg])
    setInput("")

    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50)
    await rewrite(text.trim())
  }, [isStreaming, rewrite])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  if (!isOpen) return null

  return (
    <div className="w-[320px] border-l border-border/60 bg-background flex flex-col h-full">
      {/* ── HEADER ── */}
      <div className="shrink-0 flex items-center justify-between px-4 h-12 border-b border-border/60">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-violet-100 dark:bg-violet-900/40 flex items-center justify-center">
            <Sparkles className="h-3.5 w-3.5 text-violet-600 dark:text-violet-400" />
          </div>
          <span className="text-sm font-semibold">AI Writer</span>
          {isStreaming && (
            <span className="flex items-center gap-1 text-[10px] text-violet-500 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
              đang viết
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {isStreaming && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-[11px] gap-1 text-muted-foreground hover:text-destructive"
              onClick={stop}
            >
              <StopCircle className="h-3.5 w-3.5" />
              Dừng
            </Button>
          )}
          {messages.length > 0 && !isStreaming && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground"
              onClick={() => { setMessages([]); reset() }}
              title="Xóa cuộc trò chuyện"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* ── MESSAGES ── */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-4"
      >
        {/* Empty state */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center pb-8">
            <div className="w-10 h-10 rounded-2xl bg-violet-50 dark:bg-violet-900/30 flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-violet-500" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">Chỉnh sửa với AI</p>
              <p className="text-[12px] text-muted-foreground mt-1">
                Nhập yêu cầu để AI sửa bài theo ý bạn
              </p>
            </div>
            <div className="w-full space-y-1.5 mt-2">
              {QUICK_PROMPTS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => sendMessage(p.label)}
                  disabled={isStreaming}
                  className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-[12.5px] bg-muted/50 hover:bg-muted text-foreground/80 hover:text-foreground transition-colors"
                >
                  <span className="text-base leading-none">{p.icon}</span>
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message list */}
        {messages.map((msg) => (
          <ChatBubble
            key={msg.id}
            message={msg}
            onApply={msg.role === "assistant" ? onUpdate : undefined}
          />
        ))}

        <div ref={bottomRef} />
      </div>

      {/* Scroll to bottom */}
      {showScrollBtn && (
        <div className="relative">
          <button
            onClick={() => bottomRef.current?.scrollIntoView({ behavior: "smooth" })}
            className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 text-[11px] font-medium text-muted-foreground bg-background border border-border/60 rounded-full px-3 py-1 shadow-sm hover:bg-muted transition-colors z-10"
          >
            <ChevronDown className="h-3 w-3" />
            Cuộn xuống
          </button>
        </div>
      )}

      {/* ── INPUT ── */}
      <div className="shrink-0 border-t border-border/60 p-3">
        {messages.length > 0 && !isStreaming && (
          <div className="flex gap-1.5 mb-2 overflow-x-auto scrollbar-none pb-1">
            {QUICK_PROMPTS.map((p) => (
              <button
                key={p.label}
                onClick={() => sendMessage(p.label)}
                className="shrink-0 text-[11px] whitespace-nowrap px-2.5 py-1 rounded-full bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-colors"
              >
                {p.icon} {p.label}
              </button>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2 bg-muted/40 border border-border/60 rounded-2xl px-3 py-2 focus-within:border-violet-400/60 focus-within:bg-background transition-all">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              e.target.style.height = "auto"
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px"
            }}
            onKeyDown={handleKeyDown}
            placeholder="Nhập yêu cầu sửa bài..."
            disabled={isStreaming}
            rows={1}
            className="flex-1 resize-none border-0 bg-transparent p-0 text-[13px] placeholder:text-muted-foreground/60 focus-visible:ring-0 focus-visible:ring-offset-0 min-h-[20px] max-h-[120px] leading-relaxed"
          />
          <Button
            size="icon"
            disabled={!input.trim() || isStreaming}
            onClick={() => sendMessage(input)}
            className={cn(
              "h-7 w-7 shrink-0 rounded-xl transition-all",
              input.trim() && !isStreaming
                ? "bg-violet-600 hover:bg-violet-700 text-white shadow-sm"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            )}
          >
            <Send className="h-3.5 w-3.5" />
          </Button>
        </div>
        <p className="text-[10px] text-muted-foreground/60 mt-1.5 text-center">
          Enter để gửi · Shift+Enter xuống dòng
        </p>
      </div>
    </div>
  )
}

// ─── VERSION HISTORY DRAWER ───
function VersionHistory({
  sessionId,
  isOpen,
  onClose,
  currentContent,
  onRestore,
}: {
  sessionId: string
  isOpen: boolean
  onClose: () => void
  currentContent: string
  onRestore: (content: string) => void
}) {
  const { data, isLoading } = useQuery<VersionHistoryResponse>({
    queryKey: ["versions", sessionId],
    queryFn: () => api(`/marketing/${sessionId}/versions`),
    enabled: isOpen,
  })

  if (!isOpen) return null

  return (
    <div className="w-72 border-l border-border/60 bg-muted/10 flex flex-col h-full">
      <div className="shrink-0 flex items-center justify-between px-4 h-12 border-b border-border/60">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Lịch sử</span>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
          <XCircle className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {isLoading ? (
          <div className="flex justify-center py-4">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            <div className="bg-background border border-border/60 rounded-lg p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-medium">Hiện tại</span>
                <Badge variant="outline" className="text-[10px] h-5">Current</Badge>
              </div>
              <p className="text-[11px] text-muted-foreground line-clamp-2">{currentContent.slice(0, 100)}...</p>
            </div>

            {data?.versions?.map((v, i) => (
              <div key={i} className="bg-background border border-border/40 rounded-lg p-3 hover:border-border/80 transition-colors">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] font-medium">Phiên bản {v.version}</span>
                  <span className="text-[10px] text-muted-foreground">{v.action}</span>
                </div>
                {v.instruction && (
                  <p className="text-[10px] text-blue-600 dark:text-blue-400 mb-1">"{v.instruction}"</p>
                )}
                <p className="text-[11px] text-muted-foreground line-clamp-2">{v.content.slice(0, 100)}...</p>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-[10px] mt-1 px-2"
                  onClick={() => onRestore(v.content)}
                >
                  <RotateCcw className="h-3 w-3 mr-1" />
                  Khôi phục
                </Button>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}

// ─── DETAIL VIEW ───
function DetailView({
  item,
  onClose,
  onDelete,
  onArchive,
  isLoading,
  onUpdate,
}: {
  item: ContentItem
  onClose: () => void
  onDelete: (id: string) => void
  onArchive: (id: string) => void
  isLoading: boolean
  onUpdate?: (item: ContentItem) => void
}) {
  const [chatOpen, setChatOpen] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editContent, setEditContent] = useState(item.content || "")
  const [isStreaming, setIsStreaming] = useState(false)
  // Holds the live-streaming rewrite content — replaces editContent token by token
  const [streamingContent, setStreamingContent] = useState<string | null>(null)
  // Track whether user has made local edits — if so, don't let server refetch overwrite
  const hasLocalEditRef = useRef(false)
  const queryClient = useQueryClient()

  // Only sync from server on first load (item.id change), never during/after local edits
  const prevItemIdRef = useRef(item.id)
  useEffect(() => {
    if (prevItemIdRef.current !== item.id) {
      // Navigated to a different item — reset everything
      prevItemIdRef.current = item.id
      hasLocalEditRef.current = false
      setEditContent(item.content || "")
      setStreamingContent(null)
    } else if (!hasLocalEditRef.current) {
      // Same item, no local edits yet — safe to sync from server (e.g. initial load)
      setEditContent(item.content || "")
    }
    // If hasLocalEditRef.current === true: user has streamed/edited locally, ignore server data
  }, [item.id, item.content])

  // Resume mutation (approve/reject)
  const resumeMutation = useMutation({
    mutationFn: (params: ResumeRequest) =>
      api<ResumeResponse>(`/marketing/${item.id}/resume`, {
        method: "POST",
        body: JSON.stringify(params),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketing-sessions"] })
    },
  })

  // Chat Edit mutation
  const chatEditMutation = useMutation({
    mutationFn: (instruction: string) =>
      api<ChatEditResponse>("/marketing/chat/edit", {
        method: "POST",
        body: JSON.stringify({
          draft: item.content || "",
          instruction,
        }),
      }),
    onSuccess: (data) => {
      handleContentUpdate(data.draft)
      queryClient.invalidateQueries({ queryKey: ["marketing-sessions"] })
      setEditMode(false)
      setEditContent("")
    },
  })

  // Publish mutation
  const publishMutation = useMutation({
    mutationFn: () =>
      api(`/marketing/${item.id}/publish`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketing-sessions"] })
    },
  })

  const isPaused = item.backendStatus === "paused"
  const isCompleted = item.backendStatus === "completed"
  const isApproved = item.approved

  const handleContentUpdate = useCallback((newContent: string) => {
    hasLocalEditRef.current = true  // prevent server refetch from overwriting local state
    setEditContent(newContent)
    // Just invalidate in background for list refresh — don't pass content up
    // (server content will be stale until next explicit save, that's fine)
    onUpdate?.({ ...item, content: newContent })
  }, [item, onUpdate])

  return (
    <div className="flex flex-col h-full bg-background animate-in fade-in-40 duration-200">
      {/* TOOLBAR */}
      <div className="shrink-0 flex items-center justify-between px-4 h-12 border-b border-border/60 bg-background gap-2 select-none">
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg hover:bg-muted" onClick={onClose}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <Separator orientation="vertical" className="h-4 mx-2" />

          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs gap-1.5 text-muted-foreground hover:bg-muted/80"
            onClick={() => onArchive(item.id)}
            disabled={isLoading}
          >
            <Archive className="h-3.5 w-3.5" />
            <span>Lưu kho</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs gap-1.5 text-destructive hover:bg-destructive/10 hover:text-destructive"
            onClick={() => onDelete(item.id)}
            disabled={isLoading}
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>Xóa</span>
          </Button>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge status={item.status} />
          <Separator orientation="vertical" className="h-4 mx-1" />

          {isPaused && (
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs gap-1.5 text-destructive border-destructive/30 hover:bg-destructive/10"
                onClick={() => resumeMutation.mutate({ action: "reject" })}
                disabled={resumeMutation.isPending}
              >
                <XCircle className="h-3.5 w-3.5" />
                Từ chối
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs gap-1.5"
                onClick={() => setChatOpen(true)}
              >
                <MessageSquare className="h-3.5 w-3.5" />
                Sửa bài
              </Button>
              <Button
                size="sm"
                className="h-8 text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
                onClick={() => resumeMutation.mutate({ action: "approve" })}
                disabled={resumeMutation.isPending}
              >
                {resumeMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                )}
                Duyệt
              </Button>
            </div>
          )}

          {isCompleted && isApproved && (
            <Button
              size="sm"
              className="h-8 text-xs gap-1.5"
              onClick={() => publishMutation.mutate()}
              disabled={publishMutation.isPending}
            >
              {publishMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5" />
              )}
              Xuất bản
            </Button>
          )}

          <Button
            variant="ghost"
            size="icon"
            className={cn("h-8 w-8", chatOpen && "bg-muted")}
            onClick={() => setChatOpen(!chatOpen)}
            title="Chat AI"
          >
            <MessageSquare className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className={cn("h-8 w-8", historyOpen && "bg-muted")}
            onClick={() => setHistoryOpen(!historyOpen)}
            title="Lịch sử"
          >
            <History className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Edit Mode banner */}
      {editMode && (
        <div className="shrink-0 px-4 py-3 border-b border-border/60 bg-blue-50/50 dark:bg-blue-950/20">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-4 w-4 text-blue-600" />
            <span className="text-xs font-medium text-blue-700 dark:text-blue-400">AI Chat - Nhập yêu cầu sửa:</span>
          </div>
          <Textarea
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            className="min-h-[80px] text-xs mb-2"
            placeholder="VD: Viết hay hơn, thêm CTA, ngắn gọn hơn..."
          />
          <div className="flex gap-2 justify-end">
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setEditMode(false)}>
              Hủy
            </Button>
            <Button
              size="sm"
              className="h-7 text-xs gap-1.5"
              onClick={() => chatEditMutation.mutate(editContent)}
              disabled={chatEditMutation.isPending || !editContent.trim()}
            >
              {chatEditMutation.isPending
                ? <Loader2 className="h-3 w-3 animate-spin" />
                : <Send className="h-3 w-3" />
              }
              Gửi AI sửa
            </Button>
          </div>
        </div>
      )}

      {/* MAIN BODY WITH SIDE PANELS */}
      <div className="flex-1 flex overflow-hidden">
        {/* Content */}
        <div className="flex-1 overflow-y-auto bg-background">
          <div className="max-w-2xl mx-auto px-6 sm:px-8 py-8">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <div className="relative">
                {/* Streaming indicator — subtle, doesn't block content */}
                {isStreaming && (
                  <div className="flex items-center gap-1.5 mb-3 text-violet-500 text-[11px] font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
                    AI đang viết...
                  </div>
                )}
                <Message from="assistant">
                  <MessageContent>
                    <MessageResponse>
                      {/* Show live streaming content token-by-token; fall back to saved content */}
                      {streamingContent ?? editContent}
                      {isStreaming && (
                        <span className="inline-block w-[2px] h-[1em] bg-foreground/60 ml-[1px] align-middle animate-[blink_0.9s_step-end_infinite]" />
                      )}
                    </MessageResponse>
                  </MessageContent>
                </Message>
              </div>
            )}
          </div>
        </div>

        {/* Chat Sidebar */}
        <ChatSidebar
          sessionId={item.id}
          draftContent={editContent}
          onUpdate={handleContentUpdate}
          isOpen={chatOpen}
          onClose={() => setChatOpen(false)}
          onStreamingChange={(streaming) => {
            setIsStreaming(streaming)
            // Only clear streaming buffer when idle AND no pending onStreamDone
            // onStreamDone handles the actual commit + clear
          }}
          onStreamToken={(_token, accumulated) => {
            // Stream each token into the editor in real-time
            setStreamingContent(accumulated)
          }}
          onStreamDone={(finalContent) => {
            // 1. Commit final content to editContent
            handleContentUpdate(finalContent)
            // 2. Clear streaming buffer (editor now shows editContent)
            setStreamingContent(null)
            // 3. isStreaming will be set false by onStreamingChange shortly after
          }}
        />

        {/* Version History */}
        <VersionHistory
          sessionId={item.id}
          isOpen={historyOpen}
          onClose={() => setHistoryOpen(false)}
          currentContent={item.content || ""}
          onRestore={(content) => handleContentUpdate(content)}
        />
      </div>
    </div>
  )
}

// ─── ERROR STATE ───
function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-[50vh] gap-4 text-muted-foreground">
      <AlertCircle className="h-10 w-10 text-destructive/60" />
      <div className="text-center">
        <p className="text-sm font-medium text-destructive mb-1">Đã xảy ra lỗi</p>
        <p className="text-xs max-w-xs">{message}</p>
      </div>
      <Button variant="outline" size="sm" onClick={onRetry} className="gap-1.5">
        <RefreshCw className="h-3.5 w-3.5" />
        Thử lại
      </Button>
    </div>
  )
}

// ─── ROUTE ───
export const Route = createFileRoute("/home/index copy")({
  validateSearch: (search: Record<string, unknown>) => ({
    contentId: (search.contentId as string) || undefined,
  }),
  component: ContentPage,
})

// ─── PAGE ───
function ContentPage() {
  const search = Route.useSearch()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const {
    data: sessionsData,
    isLoading,
    error,
    refetch,
  } = useQuery<SessionListResponse>({
    queryKey: ["marketing-sessions"],
    queryFn: () => api("/marketing/sessions?limit=50&offset=0"),
    refetchInterval: 10000,
    retry: 2,
  })

  const [itemOverrides, setItemOverrides] = useState<Record<string, Partial<ContentItem>>>({})

  const items = (sessionsData?.items || []).map((s) => {
    const mapped = mapSessionToContentItem(s)
    // Apply any local overrides (e.g. content updated by AI rewrite)
    return itemOverrides[mapped.id] ? { ...mapped, ...itemOverrides[mapped.id] } : mapped
  })
  const activeItem = items.find((i) => i.id === search.contentId)

  const setId = useCallback(
    (id: string | undefined) => {
      navigate({ search: (prev) => ({ ...prev, contentId: id }) })
    },
    [navigate]
  )

  const deleteMutation = useMutation({
    mutationFn: (sessionId: string) => api(`/marketing/session/${sessionId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketing-sessions"] })
      if (search.contentId) setId(undefined)
    },
  })

  const archiveMutation = useMutation({
    mutationFn: (sessionId: string) =>
      api(`/marketing/${sessionId}/resume`, {
        method: "POST",
        body: JSON.stringify({ action: "reject" }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketing-sessions"] })
    },
  })

  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set())

  const handleDelete = useCallback(async (ids: string[]) => {
    setDeletingIds(new Set(ids))
    try {
      await Promise.all(ids.map((id) => deleteMutation.mutateAsync(id)))
    } finally {
      setDeletingIds(new Set())
    }
  }, [deleteMutation])

  const handleArchive = useCallback(async (ids: string[]) => {
    setDeletingIds(new Set(ids))
    try {
      await Promise.all(ids.map((id) => archiveMutation.mutateAsync(id)))
    } finally {
      setDeletingIds(new Set())
    }
  }, [archiveMutation])

  const handleDeleteSingle = useCallback((id: string) => handleDelete([id]), [handleDelete])
  const handleArchiveSingle = useCallback((id: string) => handleArchive([id]), [handleArchive])

  const handleUpdateItem = useCallback((updatedItem: ContentItem) => {
    // Cache content override locally so activeItem reflects it immediately
    // Server will catch up on next refetch interval
    setItemOverrides(prev => ({
      ...prev,
      [updatedItem.id]: { content: updatedItem.content },
    }))
    queryClient.invalidateQueries({ queryKey: ["marketing-sessions"] })
  }, [queryClient])

  if (isLoading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground/80" />
      </div>
    )
  }

  if (error) {
    return (
      <ErrorState
        message={error instanceof Error ? error.message : "Không thể tải danh sách nội dung"}
        onRetry={() => refetch()}
      />
    )
  }

  return (
    <div className="h-[calc(100vh-4rem)] overflow-hidden bg-background relative">
      <div className={cn("h-full", activeItem ? "hidden" : "block")}>
        <ListView
          items={items}
          onSelect={(id) => setId(id)}
          onRefresh={() => refetch()}
          onDelete={handleDelete}
          onArchive={handleArchive}
          isDeleting={deleteMutation.isPending || archiveMutation.isPending}
          deletingIds={deletingIds}
        />
      </div>

      {activeItem && (
        <div className="absolute inset-0 z-10 h-full w-full bg-background">
          <DetailView
            item={activeItem}
            onClose={() => setId(undefined)}
            onDelete={handleDeleteSingle}
            onArchive={handleArchiveSingle}
            isLoading={deleteMutation.isPending || archiveMutation.isPending}
            onUpdate={handleUpdateItem}
          />
        </div>
      )}
    </div>
  )
}