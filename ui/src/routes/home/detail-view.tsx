"use client"

import { useState, useRef, useCallback, useEffect, useSyncExternalStore } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import {
  Trash2, Archive, ArrowLeft,
  Loader2, CheckCircle2, XCircle, MessageSquare,
  Send, History, Sparkles,
  RotateCcw,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Message, MessageContent, MessageResponse } from "@/components/ai-elements/message"
import { Badge } from "@/components/ui/badge"
import {
  api,
  type ContentItem,
  type VersionHistoryResponse,
  type ChatEditResponse,
  type ResumeRequest,
  type ResumeResponse,
  STATUS_LABELS,
  STATUS_STYLES,
} from "./types"
import { ChatSidebar } from "./chat-sidebar"

// ─── SHARED COMPONENTS ───
export function StatusBadge({ status }: { status: ContentItem["status"] }) {
  return (
    <Badge variant="outline" className={cn("text-[11px] font-medium px-2 py-0.5 rounded-full select-none", STATUS_STYLES[status])}>
      {STATUS_LABELS[status]}
    </Badge>
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
export function DetailView({
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

  // 🌟 1. BỔ SUNG: State để lưu ID cuộc trò chuyện từ Backend trả về
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)

  // External store — bypasses React batching, updates UI on every token
  const streamStoreRef = useRef({
    content: null as string | null,
    listeners: new Set<() => void>(),
    set(val: string | null) {
      this.content = val;
      this.listeners.forEach(fn => fn());
    },
  });
  const streamingContent = useSyncExternalStore(
    (cb) => {
      streamStoreRef.current.listeners.add(cb);
      return () => streamStoreRef.current.listeners.delete(cb);
    },
    () => streamStoreRef.current.content,
    () => null,
  );

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
      setActiveConversationId(null) // Reset conversation id khi chuyển bài viết khác
    } else if (!hasLocalEditRef.current) {
      // Same item, no local edits yet — safe to sync from server (e.g. initial load)
      setEditContent(item.content || "")
    }
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

  // 🌟 2. BỔ SUNG: Mutation gọi API POST sinh ID cuộc trò chuyện mới
  const createConversationMutation = useMutation({
    mutationFn: async () => {
      // Đi thẳng tới endpoint FastAPI dựa trên Curl của bạn
      const res = await fetch("http://localhost:8000/api/v1/chat/conversations", {
        method: "POST",
        headers: { "accept": "application/json" },
        body: ""
      })
      if (!res.ok) throw new Error("Không thể khởi tạo cuộc hội thoại AI")
      return res.json() as Promise<{ id: string; title: string }>
    },
    onSuccess: (data) => {
      setActiveConversationId(data.id)
      setChatOpen(true) // Tạo thành công thì mở sidebar chat luôn
    },
  })

  const isPaused = item.backendStatus === "paused"
  const isCompleted = item.backendStatus === "completed"
  const isApproved = item.approved

  const handleContentUpdate = useCallback((newContent: string) => {
    hasLocalEditRef.current = true  // prevent server refetch from overwriting local state
    setEditContent(newContent)
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
                disabled={createConversationMutation.isPending}
                onClick={() => {
                  if (activeConversationId) {
                    setChatOpen(true)
                  } else {
                    createConversationMutation.mutate()
                  }
                }}
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

          {/* 🌟 3. SỬA ĐỔI: Logic Click của nút mở Chat AI ở Toolbar */}
          <Button
            variant="ghost"
            size="icon"
            className={cn("h-8 w-8", chatOpen && "bg-muted")}
            disabled={createConversationMutation.isPending}
            onClick={() => {
              if (chatOpen) {
                setChatOpen(false)
              } else if (activeConversationId) {
                setChatOpen(true)
              } else {
                // Nếu chưa có ID hội thoại AI, kích hoạt gọi API POST tạo mới
                createConversationMutation.mutate()
              }
            }}
            title="Chat AI"
          >
            {createConversationMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin text-violet-600" />
            ) : (
              <MessageSquare className="h-4 w-4" />
            )}
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
                <div className="prose dark:prose-invert max-w-none">
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">
                    {streamingContent ?? editContent}
                    {isStreaming && (
                      <span className="inline-block w-[2px] h-[1em] bg-foreground/60 ml-[1px] align-middle animate-[blink_0.9s_step-end_infinite]" />
                    )}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 🌟 4. SỬA ĐỔI: Chỉ render ChatSidebar khi ĐÃ CÓ activeConversationId */}
        {activeConversationId && (
          <ChatSidebar
            conversationId={activeConversationId}
            isOpen={chatOpen}
            onClose={() => setChatOpen(false)}
            onApply={(finalContent) => {
              handleContentUpdate(finalContent)
            }}
            onStreamingChange={(streaming) => {
              setIsStreaming(streaming)
            }}
          />
        )}

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